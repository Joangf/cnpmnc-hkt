from fastapi import APIRouter, Response, status

from app.api.deps import CurrentPatient, SessionDep
from app.core.config import settings
from app.schemas.common import error_responses
from app.schemas.reviews import (
    ReportCreate,
    ReportOut,
    ReviewCreate,
    ReviewOut,
    ReviewUpdate,
)
from app.services import reviews as review_service

router = APIRouter(tags=["reviews"])


@router.post(
    "/appointments/{appointment_id}/review",
    status_code=status.HTTP_201_CREATED,
    response_model=ReviewOut,
    operation_id="createReview",
    responses=error_responses(401, 403, 404, 409, 422),
)
async def create_review(
    appointment_id: int, payload: ReviewCreate, patient: CurrentPatient, session: SessionDep
) -> ReviewOut:
    review = await review_service.create_review(session, patient, appointment_id, payload)
    return ReviewOut.model_validate(review)


@router.patch(
    "/appointments/{appointment_id}/review",
    response_model=ReviewOut,
    operation_id="updateReview",
    responses=error_responses(400, 401, 403, 404, 422),
)
async def update_review(
    appointment_id: int, payload: ReviewUpdate, patient: CurrentPatient, session: SessionDep
) -> ReviewOut:
    review = await review_service.update_review(session, patient, appointment_id, payload)
    return ReviewOut.model_validate(review)


@router.get(
    "/review-report-reasons", response_model=list[str], operation_id="listReviewReportReasons"
)
async def list_report_reasons() -> list[str]:
    return list(settings.review_report_reasons)


@router.post(
    "/reviews/{review_id}/reports",
    status_code=status.HTTP_201_CREATED,
    response_model=ReportOut,
    operation_id="reportReview",
    responses={
        200: {"description": "Already reported: the open report is returned"},
        **error_responses(401, 403, 404, 422),
    },
    description=(
        "Report a public review as inappropriate (SCRUM-50). Does not hide the review or change "
        "the rating; a moderator decides. Reporting again while a report is open returns it (200)."
    ),
)
async def report_review(
    review_id: int,
    payload: ReportCreate,
    patient: CurrentPatient,
    session: SessionDep,
    response: Response,
) -> ReportOut:
    report, created = await review_service.report_review(session, patient, review_id, payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    return ReportOut(
        id=report.id,
        review_id=report.review_id,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
        already_reported=not created,
    )
