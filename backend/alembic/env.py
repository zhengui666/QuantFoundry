import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, event, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).parents[1]))
database_url = os.getenv("QF_ALEMBIC_URL") or os.getenv("QF_DATABASE_URL")
if not database_url:
    raise RuntimeError("QF_ALEMBIC_URL or QF_DATABASE_URL is required")
os.environ.setdefault("QF_DATABASE_URL", database_url)
_previous_alembic_running = os.environ.get("QF_ALEMBIC_RUNNING")
os.environ["QF_ALEMBIC_RUNNING"] = "1"

from quantfoundry.api.app import Base  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    if database_url.startswith("sqlite"):

        @event.listens_for(connectable, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    with connectable.connect() as connection:
        sqlite_migration = database_url.startswith("sqlite")
        if sqlite_migration:
            # Rebuild migrations may contain cyclic composite FKs.  Disable
            # enforcement only on this isolated Alembic connection; every
            # restored schema is checked before the connection is closed and
            # application connections still force foreign_keys=ON.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        if sqlite_migration:
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            if violations:
                raise RuntimeError(
                    f"SQLite migration produced foreign-key violations: {violations[:3]}"
                )
            connection.commit()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 1:
                raise RuntimeError("SQLite migration failed to restore foreign keys")


try:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
finally:
    if _previous_alembic_running is None:
        os.environ.pop("QF_ALEMBIC_RUNNING", None)
    else:
        os.environ["QF_ALEMBIC_RUNNING"] = _previous_alembic_running
