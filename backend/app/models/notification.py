from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow
from app.models.enums import NotificationType, enum_column


class Notification(Base):
    """In-app notification (FR-NOT-01..03). Other channels can fan out from here later."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(enum_column(NotificationType))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    read_at: Mapped[datetime | None]
