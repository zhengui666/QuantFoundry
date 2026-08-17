"""NautilusTrader v2 bridge for the canonical live connector port."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any, Literal, Protocol

from quantfoundry.live.connector import (
    MARGIN_PREVIEW_ASSETS,
    ConnectorCapabilities,
    ConnectorError,
    ConnectorProtocolError,
    ConnectorUnavailable,
    OrderRequest,
    _idempotency_key,
    _order_fingerprint,
    _purge_expired_fingerprints,
    _segment,
    _validate_balances_response,
    _validate_fills_response,
    _validate_market_clock_response,
    _validate_order_response,
    _validate_orders_response,
    _validate_positions_response,
    _validate_preview_response,
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
        self._preview_fingerprints: dict[str, tuple[float, str]] = {}
        self._order_fingerprints: dict[tuple[str, str], str] = {}
        self._capabilities: ConnectorCapabilities | None = None
        self._capabilities_fetched_at: float | None = None

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
        if (
            self._capabilities is not None
            and self._capabilities_fetched_at is not None
            and time.monotonic() - self._capabilities_fetched_at <= 60
        ):
            return self._capabilities
        value = ConnectorCapabilities.from_wire(
            self._request("GET", "/v1/capabilities")
        )
        self._capabilities = value
        self._capabilities_fetched_at = time.monotonic()
        return value

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
        return _validate_balances_response(
            self._request(
                "GET", f"/v1/accounts/{_segment(account_id, 'account_id')}/balances"
            )
        )

    def positions(self, account_id: str) -> list[dict[str, Any]]:
        result = self._request(
            "GET", f"/v1/accounts/{_segment(account_id, 'account_id')}/positions"
        )
        return _validate_positions_response(result)

    def preview_order(self, account_id: str, order: OrderRequest) -> dict[str, Any]:
        capabilities = self.capabilities()
        result = self._request(
            "POST",
            f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/preview",
            payload=order.to_wire(),
        )
        validated = _validate_preview_response(result)
        now = time.monotonic()
        _purge_expired_fingerprints(self._preview_fingerprints, now)
        self._preview_fingerprints[_order_fingerprint(account_id, order)] = (
            now + 60,
            capabilities.content_hash(),
        )
        return validated

    def submit_order(
        self,
        account_id: str,
        order: OrderRequest,
        capabilities: ConnectorCapabilities,
    ) -> dict[str, Any]:
        capabilities.validate_order(order)
        current_capabilities = self.capabilities()
        if capabilities.content_hash() != current_capabilities.content_hash():
            raise ConnectorProtocolError("caller capabilities are stale or untrusted")
        capabilities = current_capabilities
        if account_id not in capabilities.account_ids:
            raise ConnectorProtocolError("account is not in connector capabilities")
        capabilities.validate_order(order)
        fingerprint = _order_fingerprint(account_id, order)
        identity = (account_id, order.client_order_id)
        previous_fingerprint = self._order_fingerprints.get(identity)
        if previous_fingerprint is not None and previous_fingerprint != fingerprint:
            raise ConnectorProtocolError(
                "client_order_id was reused with a different order payload"
            )
        self._order_fingerprints[identity] = fingerprint
        if order.instrument.asset_class in MARGIN_PREVIEW_ASSETS:
            _purge_expired_fingerprints(self._preview_fingerprints, time.monotonic())
            preview = self._preview_fingerprints.get(fingerprint)
            if (
                preview is None
                or preview[0] <= time.monotonic()
                or preview[1] != capabilities.content_hash()
            ):
                raise ConnectorProtocolError("validated margin preview is required")
        result = self._request(
            "POST",
            f"/v1/accounts/{_segment(account_id, 'account_id')}/orders",
            payload=order.to_wire(),
            idempotency_key=_idempotency_key(
                "submit", account_id, order.client_order_id
            ),
        )
        validated = _validate_order_response(result, order.client_order_id)
        if order.instrument.asset_class in MARGIN_PREVIEW_ASSETS:
            self._preview_fingerprints.pop(fingerprint, None)
        return validated

    def orders(
        self,
        account_id: str,
        *,
        cursor: str | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        path = f"/v1/accounts/{_segment(account_id, 'account_id')}/orders"
        query: list[str] = []
        if cursor is not None:
            query.append(f"cursor={_segment(cursor, 'cursor')}")
        if client_order_id is not None:
            query.append(
                f"client_order_id={_segment(client_order_id, 'client_order_id')}"
            )
        if query:
            path += "?" + "&".join(query)
        return _validate_orders_response(self._request("GET", path), client_order_id)

    def order(self, account_id: str, broker_order_id: str) -> dict[str, Any]:
        return _validate_order_response(
            self._request(
                "GET",
                f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/"
                f"{_segment(broker_order_id, 'broker_order_id')}",
            ),
            None,
        )

    def cancel(self, account_id: str, broker_order_id: str) -> dict[str, Any]:
        return _validate_order_response(
            self._request(
                "POST",
                f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/"
                f"{_segment(broker_order_id, 'broker_order_id')}/cancel",
                payload={},
                idempotency_key=_idempotency_key("cancel", account_id, broker_order_id),
            ),
            None,
        )

    def fills(self, account_id: str, *, cursor: str | None = None) -> dict[str, Any]:
        path = f"/v1/accounts/{_segment(account_id, 'account_id')}/fills"
        if cursor:
            path += f"?cursor={_segment(cursor, 'cursor')}"
        return _validate_fills_response(self._request("GET", path))

    def market_clock(self, venue: str) -> dict[str, Any]:
        return _validate_market_clock_response(
            self._request("GET", f"/v1/market/clock?venue={_segment(venue, 'venue')}")
        )
