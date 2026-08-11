"""Freeze Backend Design section 14 into an independent schema manifest.

This command is intentionally explicit: application startup and migrations never
regenerate the expected schema from ORM metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_DOCUMENT = (
    PROJECT_ROOT
    / "docs/后端系统技术方案/QuantFoundry_Backend_System_Technical_Design_V1.0.0.md"
)
DEFAULT_OUTPUT = BACKEND_ROOT / "schema/section14_manifest.json"
HEADING = re.compile(r"^### (14\.[0-9]+[a-z]?) `([^`]+)`$")
ROW = re.compile(r"^\|(.+)\|$")
EXPECTED_TABLE_COUNT = 63
EXPECTED_COLUMN_COUNT = 953
SUPPORT_TABLES = frozenset(
    {
        "audit_chain_heads",
        "data_snapshots",
        "data_sources",
        "event_stream_watermarks",
        "records",
        "runtime_heartbeats",
        "session_tokens",
        "setup_bindings",
        "snapshot_partitions",
        "users",
        "validations",
        "workspaces",
        "paper_scheduler_states",
    }
)


def _cells(line: str) -> list[str]:
    body = ROW.fullmatch(line)
    if body is None:
        return []
    # A pipe inside an inline-code span is field content, not a table delimiter.
    cells: list[str] = []
    current: list[str] = []
    in_code = False
    escaped = False
    for character in body.group(1):
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            current.append(character)
            escaped = True
        elif character == "`":
            current.append(character)
            in_code = not in_code
        elif character == "|" and not in_code:
            cells.append("".join(current).strip().replace(r"\|", "|"))
            current = []
        else:
            current.append(character)
    if in_code:
        raise ValueError("unterminated inline-code span in schema table")
    cells.append("".join(current).strip().replace(r"\|", "|"))
    return cells


def _plain(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    return value.replace("—", "-")


def extract_manifest(document: Path) -> dict[str, Any]:
    source = document.read_text(encoding="utf-8")
    lines = source.splitlines()
    tables: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = HEADING.fullmatch(lines[index])
        if match is None:
            index += 1
            continue
        section, table_name = match.groups()
        index += 1
        while index < len(lines) and not lines[index].startswith("| 字段 |"):
            if lines[index].startswith("### 14."):
                raise ValueError(f"{table_name}: missing field table")
            index += 1
        if index >= len(lines):
            raise ValueError(f"{table_name}: missing field table")
        index += 2  # header and delimiter
        columns: list[dict[str, Any]] = []
        while index < len(lines):
            cells = _cells(lines[index])
            if len(cells) != 6:
                break
            name, pg_type, nullable, default, constraints, semantics = map(
                _plain, cells
            )
            if nullable not in {"YES", "NO"}:
                raise ValueError(f"{table_name}.{name}: invalid Null={nullable}")
            columns.append(
                {
                    "name": name,
                    "postgres_type": pg_type.lower(),
                    "nullable": nullable == "YES",
                    "default": default,
                    "constraints": constraints,
                    "semantics": semantics,
                }
            )
            index += 1
        if not columns:
            raise ValueError(f"{table_name}: empty field table")
        tables.append(
            {
                "section": section,
                "name": table_name,
                "columns": columns,
            }
        )
    if len(tables) != EXPECTED_TABLE_COUNT:
        raise ValueError(
            f"expected {EXPECTED_TABLE_COUNT} section-14 table definitions, "
            f"got {len(tables)}"
        )
    duplicate_names = sorted(
        name
        for name in {table["name"] for table in tables}
        if sum(table["name"] == name for table in tables) > 1
    )
    if duplicate_names:
        raise ValueError(f"duplicate tables: {duplicate_names}")
    section_source = "\n".join(
        lines[
            next(
                i
                for i, line in enumerate(lines)
                if line == "# 14. PostgreSQL Schema — 字段级定义"
            ) : next(
                i for i, line in enumerate(lines) if line == "# 15. 核心索引与约束"
            )
        ]
    )
    column_count = sum(len(table["columns"]) for table in tables)
    if column_count != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            f"expected {EXPECTED_COLUMN_COUNT} section-14 columns, got {column_count}"
        )
    table_names = {table["name"] for table in tables}
    if not SUPPORT_TABLES <= table_names:
        raise ValueError(
            f"missing support tables: {sorted(SUPPORT_TABLES - table_names)}"
        )
    return {
        "manifest_version": 1,
        "source_path": str(document.relative_to(PROJECT_ROOT)),
        "source_section_sha256": hashlib.sha256(
            section_source.encode("utf-8")
        ).hexdigest(),
        "table_count": len(tables),
        "column_count": column_count,
        "domain_table_count": len(table_names - SUPPORT_TABLES),
        "domain_column_count": sum(
            len(table["columns"])
            for table in tables
            if table["name"] not in SUPPORT_TABLES
        ),
        "support_table_count": len(SUPPORT_TABLES),
        "support_column_count": sum(
            len(table["columns"]) for table in tables if table["name"] in SUPPORT_TABLES
        ),
        "support_tables": sorted(SUPPORT_TABLES),
        "tables": tables,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = extract_manifest(args.document.resolve())
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if (
            not args.output.exists()
            or args.output.read_text(encoding="utf-8") != rendered
        ):
            raise SystemExit("section 14 manifest is stale; regenerate explicitly")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(
        f"wrote {manifest['table_count']} tables/{manifest['column_count']} columns "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
