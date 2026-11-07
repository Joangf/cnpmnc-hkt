"""VietQR + SePay payment workflow (FRD 4.10, docs/sprint3-sepay-plan.md).

Payment status never implies appointment status (BR-07).

PHASE 0 SKELETON: the signatures below are the contract used by the routes and jobs.
Session S3-A implements the bodies (plan section 4, "Session A").
"""

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.integrations.erp.base import ErpAdapter
from app.models import PatientProfile, Payment
from app.repositories import payments as payment_repo
from app.schemas.payments import SepayWebhookIn


async def initiate_payment(
    session: AsyncSession, patient: PatientProfile, appointment_id: int
) -> Payment:
    """Return the open PENDING attempt, or create one with a new payment code (D3, D7, D11).

    Errors: NotFound; InvalidState codes PaymentNotRequired, PaymentNotAllowed, AlreadyPaid,
    PaymentWindowClosed. The returned payment has `appointment` loaded (for the presenter).
    """
    raise NotImplementedError("S3-A")


async def handle_webhook(
    session: AsyncSession, payload: SepayWebhookIn, authorization: str | None
) -> None:
    """Check `Authorization: Apikey <key>` (Unauthorized code InvalidApiKey), then apply an
    incoming transfer via apply_transfer. Never raises for unmatched transfers (D5, D10)."""
    raise NotImplementedError("S3-A")


async def sync_transfers(session: AsyncSession) -> bool:
    """Background job: poll the SePay User API and apply new transfers (D5)."""
    return True  # S3-A


async def expire_unpaid(session: AsyncSession, redis: Redis, erp: ErpAdapter) -> bool:
    """Background job: cancel confirmed appointments unpaid past payment_due_at (D6)."""
    return True  # S3-A


async def get_for_patient(
    session: AsyncSession, patient: PatientProfile, payment_id: int
) -> Payment:
    payment = await payment_repo.get(session, payment_id)
    if payment is None or payment.appointment.patient_id != patient.id:
        raise NotFound("Payment not found.")
    return payment
