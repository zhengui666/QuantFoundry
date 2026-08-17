from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, event, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.control_plane import CONTROL_METADATA, _control_path  # noqa: E402

config = context.config
database_url = os.getenv("QF_CONTROL_DB_URL") or f"sqlite:///{_control_path()}"
if database_url.startswith("sqlite"):
    _control_path().parent.mkdir(mode=0o750, parents=True, exist_ok=True)
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = CONTROL_METADATA


def run_migrations_offline() -> None:
    if database_url.startswith("sqlite"):
        raise RuntimeError(
            "Offline SQL generation is not supported for control-plane SQLite migrations"
        )
    context.configure(
        url=database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    injected_connection = config.attributes.get("connection")
    if injected_connection is not None:
        context.configure(connection=injected_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    if database_url.startswith("sqlite"):

        @event.listens_for(connectable, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
