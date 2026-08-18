from __future__ import annotations

import os
import sys
from pathlib import Path
from sqlalchemy import engine_from_config, event, make_url, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.control_plane import (  # noqa: E402
    CONTROL_METADATA,
    _control_path,
    register_sqlite_control_functions,
)

config = context.config
database_url = make_url(os.getenv("QF_CONTROL_DB_URL") or f"sqlite:///{_control_path()}")
if database_url.drivername.startswith("sqlite"):
    database = database_url.database
    if not database or database == ":memory:":
        database_path = None
    else:
        database_path = database
    if database_path is None:
        pass
    elif database_path.startswith("file:"):
        raise RuntimeError("SQLite URI filenames are not supported for control migrations")
    else:
        expanded_database_path = Path(database_path).expanduser()
        database_url = database_url.set(database=str(expanded_database_path))
        expanded_database_path.parent.mkdir(
            mode=0o750, parents=True, exist_ok=True
        )
database_url_text = database_url.render_as_string(hide_password=False)
config.set_main_option("sqlalchemy.url", database_url_text.replace("%", "%%"))
target_metadata = CONTROL_METADATA


def run_migrations_offline() -> None:
    if database_url.drivername.startswith("sqlite"):
        raise RuntimeError(
            "Offline SQL generation is not supported for control-plane SQLite migrations"
        )
    context.configure(
        url=database_url_text, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    injected_connection = config.attributes.get("connection")
    if injected_connection is not None:
        if injected_connection.dialect.name == "sqlite":
            driver_connection = injected_connection.connection.driver_connection
            driver_connection.execute("PRAGMA foreign_keys=ON")
            if driver_connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise RuntimeError(
                    "SQLite control-plane migrations require foreign_keys=ON"
                )
            register_sqlite_control_functions(
                driver_connection
            )
        context.configure(connection=injected_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    if database_url.drivername.startswith("sqlite"):

        @event.listens_for(connectable, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
            register_sqlite_control_functions(dbapi_connection)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
