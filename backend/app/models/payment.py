from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import PaymentStatus, enum_column

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class Payment(TimestampMixin, Base):
    """One payment attempt. Status is tracked separately from the appointment (BR-07)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), index=True)
    amount: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus), default=PaymentStatus.PENDING
    )
    provider: Mapped[str] = mapped_column(String(32))
    provider_reference: Mapped[str | None] = mapped_column(String(64), unique=True)
    checkout_url: Mapped[str | None] = mapped_column(String(500))
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    last_event_id: Mapped[str | None] = mapped_column(String(64))
    paid_at: Mapped[datetime | None]
    refunded_at: Mapped[datetime | None]

    appointment: Mapped[Appointment] = relationship(back_populates="payments", lazy="raise")
