"""Refund endpoints: patient request (SCRUM-31) and admin processing (SCRUM-32)."""

from fastapi import APIRouter

from app.api import presenters
from app.api.deps import AdminUser, CurrentPatient, PageDep, SessionDep
from app.models.enums import RefundStatus
from app.schemas.common import Page, error_responses
from app.schemas.payments import (
    AdminRefundOut,
    PaymentOut,
    RefundCompleteIn,
    RefundRejectIn,
    RefundRequestIn,
)
from app.services import refunds as refund_service

router = APIRouter(tags=["refunds"])


@router.post(
    "/payments/{payment_id}/refund-request",
    response_model=PaymentOut,
    operation_id="requestRefund",
    responses=error_responses(401, 403, 404, 409),
    description=(
        "Requests a full refund of a paid payment whose appointment was cancelled or rejected "
        "(and never checked in). The hospital pays it out manually to the given account."
    ),
)
async def request_refund(
    payment_id: int, payload: RefundRequestIn, patient: CurrentPatient, session: SessionDep
) -> PaymentOut:
    payment = await refund_service.request_refund(session, patient, payment_id, payload)
    return presenters.payment_out(payment)


@router.get(
    "/admin/refunds",
    response_model=Page[AdminRefundOut],
    operation_id="adminListRefunds",
    responses=error_responses(401, 403),
)
async def admin_list_refunds(
    admin: AdminUser,
    session: SessionDep,
    paging: PageDep,
    refund_status: RefundStatus | None = None,
) -> Page[AdminRefundOut]:
    items, total = await refund_service.list_refunds(
        session, refund_status, paging.page, paging.page_size
    )
    return Page[AdminRefundOut](
        items=[presenters.admin_refund_out(p) for p in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.post(
    "/admin/refunds/{payment_id}/complete",
    response_model=AdminRefundOut,
    operation_id="adminCompleteRefund",
    responses=error_responses(401, 403, 404, 409),
    description="Marks a requested refund as transferred; the payment becomes REFUNDED.",
)
async def admin_complete_refund(
    payment_id: int, payload: RefundCompleteIn, admin: AdminUser, session: SessionDep
) -> AdminRefundOut:
    payment = await refund_service.complete_refund(session, admin, payment_id, payload.note)
    return presenters.admin_refund_out(payment)


@router.post(
    "/admin/refunds/{payment_id}/reject",
    response_model=AdminRefundOut,
    operation_id="adminRejectRefund",
    responses=error_responses(401, 403, 404, 409),
)
async def admin_reject_refund(
    payment_id: int, payload: RefundRejectIn, admin: AdminUser, session: SessionDep
) -> AdminRefundOut:
    payment = await refund_service.reject_refund(session, admin, payment_id, payload.reason)
    return presenters.admin_refund_out(payment)
