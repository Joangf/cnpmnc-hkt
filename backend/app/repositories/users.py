from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PatientProfile, User
from app.models.enums import AccountStatus, UserRole
from app.repositories.base import paginate


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.profile))
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = (
        select(User)
        .where(User.email == email.lower())
        .options(selectinload(User.profile))
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def list_users(
    session: AsyncSession,
    *,
    q: str | None,
    role: UserRole | None,
    account_status: AccountStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    stmt = select(User).options(selectinload(User.profile)).order_by(User.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(User.email.ilike(like), User.profile.has(PatientProfile.full_name.ilike(like)))
        )
    if role:
        stmt = stmt.where(User.role == role)
    if account_status:
        stmt = stmt.where(User.account_status == account_status)
    return await paginate(session, stmt, page, page_size)
