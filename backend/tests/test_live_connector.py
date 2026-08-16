from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from quantfoundry.contracts.openapi.api_models import LiveConnectorValidationRequest
from quantfoundry.live.connector import (
    ConnectorCapabilities,
    ConnectorClient,
    ConnectorProtocolError,
    ConnectorUnavailable,
    Instrument,
    OrderRequest,
)
from quantfoundry.live.policy import (
    ActivationEvidence,
    LivePolicyError,
    apply_fill,
    transition_order,
)


def _capabilities() -> dict[str, object]:
    return {
        "protocol_version": "LIVE_CONNECTOR_V1",
        "connector_id": "fake",
        "assets": ["EQUITY", "OPTION"],
        "order_types": ["MARKET", "LIMIT"],
        "time_in_force": ["DAY", "GTC"],
        "quantity_scale": 6,
        "price_scale": 8,
        "account_ids": ["acct-1"],
        "supported_operations": [
            "GET_ACCOUNT",
            "GET_POSITIONS",
            "PREVIEW_ORDER",
            "SUBMIT_ORDER",
            "GET_ORDER",
            "CANCEL_ORDER",
            "GET_FILLS",
        ],
    }


def test_signed_submit_is_idempotent_and_capability_gated() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/accounts/acct-1/orders":
            return httpx.Response(
                200,
                json={
                    "status": "ACKNOWLEDGED",
                    "broker_order_id": "b-1",
                    "client_order_id": "LORD-1",
                    "accepted_at": "2026-08-17T00:00:00Z",
                    "updated_at": "2026-08-17T00:00:00Z",
                    "fills": [],
                },
            )
        return httpx.Response(200, json=_capabilities())

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="https://connector.test", transport=transport)
    with ConnectorClient(
        "https://connector.test",
        key_id="key-1",
        credential="secret",
        http_client=client,
        clock=lambda: 1_700_000_000,
        nonce_factory=lambda: "nonce-1",
    ) as connector:
        capabilities = connector.capabilities()
        order = OrderRequest(
            client_order_id="LORD-1",
            instrument=Instrument(
                asset_class="EQUITY", venue="NYSE", symbol="ABC", currency="USD"
            ),
            side="BUY",
            quantity="2",
            order_type="MARKET",
            time_in_force="DAY",
        )
        response = connector.submit_order("acct-1", order, capabilities)

    request = seen[-1]
    body = request.content
    canonical = "\n".join(
        (
            "POST",
            "/v1/accounts/acct-1/orders",
            hashlib.sha256(body).hexdigest(),
            "1700000000",
            "nonce-1",
        )
    )
    expected = hmac.new(b"secret", canonical.encode(), hashlib.sha256).hexdigest()
    assert response["broker_order_id"] == "b-1"
    assert request.headers["Idempotency-Key"] == "LORD-1"
    assert request.headers["X-QF-Signature"] == f"v1={expected}"
    assert json.loads(body)["quantity"] == "2"


def test_margin_asset_requires_preview_capability() -> None:
    capabilities = ConnectorCapabilities.from_wire(
        {
            **_capabilities(),
            "assets": ["OPTION"],
            "supported_operations": [
                "GET_ACCOUNT",
                "GET_POSITIONS",
                "SUBMIT_ORDER",
                "GET_ORDER",
                "CANCEL_ORDER",
                "GET_FILLS",
            ],
        }
    )
    order = OrderRequest(
        client_order_id="LORD-2",
        instrument=Instrument(
            asset_class="OPTION",
            venue="CBOE",
            symbol="ABC",
            underlying="ABC",
            expiry="2030-01-01",
            strike="100",
            right="CALL",
            style="AMERICAN",
            currency="USD",
            multiplier="100",
        ),
        side="BUY",
        quantity="1",
        order_type="LIMIT",
        time_in_force="DAY",
        limit_price="1.25",
    )
    with pytest.raises(ConnectorProtocolError, match="margin preview"):
        capabilities.validate_order(order)


def test_transport_failure_is_unknown_outcome() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = httpx.Client(
        base_url="https://connector.test", transport=httpx.MockTransport(handler)
    )
    with (
        ConnectorClient(
            "https://connector.test",
            key_id="key-1",
            credential="secret",
            http_client=client,
        ) as connector,
        pytest.raises(ConnectorUnavailable),
    ):
        connector.accounts()


def test_validation_request_rejects_non_https_and_embedded_credentials() -> None:
    with pytest.raises(ValidationError):
        LiveConnectorValidationRequest(
            connection_id="live-1",
            endpoint="http://connector.test",
            key_id="key-1",
            credential="secret",
        )
    with pytest.raises(ValidationError):
        LiveConnectorValidationRequest(
            connection_id="live-1",
            endpoint="https://user:pass@connector.test",
            key_id="key-1",
            credential="secret",
        )


def test_activation_and_fill_rules_fail_closed() -> None:
    capabilities = ConnectorCapabilities.from_wire(_capabilities())
    now = datetime(2030, 1, 1, tzinfo=UTC)
    evidence = ActivationEvidence(
        live_id="LIVE-1",
        approval_state="APPROVED",
        approval_revision=1,
        connector_revision=3,
        capabilities_hash=capabilities.content_hash(),
        account_id="acct-1",
        validated_at=now,
    )
    evidence.validate(
        now=now,
        confirmation="ENABLE LIVE LIVE-1",
        global_switch="ACTIVE",
        account_switch="ACTIVE",
        deployment_switch="ACTIVE",
        capabilities=capabilities,
        submission_account_id="acct-1",
    )
    with pytest.raises(LivePolicyError, match="confirmation"):
        evidence.validate(
            now=now,
            confirmation="ENABLE LIVE LIVE-2",
            global_switch="ACTIVE",
            account_switch="ACTIVE",
            deployment_switch="ACTIVE",
            capabilities=capabilities,
            submission_account_id="acct-1",
        )
    status, ids, changed = apply_fill(
        current="ACKNOWLEDGED",
        fill_id="fill-1",
        known_fill_ids=frozenset(),
        cumulative_quantity="0.5",
        order_quantity="1",
    )
    assert (status, ids, changed) == ("PARTIALLY_FILLED", frozenset({"fill-1"}), True)
    assert apply_fill(
        current=status,
        fill_id="fill-1",
        known_fill_ids=ids,
        cumulative_quantity="0.5",
        order_quantity="1",
        previous_cumulative_quantity="0.5",
    ) == (status, ids, False)
    with pytest.raises(LivePolicyError, match="previous cumulative"):
        apply_fill(
            current="PARTIALLY_FILLED",
            fill_id="fill-2",
            known_fill_ids=ids,
            cumulative_quantity="0.75",
            order_quantity="1",
        )
    assert (
        apply_fill(
            current="PARTIALLY_FILLED",
            fill_id="fill-3",
            known_fill_ids=ids,
            cumulative_quantity="0.75",
            order_quantity="1",
            previous_cumulative_quantity="0.5",
            terminal=True,
        )[0]
        == "EXPIRED"
    )
    with pytest.raises(LivePolicyError, match="illegal order transition"):
        transition_order("FILLED", "CANCELLED")
    stale = ActivationEvidence(
        **{**evidence.__dict__, "validated_at": now - timedelta(minutes=11)}
    )
    with pytest.raises(LivePolicyError, match="expired"):
        stale.validate(
            now=now,
            confirmation="ENABLE LIVE LIVE-1",
            global_switch="ACTIVE",
            account_switch="ACTIVE",
            deployment_switch="ACTIVE",
            capabilities=capabilities,
            submission_account_id="acct-1",
        )
