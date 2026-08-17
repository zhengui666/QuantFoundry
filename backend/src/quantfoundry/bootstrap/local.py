"""Idempotent local bootstrap for a fresh Alembic-managed database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

from quantfoundry.api.app import (
    CostModelVersionRow,
    DataSource,
    ResearchPolicyVersionRow,
    RiskPolicyVersionRow,
    SessionLocal,
    SessionToken,
    User,
    Workspace,
    content_hash,
)
from quantfoundry.infrastructure.db.schema import canonical_workspace_id

RESEARCH_POLICY = {
    "version": 1,
    "allowed_asset_classes": ["EQUITY"],
    "require_pit_snapshot": True,
    "require_cost_model": True,
}
RISK_POLICY = {
    "version": 1,
    "max_gross_exposure": 1.0,
    "max_position_weight": 0.1,
    "max_drawdown": 0.25,
}
COST_MODEL = {
    "version": 1,
    "commission_bps": 1.0,
    "slippage_bps": 2.0,
}
VALIDATION_POLICY = {
    "version": 1,
    "validation": {
        "min_observations": 20,
        "min_sharpe": 0.0,
        "max_drawdown_floor": -0.35,
    },
    "holdout": {
        "min_observations": 10,
        "min_total_return": -0.05,
        "min_sharpe": -0.25,
        "max_drawdown_floor": -0.4,
    },
    "multiple_testing_max_evaluations": 25,
    "data_quality": {
        "min_rows": 6,
        "min_symbols": 2,
        "max_late_release_fraction": 1.0,
    },
}


def _stable_public_id(workspace_id: str, aggregate: str, prefix: str) -> str:
    scope = canonical_workspace_id(workspace_id)
    raw = bytearray(
        hashlib.sha256(
            f"quantfoundry-local-seed:v1:{scope}:{aggregate}".encode()
        ).digest()[:16]
    )
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return f"{prefix}-{uuid.UUID(bytes=bytes(raw))}"


def _workspace_seed_values(workspace_id: str) -> dict[str, dict[str, Any] | str]:
    research_policy_id = _stable_public_id(workspace_id, "research-policy", "RP")
    validation_policy_id = _stable_public_id(workspace_id, "validation-policy", "RP")
    risk_policy_id = _stable_public_id(workspace_id, "risk-policy", "RISK")
    cost_model_id = _stable_public_id(workspace_id, "cost-model", "COST")
    dataset_id = _stable_public_id(workspace_id, "dataset", "DSSET")
    return {
        "research_policy": {
            **RESEARCH_POLICY,
            "policy_id": research_policy_id,
        },
        "validation_policy": {
            **VALIDATION_POLICY,
            "policy_id": validation_policy_id,
        },
        "risk_policy": {**RISK_POLICY, "policy_id": risk_policy_id},
        "cost_model": {**COST_MODEL, "cost_model_id": cost_model_id},
        "dataset_id": dataset_id,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    encoded = json.dumps(value, sort_keys=True, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError(f"refusing to overwrite different local policy: {path}")
    path.write_text(encoded, encoding="utf-8")
    path.chmod(0o640)


def _write_local_dataset(root: Path, dataset_id: str) -> str:
    root.mkdir(mode=0o750, parents=True, exist_ok=True)
    csv_path = root / f"{dataset_id}.csv"
    rows = [
        "event_time,available_at,symbol,close,benchmark_close,partition,split_factor,dividend,in_universe,sector",
        "2024-01-02T21:00:00Z,2024-01-02T21:01:00Z,AAA,100,100,RESEARCH,1,0,true,TECH",
        "2024-01-02T21:00:00Z,2024-01-02T21:01:00Z,BBB,100,100,RESEARCH,1,0,true,FINANCE",
        "2024-01-03T21:00:00Z,2024-01-03T21:01:00Z,AAA,102,101,RESEARCH,1,0,true,TECH",
        "2024-01-03T21:00:00Z,2024-01-03T21:01:00Z,BBB,99,101,RESEARCH,1,0,true,FINANCE",
        "2024-01-04T21:00:00Z,2024-01-04T21:01:00Z,AAA,103,102,RESEARCH,1,0,true,TECH",
        "2024-01-04T21:00:00Z,2024-01-04T21:01:00Z,BBB,98,102,RESEARCH,1,0,true,FINANCE",
        "2024-01-05T21:00:00Z,2024-01-05T21:01:00Z,AAA,104,103,VALIDATION,1,0,true,TECH",
        "2024-01-05T21:00:00Z,2024-01-05T21:01:00Z,BBB,97,103,VALIDATION,1,0,true,FINANCE",
        "2024-01-08T21:00:00Z,2024-01-08T21:01:00Z,AAA,105,104,HOLDOUT,1,0,true,TECH",
        "2024-01-08T21:00:00Z,2024-01-08T21:01:00Z,BBB,96,104,HOLDOUT,1,0,true,FINANCE",
    ]
    csv_value = "\n".join(rows) + "\n"
    if csv_path.exists() and csv_path.read_text(encoding="utf-8") != csv_value:
        raise RuntimeError(f"refusing to overwrite different local dataset: {csv_path}")
    csv_path.write_text(csv_value, encoding="utf-8")
    csv_path.chmod(0o640)
    _write_json(
        root / f"{dataset_id}.metadata.json",
        {
            "provider_id": "LOCAL_DETERMINISTIC",
            "adapter_key": "local-arrow",
            "adapter_version": "1.0.0",
            "timezone": "America/New_York",
            "calendar": "WEEKDAY",
            "pit_policy": "AVAILABLE_AT_STRICT_V1",
            "corporate_action_policy": "RAW_PRICE_SPLIT_DIVIDEND_V1",
            "survivorship_policy": "POINT_IN_TIME_MEMBERSHIP_V1",
        },
    )
    return dataset_id


def seed_local(
    *,
    workspace_id: str,
    owner_id: str,
    owner_email: str,
    session_token: str,
    ttl_hours: int = 30 * 24,
) -> dict[str, Any]:
    cost_root = Path(os.environ["QF_COST_MODEL_DIR"])
    policy_root = Path(os.environ["QF_POLICY_DIR"])
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    seed_values = _workspace_seed_values(workspace_id)
    research_policy = seed_values["research_policy"]
    validation_policy = seed_values["validation_policy"]
    risk_policy = seed_values["risk_policy"]
    cost_model = seed_values["cost_model"]
    dataset_id = seed_values["dataset_id"]
    assert isinstance(research_policy, dict)
    assert isinstance(validation_policy, dict)
    assert isinstance(risk_policy, dict)
    assert isinstance(cost_model, dict)
    assert isinstance(dataset_id, str)
    _write_json(cost_root / f"{cost_model['cost_model_id']}.json", cost_model)
    _write_json(
        policy_root / f"{validation_policy['policy_id']}.json", validation_policy
    )
    _write_json(policy_root / f"{research_policy['policy_id']}.json", research_policy)
    _write_json(policy_root / f"{risk_policy['policy_id']}.json", risk_policy)
    dataset_id = _write_local_dataset(dataset_root, dataset_id)
    timestamp = datetime.now(UTC)
    session = SessionLocal()
    try:
        existing_user = session.get(User, owner_id)
        if existing_user is None:
            session.add(User(id=owner_id, email=owner_email, role="OWNER", revision=1))
        elif existing_user.email != owner_email or existing_user.role != "OWNER":
            raise RuntimeError(
                "local owner is already bound to different identity data"
            )
        session.flush()
        existing_workspace = session.get(Workspace, workspace_id)
        if existing_workspace is None:
            session.add(
                Workspace(
                    id=workspace_id,
                    owner_id=owner_id,
                    name="QuantFoundry Local",
                    revision=1,
                )
            )
        elif existing_workspace.owner_id != owner_id:
            raise RuntimeError("local workspace is already bound to another owner")
        session.flush()
        rows: tuple[tuple[Any, str, str, dict[str, Any], dict[str, Any]], ...] = (
            (
                ResearchPolicyVersionRow,
                f"{research_policy['policy_id']}:1",
                "policy_id",
                research_policy,
                {"created_by": owner_id, "policy_family": "research"},
            ),
            (
                ResearchPolicyVersionRow,
                f"{validation_policy['policy_id']}:1",
                "policy_id",
                validation_policy,
                {"created_by": owner_id, "policy_family": "validation"},
            ),
            (
                RiskPolicyVersionRow,
                f"{risk_policy['policy_id']}:1",
                "policy_id",
                risk_policy,
                {},
            ),
            (
                CostModelVersionRow,
                f"{cost_model['cost_model_id']}:1",
                "cost_model_id",
                cost_model,
                {},
            ),
        )
        for model, row_id, public_field, value, extras in rows:
            expected_hash = content_hash(value)
            existing = session.get(model, row_id)
            if existing is None:
                public_match = session.execute(
                    select(model).where(
                        model.workspace_id == workspace_id,
                        getattr(model, public_field) == value[public_field],
                    )
                ).scalar_one_or_none()
                if public_match is not None:
                    raise RuntimeError("local policy public ID has conflicting binding")
                row_values = {
                    "id": row_id,
                    "workspace_id": workspace_id,
                    public_field: value[public_field],
                    "version": 1,
                    "status": "ACTIVE",
                    "content_sha256": expected_hash,
                    "created_at": timestamp,
                    "activated_at": timestamp,
                    **extras,
                }
                if model is ResearchPolicyVersionRow:
                    row_values["rules"] = value
                    row_values["max_research_steps"] = 25
                    row_values["max_tool_calls"] = 50
                elif model is RiskPolicyVersionRow:
                    row_values.update(
                        {
                            "max_single_position": Decimal(
                                str(value["max_position_weight"])
                            ),
                            "max_strategy_weight": Decimal(
                                str(value["max_gross_exposure"])
                            ),
                            "max_paper_drawdown": Decimal(str(value["max_drawdown"])),
                            "rules": value,
                        }
                    )
                elif model is CostModelVersionRow:
                    row_values.update(
                        {
                            "commission_model": {
                                "commission_bps": value["commission_bps"]
                            },
                            "slippage_model": {"slippage_bps": value["slippage_bps"]},
                            "rebalance_timing": "NEXT_OPEN",
                            "fill_assumption": "NEXT_OPEN",
                        }
                    )
                session.add(model(**row_values))
                continue
            expected = {
                "workspace_id": canonical_workspace_id(workspace_id),
                public_field: value[public_field],
                "version": 1,
                "status": "ACTIVE",
                "content_sha256": expected_hash,
                **extras,
            }
            if model is ResearchPolicyVersionRow:
                expected["rules"] = value
                expected["max_research_steps"] = 25
                expected["max_tool_calls"] = 50
            elif model is RiskPolicyVersionRow:
                expected.update(
                    {
                        "max_single_position": Decimal(
                            str(value["max_position_weight"])
                        ),
                        "max_strategy_weight": Decimal(
                            str(value["max_gross_exposure"])
                        ),
                        "max_paper_drawdown": Decimal(str(value["max_drawdown"])),
                        "rules": value,
                    }
                )
            elif model is CostModelVersionRow:
                expected.update(
                    {
                        "commission_model": {"commission_bps": value["commission_bps"]},
                        "slippage_model": {"slippage_bps": value["slippage_bps"]},
                        "rebalance_timing": "NEXT_OPEN",
                        "fill_assumption": "NEXT_OPEN",
                    }
                )
            if any(
                getattr(existing, field) != expected_value
                for field, expected_value in expected.items()
            ):
                raise RuntimeError("local policy row has conflicting immutable binding")
        if session.get(DataSource, (dataset_id, workspace_id)) is None:
            session.add(
                DataSource(
                    id=dataset_id,
                    workspace_id=workspace_id,
                    provider_id="LOCAL_DETERMINISTIC_DATA",
                    status="ACTIVE",
                    revision=1,
                )
            )
        token_sha256 = hashlib.sha256(session_token.encode()).hexdigest()
        existing_token = session.get(SessionToken, token_sha256)
        if existing_token is None:
            session.add(
                SessionToken(
                    token_sha256=token_sha256,
                    actor_id=owner_id,
                    workspace_id=workspace_id,
                    expires_at=timestamp + timedelta(hours=ttl_hours),
                )
            )
        elif (
            existing_token.actor_id != owner_id
            or existing_token.workspace_id != canonical_workspace_id(workspace_id)
        ):
            raise RuntimeError("session token is already bound to another principal")
        elif (
            existing_token.revoked_at is not None
            or (
                existing_token.expires_at.replace(tzinfo=UTC)
                if existing_token.expires_at.tzinfo is None
                else existing_token.expires_at
            )
            <= timestamp
        ):
            raise RuntimeError(
                "session token is revoked or expired; provide a new token"
            )
        active_policy = session.execute(
            select(ResearchPolicyVersionRow).where(
                ResearchPolicyVersionRow.workspace_id == workspace_id,
                ResearchPolicyVersionRow.policy_family == "research",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
        ).scalar_one()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return {
        "workspace_id": workspace_id,
        "owner_id": owner_id,
        "session_token": session_token,
        "research_policy_id": active_policy.policy_id,
        "validation_policy_id": validation_policy["policy_id"],
        "risk_policy_id": risk_policy["policy_id"],
        "cost_model_id": cost_model["cost_model_id"],
        "dataset_id": dataset_id,
        "cost_model_dir": str(cost_root.resolve()),
        "policy_dir": str(policy_root.resolve()),
        "dataset_dir": str(dataset_root.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed-local"])
    parser.add_argument("--workspace-id", default="local-workspace")
    parser.add_argument("--owner-id", default="local-owner")
    parser.add_argument("--owner-email", default="owner@local.invalid")
    parser.add_argument("--session-token")
    args = parser.parse_args()
    if args.command == "seed-local":
        result = seed_local(
            workspace_id=args.workspace_id,
            owner_id=args.owner_id,
            owner_email=args.owner_email,
            session_token=args.session_token or secrets.token_urlsafe(32),
        )
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
