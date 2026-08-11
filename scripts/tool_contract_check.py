#!/usr/bin/env python3
"""Compile and validate the staged Tool registry without mutating source files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-out", required=True, type=Path)
    parser.add_argument("--validate-instance", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    contract_path = repo_root / "docs/后端系统技术方案/contracts/tools/v1-p0.yaml"
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    schema_keys = (
        "$schema",
        "title",
        "type",
        "additionalProperties",
        "required",
        "properties",
    )
    registry_schema = {key: document[key] for key in schema_keys if key in document}
    registry_data = {key: document[key] for key in document["required"]}

    Draft202012Validator.check_schema(registry_schema)
    if args.validate_instance:
        Draft202012Validator(registry_schema).validate(registry_data)

    tools = registry_data["tools"]
    identities = [(tool["name"], tool["version"]) for tool in tools]
    if len(tools) != 13:
        raise SystemExit(f"Expected 13 staged tools, found {len(tools)}")
    if len(set(identities)) != len(identities):
        raise SystemExit("Tool name@version identities must be unique")

    for tool in tools:
        Draft202012Validator.check_schema(tool["input_schema"])
        Draft202012Validator.check_schema(tool["output_schema"])

    args.schema_out.write_text(
        json.dumps(registry_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    mode = "schema and instance" if args.validate_instance else "schema"
    print(
        f"OK: {len(tools)} unique tools; embedded schemas and registry {mode} validate"
    )


if __name__ == "__main__":
    main()
