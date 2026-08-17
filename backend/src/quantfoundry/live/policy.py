"""Fail-closed activation and order-state rules for LiveExecution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar, Literal

from quantfoundry.live.connector import ConnectorCapabilities, OrderRequest

KillSwitch = Literal["ACTIVE", "PAUSED", "STOPPED", "DISABLED"]
ApprovalState = Literal["PENDING", "APPROVED", "REJECTED", "STALE"]
OrderStatus = Literal[
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
]

_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    "CREATED": frozenset({"SUBMITTING", "CANCELLED"}),
    "SUBMITTING": frozenset(
        {
            "ACKNOWLEDGED",
            "PARTIALLY_FILLED",
            "FILLED",
            "EXPIRED",
            "UNKNOWN",
            "RECONCILING",
            "REJECTED",
        }
    ),
    "ACKNOWLEDGED": frozenset(
        {
            "PARTIALLY_FILLED",
            "FILLED",
            "CANCEL_PENDING",
            "REJECTED",
            "EXPIRED",
            "UNKNOWN",
        }
    ),
    "PARTIALLY_FILLED": frozenset(
        {"PARTIALLY_FILLED", "FILLED", "CANCEL_PENDING", "EXPIRED", "UNKNOWN"}
    ),
    "FILLED": frozenset(),
    "CANCEL_PENDING": frozenset({"CANCELLED", "FILLED", "PARTIALLY_FILLED", "UNKNOWN"}),
    "CANCELLED": frozenset({"PARTIALLY_FILLED", "FILLED"}),
    "REJECTED": frozenset(),
    "EXPIRED": frozenset({"FILLED"}),
    "UNKNOWN": frozenset({"PARTIALLY_FILLED", "FILLED", "RECONCILING"}),
    "RECONCILING": frozenset(
        {
            "ACKNOWLEDGED",
            "PARTIALLY_FILLED",
            "FILLED",
            "CANCELLED",
            "REJECTED",
            "EXPIRED",
            "UNKNOWN",
        }
    ),
}


class LivePolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActivationEvidence:
    live_id: str
    approval_state: ApprovalState
    approval_revision: int
    connector_revision: int
    capabilities_hash: str
    account_id: str
    validated_at: datetime
    max_validation_age: ClassVar[timedelta] = timedelta(minutes=10)

    def validate(
        self,
        *,
        now: datetime,
        confirmation: str,
        global_switch: KillSwitch,
        account_switch: KillSwitch,
        deployment_switch: KillSwitch,
        capabilities: ConnectorCapabilities,
        submission_account_id: str,
        current_approval_state: ApprovalState | None = None,
        current_approval_revision: int | None = None,
        current_connector_revision: int | None = None,
        order: OrderRequest | None = None,
    ) -> None:
        if confirmation != f"ENABLE LIVE {self.live_id}":
            raise LivePolicyError("explicit live confirmation is required")
        if self.approval_state != "APPROVED" or self.approval_revision < 1:
            raise LivePolicyError("live approval is not active")
        if (
            current_approval_state != "APPROVED"
            or current_approval_revision != self.approval_revision
        ):
            raise LivePolicyError("live approval is stale")
        if (
            self.connector_revision < 1
            or current_connector_revision != self.connector_revision
            or self.capabilities_hash != capabilities.content_hash()
        ):
            raise LivePolicyError("connector capabilities have changed")
        if any(
            value != "ACTIVE"
            for value in (global_switch, account_switch, deployment_switch)
        ):
            raise LivePolicyError("live kill switch is active")
        if now.tzinfo is None or self.validated_at.tzinfo is None:
            raise LivePolicyError("activation timestamps must be timezone-aware")
        current = now.astimezone(UTC)
        validated = self.validated_at.astimezone(UTC)
        if current < validated or current - validated > self.max_validation_age:
            raise LivePolicyError("connector validation has expired")
        if self.account_id not in capabilities.account_ids:
            raise LivePolicyError("approved account is not in connector capabilities")
        if submission_account_id != self.account_id:
            raise LivePolicyError("submission account does not match activation")
        if order is not None:
            capabilities.validate_order(order)


def ensure_submission_allowed(
    *,
    global_switch: KillSwitch,
    account_switch: KillSwitch,
    deployment_switch: KillSwitch,
    live_activated: bool,
    reconciliation_ok: bool,
) -> None:
    if not live_activated:
        raise LivePolicyError("live deployment is not activated")
    if not reconciliation_ok:
        raise LivePolicyError("account reconciliation is required")
    if any(
        value != "ACTIVE"
        for value in (global_switch, account_switch, deployment_switch)
    ):
        raise LivePolicyError("live kill switch is active")


def transition_order(current: OrderStatus, target: OrderStatus) -> OrderStatus:
    if target == current:
        return current
    if target not in _TRANSITIONS[current]:
        raise LivePolicyError(f"illegal order transition {current}->{target}")
    return target


def apply_fill(
    *,
    current: OrderStatus,
    fill_id: str,
    known_fill_ids: frozenset[str],
    cumulative_quantity: str,
    order_quantity: str,
    previous_cumulative_quantity: str | None = None,
    terminal_status: OrderStatus | None = None,
    known_fill_quantities: Mapping[str, str] | None = None,
) -> tuple[OrderStatus, frozenset[str], bool]:
    """Return status, fill-id set and whether this fill changed state."""
    if not fill_id:
        raise LivePolicyError("broker fill id is required")
    from decimal import Decimal, InvalidOperation

    try:
        cumulative = Decimal(cumulative_quantity)
        quantity = Decimal(order_quantity)
    except InvalidOperation as error:
        raise LivePolicyError("fill quantities are invalid") from error
    if (
        not cumulative.is_finite()
        or not quantity.is_finite()
        or cumulative <= 0
        or quantity <= 0
    ):
        raise LivePolicyError("fill quantities are invalid")
    if cumulative > quantity:
        raise LivePolicyError("cumulative fill exceeds order quantity")
    if fill_id in known_fill_ids:
        if known_fill_quantities is None or fill_id not in known_fill_quantities:
            raise LivePolicyError("duplicate fill has no retained quantity evidence")
        try:
            known_cumulative = Decimal(known_fill_quantities[fill_id])
        except (InvalidOperation, TypeError) as error:
            raise LivePolicyError("recorded fill quantity is invalid") from error
        if known_cumulative != cumulative:
            raise LivePolicyError("duplicate fill id has conflicting quantity")
        return current, known_fill_ids, False
    if previous_cumulative_quantity is not None:
        try:
            previous = Decimal(previous_cumulative_quantity)
        except InvalidOperation as error:
            raise LivePolicyError("previous cumulative quantity is invalid") from error
        if not previous.is_finite() or previous < 0 or cumulative <= previous:
            raise LivePolicyError("cumulative fill is not increasing")
    if known_fill_ids and previous_cumulative_quantity is None:
        raise LivePolicyError(
            "previous cumulative quantity is required after a prior fill"
        )
    if terminal_status is not None and terminal_status not in {
        "CANCELLED",
        "EXPIRED",
        "FILLED",
    }:
        raise LivePolicyError("terminal status is invalid")
    target: OrderStatus = (
        "FILLED" if cumulative == quantity else terminal_status or "PARTIALLY_FILLED"
    )
    next_status = (
        current
        if current in {"CANCELLED", "EXPIRED"} and cumulative < quantity
        else transition_order(current, target)
    )
    return next_status, known_fill_ids | {fill_id}, True
