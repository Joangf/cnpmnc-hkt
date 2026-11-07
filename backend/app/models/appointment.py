from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow
from app.models.enums import AppointmentStatus, CheckInStatus, StatusSource, enum_column

if TYPE_CHECKING:
    from app.models.directory import Doctor
    from app.models.payment import Payment
    from app.models.review import Review
    from app.models.scheduling import AppointmentType
    from app.models.user import PatientProfile


class Appointment(TimestampMixin, Base):
    """Patient booking.

    Double booking is prevented by the `no_overlap` exclusion constraint
    (doctor_id =, reservation_position =, reserved range &&) for active appointments.
    ERP appointments always use position 1; shared manual slots allocate distinct positions.

    `status` (appointment), `check_in_status` (ERP-only, BR-11) and payment status
    (Payment table) are deliberately separate (BR-07).
    """

    __tablename__ = "appointments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["slot_id", "doctor_id"], ["doctor_slots.id", "doctor_slots.doctor_id"],
            name="fk_appointments_slot_doctor",
        ),
        CheckConstraint("reservation_position > 0", name="ck_appointments_position"),
        CheckConstraint(
            "slot_id IS NOT NULL OR reservation_position = 1", name="ck_appointments_erp_position"
        ),
        Index("ix_appointments_slot_id", "slot_id"),
        Index(
            "uq_appointments_patient_active_slot", "patient_id", "slot_id", unique=True,
            postgresql_where=text("slot_id IS NOT NULL AND status IN ('PENDING', 'CONFIRMED')"),
        ),
        Index("ix_appointments_doctor_start", "doctor_id", "start_time"),
        CheckConstraint("end_time > start_time", name="ck_appointments_time_range"),
        CheckConstraint("end_with_buffer >= end_time", name="ck_appointments_buffer_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_reference: Mapped[str] = mapped_column(String(16), unique=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    appointment_type_id: Mapped[int] = mapped_column(ForeignKey("appointment_types.id"))
    slot_id: Mapped[int | None]
    reservation_position: Mapped[int] = mapped_column(default=1, server_default="1")
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    end_with_buffer: Mapped[datetime]
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_column(AppointmentStatus), default=AppointmentStatus.PENDING, index=True
    )
    status_reason: Mapped[str | None] = mapped_column(String(500))
    check_in_status: Mapped[CheckInStatus] = mapped_column(
        enum_column(CheckInStatus), default=CheckInStatus.NOT_CHECKED_IN
    )
    erp_booking_id: Mapped[str | None] = mapped_column(String(64), index=True)
    reason_for_visit: Mapped[str | None] = mapped_column(String(1000))
    fee_amount: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3))
    cancelled_at: Mapped[datetime | None]

    doctor: Mapped[Doctor] = relationship(lazy="raise")
    appointment_type: Mapped[AppointmentType] = relationship(lazy="raise")
    patient: Mapped[PatientProfile] = relationship(lazy="raise")
    history: Mapped[list[AppointmentStatusHistory]] = relationship(
        order_by="AppointmentStatusHistory.id", lazy="raise"
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="appointment", order_by="Payment.id", lazy="raise"
    )
    review: Mapped[Review | None] = relationship(back_populates="appointment", lazy="raise")


class AppointmentStatusHistory(Base):
    """Every status / check-in / time change, for history display (FR-HIS-02)."""

    __tablename__ = "appointment_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(32))  # status | check_in_status | start_time
    from_value: Mapped[str | None] = mapped_column(String(64))
    to_value: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[StatusSource] = mapped_column(enum_column(StatusSource))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
