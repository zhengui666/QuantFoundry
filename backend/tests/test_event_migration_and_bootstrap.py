"""Alembic-only PostgreSQL bootstrap and closed-event migration gates."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.event_contract import EVENT_TYPES
from app.public_ids import is_public_id
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError

from scripts import migration_roundtrip_check

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _roundtrip_fingerprint(total_rows: int) -> dict[str, tuple[int, str]]:
    manifest = migration_roundtrip_check._load_gate_manifest()
    critical = dict(manifest["critical_table_floors"])
    names = list(critical)
    names.extend(f"table_{index}" for index in range(63 - len(critical)))
    counts = {name: critical.get(name, 0) for name in names}
    populated = sum(count > 0 for count in counts.values())
    for name in names:
        if populated >= 38:
            break
        if counts[name] == 0:
            counts[name] = 1
            populated += 1
    remainder = total_rows - sum(counts.values())
    if remainder < 0:
        deficit = -remainder
        for name in sorted(names, key=lambda name: counts[name], reverse=True):
            removable = max(counts[name] - 1, 0)
            removed = min(removable, deficit)
            counts[name] -= removed
            deficit -= removed
            if deficit == 0:
                break
        if deficit:
            raise ValueError("total_rows cannot keep 38 tables populated")
    else:
        counts[names[0]] += remainder
    return {
        name: (count, hashlib.sha256(name.encode()).hexdigest())
        for name, count in counts.items()
    }


def _roundtrip_roles(count: int = 12) -> set[tuple[str, str]]:
    return {(f"workspace-{index}", "RESEARCH_DIRECTOR") for index in range(count)}


def _validate_roundtrip_coverage(total_rows: int) -> dict[str, object]:
    manifest = migration_roundtrip_check._load_gate_manifest()
    return migration_roundtrip_check._validate_coverage(
        _roundtrip_fingerprint(total_rows),
        _roundtrip_roles(),
        minimum_rows=manifest["minimum_rows"],
        minimum_nonempty_tables=manifest["minimum_nonempty_tables"],
        minimum_agent_roles=manifest["minimum_workspace_role_tuples"],
        critical_table_floors=manifest["critical_table_floors"],
    )


def test_populated_roundtrip_gate_rejects_2502_and_legacy_2403() -> None:
    with pytest.raises(RuntimeError, match=r"rows=2502/2503"):
        _validate_roundtrip_coverage(2502)
    manifest = migration_roundtrip_check._load_gate_manifest()
    with pytest.raises(RuntimeError, match=r"minimum_rows=2403/2503"):
        migration_roundtrip_check._validate_requested_floors(
            minimum_rows=2403,
            minimum_nonempty_tables=38,
            minimum_agent_roles=12,
            manifest=manifest,
        )


@pytest.mark.parametrize("total_rows", [2503, 2504, 3000])
def test_populated_roundtrip_gate_accepts_minimum_and_growth(
    total_rows: int,
) -> None:
    result = _validate_roundtrip_coverage(total_rows)
    assert result["total_rows"] == total_rows


def test_populated_roundtrip_manifest_and_pg18_floor_are_monotonic(
    tmp_path: Path,
) -> None:
    manifest = migration_roundtrip_check._load_gate_manifest()
    assert manifest["minimum_rows"] == 2503
    assert manifest["minimum_nonempty_tables"] == 38
    assert manifest["minimum_workspace_role_tuples"] == 12
    script = (BACKEND_ROOT / "scripts/pg18_ci.sh").read_text(encoding="utf-8")
    assert "--minimum-rows 2503" in script
    stale = {**manifest, "minimum_rows": 2403}
    path = tmp_path / "stale-gate.json"
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(RuntimeError, match="regressed committed floors"):
        migration_roundtrip_check._load_gate_manifest(path)


def test_populated_roundtrip_gate_requires_12_workspace_roles() -> None:
    manifest = migration_roundtrip_check._load_gate_manifest()
    with pytest.raises(RuntimeError, match=r"roles=11/12"):
        migration_roundtrip_check._validate_coverage(
            _roundtrip_fingerprint(2503),
            _roundtrip_roles(11),
            minimum_rows=2503,
            minimum_nonempty_tables=38,
            minimum_agent_roles=12,
            critical_table_floors=manifest["critical_table_floors"],
        )


def test_populated_roundtrip_gate_rejects_nonempty_and_critical_regressions() -> None:
    manifest = migration_roundtrip_check._load_gate_manifest()
    fingerprint = _roundtrip_fingerprint(2503)
    populated_names = [name for name, (count, _) in fingerprint.items() if count > 0]
    nonempty_regression = dict(fingerprint)
    removed = populated_names[0]
    removed_count = nonempty_regression[removed][0]
    nonempty_regression[removed] = (0, nonempty_regression[removed][1])
    padding = next(
        name for name, (count, _) in nonempty_regression.items() if count > 0
    )
    nonempty_regression[padding] = (
        nonempty_regression[padding][0] + removed_count,
        nonempty_regression[padding][1],
    )
    with pytest.raises(RuntimeError, match=r"nonempty=37/38"):
        migration_roundtrip_check._validate_coverage(
            nonempty_regression,
            _roundtrip_roles(),
            minimum_rows=2503,
            minimum_nonempty_tables=38,
            minimum_agent_roles=12,
            critical_table_floors=manifest["critical_table_floors"],
        )

    critical_regression = dict(fingerprint)
    critical = next(iter(manifest["critical_table_floors"]))
    actual, digest = critical_regression[critical]
    floor = manifest["critical_table_floors"][critical]
    moved = actual - (floor - 1)
    critical_regression[critical] = (floor - 1, digest)
    target = next(name for name in fingerprint if name != critical)
    target_count, target_digest = critical_regression[target]
    critical_regression[target] = (target_count + moved, target_digest)
    with pytest.raises(RuntimeError, match=rf"{critical}="):
        migration_roundtrip_check._validate_coverage(
            critical_regression,
            _roundtrip_roles(),
            minimum_rows=2503,
            minimum_nonempty_tables=38,
            minimum_agent_roles=12,
            critical_table_floors=manifest["critical_table_floors"],
        )


def test_populated_roundtrip_gate_rejects_per_table_hash_or_count_mutation() -> None:
    before = _roundtrip_fingerprint(2503)
    reordered = dict(reversed(list(before.items())))
    migration_roundtrip_check._validate_content_roundtrip(before, reordered)
    changed = dict(before)
    table = next(iter(changed))
    count, _ = changed[table]
    changed[table] = (count, "f" * 64)
    with pytest.raises(RuntimeError, match=rf'"{table}"'):
        migration_roundtrip_check._validate_content_roundtrip(before, changed)


def test_populated_roundtrip_fingerprint_is_sorted_and_value_sensitive(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'fingerprint.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE subject (id INTEGER, value TEXT)"))
        connection.execute(text("INSERT INTO subject VALUES (2,'beta'),(1,'alpha')"))
    first = migration_roundtrip_check._fingerprint(database_url)["subject"]
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM subject"))
        connection.execute(text("INSERT INTO subject VALUES (1,'alpha'),(2,'beta')"))
    reordered = migration_roundtrip_check._fingerprint(database_url)["subject"]
    assert reordered == first
    with engine.begin() as connection:
        connection.execute(text("UPDATE subject SET value='changed' WHERE id=2"))
    mutated = migration_roundtrip_check._fingerprint(database_url)["subject"]
    assert mutated[0] == first[0]
    assert mutated[1] != first[1]
    engine.dispose()


def test_populated_roundtrip_gate_rejects_constraint_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import schema_manifest_check

    monkeypatch.setattr(
        schema_manifest_check,
        "check",
        lambda _url: {
            "ok": False,
            "errors": ["database:check-sql:domain_events"],
            "manifest_tables": 63,
        },
    )
    with pytest.raises(RuntimeError, match="schema/constraint gate failed"):
        migration_roundtrip_check._schema_contract("unused")


def test_section14_restore_normalizes_heterogeneous_nullable_columns() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    table = Table(
        "heterogeneous_rows",
        MetaData(),
        Column("id", String(), primary_key=True),
        Column("started_at", DateTime(timezone=True), nullable=True),
    )
    prepared = migration["_prepare_rows"](
        table,
        [
            {"id": "first", "started_at": datetime.now(UTC)},
            {"id": "second"},
        ],
    )
    assert [set(row) for row in prepared] == [
        {"id", "started_at"},
        {"id", "started_at"},
    ]
    assert prepared[1]["started_at"] is None


def test_section14_downgrade_restores_active_cost_model_fk_canonically() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    metadata = MetaData()
    Table("workspaces", metadata, Column("id", Uuid(), primary_key=True))
    cost_models = Table(
        "cost_model_versions",
        metadata,
        Column("id", Uuid(), primary_key=True),
        Column("legacy_id", String(), nullable=False),
        Column("workspace_id", Uuid(), ForeignKey("workspaces.id"), nullable=False),
        UniqueConstraint("workspace_id", "id"),
    )
    settings = Table(
        "app_settings",
        metadata,
        Column("id", Uuid(), primary_key=True),
        Column("workspace_id", Uuid(), ForeignKey("workspaces.id"), nullable=False),
        Column("active_cost_model_id", Uuid(), nullable=False),
        ForeignKeyConstraint(
            ["workspace_id", "active_cost_model_id"],
            ["cost_model_versions.workspace_id", "cost_model_versions.id"],
        ),
    )
    workspace_id = uuid.uuid4()
    cost_model_id = uuid.uuid4()
    source_rows = {
        "workspaces": [{"id": workspace_id}],
        "cost_model_versions": [
            {
                "id": cost_model_id,
                "legacy_id": "COST-legacy",
                "workspace_id": workspace_id,
            }
        ],
        "app_settings": [
            {
                "id": uuid.uuid4(),
                "workspace_id": workspace_id,
                "active_cost_model_id": cost_model_id,
            }
        ],
    }
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys = ON"))
        metadata.create_all(connection)
        migration["_restore_all_tables"](
            connection, metadata, source_rows, prefer_aliases=False
        )
        assert (
            connection.execute(select(cost_models.c.id)).scalar_one() == cost_model_id
        )
        assert (
            connection.execute(select(settings.c.active_cost_model_id)).scalar_one()
            == cost_model_id
        )
    engine.dispose()


def test_section14_idempotency_aliases_preserve_operation_scope() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    table = Table(
        "idempotency_records",
        MetaData(),
        Column("actor_id", String(), primary_key=True),
        Column("workspace_id", String(), primary_key=True),
        Column("method", String(), primary_key=True),
        Column("path", String(), primary_key=True),
        Column("key", String(), primary_key=True),
        Column("request_hash", String(), nullable=False),
        Column("status", Integer(), nullable=False),
        Column("response", String(), nullable=False),
    )
    source = {
        "actor_id": "actor",
        "workspace_id": "workspace",
        "method": "POST",
        "normalized_route": "/api/v1/research",
        "key": "same-key",
        "request_sha256": "a" * 64,
        "response_status": 202,
        "response_body": {"accepted": True},
    }
    prepared = migration["_prepare_rows"](table, [source])[0]
    assert prepared["path"] == source["normalized_route"]
    assert prepared["request_hash"] == source["request_sha256"]
    assert prepared["status"] == source["response_status"]
    assert json.loads(prepared["response"]) == source["response_body"]


def test_section14_job_aliases_preserve_public_fk_graph() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    metadata = MetaData()
    jobs = Table(
        "jobs",
        metadata,
        Column("id", String(), primary_key=True),
    )
    dependencies = Table(
        "job_dependencies",
        metadata,
        Column("job_id", String(), primary_key=True),
        Column("depends_on_job_id", String(), primary_key=True),
    )
    tool_calls = Table(
        "tool_calls",
        metadata,
        Column("id", String(), primary_key=True),
        Column("agent_run_id", String(), nullable=False),
        Column("job_id", String(), nullable=True),
    )
    agent_runs = Table(
        "agent_runs",
        metadata,
        Column("id", String(), primary_key=True),
    )
    job_id = "JOB-550e8400-e29b-41d4-a716-446655440030"
    dependency_id = "JOB-550e8400-e29b-41d4-a716-446655440031"
    agent_run_id = "ARUN-550e8400-e29b-41d4-a716-446655440030"
    prepare = migration["_prepare_rows"]
    internal_id = uuid.uuid4()
    source_job = {"id": internal_id, "job_id": job_id}
    assert prepare(jobs, [source_job])[0]["id"] == job_id
    assert prepare(jobs, [source_job], prefer_aliases=False)[0]["id"] == str(
        internal_id
    )
    current_dependency = Table(
        "current_dependency",
        MetaData(),
        Column("job_id", Uuid(as_uuid=True), primary_key=True),
    )
    assert (
        prepare(
            current_dependency,
            [{"job_id": internal_id}],
            prefer_aliases=False,
        )[0]["job_id"]
        == internal_id
    )
    assert prepare(
        dependencies,
        [
            {
                "job_id": uuid.uuid4(),
                "job_public_id": job_id,
                "depends_on_job_id": uuid.uuid4(),
                "depends_on_job_public_id": dependency_id,
            }
        ],
    )[0] == {"job_id": job_id, "depends_on_job_id": dependency_id}
    assert (
        prepare(
            tool_calls,
            [
                {
                    "id": "call",
                    "agent_run_id": uuid.uuid4(),
                    "agent_run_public_id": agent_run_id,
                    "job_id": uuid.uuid4(),
                    "job_public_id": job_id,
                }
            ],
        )[0]["job_id"]
        == job_id
    )
    assert (
        prepare(
            agent_runs,
            [{"id": uuid.uuid4(), "agent_run_id": agent_run_id}],
        )[0]["id"]
        == agent_run_id
    )
    assert (
        prepare(
            tool_calls,
            [
                {
                    "id": "call",
                    "agent_run_id": uuid.uuid4(),
                    "agent_run_public_id": agent_run_id,
                }
            ],
        )[0]["agent_run_id"]
        == agent_run_id
    )


def test_section14_closed_locator_backfill_requires_unique_workspace_authority() -> (
    None
):
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    strategy_id = "STRAT-550e8400-e29b-41d4-a716-446655440000"
    event = {
        "event_id": "EVT-550e8400-e29b-41d4-a716-446655440011",
        "sequence": 3,
        "workspace_id": "workspace-a",
        "event_type": "strategy.updated",
        "object_type": "strategy_version",
        "object_id": strategy_id,
        "revision": 4,
    }
    source_rows: dict[str, list[dict[str, Any]]] = {
        "domain_events": [event],
        "strategy_versions": [
            {
                "id": "legacy-strategy-version",
                "workspace_id": "workspace-a",
                "strategy_id": strategy_id,
                "version": 2,
                "revision": 7,
            }
        ],
    }
    migration["_backfill_closed_storage"](source_rows)
    assert event["object_version"] == 2
    assert event["object_revision"] == 4
    assert event["revision"] == 4

    source_rows["strategy_versions"].append(
        {
            "id": "other-strategy-version",
            "workspace_id": "workspace-a",
            "strategy_id": strategy_id,
            "version": 3,
            "revision": 1,
        }
    )
    event.pop("object_version")
    event.pop("object_revision")
    with pytest.raises(
        migration["MigrationQuarantineError"], match="authority count is 2"
    ) as error:
        migration["_backfill_closed_storage"](source_rows)
    assert error.value.reports[0]["table"] == "domain_events"
    assert len(error.value.reports[0]["payload_sha256"]) == 64


def test_section14_domain_locator_scan_quarantines_retained_invalid_rows() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    source_rows = {
        "domain_events": [
            {
                "event_id": "EVT-550e8400-e29b-41d4-a716-446655440021",
                "sequence": 21,
                "workspace_id": "workspace-a",
                "event_type": "job.updated",
                "object_type": "job",
                "object_id": "FAC-550e8400-e29b-41d4-a716-446655440021",
                "revision": 1,
            },
            {
                "event_id": "EVT-550e8400-e29b-41d4-a716-446655440022",
                "sequence": 22,
                "workspace_id": "workspace-a",
                "event_type": "experiment.created",
                "object_type": None,
                "object_id": None,
                "revision": None,
            },
        ],
        "jobs": [
            {
                "workspace_id": "workspace-a",
                "job_id": "JOB-550e8400-e29b-41d4-a716-446655440021",
                "revision": 1,
            }
        ],
    }
    retained = json.loads(json.dumps(source_rows))

    with pytest.raises(migration["MigrationQuarantineError"]) as error:
        migration["_backfill_closed_storage"](source_rows)

    assert [report["table"] for report in error.value.reports] == [
        "domain_events",
        "domain_events",
    ]
    assert {report["reason"] for report in error.value.reports} == {
        "mandatory locator is absent",
        "ordinary locator authority count is 0",
    }
    assert source_rows == retained


def test_section14_postgres_domain_locator_check_is_not_valid_then_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    metadata = migration["load_physical_metadata"](migration["CURRENT"])
    domain_events = metadata.tables["domain_events"]
    assert any(
        constraint.name == "ck_domain_events_locator_quartet"
        for constraint in domain_events.constraints
    )
    migration["_defer_domain_locator_check"](metadata)
    assert not any(
        constraint.name == "ck_domain_events_locator_quartet"
        for constraint in domain_events.constraints
    )

    statements: list[str] = []
    monkeypatch.setattr(migration["op"], "execute", statements.append)
    migration["_install_and_validate_domain_locator_check"]()
    assert statements == [
        "ALTER TABLE domain_events ADD CONSTRAINT "
        "ck_domain_events_locator_quartet CHECK ("
        "qf_event_locator_quartet_valid(object_type, object_id, "
        "object_version, object_revision, FALSE)) NOT VALID",
        "ALTER TABLE domain_events VALIDATE CONSTRAINT "
        "ck_domain_events_locator_quartet",
    ]


def test_section14_closed_json_migration_quarantines_without_rewriting() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    bad_result = {"type": "job", "id": "must-not-be-normalized"}
    bad_next_action = {"action": "resume", "object_type": "job"}
    source_rows: dict[str, list[dict[str, Any]]] = {
        "jobs": [
            {
                "id": "JOB-550e8400-e29b-41d4-a716-446655440012",
                "result_ref": bad_result,
            }
        ],
        "agent_runs": [
            {
                "id": "ARUN-550e8400-e29b-41d4-a716-446655440012",
                "object_type": None,
                "object_id": None,
                "next_action": bad_next_action,
            }
        ],
    }
    with pytest.raises(migration["MigrationQuarantineError"]) as error:
        migration["_backfill_closed_storage"](source_rows)
    assert {report["table"] for report in error.value.reports} == {
        "agent_runs",
        "jobs",
    }
    assert source_rows["jobs"][0]["result_ref"] == bad_result
    assert source_rows["agent_runs"][0]["next_action"] == bad_next_action


def test_section14_downgrade_maps_workspace_event_sequences_without_collision() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    metadata = MetaData()
    Table(
        "domain_events",
        metadata,
        Column("sequence", Integer(), primary_key=True),
        Column("workspace_id", String(), nullable=True),
    )
    Table(
        "audit_events",
        metadata,
        Column("id", String(), primary_key=True),
        Column("workspace_id", String(), nullable=True),
    )
    source_rows = {
        "domain_events": [
            {"sequence": 1, "workspace_id": "workspace-b"},
            {"sequence": 1, "workspace_id": "workspace-a"},
        ],
        "audit_events": [
            {"id": "audit-b", "sequence": 1, "workspace_id": "workspace-b"},
            {"id": "audit-a", "sequence": 1, "workspace_id": "workspace-a"},
        ],
    }
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        metadata.create_all(connection)
        migration["_restore_all_tables"](connection, metadata, source_rows)
        events = connection.execute(
            text(
                "SELECT workspace_id, sequence FROM domain_events ORDER BY workspace_id"
            )
        ).all()
        audits = connection.execute(
            text("SELECT workspace_id FROM audit_events ORDER BY workspace_id")
        ).all()
    engine.dispose()
    assert events == [("workspace-a", 1), ("workspace-b", 2)]
    assert audits == [("workspace-a",), ("workspace-b",)]


def test_section14_restore_resolves_nullable_foreign_key_cycles() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0016_section14_schema.py")
    )
    metadata = MetaData()
    Table(
        "cycle_a",
        metadata,
        Column("id", String(), primary_key=True),
        Column("b_id", String(), ForeignKey("cycle_b.id"), nullable=True),
    )
    Table(
        "cycle_b",
        metadata,
        Column("id", String(), primary_key=True),
        Column("a_id", String(), ForeignKey("cycle_a.id"), nullable=True),
    )
    Table(
        "cycle_child",
        metadata,
        Column("id", String(), primary_key=True),
        Column("a_id", String(), ForeignKey("cycle_a.id"), nullable=False),
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys = ON"))
        metadata.create_all(connection)
        migration["_restore_all_tables"](
            connection,
            metadata,
            {
                "cycle_a": [{"id": "a", "b_id": "b"}],
                "cycle_b": [{"id": "b", "a_id": "a"}],
                "cycle_child": [{"id": "child", "a_id": "a"}],
            },
        )
        assert connection.execute(text("SELECT id, b_id FROM cycle_a")).one() == (
            "a",
            "b",
        )
        assert connection.execute(text("SELECT id, a_id FROM cycle_b")).one() == (
            "b",
            "a",
        )
        assert connection.execute(text("SELECT id, a_id FROM cycle_child")).one() == (
            "child",
            "a",
        )
    engine.dispose()


def _upgrade(database_url: str, revision: str) -> None:
    previous = os.environ.get("QF_ALEMBIC_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    try:
        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        command.upgrade(config, revision)
    finally:
        if previous is None:
            os.environ.pop("QF_ALEMBIC_URL", None)
        else:
            os.environ["QF_ALEMBIC_URL"] = previous


def _downgrade(database_url: str, revision: str) -> None:
    previous = os.environ.get("QF_ALEMBIC_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    try:
        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        command.downgrade(config, revision)
    finally:
        if previous is None:
            os.environ.pop("QF_ALEMBIC_URL", None)
        else:
            os.environ["QF_ALEMBIC_URL"] = previous


def _database_fingerprint(engine) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    with engine.connect() as connection:
        names = sorted(
            name
            for name in inspect(connection).get_table_names()
            if name != "alembic_version" and not name.startswith("_qf0016_")
        )
        preparer = connection.dialect.identifier_preparer
        for name in names:
            rows = [
                [value.hex() if isinstance(value, bytes) else value for value in row]
                for row in connection.execute(
                    text(f"SELECT * FROM {preparer.quote(name)}")
                )
            ]
            encoded = json.dumps(rows, sort_keys=True, default=str).encode()
            result[name] = (len(rows), hashlib.sha256(encoded).hexdigest())
    return result


def _load_0017_migration() -> dict[str, Any]:
    return runpy.run_path(
        str(
            BACKEND_ROOT
            / "alembic/versions/0017_paper_scheduler_state_initialization.py"
        )
    )


def _sqlite_0017_tables() -> tuple[Any, Any, Any, Any, Any, Any, Any]:
    metadata = MetaData()
    deployments = Table(
        "paper_deployments",
        metadata,
        Column("id", String(), primary_key=True),
        Column("workspace_id", String(), nullable=False),
        Column("paper_id", String(), nullable=False),
        Column("status", String(), nullable=False),
        Column("revision", Integer(), nullable=False),
    )
    states = Table(
        "paper_scheduler_states",
        metadata,
        Column("id", String(), primary_key=True),
        Column("workspace_id", String(), nullable=False),
        Column("paper_id", String(), nullable=False),
        Column("scheduler_status", String(), nullable=False),
        Column("suppressed_since_utc", DateTime(timezone=True), nullable=True),
        Column("resume_watermark_utc", DateTime(timezone=True), nullable=True),
        Column("revision", Integer(), nullable=False),
    )
    audit_events = Table(
        "audit_events",
        metadata,
        Column("id", String(), primary_key=True),
        Column("event_id", String(), nullable=False),
        Column("actor_type", String(), nullable=False),
        Column("actor_id", String(), nullable=False),
        Column("workspace_id", String(), nullable=False),
        Column("sequence", Integer(), nullable=False),
        Column("action_type", String(), nullable=False),
        Column("object_type", String(), nullable=False),
        Column("object_id", String(), nullable=False),
        Column("object_version", Integer()),
        Column("object_revision", Integer()),
        Column("result", String(), nullable=False),
        Column("summary", JSON(), nullable=False),
        Column("detail_artifact_id", String()),
        Column("prev_event_hash", String()),
        Column("event_hash", String(), nullable=False),
        Column("occurred_at", DateTime(timezone=True), nullable=False),
        Column("input_hash", String(), nullable=False),
        Column("before_hash", String()),
        Column("after_hash", String()),
    )
    domain_events = Table(
        "domain_events",
        metadata,
        Column("sequence", Integer(), primary_key=True),
        Column("event_id", String(), nullable=False),
        Column("workspace_id", String(), nullable=False),
        Column("event_type", String(), nullable=False),
        Column("object_type", String(), nullable=False),
        Column("object_id", String(), nullable=False),
        Column("payload", JSON(), nullable=False),
        Column("occurred_at", DateTime(timezone=True), nullable=False),
        Column("expires_at", DateTime(timezone=True), nullable=False),
        Column("actor_id", String()),
        Column("object_version", Integer()),
        Column("object_revision", Integer()),
        Column("revision", Integer()),
        Column("request_id", String()),
        Column("correlation_id", String()),
        Column("causation_id", String()),
        Column("job_id", String()),
        Column("agent_run_id", String()),
        Column("tool_call_id", String()),
        Column("schema_version", Integer()),
    )
    heads = Table(
        "audit_chain_heads",
        metadata,
        Column("workspace_id", String(), primary_key=True),
        Column("event_sha256", String()),
        Column("revision", Integer(), nullable=False),
    )
    watermarks = Table(
        "event_stream_watermarks",
        metadata,
        Column("workspace_id", String(), primary_key=True),
        Column("last_sequence", Integer(), nullable=False),
        Column("expired_through_sequence", Integer(), nullable=False),
    )
    return metadata, deployments, states, audit_events, domain_events, heads, watermarks


def _invoke_0017(migration: dict[str, Any], connection: Any) -> None:
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        migration["upgrade"]()


def _insert_0017_baseline(
    connection: Any,
    deployments: Any,
    states: Any,
    audit_events: Any,
    domain_events: Any,
    heads: Any,
    watermarks: Any,
) -> datetime:
    instant = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    paper_locator = "PAPER-550e8400-e29b-41d4-a716-446655440000"
    connection.execute(
        deployments.insert().values(
            id="paper-1",
            workspace_id="workspace-1",
            paper_id=paper_locator,
            status="ACTIVE",
            revision=1,
        )
    )
    connection.execute(
        states.insert().values(
            id="state-1",
            workspace_id="workspace-1",
            paper_id="paper-1",
            scheduler_status="ACTIVE",
            suppressed_since_utc=None,
            resume_watermark_utc=instant,
            revision=1,
        )
    )
    connection.execute(
        audit_events.insert().values(
            id="audit-1",
            event_id="AUD-550e8400-e29b-41d4-a716-446655440001",
            actor_type="SYSTEM",
            actor_id="migration",
            workspace_id="workspace-1",
            sequence=1,
            action_type="SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
            object_type="paper",
            object_id=paper_locator,
            object_version=None,
            object_revision=1,
            result="SUCCESS",
            summary={
                "paper_scheduler_state_evidence.v1": {
                    "state_transition_id": "transition-1",
                    "workspace_id": "workspace-1",
                    "paper_id": paper_locator,
                    "from_state": None,
                    "to_state": "ACTIVE",
                    "effective_at_utc": instant.isoformat(),
                    "suppressed_since_utc": None,
                    "resume_watermark_utc": instant.isoformat(),
                    "initialization_utc": instant.isoformat(),
                    "revision": 1,
                    "reason_code": "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
                    "actor": {"type": "SYSTEM", "id": "migration"},
                    "system": {
                        "service": "alembic",
                        "instance_id": "0017",
                    },
                    "commit_build_locator": {
                        "commit_sha": "test-commit",
                        "build_id": "test-build",
                    },
                }
            },
            detail_artifact_id=None,
            prev_event_hash=None,
            event_hash="a" * 64,
            occurred_at=instant,
            input_hash="b" * 64,
            before_hash=None,
            after_hash="c" * 64,
        )
    )
    connection.execute(
        domain_events.insert().values(
            sequence=1,
            event_id="EVT-550e8400-e29b-41d4-a716-446655440001",
            workspace_id="workspace-1",
            event_type="paper.updated",
            object_type="paper",
            object_id=paper_locator,
            payload={"status": "ACTIVE"},
            occurred_at=instant,
            expires_at=instant + timedelta(days=7),
            actor_id="alembic:0017",
            object_version=None,
            object_revision=1,
            revision=1,
            request_id=None,
            correlation_id=None,
            causation_id=None,
            job_id=None,
            agent_run_id=None,
            tool_call_id=None,
            schema_version=1,
        )
    )
    connection.execute(
        heads.insert().values(
            workspace_id="workspace-1", event_sha256="a" * 64, revision=1
        )
    )
    connection.execute(
        watermarks.insert().values(
            workspace_id="workspace-1", last_sequence=1, expired_through_sequence=0
        )
    )
    return instant


def test_0017_scheduler_state_initialization_commits_and_is_restart_idempotent() -> (
    None
):
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, domain_events, heads, watermarks = (
        _sqlite_0017_tables()
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata.create_all(connection)
        instant = _insert_0017_baseline(
            connection,
            deployments,
            states,
            audit_events,
            domain_events,
            heads,
            watermarks,
        )
        connection.commit()
        _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        rows = connection.execute(select(states)).mappings().all()
        assert len(rows) == 1
        assert rows[0]["scheduler_status"] == "ACTIVE"
        assert rows[0]["resume_watermark_utc"] == instant.replace(tzinfo=None)
        audits = connection.execute(select(audit_events)).mappings().all()
        assert len(audits) == 1
        assert audits[0]["detail_artifact_id"] is None
        assert len(connection.execute(select(domain_events)).all()) == 1
        assert connection.execute(select(heads.c.event_sha256)).scalar_one() == "a" * 64
        assert connection.execute(select(watermarks.c.last_sequence)).scalar_one() == 1
        connection.commit()
        _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        rerun = connection.execute(select(states)).mappings().all()
        assert len(rerun) == 1
        assert len(connection.execute(select(audit_events)).all()) == 1
        assert len(connection.execute(select(domain_events)).all()) == 1
        assert rerun[0]["resume_watermark_utc"] == rows[0]["resume_watermark_utc"]
    engine.dispose()


def test_0017_scheduler_state_initialization_creates_proven_baseline() -> None:
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, domain_events, heads, watermarks = (
        _sqlite_0017_tables()
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata.create_all(connection)
        connection.execute(
            deployments.insert().values(
                id="paper-legacy",
                workspace_id="workspace-legacy",
                paper_id="PAPER-550e8400-e29b-41d4-a716-446655440099",
                status="STOPPED",
                revision=3,
            )
        )
        connection.commit()
        _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        state = connection.execute(select(states)).mappings().one()
        audit = connection.execute(select(audit_events)).mappings().one()
        event = connection.execute(select(domain_events)).mappings().one()
        assert state["scheduler_status"] == "DISABLED"
        assert state["suppressed_since_utc"] == state["resume_watermark_utc"]
        assert (
            connection.execute(select(deployments.c.status)).scalar_one() == "DISABLED"
        )
        assert audit["detail_artifact_id"] is None
        assert (
            audit["summary"]["paper_scheduler_state_evidence.v1"]["reason_code"]
            == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY"
        )
        assert event["event_type"] == "paper.updated"
        assert event["payload"] == {"status": "DISABLED"}
        assert (
            connection.execute(select(heads.c.event_sha256)).scalar_one()
            == audit["event_hash"]
        )
        assert (
            connection.execute(select(watermarks.c.last_sequence)).scalar_one()
            == event["sequence"]
        )
        connection.commit()
        _invoke_0017(migration, connection)
        assert len(connection.execute(select(states)).all()) == 1
        assert len(connection.execute(select(audit_events)).all()) == 1
        assert len(connection.execute(select(domain_events)).all()) == 1
    engine.dispose()


def test_0017_rejects_unclassifiable_legacy_data_with_quarantine_report(
    tmp_path: Path,
) -> None:
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, domain_events, _, _ = (
        _sqlite_0017_tables()
    )
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'quarantine.db'}")
    with engine.connect() as connection:
        metadata.create_all(connection)
        connection.execute(
            deployments.insert().values(
                id="paper-unknown",
                workspace_id="workspace-unknown",
                paper_id="PAPER-550e8400-e29b-41d4-a716-446655440077",
                status="UNKNOWN",
                revision=1,
            )
        )
        connection.commit()
        with pytest.raises(migration["SchedulerInitializationError"]) as error:
            _invoke_0017(migration, connection)
        assert error.value.reports[0]["locator"] == (
            "PAPER-550e8400-e29b-41d4-a716-446655440077"
        )
        assert len(error.value.reports[0]["payload_sha256"]) == 64
        assert "unclassifiable legacy data" in error.value.reports[0]["reason"]
        assert not connection.in_transaction()
        assert connection.execute(select(states)).all() == []
        assert connection.execute(select(audit_events)).all() == []
        assert connection.execute(select(domain_events)).all() == []
        quarantine = (
            connection.execute(
                text(
                    "SELECT workspace_locator, source_locator, reason, payload_sha256 "
                    "FROM _qf_migration_quarantine_0017"
                )
            )
            .mappings()
            .one()
        )
        assert quarantine["workspace_locator"] == "workspace-unknown"
        assert quarantine["source_locator"] == error.value.reports[0]["locator"]
        assert quarantine["reason"] == error.value.reports[0]["reason"]
        assert quarantine["payload_sha256"] == error.value.reports[0]["payload_sha256"]
    engine.dispose()


def test_0017_blocks_restart_when_closed_baseline_event_is_missing() -> None:
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, domain_events, heads, watermarks = (
        _sqlite_0017_tables()
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata.create_all(connection)
        instant = _insert_0017_baseline(
            connection,
            deployments,
            states,
            audit_events,
            domain_events,
            heads,
            watermarks,
        )
        connection.execute(domain_events.delete())
        connection.commit()
        with pytest.raises(
            migration["SchedulerInitializationError"], match="paper.updated event"
        ):
            _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        state = connection.execute(select(states)).mappings().one()
        assert state["resume_watermark_utc"] == instant.replace(tzinfo=None)
        assert len(connection.execute(select(audit_events)).all()) == 1
        assert connection.execute(select(domain_events)).all() == []
    engine.dispose()


def test_0017_restart_validates_the_single_closed_baseline_event() -> None:
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, domain_events, heads, watermarks = (
        _sqlite_0017_tables()
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata.create_all(connection)
        _insert_0017_baseline(
            connection,
            deployments,
            states,
            audit_events,
            domain_events,
            heads,
            watermarks,
        )
        connection.execute(domain_events.update().values(actor_id="untrusted"))
        connection.commit()
        with pytest.raises(
            migration["SchedulerInitializationError"],
            match="paper.updated event",
        ):
            _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        assert len(connection.execute(select(domain_events)).all()) == 1
    engine.dispose()


@pytest.mark.parametrize("support", ["audit_chain_heads", "event_stream_watermarks"])
def test_0017_restart_rejects_ambiguous_support_state(
    support: str,
) -> None:
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, domain_events, heads, watermarks = (
        _sqlite_0017_tables()
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata.create_all(connection)
        _insert_0017_baseline(
            connection,
            deployments,
            states,
            audit_events,
            domain_events,
            heads,
            watermarks,
        )
        if support == "audit_chain_heads":
            connection.execute(heads.update().values(event_sha256="f" * 64))
        else:
            connection.execute(watermarks.update().values(last_sequence=99))
        connection.commit()
        with pytest.raises(
            migration["SchedulerInitializationError"],
            match="support state",
        ):
            _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        assert len(connection.execute(select(states)).all()) == 1
        assert len(connection.execute(select(audit_events)).all()) == 1
        assert len(connection.execute(select(domain_events)).all()) == 1
    engine.dispose()


def test_0017_scheduler_state_initialization_rolls_back_on_missing_or_ambiguous_history() -> (
    None
):
    migration = _load_0017_migration()
    metadata, deployments, states, audit_events, _, _, _ = _sqlite_0017_tables()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata.create_all(connection)
        connection.execute(
            deployments.insert(),
            [
                {
                    "id": "paper-missing",
                    "workspace_id": "workspace-1",
                    "paper_id": "PAPER-550e8400-e29b-41d4-a716-446655440001",
                    "status": "ACTIVE",
                    "revision": 1,
                },
                {
                    "id": "paper-ambiguous",
                    "workspace_id": "workspace-2",
                    "paper_id": "PAPER-550e8400-e29b-41d4-a716-446655440002",
                    "status": "ACTIVE",
                    "revision": 1,
                },
            ],
        )
        connection.execute(
            states.insert(),
            [
                {
                    "id": "state-ambiguous-1",
                    "workspace_id": "workspace-2",
                    "paper_id": "paper-ambiguous",
                    "scheduler_status": "ACTIVE",
                    "suppressed_since_utc": None,
                    "resume_watermark_utc": datetime(2026, 1, 5, tzinfo=UTC),
                    "revision": 1,
                },
                {
                    "id": "state-ambiguous-2",
                    "workspace_id": "workspace-2",
                    "paper_id": "paper-ambiguous",
                    "scheduler_status": "ACTIVE",
                    "suppressed_since_utc": None,
                    "resume_watermark_utc": datetime(2026, 1, 5, tzinfo=UTC),
                    "revision": 1,
                },
            ],
        )
        connection.commit()
        with pytest.raises(
            migration["SchedulerInitializationError"],
            match="missing.*ambiguous.*readiness blocked",
        ):
            _invoke_0017(migration, connection)
        assert not connection.in_transaction()
        rows = connection.execute(select(states)).mappings().all()
        assert {row["id"] for row in rows} == {
            "state-ambiguous-1",
            "state-ambiguous-2",
        }
        assert connection.execute(select(audit_events)).all() == []
    engine.dispose()


def test_event_migration_canonicalizes_legacy_and_checks_future_values(
    tmp_path: Path,
) -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic/versions/0012_closed_event_contract.py")
    )
    assert tuple(migration["EVENT_TYPES"]) == EVENT_TYPES
    database = tmp_path / "event-migration.db"
    database_url = f"sqlite:///{database}"
    _upgrade(database_url, "0011_provider_credentials")
    engine = create_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id,email,role,revision) VALUES "
                "('migration-owner','migration-owner@example.invalid','OWNER',1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO workspaces (id,owner_id,name,revision) VALUES "
                "('workspace','migration-owner','Migration workspace',1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO records "
                "(id,kind,revision,body,workspace_id) VALUES "
                "('SETTINGS-DEFAULT','settings',2,'{}','workspace')"
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO domain_events
                  (event_id, workspace_id, actor_id, event_type, object_type,
                   object_id, revision, payload, request_id, occurred_at, expires_at)
                VALUES
                  ('EVT-550e8400-e29b-41d4-a716-446655440000',
                   'workspace', 'actor', 'settings.UPDATED',
                   'settings', 'SETTINGS-DEFAULT',
                   2, '{"artifact_id":"must-drop"}',
                   NULL, :occurred_at, :expires_at),
                  (NULL,
                   'workspace', 'actor', 'future.secret_event',
                   'holdout', 'VAL-550e8400-e29b-41d4-a716-446655440001',
                   1, '{"credential":"must-not-leak"}',
                   NULL, :occurred_at, :expires_at)
                """
            ),
            {
                "occurred_at": now.isoformat(),
                "expires_at": (now + timedelta(days=7)).isoformat(),
            },
        )
    _upgrade(database_url, "head")
    with engine.begin() as connection:
        rows = (
            connection.execute(
                text(
                    """
                SELECT event_id, event_type, payload, request_id
                FROM domain_events ORDER BY sequence
                """
                )
            )
            .mappings()
            .all()
        )
        assert rows[0]["event_type"] == "setup.completed"
        assert rows[0]["payload"] == "{}"
        assert rows[0]["request_id"].startswith("REQ-MIGRATED-")
        assert rows[1]["event_type"] == "system.resync_required"
        assert is_public_id("domain_event", rows[1]["event_id"])
        assert "credential" not in rows[1]["payload"]
        assert "RESYNC_REQUIRED" in rows[1]["payload"]
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO domain_events
                      (event_id, event_type, object_type, object_id, payload,
                       request_id, occurred_at, expires_at)
                    VALUES
                      ('EVT-rejected', 'future.rejected', 'test', 'rejected', '{}',
                       'REQ-rejected', :occurred_at, :expires_at)
                    """
                ),
                {
                    "occurred_at": now.isoformat(),
                    "expires_at": (now + timedelta(days=7)).isoformat(),
                },
            )
    engine.dispose()


def test_section14_downgrade_upgrade_preserves_every_table_and_content(
    tmp_path: Path,
) -> None:
    database = tmp_path / "section14-roundtrip.db"
    database_url = f"sqlite:///{database}"
    _upgrade(database_url, "0011_provider_credentials")
    engine = create_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO domain_events
                  (event_id, workspace_id, actor_id, event_type, object_type,
                   object_id, revision, payload, request_id, occurred_at, expires_at)
                VALUES
                  ('EVT-550e8400-e29b-41d4-a716-446655440002',
                   'roundtrip-workspace', 'actor',
                   'system.health.updated', 'job',
                   'JOB-550e8400-e29b-41d4-a716-446655440002', 7,
                   '{"state":"HEALTHY"}', 'REQ-roundtrip', :occurred_at, :expires_at)
                """
            ),
            {
                "occurred_at": now.isoformat(),
                "expires_at": (now + timedelta(days=7)).isoformat(),
            },
        )
    _upgrade(database_url, "head")
    with engine.begin() as connection:
        first_workspace = connection.execute(
            text("SELECT id FROM workspaces LIMIT 1")
        ).scalar_one()
        second_workspace = uuid.uuid4().hex
        connection.execute(
            text(
                "INSERT INTO users (id,email,role,revision) VALUES "
                "('roundtrip-owner-2','roundtrip-owner-2@example.invalid','OWNER',1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO workspaces (id,owner_id,name,revision) VALUES "
                "(:id,'roundtrip-owner-2','Second roundtrip workspace',1)"
            ),
            {"id": second_workspace},
        )
        record_table = Table("records", MetaData(), autoload_with=connection)
        connection.execute(
            record_table.insert(),
            [
                {
                    "id": uuid.uuid4().hex,
                    "workspace_id": str(first_workspace),
                    "record_key": "SETTINGS-DEFAULT",
                    "kind": "settings",
                    "revision": 7,
                    "body": '{"workspace":"first","retained":true}',
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": uuid.uuid4().hex,
                    "workspace_id": second_workspace,
                    "record_key": "SETTINGS-DEFAULT",
                    "kind": "settings",
                    "revision": 11,
                    "body": '{"workspace":"second","retained":true}',
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )
    before = _database_fingerprint(engine)
    assert len(before) == 63
    _downgrade(database_url, "0015_langgraph_checkpoint")
    with engine.connect() as connection:
        backup_names = {
            name
            for name in inspect(connection).get_table_names()
            if name.startswith("_qf0016_roundtrip_")
        }
        downgraded_records = (
            connection.execute(
                text(
                    "SELECT id, workspace_id, record_key, kind, revision, body "
                    "FROM records WHERE kind = 'settings' ORDER BY workspace_id"
                )
            )
            .mappings()
            .all()
        )
        assert {
            (
                str(row["workspace_id"]),
                row["record_key"],
                row["kind"],
                row["revision"],
                row["body"],
            )
            for row in downgraded_records
        } == {
            (
                str(first_workspace),
                "SETTINGS-DEFAULT",
                "settings",
                7,
                '{"workspace":"first","retained":true}',
            ),
            (
                second_workspace,
                "SETTINGS-DEFAULT",
                "settings",
                11,
                '{"workspace":"second","retained":true}',
            ),
        }
        assert all(row["id"] != row["record_key"] for row in downgraded_records)
        settings_fk = next(
            foreign_key
            for foreign_key in inspect(connection).get_foreign_keys("setup_bindings")
            if foreign_key["name"] == "fk_setup_bindings_settings_record_records"
        )
        assert settings_fk["constrained_columns"] == [
            "workspace_id",
            "settings_record_id",
        ]
        assert settings_fk["referred_columns"] == ["workspace_id", "record_key"]
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    assert backup_names == {f"_qf0016_roundtrip_{name}" for name in before}
    _upgrade(database_url, "head")
    after = _database_fingerprint(engine)
    assert after == before
    with engine.connect() as connection:
        assert not any(
            name.startswith("_qf0016_")
            for name in inspect(connection).get_table_names()
        )
    engine.dispose()


def test_section14_agent_config_multi_role_mapping_is_lossless(
    tmp_path: Path,
) -> None:
    database = tmp_path / "section14-agent-config-roles.db"
    database_url = f"sqlite:///{database}"
    _upgrade(database_url, "0015_langgraph_checkpoint")
    engine = create_engine(database_url)
    roles = {
        "RESEARCH_DIRECTOR",
        "FACTOR_SCIENTIST",
        "STRATEGY_SCIENTIST",
        "PORTFOLIO_ANALYST",
        "RED_TEAM_RESEARCHER",
        "PERFORMANCE_ANALYST",
    }
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO agent_configs
                  (role, workspace_id, enabled, revision, model_provider,
                   model_name, runtime_profile, tool_timeout_seconds,
                   max_steps_override, max_tool_calls_override, created_at,
                   updated_at)
                VALUES
                  (:role, 'multi-role-workspace', 1, 7, 'local', 'model',
                   'DEFAULT', 30, 12, 20, :created_at, :updated_at)
                """
            ),
            [
                {
                    "role": role,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                for role in sorted(roles)
            ],
        )

    _upgrade(database_url, "head")
    before = _database_fingerprint(engine)
    with engine.connect() as connection:
        assert {
            row.role_key
            for row in connection.execute(text("SELECT role_key FROM agent_configs"))
        } == roles

    _downgrade(database_url, "0015_langgraph_checkpoint")
    with engine.connect() as connection:
        downgraded = connection.execute(
            text("SELECT role_key, revision, model_provider FROM agent_configs")
        ).all()
        assert {row.role_key for row in downgraded} == roles
        assert {row.revision for row in downgraded} == {7}
        assert {row.model_provider for row in downgraded} == {"local"}

    _upgrade(database_url, "head")
    assert _database_fingerprint(engine) == before
    engine.dispose()


def test_section14_failed_upgrade_restores_all_source_rows(tmp_path: Path) -> None:
    database = tmp_path / "section14-rollback.db"
    database_url = f"sqlite:///{database}"
    _upgrade(database_url, "0015_langgraph_checkpoint")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO domain_events
                  (event_id, workspace_id, actor_id, event_type, object_type,
                   object_id, revision, payload, request_id, occurred_at, expires_at)
                VALUES
                  ('EVT-550e8400-e29b-41d4-a716-446655440003',
                   'rollback-workspace', 'actor',
                   'system.health.updated', 'job',
                   'JOB-550e8400-e29b-41d4-a716-446655440003', 3, '{}',
                   'REQ-rollback', 'not-a-date', 'also-not-a-date')
                """
            )
        )
    before = _database_fingerprint(engine)
    with pytest.raises(ValueError, match="Invalid isoformat"):
        _upgrade(database_url, "head")
    after = _database_fingerprint(engine)
    assert after == before
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == ("0015_langgraph_checkpoint")
        assert not any(
            name.startswith("_qf0016_")
            for name in inspect(connection).get_table_names()
        )
    engine.dispose()


def test_postgres_section14_populated_downgrade_upgrade_preserves_content() -> None:
    database = f"qf_section14_roundtrip_{uuid.uuid4().hex}"
    try:
        with psycopg.connect("dbname=postgres", autocommit=True) as admin:
            admin.execute(f'CREATE DATABASE "{database}"')
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL unavailable: {exc}")

    database_url = f"postgresql+psycopg:///{database}"
    engine = create_engine(database_url)
    public_uuid = uuid.uuid4()
    workspace_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    try:
        _upgrade(database_url, "0015_langgraph_checkpoint")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users (id, email, role, revision)
                    VALUES (:actor_id, :email, 'OWNER', 1)
                    """
                ),
                {
                    "actor_id": f"USR-{public_uuid}",
                    "email": f"section14-{public_uuid}@example.test",
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO workspaces (id, owner_id, name, revision)
                    VALUES (:workspace_id, :actor_id, 'Section 14 roundtrip', 1)
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "actor_id": f"USR-{public_uuid}",
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO domain_events
                      (sequence, event_id, event_type, object_type, object_id,
                       revision, payload, occurred_at, expires_at, request_id,
                       correlation_id, causation_id, workspace_id, actor_id)
                    VALUES
                          (1, :event_id, 'system.health.updated', 'event_stream',
                           :event_id, 1, :payload,
                       :occurred_at, :expires_at, :request_id, :correlation_id,
                       :causation_id, :workspace_id, :actor_id)
                    """
                ),
                {
                    "event_id": f"EVT-{uuid.uuid4()}",
                    "job_id": f"JOB-{uuid.uuid4()}",
                    "payload": json.dumps(
                        {
                            "items": [1, 2],
                            "nested": {"flag": True},
                            "status": "QUEUED",
                        }
                    ),
                    "occurred_at": now,
                    "expires_at": now + timedelta(days=30),
                    "request_id": f"REQ-{uuid.uuid4()}",
                    "correlation_id": f"REQ-{uuid.uuid4()}",
                    "causation_id": f"REQ-{uuid.uuid4()}",
                    "workspace_id": workspace_id,
                    "actor_id": f"USR-{public_uuid}",
                },
            )

        _upgrade(database_url, "head")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT column_default FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'records' "
                        "AND column_name = 'id'"
                    )
                ).scalar_one()
                == "uuidv7()"
            )
        before = _database_fingerprint(engine)
        assert len(before) == 63
        assert sum(count for count, _ in before.values()) == 3

        _downgrade(database_url, "0015_langgraph_checkpoint")
        with engine.connect() as connection:
            backup_names = {
                name
                for name in inspect(connection).get_table_names()
                if name.startswith("_qf0016_roundtrip_")
            }
        assert backup_names == {f"_qf0016_roundtrip_{name}" for name in before}

        _upgrade(database_url, "head")
        assert _database_fingerprint(engine) == before
        with engine.connect() as connection:
            assert not any(
                name.startswith("_qf0016_")
                for name in inspect(connection).get_table_names()
            )
    finally:
        engine.dispose()
        with psycopg.connect("dbname=postgres", autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')


def test_postgres_schema_bootstrap_flag_fails_closed_before_connect() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "QF_ENVIRONMENT": "test",
            "QF_DATABASE_URL": "postgresql+psycopg://invalid:invalid@127.0.0.1:1/invalid",
            "QF_ALLOW_TEST_SCHEMA_BOOTSTRAP": "1",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "test schema bootstrap is allowed only for SQLite tests" in (
        result.stdout + result.stderr
    )


def test_pg18_entrypoint_explicitly_disables_schema_bootstrap() -> None:
    script = (BACKEND_ROOT / "scripts/pg18_ci.sh").read_text()
    assert "export QF_ALLOW_TEST_SCHEMA_BOOTSTRAP=0" in script
    assert "unset QF_ALLOW_TEST_SCHEMA_BOOTSTRAP" not in script
    assert "Alembic-only schema" in script
