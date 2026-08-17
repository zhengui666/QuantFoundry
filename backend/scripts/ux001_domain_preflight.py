"""Fail-closed preflight for the singleton Owner/domain namespace migration."""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


def main() -> int:
    database_url = os.getenv("QF_ALEMBIC_URL") or os.getenv("QF_DATABASE_URL")
    if not database_url:
        print(json.dumps({"status": "QUARANTINE", "reason": "DATABASE_URL_MISSING"}))
        return 2
    engine = None
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            missing = sorted({"users", "workspaces"} - tables)
            if missing:
                report = {
                    "users": None,
                    "workspaces": None,
                    "owners": None,
                    "status": "QUARANTINE",
                    "reason": "REQUIRED_TABLE_MISSING",
                    "missing_tables": missing,
                }
            else:
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
                report = {
                    "users": users,
                    "workspaces": workspaces,
                    "owners": owners,
                    "status": (
                        "EMPTY"
                        if users == 0 and workspaces == 0
                        else "READY"
                        if users == 1
                        and workspaces == 1
                        and owners == 1
                        and owner_workspaces == 1
                        else "QUARANTINE"
                    ),
                }
    except (SQLAlchemyError, ValueError):
        report = {
            "users": None,
            "workspaces": None,
            "owners": None,
            "status": "QUARANTINE",
        }
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {"READY", "EMPTY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
