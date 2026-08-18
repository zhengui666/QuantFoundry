"""Small, strict client for the canonical external Live Connector contract."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import quote, urlsplit

import httpcore
import httpx

AssetClass = Literal[
    "EQUITY",
    "FUTURE",
    "OPTION",
    "FX_SPOT",
    "CRYPTO_SPOT",
    "CRYPTO_PERPETUAL",
]
Side = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]
TimeInForce = Literal["DAY", "GTC", "IOC", "FOK"]
PositionEffect = Literal["AUTO", "OPEN", "CLOSE"]

ASSET_CLASSES = frozenset(
    {
        "EQUITY",
        "FUTURE",
        "OPTION",
        "FX_SPOT",
        "CRYPTO_SPOT",
        "CRYPTO_PERPETUAL",
    }
)
ORDER_TYPES = frozenset({"MARKET", "LIMIT"})
TIME_IN_FORCE = frozenset({"DAY", "GTC", "IOC", "FOK"})
POSITION_EFFECTS = frozenset({"AUTO", "OPEN", "CLOSE"})
MARGIN_PREVIEW_ASSETS = frozenset({"FUTURE", "OPTION", "FX_SPOT", "CRYPTO_PERPETUAL"})
SUPPORTED_OPERATIONS = frozenset(
    {
        "GET_ACCOUNT",
        "GET_POSITIONS",
        "PREVIEW_ORDER",
        "SUBMIT_ORDER",
        "GET_ORDER",
        "CANCEL_ORDER",
        "GET_FILLS",
        "GET_MARKET_CLOCK",
    }
)


def _segment(value: str, field_name: str) -> str:
    if not value or value in {".", ".."}:
        raise ValueError(f"{field_name} is required")
    return quote(value, safe="")


def _header_value(value: str, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in value)
    ):
        raise ValueError(f"{field_name} header value is invalid")
    return value


def _connector_endpoint_addresses(endpoint: str) -> tuple[str, ...]:
    parsed = urlsplit(endpoint)
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("connector endpoint hostname is required")
    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(info[4][0])
                for info in socket.getaddrinfo(
                    hostname, parsed.port or 443, type=socket.SOCK_STREAM
                )
            }
        except (OSError, socket.gaierror) as error:
            raise ValueError(
                "connector endpoint hostname could not be resolved"
            ) from error
    if not addresses:
        raise ValueError("connector endpoint hostname has no addresses")
    if any(not address.is_global for address in addresses):
        raise ValueError("connector endpoint must resolve only to global addresses")
    return tuple(str(address) for address in sorted(addresses, key=str))


class _PinnedBackend(httpcore.SyncBackend):
    def __init__(self, addresses: tuple[str, ...]) -> None:
        self.addresses = addresses

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.NetworkStream:
        last_error: Exception | None = None
        for address in self.addresses:
            try:
                return super().connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as error:
                last_error = error
        assert last_error is not None
        raise last_error


def _pinned_http_client(
    endpoint: str, timeout: float, addresses: tuple[str, ...]
) -> tuple[httpx.Client, _PinnedBackend]:
    transport = httpx.HTTPTransport(verify=True, trust_env=False)
    pool = transport._pool
    backend = _PinnedBackend(addresses)
    transport._pool = httpcore.ConnectionPool(
        ssl_context=pool._ssl_context,
        max_connections=pool._max_connections,
        max_keepalive_connections=pool._max_keepalive_connections,
        keepalive_expiry=pool._keepalive_expiry,
        http1=pool._http1,
        http2=pool._http2,
        retries=pool._retries,
        local_address=pool._local_address,
        uds=pool._uds,
        network_backend=backend,
        socket_options=pool._socket_options,
    )
    return (
        httpx.Client(
            base_url=endpoint.rstrip("/"),
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        ),
        backend,
    )


def _idempotency_key(*parts: str) -> str:
    if not parts or any(not isinstance(part, str) for part in parts):
        raise ValueError("idempotency key parts are required")
    operation, account_id, object_id = parts
    if operation not in {"submit", "cancel"}:
        raise ValueError("unsupported idempotency key operation")
    return f"{operation}:{len(account_id)}:{account_id}:{len(object_id)}:{object_id}"


def _order_fingerprint(account_id: str, order: OrderRequest) -> str:
    return hashlib.sha256(
        json.dumps(
            {"account_id": account_id, "order": order.to_wire()},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _validate_order_response(
    result: dict[str, Any],
    client_order_id: str | None,
    broker_order_id: str | None = None,
) -> dict[str, Any]:
    statuses = {
        "CREATED",
        "SUBMITTING",
        "ACKNOWLEDGED",
        "PARTIALLY_FILLED",
        "FILLED",
        "CANCEL_PENDING",
        "CANCELLED",
        "REJECTED",
        "EXPIRED",
        "UNKNOWN",
        "RECONCILING",
    }
    required = {
        "broker_order_id",
        "client_order_id",
        "status",
        "accepted_at",
        "updated_at",
        "fills",
    }
    if (
        not required.issubset(result)
        or not isinstance(result.get("client_order_id"), str)
        or not result["client_order_id"]
        or (
            client_order_id is not None
            and result.get("client_order_id") != client_order_id
        )
        or (
            broker_order_id is not None
            and result.get("broker_order_id") != broker_order_id
        )
        or not isinstance(result.get("broker_order_id"), str)
        or not result["broker_order_id"]
        or result.get("status") not in statuses
        or not _valid_timestamp(result.get("accepted_at"))
            or not _valid_timestamp(result.get("updated_at"))
            or not isinstance(result.get("fills"), list)
            or not all(_validate_fill_entry(fill) for fill in result["fills"])
            or any(
                fill.get("broker_order_id") != result.get("broker_order_id")
                for fill in result.get("fills", [])
            )
    ):
        raise ConnectorProtocolError("order response is invalid")
    return result


def _validate_preview_response(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("approved") is not True:
        raise ConnectorProtocolError("margin preview was not approved")
    return result


def _validate_orders_response(
    result: dict[str, Any], client_order_id: str | None = None
) -> dict[str, Any]:
    orders = result.get("orders")
    if not isinstance(orders, list) or not all(
        isinstance(item, dict) for item in orders
    ):
        raise ConnectorProtocolError("orders response is invalid")
    for item in orders:
        _validate_order_response(item, client_order_id)
    return result


class ConnectorError(RuntimeError):
    """Base error; message never contains credentials or response bodies."""


class ConnectorUnavailable(ConnectorError):
    """The request outcome is unknown and must be reconciled before retry."""


class ConnectorProtocolError(ConnectorError):
    """The peer returned a response outside the frozen contract."""


class ConnectorHTTPError(ConnectorError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"live connector returned HTTP {status_code}")
        self.status_code = status_code


def _decimal(value: str | Decimal, *, field_name: str, positive: bool = False) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{field_name} must be a decimal") from error
    if not parsed.is_finite() or (positive and parsed <= 0):
        raise ValueError(f"{field_name} is invalid")
    return format(parsed, "f")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _valid_response_decimal(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and _decimal_is_valid(value)


def _valid_positive_response_decimal(value: Any) -> bool:
    return (
        _valid_response_decimal(value)
        and Decimal(value) > 0
    )


def _decimal_is_valid(value: str) -> bool:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return False
    return parsed.is_finite()


def _validate_fill_entry(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    fill_id = value.get("broker_fill_id") or value.get("fill_id")
    return (
        isinstance(fill_id, str)
        and bool(fill_id)
        and isinstance(value.get("broker_order_id"), str)
        and bool(value["broker_order_id"])
        and isinstance(value.get("execution_id"), str)
        and bool(value["execution_id"])
        and _valid_positive_response_decimal(value.get("quantity"))
        and _valid_positive_response_decimal(value.get("price"))
        and _valid_timestamp(value.get("executed_at"))
    )


def _validate_balances_response(result: dict[str, Any]) -> dict[str, Any]:
    balances = result.get("balances")
    if not isinstance(balances, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("currency"), str)
        and bool(item["currency"])
        and _valid_response_decimal(item.get("available"))
        and _valid_response_decimal(item.get("total"))
        for item in balances
    ):
        raise ConnectorProtocolError("balances response is invalid")
    return result


def _validate_positions_response(result: dict[str, Any]) -> list[dict[str, Any]]:
    positions = result.get("positions")
    if not isinstance(positions, list):
        raise ConnectorProtocolError("positions response is invalid")
    for item in positions:
        identity = item.get("symbol") if isinstance(item, dict) else None
        price = (
            item.get("average_price", item.get("price"))
            if isinstance(item, dict)
            else None
        )
        if not (
            isinstance(item, dict)
            and isinstance(identity, str)
            and bool(identity)
            and isinstance(item.get("currency"), str)
            and bool(item["currency"])
            and _valid_response_decimal(item.get("quantity"))
            and _valid_response_decimal(price)
        ):
            raise ConnectorProtocolError("positions response is invalid")
    return positions


def _validate_fills_response(result: dict[str, Any]) -> dict[str, Any]:
    fills = result.get("fills")
    if not isinstance(fills, list) or not all(
        _validate_fill_entry(item) for item in fills
    ):
        raise ConnectorProtocolError("fills response is invalid")
    return result


def _validate_market_clock_response(result: dict[str, Any]) -> dict[str, Any]:
    if not (
        isinstance(result.get("venue"), str)
        and bool(result["venue"])
        and isinstance(result.get("state"), str)
        and bool(result["state"])
        and _valid_timestamp(result.get("timestamp"))
    ):
        raise ConnectorProtocolError("market clock response is invalid")
    return result


def _purge_expired_fingerprints(
    store: dict[str, tuple[float, str]], now: float
) -> None:
    for key, (expires_at, _capabilities_hash) in list(store.items()):
        if expires_at <= now:
            del store[key]


def _decimal_places(value: str | Decimal) -> int:
    exponent = Decimal(str(value)).as_tuple().exponent
    if not isinstance(exponent, int):
        raise ValueError("decimal value is not finite")
    return max(0, -exponent)


@dataclass(frozen=True)
class Instrument:
    asset_class: AssetClass
    venue: str
    symbol: str
    currency: str | None = None
    base_currency: str | None = None
    quote_currency: str | None = None
    underlying: str | None = None
    expiry: str | None = None
    strike: str | None = None
    right: Literal["CALL", "PUT"] | None = None
    style: Literal["AMERICAN", "EUROPEAN"] | None = None
    multiplier: str | None = None
    margin_currency: str | None = None

    def __post_init__(self) -> None:
        if self.asset_class not in ASSET_CLASSES:
            raise ValueError("unsupported asset_class")
        if not all(
            isinstance(value, str) and bool(value)
            for value in (self.venue, self.symbol)
        ):
            raise ValueError("venue and symbol are required")
        for name in (
            "currency",
            "base_currency",
            "quote_currency",
            "underlying",
            "expiry",
            "margin_currency",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{name} is invalid")
        allowed_fields = {
            "EQUITY": {"currency"},
            "FUTURE": {"expiry", "multiplier", "currency"},
            "OPTION": {
                "underlying",
                "expiry",
                "strike",
                "right",
                "style",
                "multiplier",
                "currency",
            },
            "FX_SPOT": {"base_currency", "quote_currency"},
            "CRYPTO_SPOT": {"base_currency", "quote_currency"},
            "CRYPTO_PERPETUAL": {"multiplier", "margin_currency"},
        }[self.asset_class]
        for name in (
            "currency",
            "base_currency",
            "quote_currency",
            "underlying",
            "expiry",
            "strike",
            "right",
            "style",
            "multiplier",
            "margin_currency",
        ):
            if name not in allowed_fields and getattr(self, name) is not None:
                raise ValueError(f"{name} is not valid for {self.asset_class}")
        if self.asset_class == "OPTION" and not all(
            (
                self.underlying,
                self.expiry,
                self.strike,
                self.right,
                self.style,
                self.multiplier,
                self.currency,
            )
        ):
            raise ValueError("option contract fields are required")
        if self.asset_class == "OPTION":
            if self.right not in {"CALL", "PUT"}:
                raise ValueError("option right is invalid")
            if self.style not in {"AMERICAN", "EUROPEAN"}:
                raise ValueError("option style is invalid")
            _decimal(self.strike or "", field_name="strike", positive=True)
        if self.asset_class == "FUTURE" and not all(
            (self.expiry, self.multiplier, self.currency)
        ):
            raise ValueError("future contract fields are required")
        if self.asset_class == "EQUITY" and not self.currency:
            raise ValueError("equity currency is required")
        if self.asset_class in {"FX_SPOT", "CRYPTO_SPOT"} and not all(
            (self.base_currency, self.quote_currency)
        ):
            raise ValueError("base_currency and quote_currency are required")
        if self.asset_class == "CRYPTO_PERPETUAL" and not all(
            (self.multiplier, self.margin_currency)
        ):
            raise ValueError("perpetual multiplier and margin_currency are required")
        if self.multiplier is not None:
            _decimal(self.multiplier or "", field_name="multiplier", positive=True)

    def to_wire(self) -> dict[str, Any]:
        value = {
            "asset_class": self.asset_class,
            "venue": self.venue,
            "symbol": self.symbol,
        }
        for key in (
            "currency",
            "base_currency",
            "quote_currency",
            "underlying",
            "expiry",
            "right",
            "style",
            "margin_currency",
        ):
            item = getattr(self, key)
            if item is not None:
                value[key] = item
        if self.strike is not None:
            value["strike"] = _decimal(self.strike, field_name="strike")
        if self.multiplier is not None:
            value["multiplier"] = _decimal(
                self.multiplier, field_name="multiplier", positive=True
            )
        return value


@dataclass(frozen=True)
class OrderRequest:
    client_order_id: str
    instrument: Instrument
    side: Side
    quantity: str | Decimal
    order_type: OrderType
    time_in_force: TimeInForce
    position_effect: PositionEffect = "AUTO"
    limit_price: str | Decimal | None = None
    reduce_only: bool = False
    schema_version: str = "LIVE_CONNECTOR_V1"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.client_order_id, str)
            or not self.client_order_id
            or len(self.client_order_id) > 160
        ):
            raise ValueError("client_order_id is invalid")
        if self.schema_version != "LIVE_CONNECTOR_V1":
            raise ValueError("schema_version is invalid")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side is invalid")
        if self.order_type not in ORDER_TYPES:
            raise ValueError("order_type is invalid")
        if self.time_in_force not in TIME_IN_FORCE:
            raise ValueError("time_in_force is invalid")
        if self.position_effect not in POSITION_EFFECTS:
            raise ValueError("position_effect is invalid")
        if not isinstance(self.reduce_only, bool):
            raise ValueError("reduce_only is invalid")
        _decimal(self.quantity, field_name="quantity", positive=True)
        if self.order_type == "LIMIT":
            if self.limit_price is None:
                raise ValueError("limit_price is required for LIMIT")
            _decimal(self.limit_price, field_name="limit_price", positive=True)
        elif self.limit_price is not None:
            raise ValueError("limit_price is only valid for LIMIT")

    def to_wire(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": self.schema_version,
            "client_order_id": self.client_order_id,
            "instrument": self.instrument.to_wire(),
            "side": self.side,
            "quantity": _decimal(self.quantity, field_name="quantity", positive=True),
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "position_effect": self.position_effect,
            "reduce_only": self.reduce_only,
        }
        if self.limit_price is not None:
            value["limit_price"] = _decimal(
                self.limit_price, field_name="limit_price", positive=True
            )
        return value


@dataclass(frozen=True)
class ConnectorCapabilities:
    protocol_version: str
    connector_id: str
    assets: frozenset[str]
    order_types: frozenset[str]
    time_in_force: frozenset[str]
    supported_operations: frozenset[str]
    quantity_scale: int
    price_scale: int
    account_ids: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_wire(cls, value: Mapping[str, Any]) -> ConnectorCapabilities:
        if not isinstance(value, Mapping):
            raise ConnectorProtocolError("capabilities must be an object")
        required = {
            "protocol_version",
            "connector_id",
            "assets",
            "order_types",
            "time_in_force",
            "quantity_scale",
            "price_scale",
            "account_ids",
            "supported_operations",
        }
        if set(value) != required:
            raise ConnectorProtocolError("capabilities shape is not canonical")
        if value["protocol_version"] != "LIVE_CONNECTOR_V1":
            raise ConnectorProtocolError("unsupported connector protocol")
        if not all(
            isinstance(value[name], list)
            for name in (
                "assets",
                "order_types",
                "time_in_force",
                "account_ids",
                "supported_operations",
            )
        ):
            raise ConnectorProtocolError("capabilities arrays are invalid")
        if not all(
            isinstance(item, str) and item
            for name in ("assets", "order_types", "time_in_force")
            for item in value[name]
        ):
            raise ConnectorProtocolError("capabilities values are invalid")
        if not all(
            isinstance(value[name], str) and value[name]
            for name in ("protocol_version", "connector_id")
        ):
            raise ConnectorProtocolError("capabilities identity is invalid")
        assets = frozenset(value["assets"])
        order_types = frozenset(value["order_types"])
        time_in_force = frozenset(value["time_in_force"])
        if not assets <= ASSET_CLASSES or not order_types <= ORDER_TYPES:
            raise ConnectorProtocolError("capabilities contain unsupported values")
        if not time_in_force <= TIME_IN_FORCE:
            raise ConnectorProtocolError("capabilities contain unsupported TIF")
        if (
            not isinstance(value["quantity_scale"], int)
            or isinstance(value["quantity_scale"], bool)
            or value["quantity_scale"] < 0
        ):
            raise ConnectorProtocolError("quantity_scale is invalid")
        if (
            not isinstance(value["price_scale"], int)
            or isinstance(value["price_scale"], bool)
            or value["price_scale"] < 0
        ):
            raise ConnectorProtocolError("price_scale is invalid")
        accounts = value["account_ids"]
        if not accounts or not all(isinstance(item, str) and item for item in accounts):
            raise ConnectorProtocolError("account_ids is invalid")
        operations = value["supported_operations"]
        if not isinstance(operations, list) or not all(
            isinstance(item, str) and item for item in operations
        ):
            raise ConnectorProtocolError("supported_operations is invalid")
        if not operations or not set(operations) <= SUPPORTED_OPERATIONS:
            raise ConnectorProtocolError(
                "supported_operations contain unsupported values"
            )
        if len(accounts) != len(set(accounts)):
            raise ConnectorProtocolError("account_ids must be unique")
        return cls(
            protocol_version=value["protocol_version"],
            connector_id=value["connector_id"],
            assets=assets,
            order_types=order_types,
            time_in_force=time_in_force,
            supported_operations=frozenset(operations),
            quantity_scale=value["quantity_scale"],
            price_scale=value["price_scale"],
            account_ids=tuple(accounts),
        )

    def content_hash(self) -> str:
        payload = {
            "protocol_version": self.protocol_version,
            "connector_id": self.connector_id,
            "assets": sorted(self.assets),
            "order_types": sorted(self.order_types),
            "time_in_force": sorted(self.time_in_force),
            "quantity_scale": self.quantity_scale,
            "price_scale": self.price_scale,
            "account_ids": list(self.account_ids),
            "supported_operations": sorted(self.supported_operations),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def validate_order(self, order: OrderRequest) -> None:
        if order.instrument.asset_class not in self.assets:
            raise ConnectorProtocolError("asset is not supported by connector")
        if order.order_type not in self.order_types:
            raise ConnectorProtocolError("order type is not supported by connector")
        if order.time_in_force not in self.time_in_force:
            raise ConnectorProtocolError("time in force is not supported by connector")
        required = {
            "GET_ACCOUNT",
            "GET_POSITIONS",
            "SUBMIT_ORDER",
            "GET_ORDER",
            "CANCEL_ORDER",
            "GET_FILLS",
        }
        if not required <= self.supported_operations:
            raise ConnectorProtocolError("connector lacks required order operations")
        if (
            order.instrument.asset_class in MARGIN_PREVIEW_ASSETS
            and "PREVIEW_ORDER" not in self.supported_operations
        ):
            raise ConnectorProtocolError("margin preview is required for this asset")
        if _decimal_places(order.quantity) > self.quantity_scale:
            raise ConnectorProtocolError("order quantity exceeds connector scale")
        if (
            order.limit_price is not None
            and _decimal_places(order.limit_price) > self.price_scale
        ):
            raise ConnectorProtocolError("order price exceeds connector scale")


class ConnectorClient:
    """No-retry client; callers reconcile unknown submit outcomes by client id."""

    def __init__(
        self,
        endpoint: str,
        *,
        key_id: str,
        credential: str,
        timeout: float = 10.0,
        http_client: httpx.Client | None = None,
        clock: Callable[[], float] = time.time,
        monotonic_clock: Callable[[], float] = time.monotonic,
        nonce_factory: Callable[[], str] = lambda: secrets.token_hex(16),
    ) -> None:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("connector endpoint must be an HTTPS origin")
        if (
            not isinstance(key_id, str)
            or not key_id
            or not isinstance(credential, str)
            or not credential
        ):
            raise ValueError("connector key_id and credential are required")
        _header_value(key_id, "key_id")
        addresses = _connector_endpoint_addresses(endpoint)
        self._owns_client = http_client is None
        if http_client is not None and not isinstance(
            getattr(http_client, "_transport", None), httpx.MockTransport
        ):
            raise ValueError("custom connector clients must use a verified transport")
        self._base_url = endpoint.rstrip("/")
        self._key_id = key_id
        self._credential = credential.encode("utf-8")
        self._clock = clock
        self._monotonic_clock = monotonic_clock
        self._nonce_factory = nonce_factory
        self._preview_fingerprints: dict[str, tuple[float, str]] = {}
        self._order_fingerprints: dict[tuple[str, str], str] = {}
        self._orders_requiring_reconciliation: set[tuple[str, str]] = set()
        self._capabilities: ConnectorCapabilities | None = None
        self._capabilities_fetched_at: float | None = None
        if timeout <= 0:
            raise ValueError("connector timeout must be positive")
        self._timeout = timeout
        self._pinned_backend: _PinnedBackend | None = None
        if http_client is None:
            self._client, self._pinned_backend = _pinned_http_client(
                self._base_url, timeout, addresses
            )
        else:
            self._client = http_client
            self._pinned_backend = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ConnectorClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not path.startswith("/") or "#" in path:
            raise ValueError("connector path is invalid")
        addresses = _connector_endpoint_addresses(self._base_url)
        if self._pinned_backend is not None:
            self._pinned_backend.addresses = addresses
        body = (
            b""
            if payload is None
            else json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
        )
        timestamp = str(int(self._clock()))
        nonce = _header_value(self._nonce_factory(), "nonce")
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = "\n".join((method.upper(), path, body_hash, timestamp, nonce))
        signature = hmac.new(
            self._credential, canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-QF-Key-Id": self._key_id,
            "X-QF-Timestamp": timestamp,
            "X-QF-Nonce": nonce,
            "X-QF-Signature": f"v1={signature}",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = _header_value(
                idempotency_key, "idempotency_key"
            )
        try:
            response = self._client.request(
                method,
                f"{self._base_url}{path}",
                content=body,
                headers=headers,
                timeout=self._timeout,
                follow_redirects=False,
            )
        except (
            httpx.InvalidURL,
            httpx.LocalProtocolError,
            httpx.UnsupportedProtocol,
        ) as error:
            raise ConnectorProtocolError(
                "connector transport protocol is invalid"
            ) from error
        except httpx.HTTPError as error:
            raise ConnectorUnavailable(
                "live connector request outcome is unknown"
            ) from error
        if response.status_code == 408 or response.status_code >= 500:
            raise ConnectorUnavailable(
                f"live connector returned ambiguous HTTP {response.status_code}"
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise ConnectorHTTPError(response.status_code)
        try:
            result = response.json()
        except ValueError as error:
            raise ConnectorProtocolError("connector response is not JSON") from error
        if not isinstance(result, dict):
            raise ConnectorProtocolError("connector response must be an object")
        return result

    def capabilities(self) -> ConnectorCapabilities:
        if (
            self._capabilities is not None
            and self._capabilities_fetched_at is not None
            and self._monotonic_clock() - self._capabilities_fetched_at <= 60
        ):
            return self._capabilities
        value = ConnectorCapabilities.from_wire(
            self._request("GET", "/v1/capabilities")
        )
        self._capabilities = value
        self._capabilities_fetched_at = self._monotonic_clock()
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
        now = self._monotonic_clock()
        _purge_expired_fingerprints(self._preview_fingerprints, now)
        self._preview_fingerprints[_order_fingerprint(account_id, order)] = (
            now + 60,
            capabilities.content_hash(),
        )
        return validated

    def submit_order(
        self, account_id: str, order: OrderRequest, capabilities: ConnectorCapabilities
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
        if identity in self._orders_requiring_reconciliation:
            raise ConnectorUnavailable(
                "order outcome is unknown; reconcile by client_order_id before retry"
            )
        previous_fingerprint = self._order_fingerprints.get(identity)
        if previous_fingerprint is not None and previous_fingerprint != fingerprint:
            raise ConnectorProtocolError(
                "client_order_id was reused with a different order payload"
            )
        if order.instrument.asset_class in MARGIN_PREVIEW_ASSETS:
            _purge_expired_fingerprints(self._preview_fingerprints, self._monotonic_clock())
            preview = self._preview_fingerprints.get(fingerprint)
            if (
                preview is None
                or preview[0] <= self._monotonic_clock()
                or preview[1] != capabilities.content_hash()
            ):
                raise ConnectorProtocolError("validated margin preview is required")
        self._order_fingerprints[identity] = fingerprint
        try:
            result = self._request(
                "POST",
                f"/v1/accounts/{_segment(account_id, 'account_id')}/orders",
                payload=order.to_wire(),
                idempotency_key=_idempotency_key(
                    "submit", account_id, order.client_order_id
                ),
            )
        except ConnectorUnavailable:
            self._orders_requiring_reconciliation.add(identity)
            raise
        validated = _validate_order_response(result, order.client_order_id)
        self._orders_requiring_reconciliation.discard(identity)
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
        result = _validate_orders_response(self._request("GET", path), client_order_id)
        if client_order_id is not None and any(
            item.get("client_order_id") == client_order_id for item in result["orders"]
        ):
            self._orders_requiring_reconciliation.discard((account_id, client_order_id))
        return result

    def order(self, account_id: str, broker_order_id: str) -> dict[str, Any]:
        return _validate_order_response(
            self._request(
                "GET",
                f"/v1/accounts/{_segment(account_id, 'account_id')}/orders/"
                f"{_segment(broker_order_id, 'broker_order_id')}",
            ),
            None,
            broker_order_id,
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
            broker_order_id,
        )

    def fills(self, account_id: str, *, cursor: str | None = None) -> dict[str, Any]:
        path = f"/v1/accounts/{_segment(account_id, 'account_id')}/fills"
        if cursor:
            path += f"?cursor={_segment(cursor, 'cursor')}"
        result = self._request("GET", path)
        return _validate_fills_response(result)

    def market_clock(self, venue: str) -> dict[str, Any]:
        return _validate_market_clock_response(
            self._request("GET", f"/v1/market/clock?venue={_segment(venue, 'venue')}")
        )
