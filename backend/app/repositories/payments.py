from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Payment


async def get(session: AsyncSession, payment_id: int) -> Payment | None:
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id)
        .options(joinedload(Payment.appointment))
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def get_by_provider_reference_for_update(
    session: AsyncSession, provider_reference: str
) -> Payment | None:
    """Row-locks the payment so concurrent duplicate callbacks are serialised."""
    stmt = (
        select(Payment)
        .where(Payment.provider_reference == provider_reference)
        .options(joinedload(Payment.appointment))
        .with_for_update(of=Payment)
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)
