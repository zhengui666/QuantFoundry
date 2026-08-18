"""Validate the UX-001 runtime snapshot columns owned by section 14.

The frozen ``0016_section14_physical.json`` already contains these columns.
This revision is intentionally non-destructive: adding or dropping them here
would change PostgreSQL column order and would lose snapshot data on downgrade.
"""

from __future__ import annotations

import re

import sqlalchemy as sa

from alembic import op

revision = "0018_ux001_runtime_snapshots"
down_revision = "0017_paper_scheduler_state_init"
branch_labels = None
depends_on = None

RUNTIME_COLUMNS = {
    "agent_runs": (
        "ai_connection_id",
        "ai_connection_revision",
        "effective_configuration_revision",
        "effective_configuration_sha256",
        "agent_configuration_revision",
        "runtime_profile",
        "tool_timeout_seconds",
        "max_steps",
        "max_tool_calls",
        "prompt_manifest_sha256",
        "tool_registry_sha256",
    ),
    "tool_calls": (
        "effective_configuration_revision",
        "configuration_sha256",
        "tool_registry_sha256",
    ),
}

_RUNTIME_COLUMN_CONTRACT = {
    "agent_runs": {
        "ai_connection_id": ("varchar", None, "'CODEX-DEFAULT'"),
        "ai_connection_revision": ("bigint", None, "1"),
        "effective_configuration_revision": ("bigint", None, "1"),
        "effective_configuration_sha256": ("varchar", 64, "'" + "0" * 64 + "'"),
        "agent_configuration_revision": ("bigint", None, "1"),
        "runtime_profile": ("varchar", None, "'DEFAULT'"),
        "tool_timeout_seconds": ("integer", None, "30"),
        "max_steps": ("integer", None, "25"),
        "max_tool_calls": ("integer", None, "50"),
        "prompt_manifest_sha256": ("varchar", 64, "'" + "0" * 64 + "'"),
        "tool_registry_sha256": ("varchar", 64, "'" + "0" * 64 + "'"),
    },
    "tool_calls": {
        "effective_configuration_revision": ("bigint", None, "1"),
        "configuration_sha256": ("varchar", 64, "'" + "0" * 64 + "'"),
        "tool_registry_sha256": ("varchar", 64, "'" + "0" * 64 + "'"),
    },
}

_RUNTIME_CHECK_NAMES = {
    "agent_runs": {
        "ck_agent_runs_effective_configuration_sha256_valid",
        "ck_agent_runs_prompt_manifest_sha256_valid",
        "ck_agent_runs_tool_registry_sha256_valid",
    },
    "tool_calls": {
        "ck_tool_calls_configuration_sha256_valid",
        "ck_tool_calls_tool_registry_sha256_valid",
    },
}


def _sha256_check(column: str) -> str:
    expression = column
    for character in "0123456789abcdef":
        expression = f"replace({expression}, '{character}', '')"
    return (
        f"length({column}) = 64 AND lower({column}) = {column} AND "
        f"{expression} = ''"
    )


_RUNTIME_CHECK_EXPRESSIONS = {
    table: {name: _sha256_check(column) for name, column in checks.items()}
    for table, checks in {
        "agent_runs": {
            "ck_agent_runs_effective_configuration_sha256_valid": "effective_configuration_sha256",
            "ck_agent_runs_prompt_manifest_sha256_valid": "prompt_manifest_sha256",
            "ck_agent_runs_tool_registry_sha256_valid": "tool_registry_sha256",
        },
        "tool_calls": {
            "ck_tool_calls_configuration_sha256_valid": "configuration_sha256",
            "ck_tool_calls_tool_registry_sha256_valid": "tool_registry_sha256",
        },
    }.items()
}


def _type_matches(column: dict[str, object], expected: str, length: int | None) -> bool:
    actual_type = column["type"]
    if expected == "bigint":
        matches = isinstance(actual_type, sa.BigInteger)
    elif expected == "integer":
        matches = isinstance(actual_type, sa.Integer) and not isinstance(
            actual_type, (sa.BigInteger, sa.SmallInteger)
        )
    else:
        actual = str(actual_type).lower().replace(" ", "")
        matches = actual.startswith(("varchar", "charactervarying", "string"))
    if not matches:
        return False
    if expected in {"bigint", "integer"}:
        return True
    return getattr(column["type"], "length", None) == length


def _default_matches(actual: object, expected: str) -> bool:
    if actual is None:
        return False
    normalized = str(actual).strip().replace(" ", "")
    normalized = re.sub(r"::(?:pg_catalog\.)?[a-z_][a-z0-9_]*(?:\[\])?$", "", normalized)
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1]
    return normalized.lower() == expected.replace(" ", "").lower()


def _normalize_sql(expression: object) -> str:
    normalized = re.sub(r"\s+", " ", str(expression)).lower().strip()
    normalized = re.sub(
        r"::(?:pg_catalog\.)?[a-z_][a-z0-9_]*(?:\[\])?", "", normalized
    )

    def strip_groups(value: str) -> str:
        result: list[str] = []
        index = 0
        while index < len(value):
            if value[index] == "'":
                end = index + 1
                while end < len(value):
                    if value[end] == "'":
                        if end + 1 < len(value) and value[end + 1] == "'":
                            end += 2
                            continue
                        end += 1
                        break
                    end += 1
                result.append(value[index:end])
                index = end
                continue
            if value[index] != "(":
                result.append(value[index])
                index += 1
                continue
            depth = 1
            end = index + 1
            while end < len(value) and depth:
                if value[end] == "'":
                    quote_end = end + 1
                    while quote_end < len(value):
                        if value[quote_end] == "'":
                            if quote_end + 1 < len(value) and value[quote_end + 1] == "'":
                                quote_end += 2
                                continue
                            quote_end += 1
                            break
                        quote_end += 1
                    end = quote_end
                    continue
                if value[end] == "(":
                    depth += 1
                elif value[end] == ")":
                    depth -= 1
                end += 1
            if depth:
                return value
            inner = strip_groups(value[index + 1 : end - 1])
            previous = value[index - 1] if index else ""
            token_match = re.search(r"[a-z_][a-z0-9_]*$", value[:index])
            token = token_match.group(0) if token_match else ""
            if previous and (previous.isalnum() or previous == "_") and token not in {
                "and",
                "or",
                "not",
                "in",
                "is",
            }:
                result.append(f"({inner})")
            else:
                result.append(inner)
            index = end
        return "".join(result)

    return re.sub(r"\s+", "", strip_groups(normalized))


def _validate_section14_columns() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    postgres = bind.dialect.name == "postgresql"
    invalid: dict[str, list[str]] = {}
    for table, columns in _RUNTIME_COLUMN_CONTRACT.items():
        reflected = {item["name"]: item for item in inspector.get_columns(table)}
        for name, (expected_type, length, expected_default) in columns.items():
            column = reflected.get(name)
            if (
                column is None
                or bool(column["nullable"])
                or not _type_matches(column, expected_type, length)
                or (postgres and not _default_matches(column.get("default"), expected_default))
            ):
                invalid.setdefault(table, []).append(name)
        if postgres:
            checks = {
                item.get("name")
                for item in inspector.get_check_constraints(table)
                if item.get("name")
            }
            missing_checks = _RUNTIME_CHECK_NAMES[table] - checks
            if missing_checks:
                invalid.setdefault(table, []).extend(sorted(missing_checks))
            for item in inspector.get_check_constraints(table):
                name = item.get("name")
                expected = _RUNTIME_CHECK_EXPRESSIONS[table].get(name)
                if expected is None:
                    continue
                if _normalize_sql(item.get("sqltext")) != _normalize_sql(expected):
                    invalid.setdefault(table, []).append(f"{name}:expression")
                validated = bind.execute(
                    sa.text(
                        "SELECT c.convalidated FROM pg_constraint c "
                        "JOIN pg_class t ON t.oid = c.conrelid "
                        "JOIN pg_namespace n ON n.oid = t.relnamespace "
                        "WHERE n.nspname = current_schema() AND t.relname = :table "
                        "AND c.conname = :name AND c.contype = 'c'"
                    ),
                    {"table": table, "name": name},
                ).scalar_one_or_none()
                if validated is not True:
                    invalid.setdefault(table, []).append(f"{name}:unvalidated")
    if invalid:
        raise RuntimeError(
            f"0018 requires exact section-14 runtime snapshot columns; invalid={invalid}"
        )


def upgrade() -> None:
    _validate_section14_columns()


def downgrade() -> None:
    # 0016 owns the physical columns. Keeping them here makes head -> 0017 ->
    # head and the populated 0016 roundtrip lossless and order-preserving.
    return None
