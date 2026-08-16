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
    paths = {entry["path"] for entry in document["operations"]}
    assert {
        "/v1/capabilities",
        "/v1/accounts",
        "/v1/accounts/{account_id}/balances",
        "/v1/accounts/{account_id}/positions",
        "/v1/accounts/{account_id}/orders/preview",
        "/v1/accounts/{account_id}/orders",
        "/v1/accounts/{account_id}/orders/{broker_order_id}",
        "/v1/accounts/{account_id}/orders/{broker_order_id}/cancel",
        "/v1/accounts/{account_id}/fills",
        "/v1/market/clock",
    } <= paths
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
