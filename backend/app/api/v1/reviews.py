from fastapi import APIRouter, status

from app.api.deps import CurrentPatient, SessionDep
from app.schemas.common import error_responses
from app.schemas.reviews import ReviewCreate, ReviewOut
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
