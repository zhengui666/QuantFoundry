from __future__ import annotations

from typing import Any

import pytest

from quantfoundry.live.connector import (
    ConnectorCapabilities,
    ConnectorProtocolError,
    ConnectorUnavailable,
    Instrument,
    OrderRequest,
)
from quantfoundry.live.nautilus import (
    NautilusTraderConnector,
    NautilusTraderUnavailable,
)


def _capabilities() -> dict[str, Any]:
    return {
        "protocol_version": "LIVE_CONNECTOR_V1",
        "connector_id": "nautilus-v2",
        "assets": ["EQUITY"],
        "order_types": ["MARKET"],
        "time_in_force": ["DAY"],
        "quantity_scale": 6,
        "price_scale": 8,
        "account_ids": ["acct-1"],
        "supported_operations": [
            "GET_ACCOUNT",
            "GET_POSITIONS",
            "SUBMIT_ORDER",
            "GET_ORDER",
            "CANCEL_ORDER",
            "GET_FILLS",
        ],
    }


class FakePort:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "payload": payload,
                "idempotency_key": idempotency_key,
            }
        )
        if path == "/v1/capabilities":
            return _capabilities()
        if path == "/v1/accounts":
            return {"accounts": [{"account_id": "acct-1"}]}
        return {"status": "ACKNOWLEDGED", "broker_order_id": "b-1"}


def _order() -> OrderRequest:
    return OrderRequest(
        client_order_id="LORD-NT-1",
        instrument=Instrument(
            asset_class="EQUITY", venue="NYSE", symbol="ABC", currency="USD"
        ),
        side="BUY",
        quantity="2",
        order_type="MARKET",
        time_in_force="DAY",
    )


def test_nautilus_port_maps_canonical_submit_and_cancel() -> None:
    port = FakePort()
    connector = NautilusTraderConnector(port)
    capabilities = connector.capabilities()

    assert (
        connector.submit_order("acct-1", _order(), capabilities)["broker_order_id"]
        == "b-1"
    )
    connector.cancel("acct-1", "b-1")

    submit = port.calls[1]
    assert submit["method"] == "POST"
    assert submit["path"] == "/v1/accounts/acct-1/orders"
    assert submit["idempotency_key"] == "LORD-NT-1"
    assert submit["payload"]["schema_version"] == "LIVE_CONNECTOR_V1"
    cancel = port.calls[2]
    assert cancel["path"].endswith("/orders/b-1/cancel")
    assert cancel["idempotency_key"] == "cancel:b-1"


def test_nautilus_port_preserves_unknown_submit_outcome() -> None:
    class TimeoutPort(FakePort):
        def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
            if path.endswith("/orders"):
                raise TimeoutError("bridge timeout")
            return super().request(method, path, **kwargs)

    connector = NautilusTraderConnector(TimeoutPort())
    capabilities = connector.capabilities()
    with pytest.raises(NautilusTraderUnavailable) as error:
        connector.submit_order("acct-1", _order(), capabilities)
    assert isinstance(error.value, ConnectorUnavailable)


def test_nautilus_port_fails_closed_on_missing_order_capability() -> None:
    connector = NautilusTraderConnector(FakePort())
    capabilities = ConnectorCapabilities.from_wire(
        {
            **_capabilities(),
            "supported_operations": ["SUBMIT_ORDER"],
        }
    )
    with pytest.raises(ConnectorProtocolError, match="required order operations"):
        connector.submit_order("acct-1", _order(), capabilities)
