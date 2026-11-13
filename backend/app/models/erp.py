from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ErpSyncState(Base):
    __tablename__ = "erp_sync_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    ready: Mapped[bool] = mapped_column(default=False)
    synced_at: Mapped[datetime | None]
