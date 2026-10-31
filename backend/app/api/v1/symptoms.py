from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Symptom
from app.schemas.common import error_responses
from app.schemas.symptoms import RecommendationRequest, RecommendationResponse, SymptomOut
from app.services import recommendation

router = APIRouter(prefix="/symptoms", tags=["symptoms"])


@router.get("", response_model=list[SymptomOut], operation_id="listSymptoms")
async def list_symptoms(session: SessionDep) -> list[SymptomOut]:
    rows = await session.scalars(
        select(Symptom).where(Symptom.is_active.is_(True)).order_by(Symptom.name)
    )
    return [SymptomOut.model_validate(s) for s in rows.all()]


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    operation_id="recommendSpecialties",
    responses=error_responses(422),
    description=(
        "Rule-based specialty suggestions for navigation only - not a diagnosis (BR-10). "
        "Available to guests; no symptom data is stored."
    ),
)
async def recommend_specialties(
    payload: RecommendationRequest, session: SessionDep
) -> RecommendationResponse:
    return await recommendation.recommend(session, payload.symptom_ids, payload.free_text)
