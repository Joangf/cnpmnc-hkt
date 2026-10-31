from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ReviewStatus, enum_column

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.directory import Doctor


class Review(TimestampMixin, Base):
    """Doctor review. `appointment_id` is unique: one review per appointment (BR-09)."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus), default=ReviewStatus.PUBLISHED
    )
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    moderation_note: Mapped[str | None] = mapped_column(String(500))

    appointment: Mapped[Appointment] = relationship(back_populates="review", lazy="raise")
    doctor: Mapped[Doctor] = relationship(lazy="raise")
