from datetime import datetime

from pydantic import BaseModel

from app.models.enums import NotificationType
from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: int
    type: NotificationType
    title: str
    content: str
    link: str | None
    created_at: datetime
    read_at: datetime | None


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int
