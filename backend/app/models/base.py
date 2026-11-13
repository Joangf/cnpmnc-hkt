from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        Decimal: Numeric(12, 2),
    }


class TimestampMixin:
    # Python-side defaults keep values loaded after flush (no implicit lazy refresh in async).
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow, onupdate=utcnow, server_default=func.now()
    )


class ErpMirrorMixin:
    """Stable upstream identity; local primary keys never change during synchronization."""

    erp_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    synced_at: Mapped[datetime | None]
