from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow
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
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    moderation_note: Mapped[str | None] = mapped_column(String(500))

    appointment: Mapped[Appointment] = relationship(back_populates="review", lazy="raise")
    doctor: Mapped[Doctor] = relationship(lazy="raise")


class ReviewReport(Base):
    """A patient's report of an inappropriate public review (SCRUM-50).

    Reporting never changes the review or the rating; an admin decides (SCRUM-47) and that
    decision resolves every open report of the review. One open report per reporter/review.
    """

    __tablename__ = "review_reports"
    __table_args__ = (
        Index(
            "uq_review_reports_open",
            "review_id",
            "reporter_user_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), index=True)
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(50))
    details: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN | RESOLVED
    # The moderation outcome: PUBLISHED (kept, report dismissed) | HIDDEN | REMOVED.
    resolution: Mapped[str | None] = mapped_column(String(20))
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
