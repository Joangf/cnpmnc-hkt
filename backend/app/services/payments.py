"""VietQR + SePay payment workflow (FRD 4.10, docs/sprint3-sepay-plan.md D3-D11).

The patient transfers money with the payment code as the transfer content; SePay reports the
incoming transaction by webhook, or the poller finds it through the User API. Both paths call
`apply_transfer`. Payment status never implies appointment status (BR-07).
"""

from datetime import UTC, datetime, timedelta

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import InvalidState, NotFound, Unauthorized
from app.core.metrics import PAYMENTS
from app.integrations.erp.base import (
    ErpAdapter,
    ErpRejectedError,
    ErpTimeoutError,
    ErpUnavailableError,
)
from app.models import Appointment, PatientProfile, Payment
from app.models.enums import (
    ActorType,
    AppointmentStatus,
    NotificationType,
    PaymentStatus,
    StatusSource,
)
from app.repositories import appointments as appointment_repo
from app.repositories import payments as payment_repo
from app.schemas.payments import SepayWebhookIn
from app.services import audit, booking, notifications, policies, sepay
from app.services.sepay import BankTransfer

logger = structlog.get_logger(__name__)

# The expiry job waits this long past the deadline, so a transfer made at the last second
# still lands before the appointment is released (plan 2a).
EXPIRY_GRACE = timedelta(seconds=60)
# The poller looks back at most this far, and only while a payment is PENDING or recently
# EXPIRED (a late transfer still settles it, D10).
POLL_LOOKBACK = timedelta(hours=24)
_SETTLED = (PaymentStatus.PAID, PaymentStatus.REFUNDED)


async def initiate_payment(
    session: AsyncSession, patient: PatientProfile, appointment_id: int
) -> Payment:
    """Return the open PENDING attempt, or create one with a new payment code (D3, D7, D11).

    Errors: NotFound; InvalidState codes PaymentNotRequired, PaymentNotAllowed, AlreadyPaid,
    PaymentWindowClosed. The returned payment has `appointment` loaded (for the presenter).
    """
    # Serialise concurrent clicks so they cannot create two payment codes.
    await session.execute(
        select(Appointment.id).where(Appointment.id == appointment_id).with_for_update()
    )
    appointment = await appointment_repo.get_detail(session, appointment_id)
    if appointment is None or appointment.patient_id != patient.id:
        raise NotFound("Appointment not found.")
    if appointment.fee_amount <= 0:
        raise InvalidState("This appointment has no payable fee.", code="PaymentNotRequired")
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise InvalidState(
            "Payment becomes available once the hospital has confirmed the appointment.",
            code="PaymentNotAllowed",
        )
    if policies.payment_status_of(appointment.payments) in _SETTLED:
        raise InvalidState("This appointment has already been paid.", code="AlreadyPaid")
    now = datetime.now(UTC)
    if appointment.payment_due_at is not None and appointment.payment_due_at < now:
        raise InvalidState(
            "The payment deadline for this appointment has passed.", code="PaymentWindowClosed"
        )

    for previous in appointment.payments:
        if previous.status != PaymentStatus.PENDING:
            continue
        if previous.expires_at is None or previous.expires_at > now:
            open_id = previous.id  # rollback expires ORM objects; read the id first
            await session.rollback()  # release the lock
            return await _reload(session, open_id)
        previous.status = PaymentStatus.EXPIRED

    payment = Payment(
        appointment_id=appointment.id,
        amount=appointment.fee_amount,
        currency=appointment.currency,
        status=PaymentStatus.PENDING,
        payment_code=sepay.new_payment_code(),
        expires_at=appointment.payment_due_at,
    )
    session.add(payment)
    await session.flush()
    audit.record(
        session,
        "payment.initiated",
        "payment",
        payment.id,
        actor_id=patient.user_id,
        details={"appointment_id": appointment.id, "amount": str(payment.amount)},
    )
    await session.commit()
    PAYMENTS.labels(status=PaymentStatus.PENDING).inc()
    return await _reload(session, payment.id)


async def _reload(session: AsyncSession, payment_id: int) -> Payment:
    payment = await payment_repo.get(session, payment_id)
    assert payment is not None
    return payment


async def handle_webhook(
    session: AsyncSession, payload: SepayWebhookIn, authorization: str | None
) -> None:
    """Check `Authorization: Apikey <key>` (Unauthorized code InvalidApiKey), then apply an
    incoming transfer via apply_transfer. Never raises for unmatched transfers (D5, D10)."""
    if not sepay.check_api_key(authorization):
        logger.warning("sepay_webhook_rejected")
        raise Unauthorized("Invalid SePay API key.", code="InvalidApiKey")
    if payload.transferType != "in" or payload.transferAmount <= 0:
        return
    transfer = BankTransfer(
        id=str(payload.id),
        amount_in=payload.transferAmount,
        transaction_content=payload.content,
        code=payload.code,
        transaction_date=sepay.parse_local_time(payload.transactionDate),
    )
    outcome = await apply_transfer(session, transfer)
    if outcome == "unmatched":
        logger.warning("payment_unmatched_transfer", transfer_id=transfer.id)


async def apply_transfer(session: AsyncSession, t: BankTransfer) -> str:
    """Settle the payment named in a transfer's content (D10). Idempotent per transfer id.

    Returns: "paid", "amount_mismatch", "duplicate_transfer" (money for an appointment that is
    already paid; the hospital handles it on SePay), "duplicate" (already handled) or
    "unmatched" (no known payment code).
    """
    payment = await payment_repo.get_by_codes_for_update(
        session, sepay.extract_codes(t.code, t.transaction_content)
    )
    if payment is None:
        await session.rollback()
        return "unmatched"
    if await payment_repo.settled_by(session, t.id) or await payment_repo.transfer_seen(
        session, payment.id, t.id
    ):
        await session.rollback()
        return "duplicate"

    appointment = payment.appointment
    details = {
        "transfer_id": t.id,
        "amount": str(t.amount_in),
        "appointment_id": appointment.id,
    }
    already_paid = payment.status in _SETTLED or any(
        p.status in _SETTLED for p in appointment.payments if p.id != payment.id
    )
    if already_paid:
        logger.warning("payment_duplicate_transfer", payment_id=payment.id, transfer_id=t.id)
        audit.record(
            session,
            "payment.duplicate_transfer",
            "payment",
            payment.id,
            actor_type=ActorType.PAYMENT_GATEWAY,
            details=details,
        )
        await session.commit()
        return "duplicate_transfer"

    if t.amount_in != payment.amount:
        payment.failure_reason = (
            f"Received {t.amount_in:,.0f} {payment.currency}, expected "
            f"{payment.amount:,.0f} {payment.currency}. Please contact the hospital."
        )
        logger.warning("payment_amount_mismatch", payment_id=payment.id, transfer_id=t.id)
        audit.record(
            session,
            "payment.amount_mismatch",
            "payment",
            payment.id,
            actor_type=ActorType.PAYMENT_GATEWAY,
            details={**details, "expected": str(payment.amount)},
        )
        await notifications.notify_patient(
            session,
            appointment.patient_id,
            NotificationType.PAYMENT_RESULT,
            "Payment amount does not match",
            f"We received a transfer for appointment {appointment.booking_reference}, "
            f"but the amount does not match. {payment.failure_reason}",
            f"/appointments/{appointment.id}",
        )
        await session.commit()
        return "amount_mismatch"

    old_status = payment.status
    payment.status = PaymentStatus.PAID
    payment.provider_reference = t.id
    payment.paid_at = t.transaction_date
    payment.failure_reason = None
    audit.record(
        session,
        "payment.status_changed",
        "payment",
        payment.id,
        actor_type=ActorType.PAYMENT_GATEWAY,
        details={**details, "from": old_status, "to": PaymentStatus.PAID},
    )
    content = f"We received your payment for appointment {appointment.booking_reference}."
    if appointment.status != AppointmentStatus.CONFIRMED:
        # Late money for an appointment that was already released (D10).
        content += (
            " The appointment is no longer active, so you can request a full refund "
            "from the appointment page."
        )
    await notifications.notify_patient(  # FR-NOT-03
        session,
        appointment.patient_id,
        NotificationType.PAYMENT_RESULT,
        "Payment received",
        content,
        f"/appointments/{appointment.id}",
    )
    await session.commit()
    PAYMENTS.labels(status=PaymentStatus.PAID).inc()
    return "paid"


async def sync_transfers(session: AsyncSession) -> bool:
    """Background job: poll the SePay User API and apply new transfers (D5).

    No-op without `SEPAY_API_TOKEN` or when no payment is waiting for money.
    """
    if not settings.sepay_api_token:
        return True
    now = datetime.now(UTC)
    oldest = await payment_repo.pending_or_recent(session, now - POLL_LOOKBACK)
    await session.rollback()
    if oldest is None:
        return True
    since = max(oldest, now - POLL_LOOKBACK) - timedelta(minutes=1)
    try:
        transfers = await sepay.fetch_transactions(since)
    except (httpx.HTTPError, ValueError, KeyError):
        logger.warning("sepay_poll_failed", exc_info=True)
        return False
    for transfer in transfers:
        await apply_transfer(session, transfer)
    return True


async def expire_unpaid(session: AsyncSession, redis: Redis, erp: ErpAdapter) -> bool:
    """Background job: cancel confirmed appointments unpaid past payment_due_at (D6).

    One appointment per transaction, each row-locked with SKIP LOCKED. If the ERP refuses or
    is down, that appointment is skipped and retried on the next run.
    """
    before = datetime.now(UTC) - EXPIRY_GRACE
    skipped: list[int] = []
    while True:
        appointment = await appointment_repo.next_payment_overdue(session, before, skipped)
        if appointment is None:
            await session.rollback()
            return not skipped
        try:
            await booking.cancel(
                session,
                redis,
                erp,
                appointment,
                reason="Payment was not received before the deadline.",
                source=StatusSource.SYSTEM,
            )
        except (ErpRejectedError, ErpUnavailableError, ErpTimeoutError):
            logger.warning("payment_expiry_erp_failed", appointment_id=appointment.id)
            skipped.append(appointment.id)
            await session.rollback()
            continue
        logger.info("appointment_payment_expired", appointment_id=appointment.id)


async def get_for_patient(
    session: AsyncSession, patient: PatientProfile, payment_id: int
) -> Payment:
    payment = await payment_repo.get(session, payment_id)
    if payment is None or payment.appointment.patient_id != patient.id:
        raise NotFound("Payment not found.")
    return payment
