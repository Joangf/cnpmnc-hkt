from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Doctor, Review
from app.models.enums import ReviewStatus
from app.repositories.base import paginate


async def list_published_for_doctor(
    session: AsyncSession, doctor_id: int, page: int, page_size: int
) -> tuple[list[Review], int]:
    stmt = (
        select(Review)
        .where(Review.doctor_id == doctor_id, Review.status == ReviewStatus.PUBLISHED)
        .order_by(Review.created_at.desc())
    )
    return await paginate(session, stmt, page, page_size)


async def list_admin(
    session: AsyncSession,
    *,
    status: ReviewStatus | None,
    doctor_id: int | None,
    page: int,
    page_size: int,
) -> tuple[list[Review], int]:
    stmt = select(Review).options(joinedload(Review.doctor)).order_by(Review.created_at.desc())
    if status:
        stmt = stmt.where(Review.status == status)
    if doctor_id:
        stmt = stmt.where(Review.doctor_id == doctor_id)
    return await paginate(session, stmt, page, page_size)


async def get(session: AsyncSession, review_id: int) -> Review | None:
    stmt = (
        select(Review)
        .where(Review.id == review_id)
        .options(joinedload(Review.doctor))
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def recompute_doctor_rating(session: AsyncSession, doctor_id: int) -> None:
    avg, count = (
        await session.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.doctor_id == doctor_id, Review.status == ReviewStatus.PUBLISHED
            )
        )
    ).one()
    rating = Decimal(str(round(float(avg), 2))) if avg is not None else Decimal("0")
    await session.execute(
        update(Doctor).where(Doctor.id == doctor_id).values(rating_avg=rating, rating_count=count)
    )
