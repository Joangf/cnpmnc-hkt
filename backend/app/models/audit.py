from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow
from app.models.enums import ActorType, enum_column


class AuditLog(Base):
    """Important actions: booking status changes, payment updates, admin operations (NFR-10)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[int | None]
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
