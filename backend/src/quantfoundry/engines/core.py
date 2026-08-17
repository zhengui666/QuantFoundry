"""Deterministic local data, factor, simulation and validation engines."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import duckdb
import pyarrow as pa
import pyarrow.csv as arrow_csv
import pyarrow.parquet as parquet


class EngineInputError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatasetBundle:
    rows: list[dict[str, Any]]
    provider_id: str
    adapter_key: str
    adapter_version: str
    timezone: str
    calendar: str
    schema_sha256: str
    pit_policy: str
    corporate_action_policy: str
    survivorship_policy: str


@dataclass(frozen=True)
class CostModel:
    cost_model_id: str
    version: int
    commission_bps: float
    slippage_bps: float


@dataclass(frozen=True)
class ValidationPolicy:
    policy_id: str
    version: int
    validation_min_observations: int
    validation_min_sharpe: float
    validation_max_drawdown_floor: float
    holdout_min_observations: int
    holdout_min_total_return: float
    holdout_min_sharpe: float
    holdout_max_drawdown_floor: float
    multiple_testing_max_evaluations: int
    data_min_rows: int
    data_min_symbols: int
    data_max_late_release_fraction: float


def _parse_timestamp(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise EngineInputError(f"invalid {field}: {value}") from error
    else:
        raise EngineInputError(f"invalid {field}")
    if parsed.tzinfo is None:
        raise EngineInputError(f"{field} must include an explicit timezone")
    return parsed.astimezone(UTC)


def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise EngineInputError(f"invalid {field}")


def _dataset_paths(dataset_id: str) -> tuple[Path, Path]:
    root_value = os.getenv("QF_DATASET_DIR")
    if not root_value:
        raise EngineInputError("QF_DATASET_DIR is not configured")
    root = Path(root_value).resolve()
    candidates = [root / f"{dataset_id}.parquet", root / f"{dataset_id}.csv"]
    source = next(
        (candidate.resolve() for candidate in candidates if candidate.is_file()), None
    )
    metadata = (root / f"{dataset_id}.metadata.json").resolve()
    if source is None or root not in source.parents or root not in metadata.parents:
        raise EngineInputError(f"dataset is unavailable: {dataset_id}")
    if not metadata.is_file():
        raise EngineInputError(f"dataset metadata is unavailable: {dataset_id}")
    return source, metadata


def _read_table(path: Path) -> pa.Table:
    try:
        table = (
            parquet.read_table(path)
            if path.suffix == ".parquet"
            else arrow_csv.read_csv(path)
        )
    except (OSError, pa.ArrowException) as error:
        raise EngineInputError(f"dataset cannot be decoded: {path.name}") from error
    required = {
        "event_time",
        "available_at",
        "symbol",
        "close",
        "benchmark_close",
        "partition",
    }
    optional = {"split_factor", "dividend", "in_universe", "sector"}
    if not required.issubset(table.column_names) or not set(table.column_names) <= (
        required | optional
    ):
        raise EngineInputError(
            "dataset schema mismatch; required canonical fields or supported "
            f"corporate-action/universe fields expected, got {sorted(table.column_names)}"
        )
    connection = duckdb.connect(database=":memory:")
    try:
        relation = connection.from_arrow(table)
        return relation.order("event_time, symbol").arrow().read_all()
    except duckdb.Error as error:
        raise EngineInputError("dataset cannot be normalized") from error
    finally:
        connection.close()


def load_dataset(dataset_id: str) -> DatasetBundle:
    source, metadata_path = _dataset_paths(dataset_id)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EngineInputError("dataset metadata cannot be decoded") from error
    required_metadata = {
        "provider_id",
        "adapter_key",
        "adapter_version",
        "timezone",
        "calendar",
    }
    policy_metadata = {
        "pit_policy",
        "corporate_action_policy",
        "survivorship_policy",
    }
    if not isinstance(metadata, dict) or frozenset(metadata) not in {
        frozenset(required_metadata),
        frozenset(required_metadata | policy_metadata),
    }:
        raise EngineInputError("dataset metadata schema mismatch")
    if not policy_metadata.issubset(metadata):
        if metadata.get("provider_id") != "LOCAL_DETERMINISTIC":
            raise EngineInputError("production dataset policy metadata is required")
        metadata.update(
            {
                "pit_policy": "AVAILABLE_AT_STRICT_V1",
                "corporate_action_policy": "RAW_PRICE_SPLIT_DIVIDEND_V1",
                "survivorship_policy": "POINT_IN_TIME_MEMBERSHIP_V1",
            }
        )
    try:
        timezone = ZoneInfo(str(metadata["timezone"]))
    except ZoneInfoNotFoundError as error:
        raise EngineInputError("dataset timezone is unknown") from error
    calendar = str(metadata["calendar"])
    if calendar not in {"WEEKDAY", "24X7"}:
        raise EngineInputError("unsupported dataset calendar")
    table = _read_table(source)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in table.to_pylist():
        event_time = _parse_timestamp(raw["event_time"], "event_time")
        available_at = _parse_timestamp(raw["available_at"], "available_at")
        if available_at < event_time:
            raise EngineInputError("available_at cannot precede event_time")
        symbol = str(raw["symbol"])
        partition = str(raw["partition"])
        try:
            close = float(raw["close"])
            benchmark_close = float(raw["benchmark_close"])
            split_factor = float(
                1.0 if raw.get("split_factor") is None else raw["split_factor"]
            )
            dividend = float(0.0 if raw.get("dividend") is None else raw["dividend"])
        except (TypeError, ValueError) as error:
            raise EngineInputError("market prices must be numeric") from error
        local_date = event_time.astimezone(timezone).date().isoformat()
        if calendar == "WEEKDAY" and event_time.astimezone(timezone).weekday() >= 5:
            raise EngineInputError(f"off-calendar market row: {local_date}")
        if partition not in {"RESEARCH", "VALIDATION", "HOLDOUT"}:
            raise EngineInputError(f"invalid dataset partition: {partition}")
        if not symbol or not all(
            math.isfinite(value) and value > 0
            for value in (close, benchmark_close, split_factor)
        ):
            raise EngineInputError("market row symbol/price is invalid")
        if not math.isfinite(dividend) or dividend < 0:
            raise EngineInputError("market row dividend is invalid")
        key = (local_date, symbol)
        if key in seen:
            raise EngineInputError(f"duplicate market row: {key}")
        seen.add(key)
        rows.append(
            {
                "event_time": event_time.isoformat().replace("+00:00", "Z"),
                "available_at": available_at.isoformat().replace("+00:00", "Z"),
                "date": local_date,
                "symbol": symbol,
                "close": close,
                "benchmark_close": benchmark_close,
                "partition": partition,
                "split_factor": split_factor,
                "dividend": dividend,
                "in_universe": (
                    True
                    if raw.get("in_universe") is None
                    else _parse_bool(raw["in_universe"], "in_universe")
                ),
                "sector": str(raw.get("sector") or "UNCLASSIFIED"),
            }
        )
    if not rows:
        raise EngineInputError("dataset must contain at least one market row")
    schema_value = [
        ("event_time", "timestamp[us,UTC]"),
        ("available_at", "timestamp[us,UTC]"),
        ("symbol", "string"),
        ("close", "float64"),
        ("benchmark_close", "float64"),
        ("partition", "enum[RESEARCH,VALIDATION,HOLDOUT]"),
        ("split_factor", "float64"),
        ("dividend", "float64"),
        ("in_universe", "bool"),
        ("sector", "string"),
    ]
    schema_sha256 = hashlib.sha256(
        json.dumps(schema_value, separators=(",", ":")).encode()
    ).hexdigest()
    return DatasetBundle(
        rows=rows,
        provider_id=str(metadata["provider_id"]),
        adapter_key=str(metadata["adapter_key"]),
        adapter_version=str(metadata["adapter_version"]),
        timezone=str(metadata["timezone"]),
        calendar=calendar,
        schema_sha256=schema_sha256,
        pit_policy=str(metadata["pit_policy"]),
        corporate_action_policy=str(metadata["corporate_action_policy"]),
        survivorship_policy=str(metadata["survivorship_policy"]),
    )


def load_cost_model(cost_model_id: str) -> CostModel:
    root_value = os.getenv("QF_COST_MODEL_DIR")
    if not root_value:
        raise EngineInputError("QF_COST_MODEL_DIR is not configured")
    root = Path(root_value).resolve()
    path = (root / f"{cost_model_id.replace(':', '_')}.json").resolve()
    if root not in path.parents or not path.is_file():
        raise EngineInputError(f"cost model is unavailable: {cost_model_id}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EngineInputError("cost model cannot be decoded") from error
    if not isinstance(value, dict) or set(value) != {
        "cost_model_id",
        "version",
        "commission_bps",
        "slippage_bps",
    }:
        raise EngineInputError("cost model schema mismatch")
    if value["cost_model_id"] != cost_model_id:
        raise EngineInputError("cost model identity mismatch")
    if not isinstance(value["version"], int) or isinstance(value["version"], bool):
        raise EngineInputError("cost model version must be an integer")
    try:
        commission = float(value["commission_bps"])
        slippage = float(value["slippage_bps"])
    except (TypeError, ValueError) as error:
        raise EngineInputError("cost model values must be numeric") from error
    if not all(math.isfinite(item) and item >= 0 for item in (commission, slippage)):
        raise EngineInputError("cost model rates must be finite and non-negative")
    version = value["version"]
    if version < 1:
        raise EngineInputError("cost model version must be positive")
    return CostModel(cost_model_id, version, commission, slippage)


def load_validation_policy(policy_id: str) -> ValidationPolicy:
    root_value = os.getenv("QF_POLICY_DIR")
    if not root_value:
        raise EngineInputError("QF_POLICY_DIR is not configured")
    root = Path(root_value).resolve()
    path = (root / f"{policy_id.replace(':', '_')}.json").resolve()
    if root not in path.parents or not path.is_file():
        raise EngineInputError(f"validation policy is unavailable: {policy_id}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EngineInputError("validation policy cannot be decoded") from error
    expected = {
        "policy_id",
        "version",
        "validation",
        "holdout",
        "multiple_testing_max_evaluations",
        "data_quality",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise EngineInputError("validation policy schema mismatch")
    if value["policy_id"] != policy_id:
        raise EngineInputError("validation policy identity mismatch")
    validation = value["validation"]
    holdout = value["holdout"]
    data_quality = value["data_quality"]
    if not all(isinstance(item, dict) for item in (validation, holdout, data_quality)):
        raise EngineInputError("validation policy sections must be objects")
    integer_values = (
        value.get("version"),
        validation.get("min_observations"),
        holdout.get("min_observations"),
        value.get("multiple_testing_max_evaluations"),
        data_quality.get("min_rows"),
        data_quality.get("min_symbols"),
    )
    if any(
        not isinstance(item, int) or isinstance(item, bool) for item in integer_values
    ):
        raise EngineInputError("validation policy integer values are invalid")
    try:
        policy = ValidationPolicy(
            policy_id=policy_id,
            version=value["version"],
            validation_min_observations=validation["min_observations"],
            validation_min_sharpe=float(validation["min_sharpe"]),
            validation_max_drawdown_floor=float(validation["max_drawdown_floor"]),
            holdout_min_observations=holdout["min_observations"],
            holdout_min_total_return=float(holdout["min_total_return"]),
            holdout_min_sharpe=float(holdout["min_sharpe"]),
            holdout_max_drawdown_floor=float(holdout["max_drawdown_floor"]),
            multiple_testing_max_evaluations=value["multiple_testing_max_evaluations"],
            data_min_rows=data_quality["min_rows"],
            data_min_symbols=data_quality["min_symbols"],
            data_max_late_release_fraction=float(
                data_quality["max_late_release_fraction"]
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EngineInputError("validation policy values are invalid") from error
    if (
        policy.version < 1
        or policy.validation_min_observations < 1
        or policy.holdout_min_observations < 1
        or policy.multiple_testing_max_evaluations < 1
        or policy.data_min_rows < 1
        or policy.data_min_symbols < 1
        or not 0 <= policy.data_max_late_release_fraction <= 1
        or not -1 <= policy.validation_max_drawdown_floor <= 0
        or not -1 <= policy.holdout_max_drawdown_floor <= 0
        or not all(
            math.isfinite(value)
            for value in (
                policy.validation_min_sharpe,
                policy.holdout_min_total_return,
                policy.holdout_min_sharpe,
                policy.data_max_late_release_fraction,
            )
        )
    ):
        raise EngineInputError("validation policy thresholds are out of range")
    return policy


def data_quality_profile(
    bundle: DatasetBundle, policy: ValidationPolicy
) -> dict[str, Any]:
    symbols = {row["symbol"] for row in bundle.rows}
    timezone = ZoneInfo(bundle.timezone)
    late_release_count = sum(
        1
        for row in bundle.rows
        if _parse_timestamp(row["available_at"], "available_at")
        .astimezone(timezone)
        .date()
        .isoformat()
        > row["date"]
    )
    late_fraction = late_release_count / len(bundle.rows)
    failures = []
    if len(bundle.rows) < policy.data_min_rows:
        failures.append("ROW_COUNT_BELOW_POLICY")
    if len(symbols) < policy.data_min_symbols:
        failures.append("SYMBOL_COUNT_BELOW_POLICY")
    if late_fraction > policy.data_max_late_release_fraction:
        failures.append("LATE_RELEASE_FRACTION_ABOVE_POLICY")
    return {
        "state": "PASS" if not failures else "FAIL",
        "row_count": len(bundle.rows),
        "symbol_count": len(symbols),
        "late_release_count": late_release_count,
        "late_release_fraction": late_fraction,
        "failures": failures,
        "policy": {"id": policy.policy_id, "version": policy.version},
    }


def holdout_policy_result(
    metrics: dict[str, Any], policy: ValidationPolicy
) -> tuple[str, list[str]]:
    checks = {
        "MIN_OBSERVATIONS": int(metrics["observations"])
        >= policy.holdout_min_observations,
        "MIN_TOTAL_RETURN": float(metrics["total_return"])
        >= policy.holdout_min_total_return,
        "MIN_SHARPE": float(metrics["sharpe"]) >= policy.holdout_min_sharpe,
        "MAX_DRAWDOWN": float(metrics["maximum_drawdown"])
        >= policy.holdout_max_drawdown_floor,
    }
    failures = [key for key, passed in checks.items() if not passed]
    return ("PASS" if not failures else "FAIL", failures)


def snapshot_content_sha256(
    dataset_id: str,
    bundle: DatasetBundle,
    public_rows: list[dict[str, Any]],
    holdout_rows: list[dict[str, Any]],
) -> str:
    """Hash normalized rows plus the data identity that gives them meaning."""
    value = {
        "dataset_id": dataset_id,
        "schema_sha256": bundle.schema_sha256,
        "provider": {
            "provider_id": bundle.provider_id,
            "adapter_key": bundle.adapter_key,
            "adapter_version": bundle.adapter_version,
            "timezone": bundle.timezone,
            "calendar": bundle.calendar,
            "pit_policy": bundle.pit_policy,
            "corporate_action_policy": bundle.corporate_action_policy,
            "survivorship_policy": bundle.survivorship_policy,
        },
        "public_rows": public_rows,
        "holdout_rows": holdout_rows,
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def snapshot_rows(
    bundle: DatasetBundle,
    start: str,
    end: str,
    as_of_time: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    as_of = _parse_timestamp(as_of_time, "as_of_time")
    selected = [
        row
        for row in bundle.rows
        if start <= row["date"] <= end
        and _parse_timestamp(row["available_at"], "available_at") <= as_of
    ]
    public = [row for row in selected if row["partition"] != "HOLDOUT"]
    protected = [row for row in selected if row["partition"] == "HOLDOUT"]
    if not public:
        raise EngineInputError(
            "snapshot contains no PIT-visible research/validation rows"
        )
    return public, protected


def date_range_rows(
    rows: list[dict[str, Any]], start: str, end: str, partition: str | None = None
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if start <= row["date"] <= end
        and (partition is None or row["partition"] == partition)
    ]
    if not selected:
        raise EngineInputError("requested engine date range contains no rows")
    return selected


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(left) != len(right):
        raise EngineInputError("correlation requires at least two paired observations")
    left_mean, right_mean = statistics.fmean(left), statistics.fmean(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return numerator / denominator if denominator else 0.0


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2
        for index in order[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def _adjusted_price_map(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Return split-adjusted total-return prices without resetting action state."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["symbol"]].append(row)
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for symbol, history in grouped.items():
        adjusted_level: float | None = None
        previous_close: float | None = None
        for row in sorted(history, key=lambda item: item["date"]):
            close = float(row["close"])
            split_factor = float(row.get("split_factor", 1.0))
            dividend = float(row.get("dividend", 0.0))
            if previous_close is None:
                price = close + dividend
            else:
                gross_return = (close + dividend) * split_factor / previous_close
                if not math.isfinite(gross_return) or gross_return <= 0:
                    raise EngineInputError("adjusted market return is invalid")
                price = (adjusted_level or previous_close) * gross_return
            if not math.isfinite(price) or price <= 0:
                raise EngineInputError("adjusted market price is invalid")
            result[row["date"]][symbol] = price
            adjusted_level = price
            previous_close = close
    return result


def compute_factor_rows(
    rows: list[dict[str, Any]],
    expression: str,
    parameters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate the versioned P0 formula allowlist; arbitrary code is forbidden."""

    resolved = expression
    for key, value in (parameters or {}).items():
        resolved = resolved.replace("{" + key + "}", value)
    if resolved == "close":
        return [{**row, "factor_score": float(row["close"])} for row in rows]
    match = re.fullmatch(r"(momentum|return|mean_reversion)_(\d+)", resolved)
    if match is None:
        raise EngineInputError(f"unsupported factor expression: {expression}")
    operation, raw_lookback = match.groups()
    lookback = int(raw_lookback)
    if not 1 <= lookback <= 252:
        raise EngineInputError("factor lookback must be within 1..252 sessions")
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item["symbol"], item["date"])):
        by_symbol[row["symbol"]].append(row)
    calculated: list[dict[str, Any]] = []
    for history in by_symbol.values():
        adjusted = _adjusted_price_map(history)
        for index in range(lookback, len(history)):
            current = history[index]
            knowledge_time = _parse_timestamp(current["event_time"], "event_time")
            if (
                _parse_timestamp(current["available_at"], "available_at")
                > knowledge_time
            ):
                continue
            available_history = [
                item
                for item in history[:index]
                if _parse_timestamp(item["available_at"], "available_at")
                <= knowledge_time
            ]
            if len(available_history) < lookback:
                continue
            prior = available_history[-lookback]
            current_price = adjusted[current["date"]][current["symbol"]]
            prior_price = adjusted[prior["date"]][prior["symbol"]]
            score = current_price / prior_price - 1.0
            if operation == "mean_reversion":
                score *= -1
            calculated.append({**current, "factor_score": score})
    if not calculated:
        raise EngineInputError("factor formula has insufficient lookback history")
    return sorted(calculated, key=lambda item: (item["date"], item["symbol"]))


def factor_metrics(rows: list[dict[str, Any]], horizons: list[int]) -> dict[str, Any]:
    if not horizons or any(value < 1 for value in horizons):
        raise EngineInputError("factor horizons must be positive")
    by_date: dict[str, dict[str, float]] = defaultdict(dict)
    prices: dict[str, dict[str, float]] = defaultdict(dict)
    sectors: dict[str, dict[str, str]] = defaultdict(dict)
    adjusted_prices = _adjusted_price_map(rows)
    for row in rows:
        by_date[row["date"]][row["symbol"]] = float(
            row.get("factor_score", row["close"])
        )
        prices[row["date"]][row["symbol"]] = adjusted_prices[row["date"]][row["symbol"]]
        sectors[row["date"]][row["symbol"]] = str(row.get("sector", "__all__"))
    dates = sorted(by_date)
    result: dict[str, Any] = {"horizons": {}}
    total_possible = 0
    total_pairs = 0
    memberships: list[set[str]] = []
    for day in dates:
        ranked = sorted(
            by_date[day], key=lambda symbol: (-by_date[day][symbol], symbol)
        )
        memberships.append(set(ranked[: max(1, len(ranked) // 2)]))
    turnover_values = [
        len(previous.symmetric_difference(current)) / (2 * max(1, len(previous)))
        for previous, current in zip(memberships, memberships[1:], strict=False)
    ]
    for horizon in horizons:
        ic_values: list[float] = []
        rank_ic_values: list[float] = []
        neutralized_ic_values: list[float] = []
        quantile_spreads: list[float] = []
        pairs = 0
        possible = 0
        for index, day in enumerate(dates[:-horizon]):
            future = dates[index + horizon]
            symbols = sorted(set(by_date[day]) & set(by_date[future]))
            possible += len(by_date[day])
            if len(symbols) < 2:
                continue
            scores = [by_date[day][symbol] for symbol in symbols]
            forward = [
                prices[future][symbol] / prices[day][symbol] - 1.0 for symbol in symbols
            ]
            ic_values.append(_pearson(scores, forward))
            rank_ic_values.append(_pearson(_ranks(scores), _ranks(forward)))
            sector_groups: dict[str, list[float]] = defaultdict(list)
            for symbol, score in zip(symbols, scores, strict=True):
                sector_groups[sectors[day][symbol]].append(score)
            sector_means = {
                sector: statistics.fmean(values)
                for sector, values in sector_groups.items()
            }
            neutralized = [
                score - sector_means[sectors[day][symbol]]
                for symbol, score in zip(symbols, scores, strict=True)
            ]
            neutralized_ic_values.append(_pearson(neutralized, forward))
            quantile_size = max(1, len(symbols) // 5)
            ordered = sorted(range(len(scores)), key=scores.__getitem__)
            bottom = statistics.fmean(
                forward[index] for index in ordered[:quantile_size]
            )
            top = statistics.fmean(forward[index] for index in ordered[-quantile_size:])
            quantile_spreads.append(top - bottom)
            pairs += len(symbols)
        if not ic_values:
            raise EngineInputError(
                f"horizon {horizon} has no valid cross-sectional observations"
            )
        total_pairs += pairs
        total_possible += possible
        mean_ic = statistics.fmean(ic_values)
        mean_rank_ic = statistics.fmean(rank_ic_values)
        result["horizons"][str(horizon)] = {
            "ic": mean_ic,
            "ic_ir": (
                mean_ic / statistics.stdev(ic_values)
                if len(ic_values) > 1 and statistics.stdev(ic_values) > 0
                else 0.0
            ),
            "rank_ic": mean_rank_ic,
            "rank_ic_ir": (
                mean_rank_ic / statistics.stdev(rank_ic_values)
                if len(rank_ic_values) > 1 and statistics.stdev(rank_ic_values) > 0
                else 0.0
            ),
            "neutralized_ic": statistics.fmean(neutralized_ic_values),
            "quantile_return_spread": statistics.fmean(quantile_spreads),
            "cross_sections": len(ic_values),
        }
    result.update(
        {
            "coverage": total_pairs / total_possible if total_possible else 0.0,
            "turnover": statistics.fmean(turnover_values) if turnover_values else 0.0,
            "observations": total_pairs,
        }
    )
    return result


def _portfolio_returns(
    rows: list[dict[str, Any]],
    selection_count: int,
    cost: CostModel,
    strategy_spec: dict[str, Any] | None = None,
) -> tuple[list[float], list[float], list[float], int, dict[str, float]]:
    if selection_count < 1:
        raise EngineInputError("selection_count must be positive")
    by_date: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["symbol"] in by_date[row["date"]]:
            raise EngineInputError(
                "duplicate market row for local date and symbol: "
                f"{row['date']}/{row['symbol']}"
            )
        by_date[row["date"]][row["symbol"]] = row
    dates = sorted(by_date)
    net_returns: list[float] = []
    benchmark_returns: list[float] = []
    turnovers: list[float] = []
    trade_count = 0
    previous_weights: dict[str, float] = {}
    final_weights: dict[str, float] = {}
    rules = (strategy_spec or {}).get("rules", {})
    universe_symbols = set((strategy_spec or {}).get("universe", {}).get("symbols", []))
    weighting = rules.get("weighting", "EQUAL")
    rebalance_frequency = rules.get("rebalance_frequency", "DAILY")
    long_short = bool(rules.get("long_short", False))
    try:
        leverage_limit = float(rules.get("leverage_limit", 1))
        position_limit = float(rules.get("position_limit", 1))
        signals = (strategy_spec or {}).get(
            "signals", [{"weight": "1", "direction": "LONG"}]
        )
        signal_scale = sum(
            float(signal["weight"]) * (1 if signal["direction"] == "LONG" else -1)
            for signal in signals
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EngineInputError("strategy signal/leverage inputs are invalid") from error
    if (
        signal_scale == 0
        or not math.isfinite(signal_scale)
        or not math.isfinite(leverage_limit)
        or not math.isfinite(position_limit)
        or leverage_limit <= 0
        or not 0 < position_limit <= leverage_limit
    ):
        raise EngineInputError(
            "strategy signal/leverage/position constraints are invalid"
        )

    def signal_score(row: dict[str, Any]) -> float:
        value = row.get("strategy_score")
        score = (
            float(value) if value is not None else signal_scale * float(row["close"])
        )
        if not math.isfinite(score):
            raise EngineInputError("strategy score must be finite")
        return score

    def rebalance_due(index: int) -> bool:
        if index == 0 or rebalance_frequency == "DAILY":
            return True
        current = datetime.fromisoformat(dates[index]).date()
        previous = datetime.fromisoformat(dates[index - 1]).date()
        if rebalance_frequency == "WEEKLY":
            return current.isocalendar()[:2] != previous.isocalendar()[:2]
        if rebalance_frequency == "MONTHLY":
            return (current.year, current.month) != (previous.year, previous.month)
        if rebalance_frequency == "QUARTERLY":
            return (current.year, (current.month - 1) // 3) != (
                previous.year,
                (previous.month - 1) // 3,
            )
        raise EngineInputError("unsupported rebalance frequency")

    price_history: dict[str, list[float]] = defaultdict(list)
    adjusted_prices = _adjusted_price_map(rows)
    for index in range(len(dates) - 1):
        today, tomorrow = dates[index], dates[index + 1]
        next_rows = by_date[tomorrow]
        today_rows = {
            symbol: row
            for symbol, row in by_date[today].items()
            if _parse_timestamp(row["available_at"], "available_at")
            <= _parse_timestamp(row["event_time"], "event_time")
        }
        if not today_rows:
            continue
        for symbol in today_rows:
            price_history[symbol].append(adjusted_prices[today][symbol])
        ranked = sorted(
            (
                symbol
                for symbol in today_rows
                if symbol in next_rows
                and _parse_bool(
                    today_rows[symbol].get("in_universe", True), "in_universe"
                )
                and (not universe_symbols or symbol in universe_symbols)
            ),
            key=lambda symbol: (
                -signal_score(today_rows[symbol]),
                symbol,
            ),
        )
        selected = ranked[:selection_count]
        if not selected:
            continue
        if long_short and len(ranked) < selection_count * 2:
            raise EngineInputError(
                "long-short simulation requires disjoint long and short selections"
            )
        if not rebalance_due(index) and previous_weights:
            target = {
                symbol: weight
                for symbol, weight in previous_weights.items()
                if symbol in today_rows and symbol in next_rows
            }
        else:
            if weighting == "SCORE":
                raw = {
                    symbol: abs(signal_score(today_rows[symbol])) for symbol in selected
                }
            elif weighting == "VOLATILITY":
                raw = {}
                for symbol in selected:
                    history = price_history[symbol]
                    returns = [
                        history[position] / history[position - 1] - 1
                        for position in range(1, len(history))
                    ]
                    volatility = statistics.stdev(returns) if len(returns) > 1 else 1.0
                    raw[symbol] = 1.0 / max(volatility, 1e-12)
            elif weighting == "EQUAL":
                raw = dict.fromkeys(selected, 1.0)
            else:
                raise EngineInputError("unsupported strategy weighting")
            raw_total = sum(raw.values())
            if not math.isfinite(raw_total) or raw_total <= 0:
                raise EngineInputError(
                    "strategy weights must have a positive finite total"
                )
            target = {
                symbol: min(position_limit, leverage_limit * value / raw_total)
                for symbol, value in raw.items()
            }
            if long_short:
                shorted = ranked[-selection_count:]
                long_gross = leverage_limit / 2
                short_gross = leverage_limit / 2
                target = {
                    symbol: min(position_limit, long_gross / len(selected))
                    for symbol in selected
                }
                target.update(
                    {
                        symbol: -min(position_limit, short_gross / len(shorted))
                        for symbol in shorted
                        if symbol not in target
                    }
                )
        universe = set(previous_weights) | set(target)
        turnover = sum(
            abs(target.get(symbol, 0.0) - previous_weights.get(symbol, 0.0))
            for symbol in universe
        )
        asset_returns = {
            symbol: adjusted_prices[tomorrow][symbol] / adjusted_prices[today][symbol]
            - 1.0
            for symbol in target
        }
        gross = sum(weight * asset_returns[symbol] for symbol, weight in target.items())
        cost_rate = (cost.commission_bps + cost.slippage_bps) / 10_000
        net = gross - turnover * cost_rate
        if (
            not math.isfinite(cost_rate)
            or cost_rate < 0
            or not math.isfinite(gross)
            or not math.isfinite(net)
            or gross <= -1
            or net <= -1
        ):
            raise EngineInputError(
                "simulation produced an insolvent or non-finite return"
            )
        net_returns.append(net)
        benchmark_today = statistics.fmean(
            float(value["benchmark_close"]) for value in today_rows.values()
        )
        benchmark_tomorrow = statistics.fmean(
            float(value["benchmark_close"]) for value in next_rows.values()
        )
        benchmark_returns.append(benchmark_tomorrow / benchmark_today - 1.0)
        turnovers.append(turnover)
        trade_count += sum(
            1
            for symbol in universe
            if target.get(symbol, 0.0) != previous_weights.get(symbol, 0.0)
        )
        previous_weights = {
            symbol: weight * (1.0 + asset_returns[symbol]) / (1.0 + net)
            for symbol, weight in target.items()
        }
        final_weights = previous_weights.copy()
    if not net_returns:
        raise EngineInputError("simulation requires at least two comparable sessions")
    return net_returns, benchmark_returns, turnovers, trade_count, final_weights


def _risk_contribution(
    rows: list[dict[str, Any]], weights: dict[str, float]
) -> dict[str, float]:
    adjusted_prices = _adjusted_price_map(rows)
    by_symbol: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row["symbol"] in weights:
            by_symbol[row["symbol"]][row["date"]] = adjusted_prices[row["date"]][
                row["symbol"]
            ]
    return_maps: dict[str, dict[str, float]] = {}
    for symbol, prices in by_symbol.items():
        dates = sorted(prices)
        return_maps[symbol] = {
            dates[index]: prices[dates[index]] / prices[dates[index - 1]] - 1.0
            for index in range(1, len(dates))
        }
    symbols = sorted(weights)
    if not symbols:
        return {}
    common_dates = set.intersection(
        *(set(return_maps.get(symbol, {})) for symbol in symbols)
    )
    if len(common_dates) < 2:
        return {symbol: 0.0 for symbol in symbols}
    ordered_dates = sorted(common_dates)
    covariance: dict[tuple[str, str], float] = {}
    for left in symbols:
        for right in symbols:
            covariance[left, right] = statistics.covariance(
                [return_maps[left][day] for day in ordered_dates],
                [return_maps[right][day] for day in ordered_dates],
            )
    marginal = {
        left: sum(covariance[left, right] * weights[right] for right in symbols)
        for left in symbols
    }
    variance = sum(weights[symbol] * marginal[symbol] for symbol in symbols)
    if variance <= 0:
        return {symbol: 0.0 for symbol in symbols}
    return {symbol: weights[symbol] * marginal[symbol] / variance for symbol in symbols}


def simulation_metrics(
    rows: list[dict[str, Any]],
    selection_count: int,
    cost: CostModel,
    strategy_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    returns, benchmark, turnovers, trade_count, final_weights = _portfolio_returns(
        rows, selection_count, cost, strategy_spec
    )
    wealth = 1.0
    peak = 1.0
    maximum_drawdown = 0.0
    for value in returns:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        maximum_drawdown = min(maximum_drawdown, wealth / peak - 1.0)
    periods = len(returns)
    mean = statistics.fmean(returns)
    volatility_daily = statistics.stdev(returns) if periods > 1 else 0.0
    downside = [min(value, 0.0) for value in returns]
    downside_deviation = math.sqrt(
        statistics.fmean(value * value for value in downside)
    )
    cagr = wealth ** (252 / periods) - 1.0
    annualized_volatility = volatility_daily * math.sqrt(252)
    sharpe = mean / volatility_daily * math.sqrt(252) if volatility_daily else 0.0
    sortino = mean / downside_deviation * math.sqrt(252) if downside_deviation else 0.0
    calmar = cagr / abs(maximum_drawdown) if maximum_drawdown else 0.0
    benchmark_wealth = math.prod(1.0 + value for value in benchmark)
    total_turnover = sum(turnovers)
    return {
        "observations": periods,
        "total_return": wealth - 1.0,
        "benchmark_total_return": benchmark_wealth - 1.0,
        "cagr": cagr,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "maximum_drawdown": maximum_drawdown,
        "turnover": total_turnover,
        "trade_count": trade_count,
        "average_holding_period": periods / max(1, trade_count),
        "commission": total_turnover * cost.commission_bps / 10_000,
        "slippage": total_turnover * cost.slippage_bps / 10_000,
        "exposure": statistics.fmean(
            sum(abs(value) for value in final_weights.values()) for _ in returns
        ),
        "cash_weight": 1.0 - sum(final_weights.values()),
        "final_weights": final_weights,
        "risk_contribution": _risk_contribution(rows, final_weights),
        "returns": returns,
    }


def validation_checks(
    metrics: dict[str, Any],
    periods: dict[str, dict[str, str]],
    rows: list[dict[str, Any]],
    robustness: dict[str, Any] | None = None,
    policy: ValidationPolicy | None = None,
) -> list[tuple[str, bool, str]]:
    split_ok = (
        periods["research_period"]["end"]
        < periods["validation_period"]["start"]
        <= periods["validation_period"]["end"]
        < periods["holdout_period"]["start"]
    )
    leakage_ok = all(row["partition"] == "VALIDATION" for row in rows)
    numerical_ok = (
        int(metrics["observations"]) >= 2
        and -1.0 <= float(metrics["maximum_drawdown"]) <= 0.0
        and float(metrics["turnover"]) >= 0.0
        and float(metrics["commission"]) >= 0.0
        and float(metrics["slippage"]) >= 0.0
        and all(math.isfinite(float(value)) for value in metrics["returns"])
    )
    checks = [
        (
            "split_isolation",
            split_ok,
            "Research, validation and holdout periods are disjoint",
        ),
        ("pit_leakage", leakage_ok, "Strict validation consumed only VALIDATION rows"),
        (
            "numerical_robustness",
            numerical_ok,
            "Metrics satisfy deterministic invariants",
        ),
    ]
    if policy is not None:
        checks.extend(
            [
                (
                    "policy_min_observations",
                    int(metrics["observations"]) >= policy.validation_min_observations,
                    "Validation observation count meets the versioned policy",
                ),
                (
                    "policy_min_sharpe",
                    float(metrics["sharpe"]) >= policy.validation_min_sharpe,
                    "Validation Sharpe meets the versioned policy",
                ),
                (
                    "policy_max_drawdown",
                    float(metrics["maximum_drawdown"])
                    >= policy.validation_max_drawdown_floor,
                    "Validation drawdown meets the versioned policy",
                ),
            ]
        )
    if robustness is not None:
        cost_stress = robustness.get("cost_stress")
        alternatives = robustness.get("parameter_alternatives")
        cost_return = (
            cost_stress.get("total_return") if isinstance(cost_stress, dict) else None
        )
        cost_ok = (
            isinstance(cost_return, (int, float))
            and not isinstance(cost_return, bool)
            and math.isfinite(float(cost_return))
            and float(cost_return) <= float(metrics["total_return"]) + 1e-12
        )
        parameter_ok = (
            isinstance(alternatives, list)
            and bool(alternatives)
            and all(
                isinstance(item, dict)
                and isinstance(item.get("total_return"), (int, float))
                and not isinstance(item.get("total_return"), bool)
                and math.isfinite(float(item["total_return"]))
                and isinstance(item.get("maximum_drawdown"), (int, float))
                and not isinstance(item.get("maximum_drawdown"), bool)
                and -1.0 <= float(item["maximum_drawdown"]) <= 0.0
                for item in alternatives
            )
        )
        subperiod_ok = len({row["date"] for row in rows}) >= 3
        checks.extend(
            [
                (
                    "cost_sensitivity",
                    cost_ok,
                    "Higher modeled costs do not improve deterministic net return",
                ),
                (
                    "parameter_stability",
                    parameter_ok,
                    "Adjacent selection parameters produce finite portfolio results",
                ),
                (
                    "subperiod_coverage",
                    subperiod_ok,
                    "Validation includes at least three independent sessions",
                ),
                (
                    "multiple_testing_budget",
                    policy is None
                    or len(alternatives or [])
                    <= policy.multiple_testing_max_evaluations,
                    "Robustness alternatives remain within the versioned testing budget",
                ),
            ]
        )
    return checks
