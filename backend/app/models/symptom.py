from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Symptom(TimestampMixin, Base):
    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Comma-separated synonyms used for free-text matching.
    keywords: Mapped[str | None] = mapped_column(String(500))
    # Warning-sign rule (FR-REC-06). Must be reviewed by a clinician before production use.
    is_red_flag: Mapped[bool] = mapped_column(default=False)
    red_flag_message: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)


class SymptomSpecialtyRule(Base):
    """Rule-based symptom -> specialty mapping with a weight (FR-REC-02)."""

    __tablename__ = "symptom_specialty_rules"
    __table_args__ = (UniqueConstraint("symptom_id", "specialty_id", name="uq_symptom_specialty"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    symptom_id: Mapped[int] = mapped_column(
        ForeignKey("symptoms.id", ondelete="CASCADE"), index=True
    )
    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialties.id", ondelete="CASCADE"), index=True
    )
    weight: Mapped[float] = mapped_column(default=1.0)


class RecommendationLog(Base):
    """Anonymous count of suggested specialties (FR-RPT-03). No user or symptom data."""

    __tablename__ = "recommendation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
