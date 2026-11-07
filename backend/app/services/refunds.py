"""Manual full refunds (SCRUM-31/32, docs/sprint3-sepay-plan.md D12-D14).

A patient asks for a 100% refund of a paid payment whose appointment will not take place;
an admin transfers the money from the hospital's bank app (QR from `sepay.refund_qr_url`)
and marks it done, or rejects it with a reason. A rejected request may be submitted again.
"""

import secrets
import string
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidState, NotFound
from app.core.metrics import PAYMENTS
from app.models import PatientProfile, Payment, User
from app.models.enums import NotificationType, PaymentStatus, RefundStatus
from app.repositories import refunds as refund_repo
from app.schemas.payments import RefundRequestIn
from app.services import audit, notifications, policies

REFERENCE_PREFIX = "RF"
_ALPHABET = string.ascii_uppercase + string.digits


def new_refund_reference() -> str:
    """Transfer content the admin puts on the refund (UNIQUE column, 36^8 space)."""
    return REFERENCE_PREFIX + "".join(secrets.choice(_ALPHABET) for _ in range(8))


async def _notify(session: AsyncSession, payment: Payment, title: str, content: str) -> None:
    appointment = payment.appointment
    await notifications.notify_patient(
        session,
        appointment.patient_id,
        NotificationType.PAYMENT_RESULT,
        title,
        content,
        f"/appointments/{appointment.id}",
    )


async def request_refund(
    session: AsyncSession, patient: PatientProfile, payment_id: int, data: RefundRequestIn
) -> Payment:
    """Errors: NotFound; InvalidState codes RefundNotAllowed, RefundAlreadyRequested.
    Returns the payment with `appointment` loaded."""
    payment = await refund_repo.get_for_update(session, payment_id)
    if payment is None or payment.appointment.patient_id != patient.id:
        raise NotFound("Payment not found.")
    if payment.refund_status in (RefundStatus.REQUESTED, RefundStatus.COMPLETED):
        raise InvalidState(
            "A refund has already been requested for this payment.",
            code="RefundAlreadyRequested",
        )
    appointment = payment.appointment
    refundable = policies.refundable_payment(appointment)
    if (
        refundable is None
        or refundable.id != payment.id
        or not policies.can_request_refund(appointment)
    ):
        raise InvalidState(
            "A refund can be requested only for a paid appointment that was cancelled or "
            "rejected and never checked in.",
            code="RefundNotAllowed",
        )

    payment.refund_status = RefundStatus.REQUESTED
    payment.refund_reference = new_refund_reference()
    payment.refund_bank_bin = data.bank_bin
    payment.refund_bank_name = data.bank_name
    payment.refund_account_number = data.account_number
    payment.refund_account_name = data.account_name
    payment.refund_reason = data.reason
    payment.refund_note = None  # drop the previous rejection reason on a resubmission
    payment.refund_requested_at = datetime.now(UTC)
    audit.record(
        session,
        "payment.refund_requested",
        "payment",
        payment.id,
        actor_id=patient.user_id,
        details={
            "appointment_id": appointment.id,
            "amount": str(payment.amount),
            "refund_reference": payment.refund_reference,
        },
    )
    await _notify(
        session,
        payment,
        "Refund requested",
        f"We received your refund request for appointment {appointment.booking_reference}. "
        "The hospital will transfer the full amount to your bank account.",
    )
    await session.commit()
    return payment


async def list_refunds(
    session: AsyncSession, refund_status: RefundStatus | None, page: int, page_size: int
) -> tuple[list[Payment], int]:
    """Payments with a refund request, newest request first.
    Each has `appointment.patient.user` loaded (for presenters.admin_refund_out)."""
    return await refund_repo.list_refunds(session, refund_status, page, page_size)


async def _requested_for_update(session: AsyncSession, payment_id: int) -> Payment:
    payment = await refund_repo.get_for_update(session, payment_id)
    if payment is None or payment.refund_status is None:
        raise NotFound("Refund request not found.")
    if payment.refund_status != RefundStatus.REQUESTED:
        raise InvalidState(f"This refund is already {payment.refund_status.lower()}.")
    return payment


async def complete_refund(
    session: AsyncSession, admin: User, payment_id: int, note: str | None
) -> Payment:
    """REQUESTED -> COMPLETED, payment -> REFUNDED. Errors: NotFound; InvalidState.
    Returns the payment with `appointment.patient.user` loaded."""
    payment = await _requested_for_update(session, payment_id)
    payment.refund_status = RefundStatus.COMPLETED
    payment.status = PaymentStatus.REFUNDED
    payment.refunded_at = datetime.now(UTC)
    payment.refund_note = note
    audit.record(
        session,
        "payment.refunded",
        "payment",
        payment.id,
        actor_id=admin.id,
        details={"refund_reference": payment.refund_reference, "amount": str(payment.amount)},
    )
    await _notify(
        session,
        payment,
        "Refund completed",
        f"The hospital has transferred your refund for appointment "
        f"{payment.appointment.booking_reference} (reference {payment.refund_reference}).",
    )
    await session.commit()
    PAYMENTS.labels(status=PaymentStatus.REFUNDED).inc()
    return payment


async def reject_refund(
    session: AsyncSession, admin: User, payment_id: int, reason: str
) -> Payment:
    """REQUESTED -> REJECTED. Errors: NotFound; InvalidState.
    Returns the payment with `appointment.patient.user` loaded."""
    payment = await _requested_for_update(session, payment_id)
    payment.refund_status = RefundStatus.REJECTED
    payment.refund_note = reason
    audit.record(
        session,
        "payment.refund_rejected",
        "payment",
        payment.id,
        actor_id=admin.id,
        details={"refund_reference": payment.refund_reference},
    )
    await _notify(
        session,
        payment,
        "Refund request rejected",
        f"Your refund request for appointment {payment.appointment.booking_reference} was "
        f"rejected: {reason} You can correct it and submit again.",
    )
    await session.commit()
    return payment
