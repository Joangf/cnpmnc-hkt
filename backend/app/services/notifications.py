from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.models import Notification, PatientProfile
from app.models.enums import NotificationType


def notify_user(
    session: AsyncSession,
    user_id: int,
    type_: NotificationType,
    title: str,
    content: str,
    link: str | None = None,
) -> None:
    session.add(Notification(user_id=user_id, type=type_, title=title, content=content, link=link))


async def notify_patient(
    session: AsyncSession,
    patient_id: int,
    type_: NotificationType,
    title: str,
    content: str,
    link: str | None = None,
) -> None:
    user_id = await session.scalar(
        select(PatientProfile.user_id).where(PatientProfile.id == patient_id)
    )
    if user_id is not None:
        notify_user(session, user_id, type_, title, content, link)


async def list_for_user(
    session: AsyncSession, user_id: int, *, unread_only: bool, limit: int
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    items = (
        await session.scalars(stmt.order_by(Notification.created_at.desc()).limit(limit))
    ).all()
    unread = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    )
    return list(items), int(unread or 0)


async def mark_read(session: AsyncSession, user_id: int, notification_id: int) -> Notification:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise NotFound("Notification not found.")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await session.commit()
    return notification


async def mark_all_read(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    await session.commit()
