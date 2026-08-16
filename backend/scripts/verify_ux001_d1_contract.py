"""Fail-closed checks for the UX-001 D1 machine contract bundle."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "docs/后端系统技术方案/contracts"


def load(name: str) -> dict:
    value = yaml.safe_load((CONTRACT_ROOT / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must contain an object")
    return value


def main() -> int:
    openapi = load("openapi-v1.yaml")
    catalog = load("configuration-catalog-v1.yaml")
    bootstrap = load("bootstrap-control-v1.yaml")
    matrix = load("ux001-d1-test-matrix.yaml")

    operations = sum(
        1
        for path_item in openapi["paths"].values()
        for method in path_item
        if method in {"get", "post", "put", "patch", "delete"}
    )
    schemas = len(openapi["components"]["schemas"])
    errors = len(openapi["components"]["schemas"]["CanonicalErrorCode"]["enum"])
    expected = openapi["info"]
    assert expected["x-quantfoundry-contract-revision"] == "UX001_D1_R1"
    assert operations == expected["x-quantfoundry-operation-count"] == 65
    assert schemas == expected["x-quantfoundry-schema-count"] == 186
    assert errors == expected["x-quantfoundry-error-count"] == 75
    assert "cookieSession" in openapi["components"]["securitySchemes"]
    assert "bearerAuth" not in openapi["components"]["securitySchemes"]

    assert catalog["status"] == "FROZEN"
    assert catalog["scope"] == "INSTALLATION"
    keys = [entry["key"] for entry in catalog["entries"]]
    assert keys and len(keys) == len(set(keys))
    assert all(entry["scope"] == "INSTALLATION" for entry in catalog["entries"])
    required_entry_fields = {
        "key",
        "group",
        "schema_version",
        "scope",
        "sensitivity",
        "apply_mode",
        "consumers",
        "dependencies",
        "schema",
        "validator",
        "safe_range",
    }
    assert all(required_entry_fields <= set(entry) for entry in catalog["entries"])
    assert (
        expected["x-quantfoundry-configuration-catalog-version"]
        == catalog["catalog_version"]
    )
    assert expected["x-quantfoundry-configuration-entry-count"] == len(keys) == 15

    assert bootstrap["status"] == "TARGET_SCHEMA_FROZEN"
    assert bootstrap["authority"]["physical_source"].startswith("SQLAlchemy")
    assert len(bootstrap["relations"]) == 10
    assert bootstrap["domain_transition"]["target_status"] == "TARGET_TRANSITION_FROZEN"

    assert matrix["status"] == "FROZEN"
    assert matrix["counts"] == {
        "operations": 65,
        "schemas": 186,
        "errors": 75,
        "semantic_tools": 13,
    }
    print("OK: UX-001 D1 machine contract bundle is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
