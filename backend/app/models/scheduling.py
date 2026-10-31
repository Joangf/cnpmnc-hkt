from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow
from app.models.enums import ScheduleSource, enum_column


class AppointmentType(TimestampMixin, Base):
    """Configurable duration/buffer rules (FR-BOOK-08/09, BR-05).

    Scope: `doctor_id` set -> that doctor only; else `specialty_id` set -> doctors of that
    specialty; else -> every doctor.
    """

    __tablename__ = "appointment_types"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_appointment_types_duration_positive"),
        CheckConstraint("buffer_minutes >= 0", name="ck_appointment_types_buffer_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int]
    buffer_minutes: Mapped[int] = mapped_column(default=0)
    fee_override: Mapped[Decimal | None]
    specialty_id: Mapped[int | None] = mapped_column(ForeignKey("specialties.id"), index=True)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class DoctorSchedule(Base):
    """Local cache of doctor availability windows synced from the ERP (FRD section 9 note).

    The ERP remains the source of truth; rows are replaced on every sync.
    """

    __tablename__ = "doctor_schedules"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_doctor_schedules_range"),
        Index("ix_doctor_schedules_doctor_start", "doctor_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    max_appointments: Mapped[int | None]
    is_available: Mapped[bool] = mapped_column(default=True)
    source: Mapped[ScheduleSource] = mapped_column(
        enum_column(ScheduleSource), default=ScheduleSource.ERP
    )
    synced_at: Mapped[datetime] = mapped_column(default=utcnow)
