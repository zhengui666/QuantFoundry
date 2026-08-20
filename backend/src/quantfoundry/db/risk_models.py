"""Risk persistence models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from quantfoundry.db.base import Base, IDENTITY_INT, JSON_VALUE, MONEY


class RiskAccount(Base):
    __tablename__ = "risk_accounts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('BLOCKED','RECONCILING','READY')", name="ck_risk_account_status"
        ),
    )

    funder_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="BLOCKED")
    gross_limit_pusd: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    owner_deployment_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("deployments.id", ondelete="SET NULL")
    )
    owner_generation: Mapped[int | None] = mapped_column(Integer)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RiskPosition(Base):
    __tablename__ = "risk_positions"

    funder_id: Mapped[str] = mapped_column(
        String(300), ForeignKey("risk_accounts.funder_id", ondelete="CASCADE"), primary_key=True
    )
    instrument_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    entry_cost_pusd: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskOpenOrder(Base):
    __tablename__ = "risk_open_orders"
    __table_args__ = (
        CheckConstraint(
            "state IN ('OPEN','PENDING_CANCEL','UNKNOWN')", name="ck_risk_open_order_state"
        ),
    )

    funder_id: Mapped[str] = mapped_column(
        String(300), ForeignKey("risk_accounts.funder_id", ondelete="CASCADE"), primary_key=True
    )
    client_order_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(300), nullable=False)
    increase_debit_pusd: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskReservation(Base):
    __tablename__ = "risk_reservations"
    __table_args__ = (
        UniqueConstraint(
            "funder_id",
            "runner_generation",
            "client_order_id",
            name="uq_risk_reservation_order",
        ),
        CheckConstraint(
            "state IN ('PENDING','ACCEPTED','REJECTED','RELEASED','UNKNOWN')",
            name="ck_risk_reservation_state",
        ),
        Index("ix_risk_reservation_state", "funder_id", "state"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    funder_id: Mapped[str] = mapped_column(
        String(300), ForeignKey("risk_accounts.funder_id", ondelete="CASCADE"), nullable=False
    )
    runner_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    client_order_id: Mapped[str] = mapped_column(String(300), nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(300), nullable=False)
    reserved_pusd: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(IDENTITY_INT, primary_key=True, autoincrement=True)
    funder_id: Mapped[str] = mapped_column(
        String(300), ForeignKey("risk_accounts.funder_id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = [
    "RiskAccount",
    "RiskPosition",
    "RiskOpenOrder",
    "RiskReservation",
    "RiskEvent",
]
