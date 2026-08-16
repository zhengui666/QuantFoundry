"""NautilusTrader v2 bridge for the canonical live connector port."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol

from quantfoundry.live.connector import (
    ConnectorCapabilities,
    ConnectorError,
    ConnectorProtocolError,
    ConnectorUnavailable,
    OrderRequest,
    _segment,
    _validate_order_response,
)

NautilusMethod = Literal["GET", "POST"]


class NautilusTraderPort(Protocol):
    """Bridge boundary implemented by the NautilusTrader runtime."""

    def request(
        self,
        method: NautilusMethod,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Mapping[str, Any]: ...


class NautilusTraderUnavailable(ConnectorUnavailable):
    """The NautilusTrader bridge is unavailable or returned an unknown outcome."""


class NautilusTraderConnector:
    """Map QF connector operations to a NautilusTrader v2 execution port.

    The bridge owns venue-specific Nautilus objects. QF sends only canonical wire
    payloads and never imports or reflects NautilusTrader runtime internals.
    """

    def __init__(self, port: NautilusTraderPort) -> None:
        if not callable(getattr(port, "request", None)):
            raise ValueError("NautilusTrader port must expose request()")
        self._port = port

    def _request(
        self,
        method: NautilusMethod,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = self._port.request(
                method,
                path,
                payload=None if payload is None else dict(payload),
                idempotency_key=idempotency_key,
            )
        except ConnectorError:
            raise
        except Exception as error:
            raise NautilusTraderUnavailable(
                "NautilusTrader bridge request outcome is unknown"
            ) from error
        if not isinstance(result, Mapping):
            raise ConnectorProtocolError("NautilusTrader response must be an object")
        return dict(result)

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities.from_wire(self._request("GET", "/v1/capabilities"))

    def accounts(self) -> list[dict[str, Any]]:
        value = self._request("GET", "/v1/accounts").get("accounts")
        if (
            not isinstance(value, list)
            or not value
            or not all(
                isinstance(item, dict)
                and isinstance(item.get("account_id"), str)
                and bool(item["account_id"])
                for item in value
            )
        ):
            raise ConnectorProtocolError("accounts response is invalid")
        return value

    def balances(self, account_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/v1/accounts/{_segment(account_id, 'account_id')}/balances"
        )

    def positions(self, account_id: str) -> list[dict[str, Any]]:
        value = self._request(
            "GET", f"/v1/accounts/{_segment(account_id, 'account_id')}/positions"
        ).get("positions")
        if not isinstance(value, list) or not all(
            isinstance(item, dict) for item in value
        ):
            raise ConnectorProtocolError("positions response is invalid")
        return value

    def preview_order(self, account_id: str, order: OrderRequest) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/preview",
            payload=order.to_wire(),
        )

    def submit_order(
        self,
        account_id: str,
        order: OrderRequest,
        capabilities: ConnectorCapabilities,
    ) -> dict[str, Any]:
        if account_id not in capabilities.account_ids:
            raise ConnectorProtocolError("account is not in connector capabilities")
        capabilities.validate_order(order)
        result = self._request(
            "POST",
            f"/v1/accounts/{_segment(account_id, 'account_id')}/orders",
            payload=order.to_wire(),
            idempotency_key=f"{account_id}:{order.client_order_id}",
        )
        return _validate_order_response(result, order.client_order_id)

    def orders(self, account_id: str, *, cursor: str | None = None) -> dict[str, Any]:
        path = f"/v1/accounts/{_segment(account_id, 'account_id')}/orders"
        if cursor:
            path += f"?cursor={_segment(cursor, 'cursor')}"
        return self._request("GET", path)

    def order(self, account_id: str, broker_order_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/"
            f"{_segment(broker_order_id, 'broker_order_id')}",
        )

    def cancel(self, account_id: str, broker_order_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/"
            f"{_segment(broker_order_id, 'broker_order_id')}/cancel",
            payload={},
            idempotency_key=f"{account_id}:cancel:{broker_order_id}",
        )

    def fills(self, account_id: str, *, cursor: str | None = None) -> dict[str, Any]:
        path = f"/v1/accounts/{_segment(account_id, 'account_id')}/fills"
        if cursor:
            path += f"?cursor={_segment(cursor, 'cursor')}"
        return self._request("GET", path)

    def market_clock(self, venue: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/v1/market/clock?venue={_segment(venue, 'venue')}"
        )
