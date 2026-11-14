from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Doctor, Review, ReviewReport
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
    reported: bool = False,
) -> tuple[list[Review], int]:
    stmt = select(Review).options(joinedload(Review.doctor)).order_by(Review.created_at.desc())
    if reported:  # the moderation queue: reviews with an open report (SCRUM-47/50)
        stmt = stmt.where(
            select(ReviewReport.id)
            .where(ReviewReport.review_id == Review.id, ReviewReport.status == "OPEN")
            .exists()
        )
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


async def open_reports(session: AsyncSession, review_ids: list[int]) -> dict[int, list[str]]:
    """Reasons of the open reports, per review."""
    if not review_ids:
        return {}
    rows = (
        await session.execute(
            select(ReviewReport.review_id, ReviewReport.reason)
            .where(ReviewReport.review_id.in_(review_ids), ReviewReport.status == "OPEN")
            .order_by(ReviewReport.created_at)
        )
    ).all()
    out: dict[int, list[str]] = {}
    for review_id, reason in rows:
        out.setdefault(review_id, []).append(reason)
    return out


async def recompute_doctor_rating(session: AsyncSession, doctor_id: int) -> None:
    """SCRUM-49: average of PUBLISHED reviews, 2 decimals (half-up via `round` on the float
    average); 0 reviews = unrated (avg 0, count 0). The doctor row is locked first so
    concurrent submissions/moderations recompute one after another from committed data."""
    await session.execute(select(Doctor.id).where(Doctor.id == doctor_id).with_for_update())
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


async def recompute_all_ratings(session: AsyncSession) -> int:
    """Reconciliation (SCRUM-49): rebuild every doctor's aggregate from the reviews."""
    ids = (await session.scalars(select(Doctor.id).order_by(Doctor.id))).all()
    for doctor_id in ids:
        await recompute_doctor_rating(session, doctor_id)
    return len(ids)
