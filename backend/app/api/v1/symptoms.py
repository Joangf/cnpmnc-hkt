from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep, client_ip
from app.core.config import settings
from app.core.errors import TooManyRequests, ValidationFailed
from app.models import Symptom
from app.schemas.common import error_responses
from app.schemas.symptoms import (
    InterpretRequest,
    InterpretResponse,
    RecommendationRequest,
    RecommendationResponse,
    SymptomOut,
)
from app.services import ai_symptoms, recommendation

router = APIRouter(prefix="/symptoms", tags=["symptoms"])


async def _rate_limit(redis: RedisDep, request: Request, bucket: str) -> None:
    """AI calls cost money: cap them per client IP and minute."""
    key = f"ratelimit:ai:{bucket}:{client_ip(request)}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.ai_requests_per_minute:
        raise TooManyRequests("Too many symptom searches. Please wait a minute and try again.")


@router.get("", response_model=list[SymptomOut], operation_id="listSymptoms")
async def list_symptoms(session: SessionDep) -> list[SymptomOut]:
    rows = await session.scalars(
        select(Symptom).where(Symptom.is_active.is_(True)).order_by(Symptom.name)
    )
    return [SymptomOut.model_validate(s) for s in rows.all()]


@router.post(
    "/interpret",
    response_model=InterpretResponse,
    operation_id="interpretSymptoms",
    responses=error_responses(422, 429),
    description=(
        "Find catalog symptoms in the patient's own words (AI search: hybrid retrieval, "
        "ColBERT rerank, relevance gate, one verified AI rephrasing). Returns symptoms for the "
        "patient to confirm, warning signs and a step-by-step trace. Falls back to word "
        "matching when AI is unavailable. Available to guests; the text is not stored."
    ),
)
async def interpret_symptoms(
    payload: InterpretRequest, session: SessionDep, redis: RedisDep, request: Request
) -> InterpretResponse:
    await _rate_limit(redis, request, "interpret")
    return await ai_symptoms.interpret(session, payload.text)


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    operation_id="recommendSpecialties",
    responses=error_responses(422, 429),
    description=(
        "Rule-based specialty suggestions for navigation only - not a diagnosis (BR-10). "
        "With `context_text` or `explain`, also ranks published doctors of those specialties "
        "(profile relevance, rating, next free slot) and adds an AI explanation; symptom ids must "
        "then all be active catalog symptoms. Available to guests; no symptom data is stored."
    ),
)
async def recommend_specialties(
    payload: RecommendationRequest, session: SessionDep, redis: RedisDep, request: Request
) -> RecommendationResponse:
    if payload.context_text is None and not payload.explain:
        return await recommendation.recommend(session, payload.symptom_ids, payload.free_text)

    await _rate_limit(redis, request, "recommend")
    ids = list(dict.fromkeys(payload.symptom_ids))
    if not ids:
        raise ValidationFailed("Confirm at least one symptom.")
    active = set(
        (
            await session.scalars(
                select(Symptom.id).where(Symptom.id.in_(ids), Symptom.is_active.is_(True))
            )
        ).all()
    )
    unknown = [i for i in ids if i not in active]
    if unknown:
        raise ValidationFailed(f"Unknown or inactive symptom id(s): {unknown}.")
    return await ai_symptoms.recommend(session, ids, payload.context_text, payload.explain)
