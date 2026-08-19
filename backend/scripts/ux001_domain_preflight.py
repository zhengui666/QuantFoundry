"""Fail-closed preflight for the singleton Owner/domain namespace migration."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


def _report(connection) -> dict[str, object]:
    tables = set(inspect(connection).get_table_names())
    if not tables:
        return {
            "users": 0,
            "workspaces": 0,
            "owners": 0,
            "status": "EMPTY",
        }
    missing = sorted({"users", "workspaces"} - tables)
    if missing:
        return {
            "users": None,
            "workspaces": None,
            "owners": None,
            "status": "QUARANTINE",
            "reason": "REQUIRED_TABLE_MISSING",
            "missing_tables": missing,
        }
    row = connection.execute(
        text(
            "SELECT "
            "(SELECT count(*) FROM users) AS users, "
            "(SELECT count(*) FROM workspaces) AS workspaces, "
            "(SELECT count(*) FROM users WHERE role = 'OWNER') AS owners, "
            "(SELECT count(*) FROM workspaces w "
            "JOIN users u ON u.id = w.owner_id "
            "WHERE u.role = 'OWNER') AS owner_workspaces"
        )
    ).one()
    users = int(row.users)
    workspaces = int(row.workspaces)
    owners = int(row.owners)
    owner_workspaces = int(row.owner_workspaces)
    return {
        "users": users,
        "workspaces": workspaces,
        "owners": owners,
        "status": (
            "EMPTY"
            if users == 0 and workspaces == 0
            else "READY"
            if users == 1 and workspaces == 1 and owners == 1 and owner_workspaces == 1
            else "QUARANTINE"
        ),
    }


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def _apply_migration(config: Config, database_url: str, connection=None) -> None:
    if connection is not None:
        config.attributes["connection"] = connection
    else:
        config.attributes.pop("connection", None)
    previous_alembic = os.environ.get("QF_ALEMBIC_URL")
    previous_database = os.environ.get("QF_DATABASE_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    os.environ["QF_DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "head")
    finally:
        _restore_env("QF_ALEMBIC_URL", previous_alembic)
        _restore_env("QF_DATABASE_URL", previous_database)


def main() -> int:
    migrate = len(sys.argv) == 2 and sys.argv[1] == "--migrate"
    if len(sys.argv) > 1 and not migrate:
        print("usage: ux001_domain_preflight.py [--migrate]", file=sys.stderr)
        return 2
    database_url = os.getenv("QF_ALEMBIC_URL") or os.getenv("QF_DATABASE_URL")
    if not database_url:
        print(json.dumps({"status": "QUARANTINE", "reason": "DATABASE_URL_MISSING"}))
        return 2
    engine = None
    migration_started = False
    report: dict[str, object] = {
        "users": None,
        "workspaces": None,
        "owners": None,
        "status": "QUARANTINE",
        "reason": "PREFLIGHT_NOT_COMPLETED",
    }
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        with engine.connect() as connection:
            report = _report(connection)
            if migrate and report["status"] in {"READY", "EMPTY"}:
                if connection.dialect.name == "sqlite":
                    report = {
                        **report,
                        "status": "QUARANTINE",
                        "reason": "SQLITE_MIGRATION_REQUIRES_EXCLUSIVE_LOCK",
                    }
                elif connection.dialect.name != "postgresql":
                    report = {
                        **report,
                        "status": "QUARANTINE",
                        "reason": "UNSUPPORTED_MIGRATION_DIALECT",
                    }
                else:
                    # _report() leaves an implicit read transaction open. End it
                    # before binding Alembic to this same connection.
                    connection.commit()
                    migration_started = True
                    with connection.begin():
                        _apply_migration(config, database_url, connection)
                    report = {**_report(connection), "migration": "APPLIED"}
    except Exception as error:
        reason = (
            "MIGRATION_FAILED"
            if migration_started
            else "DATABASE_UNAVAILABLE"
            if isinstance(error, SQLAlchemyError)
            else "INVALID_DATABASE"
            if isinstance(error, ValueError)
            else "MIGRATION_FAILED"
        )
        report = {
            "users": None,
            "workspaces": None,
            "owners": None,
            "status": "QUARANTINE",
            "reason": reason,
        }
        print(f"domain preflight failed: {type(error).__name__}: {error}", file=sys.stderr)
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {"READY", "EMPTY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
