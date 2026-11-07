from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.models import Appointment, AuditLog, Payment
from app.models.enums import PaymentStatus


async def get(session: AsyncSession, payment_id: int) -> Payment | None:
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id)
        .options(joinedload(Payment.appointment))
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def get_by_codes_for_update(session: AsyncSession, codes: list[str]) -> Payment | None:
    """The payment matching one of `codes`, locked together with its appointment.

    Lock order is appointment, then payment, the same as the expiry job, so an incoming
    transfer and the expiry of the same appointment serialise instead of deadlocking.
    Loads `payment.appointment.payments`.
    """
    if not codes:
        return None
    appointment_id = await session.scalar(
        select(Payment.appointment_id).where(Payment.payment_code.in_(codes)).limit(1)
    )
    if appointment_id is None:
        return None
    await session.execute(
        select(Appointment.id).where(Appointment.id == appointment_id).with_for_update()
    )
    payment_id = await session.scalar(
        select(Payment.id)
        .where(Payment.payment_code.in_(codes), Payment.appointment_id == appointment_id)
        .limit(1)
        .with_for_update()
    )
    # Plain reads once locked (eager loads and FOR UPDATE do not combine well). Load the
    # appointment with all its payments, then wire the back-reference by hand: re-loading
    # the payment itself would reset the eagerly loaded relationship.
    appointment = await session.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(selectinload(Appointment.payments))
        .execution_options(populate_existing=True)
    )
    if appointment is None:
        return None
    payment = next(p for p in appointment.payments if p.id == payment_id)
    set_committed_value(payment, "appointment", appointment)
    return payment


async def transfer_seen(session: AsyncSession, payment_id: int, transfer_id: str) -> bool:
    """True if this bank transaction was already handled for this payment (polling repeats
    the same transactions; their audit rows carry `transfer_id`)."""
    stmt = select(
        exists().where(
            AuditLog.entity_type == "payment",
            AuditLog.entity_id == str(payment_id),
            AuditLog.details["transfer_id"].astext == transfer_id,
        )
    )
    return bool(await session.scalar(stmt))


async def pending_or_recent(session: AsyncSession, since: datetime) -> datetime | None:
    """Creation time of the oldest payment still worth polling for: PENDING, or EXPIRED
    within the window (a late transfer still settles it, D10). None if there is none."""
    stmt = select(func.min(Payment.created_at)).where(
        or_(
            Payment.status == PaymentStatus.PENDING,
            and_(Payment.status == PaymentStatus.EXPIRED, Payment.created_at >= since),
        )
    )
    return await session.scalar(stmt)
