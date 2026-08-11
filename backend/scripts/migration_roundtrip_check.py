#!/usr/bin/env python3
"""Verify populated 0016 downgrade/upgrade preservation on the active database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]
GATE_MANIFEST_PATH = BACKEND_ROOT / "schema/populated_migration_gate.json"
APPLICATION_TABLE_COUNT = 63
CHECK_CONSTRAINT_COUNT = 191
COMMITTED_MINIMUM_ROWS = 2503
COMMITTED_MINIMUM_NONEMPTY_TABLES = 38
COMMITTED_MINIMUM_WORKSPACE_ROLE_TUPLES = 12


def _load_gate_manifest(path: Path = GATE_MANIFEST_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "minimum_rows",
        "minimum_nonempty_tables",
        "minimum_workspace_role_tuples",
        "critical_table_floors",
    }
    if set(value) != required or value["schema_version"] != 1:
        raise RuntimeError("populated migration gate manifest shape/version is invalid")
    scalar_floors = (
        value["minimum_rows"],
        value["minimum_nonempty_tables"],
        value["minimum_workspace_role_tuples"],
    )
    critical = value["critical_table_floors"]
    if (
        not all(isinstance(item, int) and item > 0 for item in scalar_floors)
        or not isinstance(critical, dict)
        or not critical
        or any(
            not isinstance(table, str)
            or not isinstance(floor, int)
            or isinstance(floor, bool)
            or floor <= 0
            for table, floor in critical.items()
        )
    ):
        raise RuntimeError("populated migration gate manifest floors are invalid")
    committed_minima = (
        COMMITTED_MINIMUM_ROWS,
        COMMITTED_MINIMUM_NONEMPTY_TABLES,
        COMMITTED_MINIMUM_WORKSPACE_ROLE_TUPLES,
    )
    if any(
        actual < committed
        for actual, committed in zip(scalar_floors, committed_minima, strict=True)
    ):
        raise RuntimeError(
            "populated migration gate manifest regressed committed floors"
        )
    return value


def _normalized(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {key: _normalized(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    return (
        str(value)
        if value is not None and not isinstance(value, (bool, int, float, str))
        else value
    )


def _fingerprint(database_url: str) -> dict[str, tuple[int, str]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            preparer = connection.dialect.identifier_preparer
            result: dict[str, tuple[int, str]] = {}
            for table_name in sorted(inspect(connection).get_table_names()):
                if table_name == "alembic_version" or table_name.startswith("_qf0016_"):
                    continue
                rows = [
                    [_normalized(value) for value in row]
                    for row in connection.execute(
                        text(f"SELECT * FROM {preparer.quote(table_name)}")
                    )
                ]
                rows.sort(
                    key=lambda row: json.dumps(
                        row, sort_keys=True, separators=(",", ":")
                    )
                )
                encoded = json.dumps(
                    rows, sort_keys=True, separators=(",", ":")
                ).encode()
                result[table_name] = (len(rows), hashlib.sha256(encoded).hexdigest())
            return result
    finally:
        engine.dispose()


def _agent_roles(database_url: str, column: str) -> set[tuple[str, str]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                (str(row.workspace_id), str(row.role_value))
                for row in connection.execute(
                    text(
                        f"SELECT workspace_id, {column} AS role_value "
                        "FROM agent_configs"
                    )
                )
            }
    finally:
        engine.dispose()


def _validate_requested_floors(
    *,
    minimum_rows: int,
    minimum_nonempty_tables: int,
    minimum_agent_roles: int,
    manifest: dict[str, Any],
) -> None:
    requested = {
        "minimum_rows": minimum_rows,
        "minimum_nonempty_tables": minimum_nonempty_tables,
        "minimum_workspace_role_tuples": minimum_agent_roles,
    }
    lowered = {
        name: (actual, int(manifest[name]))
        for name, actual in requested.items()
        if actual < int(manifest[name])
    }
    if lowered:
        detail = ", ".join(
            f"{name}={actual}/{committed}"
            for name, (actual, committed) in sorted(lowered.items())
        )
        raise RuntimeError(f"populated migration floors cannot decrease: {detail}")


def _validate_coverage(
    fingerprint: dict[str, tuple[int, str]],
    roles: set[tuple[str, str]],
    *,
    minimum_rows: int,
    minimum_nonempty_tables: int,
    minimum_agent_roles: int,
    critical_table_floors: dict[str, int],
) -> dict[str, Any]:
    total_rows = sum(count for count, _ in fingerprint.values())
    nonempty = sum(count > 0 for count, _ in fingerprint.values())
    if len(fingerprint) != APPLICATION_TABLE_COUNT:
        raise RuntimeError(
            f"expected {APPLICATION_TABLE_COUNT} application tables, "
            f"found {len(fingerprint)}"
        )
    if total_rows < minimum_rows or nonempty < minimum_nonempty_tables:
        raise RuntimeError(
            "populated migration gate is insufficient: "
            f"rows={total_rows}/{minimum_rows}, "
            f"nonempty={nonempty}/{minimum_nonempty_tables}"
        )
    if len(roles) < minimum_agent_roles:
        raise RuntimeError(
            "multi-role migration coverage is insufficient: "
            f"roles={len(roles)}/{minimum_agent_roles}"
        )
    critical_failures = {
        table: (fingerprint.get(table, (0, ""))[0], floor)
        for table, floor in sorted(critical_table_floors.items())
        if fingerprint.get(table, (0, ""))[0] < floor
    }
    if critical_failures:
        detail = ", ".join(
            f"{table}={actual}/{floor}"
            for table, (actual, floor) in critical_failures.items()
        )
        raise RuntimeError(
            f"critical-table migration coverage is insufficient: {detail}"
        )
    return {
        "application_tables": len(fingerprint),
        "total_rows": total_rows,
        "nonempty_tables": nonempty,
        "workspace_role_tuples": len(roles),
        "critical_table_counts": {
            table: fingerprint[table][0] for table in sorted(critical_table_floors)
        },
    }


def _validate_content_roundtrip(
    before: dict[str, tuple[int, str]], after: dict[str, tuple[int, str]]
) -> None:
    if after == before:
        return
    changed = sorted(set(before) | set(after))
    changed = [name for name in changed if before.get(name) != after.get(name)]
    detail = {
        name: {"before": before.get(name), "after": after.get(name)} for name in changed
    }
    raise RuntimeError(
        "0016 populated roundtrip changed table count/hash: "
        + json.dumps(detail, sort_keys=True)
    )


def _schema_contract(database_url: str) -> dict[str, Any]:
    from scripts.schema_manifest_check import check

    result = check(database_url)
    if not result["ok"]:
        raise RuntimeError(
            "populated migration schema/constraint gate failed: "
            + json.dumps(result["errors"], sort_keys=True)
        )
    if result["manifest_tables"] != APPLICATION_TABLE_COUNT:
        raise RuntimeError("populated migration schema table count is not canonical")
    physical = json.loads(
        (BACKEND_ROOT / "alembic/versions/0016_section14_physical.json").read_text(
            encoding="utf-8"
        )
    )
    check_count = sum(len(table["checks"]) for table in physical["tables"])
    if check_count != CHECK_CONSTRAINT_COUNT:
        raise RuntimeError(
            f"populated migration CHECK count={check_count}/{CHECK_CONSTRAINT_COUNT}"
        )
    return {"tables": result["manifest_tables"], "checks": check_count}


def _alembic(database_url: str, action: str, revision: str) -> None:
    previous = os.environ.get("QF_ALEMBIC_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    try:
        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        getattr(command, action)(config, revision)
    finally:
        if previous is None:
            os.environ.pop("QF_ALEMBIC_URL", None)
        else:
            os.environ["QF_ALEMBIC_URL"] = previous


def _alembic_check(database_url: str) -> None:
    previous = os.environ.get("QF_ALEMBIC_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    try:
        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        command.check(config)
    finally:
        if previous is None:
            os.environ.pop("QF_ALEMBIC_URL", None)
        else:
            os.environ["QF_ALEMBIC_URL"] = previous


def main() -> int:
    gate_manifest = _load_gate_manifest()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url", default=os.getenv("QF_DATABASE_URL"), required=False
    )
    parser.add_argument(
        "--minimum-rows", type=int, default=gate_manifest["minimum_rows"]
    )
    parser.add_argument(
        "--minimum-nonempty-tables",
        type=int,
        default=gate_manifest["minimum_nonempty_tables"],
    )
    parser.add_argument(
        "--minimum-agent-roles",
        type=int,
        default=gate_manifest["minimum_workspace_role_tuples"],
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or QF_DATABASE_URL is required")

    _validate_requested_floors(
        minimum_rows=args.minimum_rows,
        minimum_nonempty_tables=args.minimum_nonempty_tables,
        minimum_agent_roles=args.minimum_agent_roles,
        manifest=gate_manifest,
    )
    _alembic_check(args.database_url)
    schema_before = _schema_contract(args.database_url)
    before = _fingerprint(args.database_url)
    roles_before = _agent_roles(args.database_url, "role_key")
    coverage = _validate_coverage(
        before,
        roles_before,
        minimum_rows=args.minimum_rows,
        minimum_nonempty_tables=args.minimum_nonempty_tables,
        minimum_agent_roles=args.minimum_agent_roles,
        critical_table_floors=gate_manifest["critical_table_floors"],
    )

    _alembic(args.database_url, "downgrade", "0015_langgraph_checkpoint")
    roles_downgraded = _agent_roles(args.database_url, "role")
    if roles_downgraded != roles_before:
        raise RuntimeError(
            "agent_configs role mapping changed during downgrade: "
            f"before={sorted(roles_before)!r}, downgraded={sorted(roles_downgraded)!r}"
        )
    _alembic(args.database_url, "upgrade", "head")
    after = _fingerprint(args.database_url)
    roles_after = _agent_roles(args.database_url, "role_key")
    _validate_content_roundtrip(before, after)
    if roles_after != roles_before:
        raise RuntimeError("agent_configs role mapping changed after upgrade")
    _validate_coverage(
        after,
        roles_after,
        minimum_rows=args.minimum_rows,
        minimum_nonempty_tables=args.minimum_nonempty_tables,
        minimum_agent_roles=args.minimum_agent_roles,
        critical_table_floors=gate_manifest["critical_table_floors"],
    )
    _alembic_check(args.database_url)
    schema_after = _schema_contract(args.database_url)
    if schema_after != schema_before:
        raise RuntimeError(
            f"schema/constraint report changed: before={schema_before}, "
            f"after={schema_after}"
        )
    print(
        "0016 populated roundtrip preserved "
        f"{coverage['application_tables']} tables/{coverage['total_rows']} rows/"
        f"{coverage['nonempty_tables']} nonempty/"
        f"{coverage['workspace_role_tuples']} workspace-role tuples/"
        f"{schema_after['checks']} CHECKs; critical="
        + json.dumps(coverage["critical_table_counts"], sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
