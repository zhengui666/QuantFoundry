"""Apply the embedded Bootstrap Control DB schema and seed its frozen catalog."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from alembic.config import Config
from sqlalchemy.engine import make_url

from alembic import command

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _side_effect_free_control_path() -> Path:
    test_root = os.getenv("QF_TEST_RUNTIME_ROOT")
    if os.getenv("QF_ENV", "production") == "test" and test_root:
        return Path(test_root) / "control.db"
    data_root = os.getenv("QF_DATA_ROOT")
    return (
        Path(data_root) if data_root else Path.home() / ".quantfoundry"
    ) / "control.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="only report the control DB path"
    )
    args = parser.parse_args()
    configured_url = os.getenv("QF_CONTROL_DB_URL")
    if args.check:
        target = (
            make_url(configured_url).render_as_string(hide_password=True)
            if configured_url
            else str(_side_effect_free_control_path())
        )
        print(f"control_db={target} schema=UX001_D1_R1")
        return 0

    from app.control_plane import (
        CONTROL_ENGINE,
        CONTROL_SCHEMA_VERSION,
        _control_path,
        init_control_db,
    )

    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic_control.ini"))
    config.set_main_option(
        "script_location", str(root / "alembic_control").replace("%", "%%")
    )
    with CONTROL_ENGINE.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        init_control_db(connection)
    target = (
        make_url(configured_url).render_as_string(hide_password=True)
        if configured_url
        else str(_control_path())
    )
    print(f"control_db={target} schema={CONTROL_SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
