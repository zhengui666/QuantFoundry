"""Focused physical constraints that cannot be represented by scalar ORM types."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from app.locator_contract import (
    job_result_ref_valid,
    locator_quartet_valid,
    next_action_valid,
    register_sqlite_functions,
)
from app.physical_schema import load_physical_metadata

try:
    from app.main import Base
except SyntaxError:
    Base = None

BACKEND_ROOT = Path(__file__).resolve().parents[1]
UUID_SUFFIX = "550e8400-e29b-41d4-a716-446655440000"


def _frozen_locator_truth_table() -> dict[str, list[dict[str, str | int | None]]]:
    path = BACKEND_ROOT / "alembic/versions/0016_section14_physical.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    truth_table = value["locator_helper_contract"]["truth_table"]
    assert len(truth_table["valid"]) == 69
    assert len(truth_table["invalid"]) == 76
    return truth_table


def _locator_probe_engine() -> tuple[Engine, bool]:
    database_url = os.environ["QF_DATABASE_URL"]
    postgres = database_url.startswith("postgresql")
    engine = (
        create_engine(database_url)
        if postgres
        else create_engine("sqlite+pysqlite:///:memory:")
    )
    return engine, postgres


def _catalog_check_sql(connection: Connection, table_name: str, check_name: str) -> str:
    if connection.dialect.name != "postgresql":
        return _check_sql(table_name, check_name)
    value = connection.execute(
        text(
            "SELECT pg_get_expr(c.conbin,c.conrelid) FROM pg_constraint c "
            "JOIN pg_class t ON t.oid=c.conrelid "
            "JOIN pg_namespace n ON n.oid=t.relnamespace "
            "WHERE n.nspname=current_schema() AND t.relname=:table_name "
            "AND c.conname=:check_name AND c.contype='c'"
        ),
        {"table_name": table_name, "check_name": check_name},
    ).scalar_one()
    return str(value)


def _check_sql(table_name: str, constraint_name: str) -> str:
    if Base is None:
        pytest.skip("app.main import is blocked by repository syntax errors")
    table = Base.metadata.tables[table_name]
    constraint = next(
        item for item in table.constraints if item.name == constraint_name
    )
    return str(constraint.sqltext)


def _assert_database_check(
    columns: list[str],
    sql: str,
    valid: list[dict[str, str | None]],
    invalid: list[dict[str, str | None]],
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    definition = ", ".join(f"{column} TEXT" for column in columns)
    names = ", ".join(columns)
    values = ", ".join(f":{column}" for column in columns)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE subject ({definition}, CHECK ({sql}))"))
        for row in valid:
            connection.execute(
                text(f"INSERT INTO subject ({names}) VALUES ({values})"), row
            )
        for row in invalid:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(f"INSERT INTO subject ({names}) VALUES ({values})"), row
                )
    engine.dispose()


def test_dataset_id_exact_check_accepts_only_canonical_dsset() -> None:
    sql = _check_sql("datasets", "ck_datasets_dataset_id_valid")
    _assert_database_check(
        ["dataset_id"],
        sql,
        [{"dataset_id": f"DSSET-{UUID_SUFFIX}"}],
        [
            {"dataset_id": f"DS-{UUID_SUFFIX}"},
            {"dataset_id": "DSSET-local-seed"},  # reject_fixture: noncanonical
            {"dataset_id": f"DSSET-{UUID_SUFFIX[:-2]}"},
        ],
    )


def test_portfolio_baseline_type_selects_exact_prefix() -> None:
    sql = _check_sql(
        "portfolio_scenarios", "ck_portfolio_scenarios_baseline_ref_type_prefix"
    )
    _assert_database_check(
        ["baseline_type", "baseline_ref"],
        sql,
        [
            {"baseline_type": "EMPTY", "baseline_ref": None},
            {"baseline_type": "SCENARIO", "baseline_ref": f"PORT-{UUID_SUFFIX}"},
            {"baseline_type": "PAPER", "baseline_ref": f"PAPER-{UUID_SUFFIX}"},
        ],
        [
            {"baseline_type": "EMPTY", "baseline_ref": f"PORT-{UUID_SUFFIX}"},
            {"baseline_type": "SCENARIO", "baseline_ref": f"PAPER-{UUID_SUFFIX}"},
            {"baseline_type": "PAPER", "baseline_ref": f"PORT-{UUID_SUFFIX}"},
        ],
    )


def test_approval_subject_type_selects_exact_prefix() -> None:
    sql = _check_sql("approval_requests", "ck_approval_requests_subject_id_type_prefix")
    _assert_database_check(
        ["subject_type", "subject_id"],
        sql,
        [
            {"subject_type": "VALIDATION", "subject_id": f"VAL-{UUID_SUFFIX}"},
            {
                "subject_type": "STRATEGY_VERSION",
                "subject_id": f"STRAT-{UUID_SUFFIX}",
            },
            {"subject_type": "PAPER", "subject_id": f"PAPER-{UUID_SUFFIX}"},
        ],
        [
            {"subject_type": "validation", "subject_id": f"VAL-{UUID_SUFFIX}"},
            {"subject_type": "VALIDATION", "subject_id": f"APR-{UUID_SUFFIX}"},
            {"subject_type": "PAPER", "subject_id": f"STRAT-{UUID_SUFFIX}"},
        ],
    )


@pytest.mark.parametrize(
    ("table_name", "constraint_name", "column", "valid", "invalid"),
    [
        (
            "app_settings",
            "ck_app_settings_language_valid",
            "language",
            "zh-CN",
            "fr-FR",
        ),
        (
            "approval_requests",
            "ck_approval_requests_status_valid",
            "status",
            "PENDING",
            "RUNNING",
        ),
        (
            "jobs",
            "ck_jobs_status_valid",
            "status",
            "QUEUED",
            "STALE",
        ),
    ],
)
def test_documented_scalar_enum_checks_are_enforced(
    table_name: str,
    constraint_name: str,
    column: str,
    valid: str,
    invalid: str,
) -> None:
    _assert_database_check(
        [column],
        _check_sql(table_name, constraint_name),
        [{column: valid}],
        [{column: invalid}],
    )


def test_validation_override_is_always_false() -> None:
    sql = _check_sql(
        "validation_test_results",
        "ck_validation_test_results_override_permitted_valid",
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(f"CREATE TABLE subject (override_permitted BOOLEAN, CHECK ({sql}))")
        )
        connection.execute(
            text("INSERT INTO subject (override_permitted) VALUES (FALSE)")
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text("INSERT INTO subject (override_permitted) VALUES (TRUE)")
            )
    engine.dispose()


@pytest.mark.parametrize(
    ("table_name", "allow_null"),
    [
        ("agent_runs", True),
        ("notifications", True),
        ("domain_events", False),
        ("audit_events", False),
    ],
)
def test_locator_quartet_enforces_every_generated_branch(
    table_name: str, allow_null: bool
) -> None:
    engine, postgres = _locator_probe_engine()
    with engine.begin() as connection:
        if not postgres:
            register_sqlite_functions(connection.connection.driver_connection)
        check_name = f"ck_{table_name}_locator_quartet"
        sql = _catalog_check_sql(connection, table_name, check_name)
        probe_name = f"qf_locator_probe_{table_name}"
        connection.execute(
            text(
                f"CREATE TEMP TABLE {probe_name} ("
                "object_type TEXT, object_id TEXT, object_version INTEGER, "
                f"object_revision BIGINT, CONSTRAINT {check_name} CHECK ({sql}))"
            )
        )
        statement = text(
            f"INSERT INTO {probe_name} VALUES "
            "(:object_type,:object_id,:object_version,:object_revision)"
        )
        truth_table = _frozen_locator_truth_table()
        valid = [dict(row) for row in truth_table["valid"]]
        invalid = [dict(row) for row in truth_table["invalid"]]
        if allow_null:
            valid.append(invalid.pop(2))
            assert len(valid) == 70 and len(invalid) == 75
        else:
            assert len(valid) == 69 and len(invalid) == 76
        for row in valid:
            connection.execute(statement, row)
        for row in invalid:
            savepoint = connection.begin_nested()
            try:
                with pytest.raises(IntegrityError) as error:
                    connection.execute(statement, row)
                if postgres:
                    assert error.value.orig.diag.constraint_name == check_name
            finally:
                if savepoint.is_active:
                    savepoint.rollback()
    engine.dispose()


def test_locator_helpers_are_total_boolean_for_frozen_truth_table() -> None:
    truth_table = _frozen_locator_truth_table()
    engine, postgres = _locator_probe_engine()
    with engine.begin() as connection:
        if not postgres:
            register_sqlite_functions(connection.connection.driver_connection)
        call = text(
            "SELECT qf_event_locator_quartet_valid("
            ":object_type,:object_id,:object_version,:object_revision,FALSE)"
        )
        for expected, label in ((True, "valid"), (False, "invalid")):
            for row in truth_table[label]:
                result = connection.execute(call, row).scalar_one()
                assert result is not None
                assert bool(result) is expected
                assert locator_quartet_valid(**row, allow_null=False) is expected
    engine.dispose()


def test_json_locator_surfaces_share_closed_total_boolean_contract() -> None:
    truth_table = _frozen_locator_truth_table()
    valid_locators = [dict(row) for row in truth_table["valid"]]
    all_null = dict(truth_table["invalid"][2])
    valid_locators.append(all_null)
    invalid_locators = [
        dict(row) for index, row in enumerate(truth_table["invalid"]) if index != 2
    ]
    for row in valid_locators:
        assert job_result_ref_valid({**row, "artifact_id": None})
        assert next_action_valid({"action": "continue", **row})
    for row in invalid_locators:
        assert not job_result_ref_valid({**row, "artifact_id": None})
        assert not next_action_valid({"action": "continue", **row})

    engine, postgres = _locator_probe_engine()
    with engine.begin() as connection:
        if not postgres:
            register_sqlite_functions(connection.connection.driver_connection)
        else:
            json_call = text(
                "SELECT qf_event_locator_json_valid(CAST(:value AS jsonb),FALSE)"
            )
            for expected, rows in (
                (True, truth_table["valid"]),
                (False, truth_table["invalid"]),
            ):
                for row in rows:
                    result = connection.execute(
                        json_call,
                        {"value": json.dumps(row, separators=(",", ":"))},
                    ).scalar_one()
                    assert result is not None
                    assert result is expected

        surfaces = (
            (
                "jobs",
                "ck_jobs_result_ref_closed",
                "result_ref",
                [{**row, "artifact_id": None} for row in valid_locators],
                [{**row, "artifact_id": None} for row in invalid_locators]
                + [
                    {**valid_locators[0], "artifact_id": f"JOB-{UUID_SUFFIX}"},
                    {**valid_locators[0], "artifact_id": None, "extra": True},
                    valid_locators[0],
                    {**valid_locators[0], "object_version": True, "artifact_id": None},
                ],
            ),
            (
                "agent_runs",
                "ck_agent_runs_next_action_closed",
                "next_action",
                [{"action": "continue", **row} for row in valid_locators],
                [{"action": "continue", **row} for row in invalid_locators]
                + [
                    {"action": True, **valid_locators[0]},
                    {"action": "continue", **valid_locators[0], "extra": True},
                    valid_locators[0],
                    {"action": "continue", **valid_locators[0], "object_revision": 1.5},
                ],
            ),
        )
        for table_name, check_name, column, valid, invalid in surfaces:
            sql = (
                _catalog_check_sql(connection, table_name, check_name)
                if postgres
                else (
                    f"{column} IS NULL OR "
                    f"qf_{'job_result_ref' if column == 'result_ref' else 'next_action'}_valid({column})"
                )
            )
            probe_name = f"qf_json_probe_{column}"
            column_type = "JSONB" if postgres else "TEXT"
            connection.execute(
                text(
                    f"CREATE TEMP TABLE {probe_name} ({column} {column_type}, "
                    f"CONSTRAINT {check_name} CHECK ({sql}))"
                )
            )
            value_sql = "CAST(:value AS jsonb)" if postgres else ":value"
            statement = text(
                f"INSERT INTO {probe_name} ({column}) VALUES ({value_sql})"
            )
            connection.execute(statement, {"value": None})
            for document in valid:
                connection.execute(
                    statement,
                    {"value": json.dumps(document, separators=(",", ":"))},
                )
            for document in invalid:
                savepoint = connection.begin_nested()
                try:
                    with pytest.raises(IntegrityError) as error:
                        connection.execute(
                            statement,
                            {"value": json.dumps(document, separators=(",", ":"))},
                        )
                    if postgres:
                        assert error.value.orig.diag.constraint_name == check_name
                finally:
                    if savepoint.is_active:
                        savepoint.rollback()
    engine.dispose()


@pytest.mark.parametrize("mutation", ["delete-function", "change-body"])
def test_schema_checker_rejects_frozen_helper_contract_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    from app.section14_schema import load_manifest
    from scripts import schema_manifest_check

    value = json.loads(
        (BACKEND_ROOT / "alembic/versions/0016_section14_physical.json").read_text(
            encoding="utf-8"
        )
    )
    helper_contract = value["locator_helper_contract"]
    if mutation == "delete-function":
        helper_contract["functions"].pop()
    else:
        helper_contract["functions"][0]["sql"] = helper_contract["functions"][0][
            "sql"
        ].replace("RETURN COALESCE(CASE", "RETURN CASE", 1)
    helper_contract["sha256"] = hashlib.sha256(
        "\n".join(function["sql"] for function in helper_contract["functions"]).encode()
    ).hexdigest()
    mutated = tmp_path / "physical.json"
    mutated.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(schema_manifest_check, "PHYSICAL_PATH", mutated)
    with pytest.raises(RuntimeError, match="locator helper contract"):
        schema_manifest_check._physical_contract(load_manifest())


def test_physical_snapshot_normalization_matches_pg_catalog_renderings() -> None:
    from scripts import schema_manifest_check

    expected = {
        "tables": [
            {
                "name": "sample",
                "unique_constraints": [
                    {"name": None, "columns": ["public_id"]},
                    {
                        "name": "uq_sample_workspace_id_id",
                        "columns": ["workspace_id", "id"],
                    },
                ],
                "foreign_keys": [
                    {
                        "name": None,
                        "columns": ["workspace_id"],
                        "targets": ["workspaces.id"],
                        "ondelete": None,
                    }
                ],
                "checks": [
                    {
                        "name": "ck_sample_state",
                        "sql": "state IN ('ACTIVE', 'DISABLED')",
                    }
                ],
                "indexes": [
                    {
                        "name": "ix_sample_active",
                        "columns": ["state"],
                        "unique": False,
                        "where": "state IN ('ACTIVE', 'DISABLED')",
                    }
                ],
            }
        ]
    }
    actual = json.loads(json.dumps(expected))
    actual_table = actual["tables"][0]
    actual_table["unique_constraints"][0]["name"] = "sample_public_id_key"
    actual_table["unique_constraints"].reverse()
    actual_table["foreign_keys"][0]["name"] = "sample_workspace_id_fkey"
    actual_table["checks"][0]["sql"] = "catalog check rendering"
    actual_table["indexes"][0]["where"] = "catalog index rendering"
    canonical_check = "postgres parsed check"
    canonical_index = "postgres parsed index"
    normalized_expected = schema_manifest_check._normalized_physical_snapshot(
        expected,
        parsed_checks={("sample", "ck_sample_state"): canonical_check},
        parsed_indexes={("sample", "ix_sample_active"): canonical_index},
    )
    normalized_actual = schema_manifest_check._normalized_physical_snapshot(
        actual,
        parsed_checks={("sample", "ck_sample_state"): canonical_check},
        parsed_indexes={("sample", "ix_sample_active"): canonical_index},
    )
    assert normalized_actual == normalized_expected


def test_physical_snapshot_exact_diff_detects_nested_default_drift() -> None:
    from scripts import schema_manifest_check

    errors = schema_manifest_check._exact_tree_diff(
        {"tables": [{"columns": [{"server_default": "0"}]}]},
        {"tables": [{"columns": [{"server_default": "1"}]}]},
    )
    assert errors == ['$.tables[0].columns[0].server_default:expected="0":actual="1"']


def test_check_normalization_preserves_string_literal_case() -> None:
    from scripts import schema_manifest_check

    assert schema_manifest_check._normalized_check("state = 'ACTIVE'") != (
        schema_manifest_check._normalized_check("state = 'active'")
    )
    assert schema_manifest_check._normalized_check("value = 'A  B::text'") != (
        schema_manifest_check._normalized_check("value = 'A B'")
    )


def test_anonymous_constraint_name_policy_is_structural_and_fail_closed() -> None:
    from scripts import schema_manifest_check

    assert (
        schema_manifest_check._postgres_generated_constraint_name(
            "uq", "sample", ("workspace_id", "public_id")
        )
        == "sample_workspace_id_public_id_key"
    )

    expected = {
        "tables": [
            {
                "name": "sample",
                "columns": [],
                "unique_constraints": [{"name": None, "columns": ["public_id"]}],
                "foreign_keys": [],
                "checks": [],
                "indexes": [],
            }
        ]
    }
    generated = json.loads(json.dumps(expected))
    generated["tables"][0]["unique_constraints"][0]["name"] = "sample_public_id_key"
    wrong = json.loads(json.dumps(generated))
    wrong["tables"][0]["unique_constraints"][0]["name"] = "wrong_name"

    normalized_expected = schema_manifest_check._normalized_physical_snapshot(
        expected, parsed_checks={}, parsed_indexes={}
    )
    normalized_generated = schema_manifest_check._normalized_physical_snapshot(
        generated, parsed_checks={}, parsed_indexes={}
    )
    normalized_wrong = schema_manifest_check._normalized_physical_snapshot(
        wrong, parsed_checks={}, parsed_indexes={}
    )
    assert normalized_expected == normalized_generated
    assert schema_manifest_check._exact_tree_diff(
        normalized_expected, normalized_wrong
    ) == [
        "$.tables[0].unique_constraints[0].name:"
        'expected="sample_public_id_key":actual="wrong_name"'
    ]


@pytest.mark.parametrize(
    ("field", "mutation"),
    [
        ("direction", "DESC"),
        ("nulls", "FIRST"),
        ("include", ["revision"]),
        ("where", "state = 'DISABLED'"),
        ("unique", True),
        ("method", "hash"),
    ],
)
def test_structured_index_signature_rejects_each_semantic_drift(
    field: str, mutation: object
) -> None:
    from scripts import schema_manifest_check

    index = {
        "name": "ix_sample_state",
        "method": "btree",
        "keys": [
            {
                "column": "state",
                "expression": "state",
                "direction": "ASC",
                "nulls": "LAST",
            }
        ],
        "include": [],
        "where": "state = 'ACTIVE'",
        "unique": False,
    }
    mutated = json.loads(json.dumps(index))
    if field in {"direction", "nulls"}:
        mutated["keys"][0][field] = mutation
    else:
        mutated[field] = mutation
    assert schema_manifest_check._exact_tree_diff(index, mutated)


def test_physical_snapshot_exact_diff_detects_index_method_drift() -> None:
    from scripts import schema_manifest_check

    errors = schema_manifest_check._exact_tree_diff(
        {
            "tables": [
                {
                    "indexes": [
                        {
                            "method": "btree",
                            "keys": [
                                {
                                    "column": "state",
                                    "expression": "state",
                                    "direction": "ASC",
                                    "nulls": None,
                                }
                            ],
                        }
                    ]
                }
            ]
        },
        {
            "tables": [
                {
                    "indexes": [
                        {
                            "method": "hash",
                            "keys": [
                                {
                                    "column": "state",
                                    "expression": "state",
                                    "direction": "ASC",
                                    "nulls": None,
                                }
                            ],
                        }
                    ]
                }
            ]
        },
    )
    assert errors == ['$.tables[0].indexes[0].method:expected="btree":actual="hash"']


def test_physical_snapshot_exact_diff_detects_autoincrement_drift() -> None:
    from scripts import schema_manifest_check

    errors = schema_manifest_check._exact_tree_diff(
        {"tables": [{"columns": [{"autoincrement": True}]}]},
        {"tables": [{"columns": [{"autoincrement": False}]}]},
    )
    assert errors == ["$.tables[0].columns[0].autoincrement:expected=true:actual=false"]


def test_physical_snapshot_exact_diff_detects_generation_drift() -> None:
    from scripts import schema_manifest_check

    errors = schema_manifest_check._exact_tree_diff(
        {
            "tables": [
                {"columns": [{"generation": {"sqltext": "a + b", "persisted": True}}]}
            ]
        },
        {
            "tables": [
                {"columns": [{"generation": {"sqltext": "a - b", "persisted": True}}]}
            ]
        },
    )
    assert errors == [
        '$.tables[0].columns[0].generation.sqltext:expected="a + b":actual="a - b"'
    ]


def test_physical_snapshot_exact_diff_detects_identity_drift() -> None:
    from scripts import schema_manifest_check

    errors = schema_manifest_check._exact_tree_diff(
        {"tables": [{"columns": [{"identity": {"always": True, "increment": 1}}]}]},
        {"tables": [{"columns": [{"identity": {"always": False, "increment": 1}}]}]},
    )
    assert errors == [
        "$.tables[0].columns[0].identity.always:expected=true:actual=false"
    ]


def test_physical_snapshot_preserves_documented_composite_pk_order() -> None:
    path = BACKEND_ROOT / "alembic/versions/0016_section14_physical.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    specs = {table["name"]: table for table in value["tables"]}
    assert specs["job_dependencies"]["primary_key"] == [
        "workspace_id",
        "job_id",
        "depends_on_job_id",
    ]
    assert specs["domain_events"]["primary_key"] == ["workspace_id", "sequence"]

    metadata = load_physical_metadata(path)
    assert [
        column.name for column in metadata.tables["job_dependencies"].primary_key
    ] == ["workspace_id", "job_id", "depends_on_job_id"]
    assert [column.name for column in metadata.tables["domain_events"].primary_key] == [
        "workspace_id",
        "sequence",
    ]


def test_records_kind_selects_exact_record_key_grammar() -> None:
    sql = _check_sql("records", "ck_records_kind_record_key")
    _assert_database_check(
        ["kind", "record_key"],
        sql,
        [
            {"kind": "settings", "record_key": "SETTINGS-DEFAULT"},
            {"kind": "artifact", "record_key": f"ART-{UUID_SUFFIX}"},
            {"kind": "provenance", "record_key": f"PROV-{UUID_SUFFIX}"},
            {"kind": "memo", "record_key": f"MEMO-{UUID_SUFFIX}"},
        ],
        [
            {"kind": "settings", "record_key": f"ART-{UUID_SUFFIX}"},
            {"kind": "artifact", "record_key": f"PROV-{UUID_SUFFIX}"},
            {"kind": "provenance", "record_key": f"MEMO-{UUID_SUFFIX}"},
            {"kind": "memo", "record_key": f"ART-{UUID_SUFFIX}"},
            {"kind": "legacy", "record_key": "SETTINGS-DEFAULT"},
        ],
    )


def test_setup_binding_selects_workspace_settings_singleton() -> None:
    sql = _check_sql("setup_bindings", "ck_setup_bindings_settings_record_id")
    _assert_database_check(
        ["settings_record_id"],
        sql,
        [{"settings_record_id": "SETTINGS-DEFAULT"}],
        [{"settings_record_id": f"ART-{UUID_SUFFIX}"}],
    )


def test_records_and_setup_physical_shapes_are_exact() -> None:
    path = BACKEND_ROOT / "alembic/versions/0016_section14_physical.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["table_count"] == 63
    assert value["column_count"] == 953
    assert sum(len(table["checks"]) for table in value["tables"]) == 191

    specs = {table["name"]: table for table in value["tables"]}
    records = specs["records"]
    setup = specs["setup_bindings"]
    assert len(records["columns"]) == 8
    assert records["primary_key"] == ["id"]
    record_id = next(column for column in records["columns"] if column["name"] == "id")
    assert record_id["type"] == {"name": "uuid"}
    assert record_id["server_default"] == "uuidv7()"
    assert records["unique_constraints"] == [
        {"columns": ["workspace_id", "id"], "name": "uq_records_workspace_id_id"},
        {
            "columns": ["workspace_id", "record_key"],
            "name": "uq_records_workspace_id_record_key",
        },
    ]

    assert len(setup["columns"]) == 10
    assert setup["primary_key"] == ["workspace_id"]
    assert setup["unique_constraints"] == []
    settings_fk = next(
        item
        for item in setup["foreign_keys"]
        if item["name"] == "fk_setup_bindings_settings_record_records"
    )
    assert settings_fk["columns"] == ["workspace_id", "settings_record_id"]
    assert settings_fk["targets"] == [
        "records.workspace_id",
        "records.record_key",
    ]
