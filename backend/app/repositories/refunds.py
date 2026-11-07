"""Refund queries (SCRUM-31/32). Refunds live on the `payments` row (plan D12)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import set_committed_value

from app.models import Appointment, PatientProfile, Payment
from app.models.enums import RefundStatus
from app.repositories.base import paginate


def _with_patient() -> tuple:
    return (
        joinedload(Payment.appointment)
        .joinedload(Appointment.patient)
        .joinedload(PatientProfile.user),
    )


async def get_for_update(session: AsyncSession, payment_id: int) -> Payment | None:
    """Row-locks the payment so concurrent refund actions on it are serialised.
    Loads `appointment.patient.user` (presenter) and `appointment.payments` (refund policy)."""
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id)
        .options(*_with_patient())
        .with_for_update(of=Payment)
        .execution_options(populate_existing=True)
    )
    payment = await session.scalar(stmt)
    if payment is None:
        return None
    # A second populate_existing load of this row (e.g. selectinload of the collection) would
    # reset `payment.appointment`; load the siblings plainly and attach them instead.
    siblings = await session.scalars(
        select(Payment).where(Payment.appointment_id == payment.appointment_id).order_by(Payment.id)
    )
    set_committed_value(payment.appointment, "payments", list(siblings))
    return payment


async def list_refunds(
    session: AsyncSession, refund_status: RefundStatus | None, page: int, page_size: int
) -> tuple[list[Payment], int]:
    stmt = select(Payment).options(*_with_patient())
    if refund_status is None:
        stmt = stmt.where(Payment.refund_status.is_not(None))
    else:
        stmt = stmt.where(Payment.refund_status == refund_status)
    stmt = stmt.order_by(Payment.refund_requested_at.desc(), Payment.id.desc())
    return await paginate(session, stmt, page, page_size)
