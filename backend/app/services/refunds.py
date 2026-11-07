"""Manual full refunds (SCRUM-31/32, docs/sprint3-sepay-plan.md D12-D14).

PHASE 0 SKELETON: signatures are the contract used by api/v1/refunds.py.
Session S3-C implements the bodies (plan section 4, "Session C").
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PatientProfile, Payment, User
from app.models.enums import RefundStatus
from app.schemas.payments import RefundRequestIn


async def request_refund(
    session: AsyncSession, patient: PatientProfile, payment_id: int, data: RefundRequestIn
) -> Payment:
    """Errors: NotFound; InvalidState codes RefundNotAllowed, RefundAlreadyRequested.
    Returns the payment with `appointment` loaded."""
    raise NotImplementedError("S3-C")


async def list_refunds(
    session: AsyncSession, refund_status: RefundStatus | None, page: int, page_size: int
) -> tuple[list[Payment], int]:
    """Payments with a refund request, newest request first.
    Each has `appointment.patient.user` loaded (for presenters.admin_refund_out)."""
    raise NotImplementedError("S3-C")


async def complete_refund(
    session: AsyncSession, admin: User, payment_id: int, note: str | None
) -> Payment:
    """REQUESTED -> COMPLETED, payment -> REFUNDED. Errors: NotFound; InvalidState.
    Returns the payment with `appointment.patient.user` loaded."""
    raise NotImplementedError("S3-C")


async def reject_refund(
    session: AsyncSession, admin: User, payment_id: int, reason: str
) -> Payment:
    """REQUESTED -> REJECTED. Errors: NotFound; InvalidState.
    Returns the payment with `appointment.patient.user` loaded."""
    raise NotImplementedError("S3-C")
