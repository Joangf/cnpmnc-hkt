from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import PaymentStatus, RefundStatus, enum_column

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class Payment(TimestampMixin, Base):
    """One VietQR bank-transfer attempt, matched by `payment_code` in the transfer content.

    Status is tracked separately from the appointment (BR-07). A refund is at most one full
    refund per payment, paid out manually by an admin, so its fields live on this row.
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), index=True)
    amount: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus), default=PaymentStatus.PENDING
    )
    payment_code: Mapped[str] = mapped_column(String(16), unique=True)
    expires_at: Mapped[datetime | None]
    # SePay transaction id of the transfer that settled this payment.
    provider_reference: Mapped[str | None] = mapped_column(String(64), unique=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    paid_at: Mapped[datetime | None]

    refund_status: Mapped[RefundStatus | None] = mapped_column(enum_column(RefundStatus))
    refund_reference: Mapped[str | None] = mapped_column(String(16), unique=True)
    refund_bank_bin: Mapped[str | None] = mapped_column(String(8))
    refund_bank_name: Mapped[str | None] = mapped_column(String(64))
    refund_account_number: Mapped[str | None] = mapped_column(String(32))
    refund_account_name: Mapped[str | None] = mapped_column(String(128))
    refund_reason: Mapped[str | None] = mapped_column(String(500))
    refund_note: Mapped[str | None] = mapped_column(String(500))
    refund_requested_at: Mapped[datetime | None]
    refunded_at: Mapped[datetime | None]

    appointment: Mapped[Appointment] = relationship(back_populates="payments", lazy="raise")
