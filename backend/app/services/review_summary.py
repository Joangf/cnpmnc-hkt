"""AI summary of a doctor's public reviews (SCRUM-46, follows SCRUM-47 moderation).

Only PUBLISHED reviews with a comment are read - hidden or removed ones never reach the
model. The summary is stored with a hash of the review set it was made from, and made
again (lazily, on the next profile view) only when that set changes: a new review, an
edit, or a moderation decision. Each point must cite the ids of the reviews behind it;
points citing nothing valid are dropped. A failure never blocks the doctor profile.
"""

from __future__ import annotations

import hashlib
import json

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.llm import AIUnavailable, get_llm
from app.models import DoctorReviewSummary, Review
from app.models.base import utcnow
from app.models.enums import ReviewStatus
from app.schemas.reviews import ReviewSummaryOut, ReviewSummaryPoint

logger = structlog.get_logger(__name__)

_SYSTEM = (
    "You summarise patient reviews of one doctor for a hospital website. Use ONLY the reviews "
    "given. Write a 1-2 sentence neutral overview, then 2-4 short points about what patients "
    "repeatedly praise or criticise (manner, explanations, waiting time, ...). Every point must "
    "list the ids of the reviews it comes from. Do not invent facts, do not give medical advice, "
    "do not mention patient names or personal details. Always write in English, even if some reviews are in another language. "
    'Return JSON: {"summary": "...", "points": [{"text": "...", "review_ids": [1, 2]}]}'
)


async def _visible_reviews(session: AsyncSession, doctor_id: int) -> list[Review]:
    stmt = (
        select(Review)
        .where(
            Review.doctor_id == doctor_id,
            Review.status == ReviewStatus.PUBLISHED,
            Review.comment.is_not(None),
            func.length(func.trim(Review.comment)) > 0,
        )
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(settings.review_summary_max_reviews)
    )
    return list((await session.scalars(stmt)).all())


def review_set_hash(reviews: list[Review]) -> str:
    material = sorted((r.id, r.rating, (r.comment or "").strip()) for r in reviews)
    return hashlib.sha256(json.dumps(material, ensure_ascii=False).encode()).hexdigest()


def _out(row: DoctorReviewSummary, *, stale: bool, count: int) -> ReviewSummaryOut:
    return ReviewSummaryOut(
        status="ready",
        summary=row.summary,
        points=[ReviewSummaryPoint(**p) for p in row.points],
        review_count=count,
        min_reviews=settings.review_summary_min_reviews,
        generated_at=row.generated_at,
        stale=stale,
    )


async def get_summary(session: AsyncSession, doctor_id: int) -> ReviewSummaryOut:
    reviews = await _visible_reviews(session, doctor_id)
    count = len(reviews)
    stored = await session.get(DoctorReviewSummary, doctor_id)
    if count < settings.review_summary_min_reviews:
        if stored is not None:  # reviews were hidden since: the old summary must go too
            await session.delete(stored)
            await session.commit()
        return ReviewSummaryOut(
            status="insufficient",
            review_count=count,
            min_reviews=settings.review_summary_min_reviews,
        )

    digest = review_set_hash(reviews)
    if stored is not None and stored.review_set_hash == digest:
        return _out(stored, stale=False, count=count)

    lock = f"ai:review-summary-lock:{doctor_id}"
    if not await redis_client.set(lock, "1", nx=True, ex=90):
        # Another request is writing it. Never show a summary of a set that lost reviews.
        return ReviewSummaryOut(
            status="generating", review_count=count, min_reviews=settings.review_summary_min_reviews
        )
    try:
        summary, points = await _generate(reviews)
    except AIUnavailable as exc:
        logger.warning("review_summary_failed", doctor_id=doctor_id, error=str(exc))
        return ReviewSummaryOut(
            status="unavailable",
            review_count=count,
            min_reviews=settings.review_summary_min_reviews,
        )
    finally:
        await redis_client.delete(lock)

    if stored is None:
        stored = DoctorReviewSummary(doctor_id=doctor_id)
        session.add(stored)
    stored.summary = summary
    stored.points = points
    stored.review_count = count
    stored.review_set_hash = digest
    stored.generated_at = utcnow()
    await session.commit()
    return _out(stored, stale=False, count=count)


async def _generate(reviews: list[Review]) -> tuple[str, list[dict]]:
    lines = [f"[{r.id}] {r.rating}/5: {' '.join((r.comment or '').split())[:600]}" for r in reviews]
    data = await get_llm().chat_json(
        _SYSTEM, "\n".join(lines), max_tokens=500, purpose="review_summary"
    )
    if not isinstance(data, dict) or not isinstance(data.get("summary"), str):
        raise AIUnavailable("review summary: no summary")
    valid_ids = {r.id for r in reviews}
    points = []
    for p in data.get("points") or []:
        if not isinstance(p, dict) or not isinstance(p.get("text"), str):
            continue
        cited = [i for i in p.get("review_ids") or [] if isinstance(i, int) and i in valid_ids]
        if cited and p["text"].strip():
            points.append({"text": p["text"].strip(), "review_ids": sorted(set(cited))})
    return data["summary"].strip(), points
