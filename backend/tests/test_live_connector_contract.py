from __future__ import annotations

from pathlib import Path

import yaml

CONTRACT = (
    Path(__file__).resolve().parents[2]
    / "docs/后端系统技术方案/contracts/live-connector-v1.yaml"
)


def test_live_connector_contract_is_frozen_and_complete() -> None:
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert document["schema_version"] == "LIVE_CONNECTOR_V1"
    assert document["transport"]["protocol"] == "HTTPS"
    assert document["transport"]["tls_verification"] == "REQUIRED"
    assert document["transport"]["redirects"] == "FORBIDDEN"
    assert document["transport"]["inbound_webhooks"] == "FORBIDDEN"
    assert document["implementations"]["first"]["name"] == "NAUTILUS_TRADER"
    assert (
        document["implementations"]["first"]["integration_mode"]
        == "EXECUTION_CLIENT_PORT"
    )
    assert document["implementations"]["first"]["port"]["method"] == "request"
    assert document["implementations"]["first"]["port"]["response"] == "JSON_OBJECT"
    operations = {(entry["method"], entry["path"]) for entry in document["operations"]}
    assert {
        ("GET", "/v1/capabilities"),
        ("GET", "/v1/accounts"),
        ("GET", "/v1/accounts/{account_id}/balances"),
        ("GET", "/v1/accounts/{account_id}/positions"),
        ("POST", "/v1/accounts/{account_id}/orders/preview"),
        ("POST", "/v1/accounts/{account_id}/orders"),
        ("GET", "/v1/accounts/{account_id}/orders"),
        ("GET", "/v1/accounts/{account_id}/orders/{broker_order_id}"),
        ("POST", "/v1/accounts/{account_id}/orders/{broker_order_id}/cancel"),
        ("GET", "/v1/accounts/{account_id}/fills"),
        ("GET", "/v1/market/clock"),
    } == operations
    assert set(document["assets"]) == {
        "EQUITY",
        "FUTURE",
        "OPTION",
        "FX_SPOT",
        "CRYPTO_SPOT",
        "CRYPTO_PERPETUAL",
    }
    assert document["order"]["types"] == ["MARKET", "LIMIT"]
    assert document["order"]["time_in_force"] == ["DAY", "GTC", "IOC", "FOK"]
    assert document["failure_semantics"]["unknown_order_result"] == "RECONCILING"
