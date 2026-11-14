from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Computed,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.models.base import Base, utcnow


class SearchDocument(Base):
    """One searchable text of a catalog entry for the AI symptom search.

    A symptom has one row per phrase (its name, then each synonym) so a phrase can be
    matched inside a longer sentence; a published doctor has one row (the profile).
    Rebuilt from the source rows by `services.search_index`; `content_hash` tells which
    rows changed, so only those are embedded again.
    """

    __tablename__ = "search_documents"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "part", name="uq_search_documents_entity"),
        Index("ix_search_documents_tsv", "tsv", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # "symptom" | "doctor"
    entity_id: Mapped[int]
    part: Mapped[int] = mapped_column(default=0)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dims))
    # ColBERT token vectors, float32, row-major (tokens x embedding_dims).
    colbert: Mapped[bytes] = mapped_column(LargeBinary)
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', content)", persisted=True)
    )
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class DoctorReviewSummary(Base):
    """AI summary of a doctor's public reviews (SCRUM-46), regenerated when that set changes."""

    __tablename__ = "doctor_review_summaries"

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[str] = mapped_column(Text)
    # [{"text": str, "review_ids": [int, ...]}] - every point cites the reviews it came from.
    points: Mapped[list[dict]] = mapped_column(JSON, default=list)
    review_count: Mapped[int]
    review_set_hash: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(default=utcnow)
