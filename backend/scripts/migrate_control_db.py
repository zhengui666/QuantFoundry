"""Apply the embedded Bootstrap Control DB schema and seed its frozen catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic.config import Config

from alembic import command

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.control_plane import CONTROL_SCHEMA_VERSION, _control_path, init_control_db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="only report the control DB path"
    )
    args = parser.parse_args()
    if not args.check:
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic_control.ini"))
        config.set_main_option("script_location", str(root / "alembic_control"))
        command.upgrade(config, "head")
        init_control_db()
    print(f"control_db={_control_path()} schema={CONTROL_SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
