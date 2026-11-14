"""AI symptom search and recommendations (SCRUM-39..43, 48). Navigation only, never a diagnosis.

The language model never decides what is recommended. Every result is a catalog row:

    interpret(text)
      1  red-flag rules on the text as written (deterministic, before anything else)
      2  hybrid retrieval over symptom phrases: dense (pgvector) + lexical (Postgres FTS),
         fused by Reciprocal Rank Fusion
      3  rerank: ColBERT phrase coverage - how fully a symptom phrase appears in the text
      4  relevance gate: a symptom is kept only above an absolute score
      5  nothing kept -> ONE corrective round: the LLM rephrases the text in the catalog's
         words; a symptom found that way must ALSO relate to the original text
         (`ai_rephrase_floor_score`), so a rephrasing that changed the meaning finds nothing
      6  red-flag rules again on the symptoms kept
    -> the user confirms or edits the symptom chips

    recommend(confirmed symptom ids)
      7  specialties scored ONLY by the active symptom -> specialty rules (SCRUM-40)
      8  published doctors of those specialties ranked by profile relevance (ColBERT),
         rating and next free slot (SCRUM-48)
      9  the LLM explains the ranking it was given; ids it mentions are checked

Any AI failure falls back to the rule-only matcher, flagged `mode="rule_fallback"`.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.llm import AIUnavailable, get_llm
from app.models import Appointment, Doctor, DoctorSlot, SearchDocument, Symptom
from app.models.base import utcnow
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES
from app.repositories import directory as directory_repo
from app.schemas.symptoms import (
    DoctorRecommendation,
    InterpretedSymptom,
    InterpretResponse,
    RecommendationResponse,
    SpecialtyExplanation,
    TraceStep,
)
from app.services import recommendation as rules
from app.services.search_index import DOCTOR, SYMPTOM, colbert_from_bytes

logger = structlog.get_logger(__name__)

_CLAUSE_SPLIT = re.compile(r"[,.;:!?\n]+|\s+(?:và|với|kèm|kèm theo|hoặc|and|with|or|plus)\s+", re.I)
_WORD = re.compile(r"\w+", re.UNICODE)
_VIETNAMESE = re.compile(
    r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I
)


def clauses(text: str) -> list[str]:
    """The text cut at punctuation and joining words, for the dense and lexical legs:
    a long sentence about three symptoms embeds as three short queries."""
    parts = [" ".join(p.split()) for p in _CLAUSE_SPLIT.split(text)]
    parts = [p for p in parts if len(p) >= 2][: settings.ai_max_symptoms]
    return parts or [" ".join(text.split())]


def language_of(text: str | None) -> str:
    return "vi" if text and _VIETNAMESE.search(text) else "en"


def content_tokens(matrix: np.ndarray) -> np.ndarray:
    """bge-m3 ColBERT ends every text with the </s> vector. It matches any other </s> at
    ~0.83, which lifts the score of short phrases, so scoring leaves it out."""
    return matrix[:-1] if len(matrix) > 1 else matrix


def token_matches(phrase: np.ndarray, text: np.ndarray) -> np.ndarray:
    """For each content token of the phrase, its best ColBERT match in the text."""
    return (content_tokens(phrase) @ content_tokens(text).T).max(axis=1)


def phrase_coverage(phrase: np.ndarray, text: np.ndarray) -> float:
    """ColBERT MaxSim seen from the phrase: 1.0 = every token of the phrase is in the text."""
    return float(token_matches(phrase, text).mean())


def text_coverage(text: np.ndarray, profile: np.ndarray) -> float:
    """ColBERT MaxSim seen from the query: how much of the text a doctor profile covers."""
    return float((content_tokens(text) @ content_tokens(profile).T).max(axis=1).mean())


def words(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(unicodedata.normalize("NFC", text))}


def phrase_present(phrase: str, text: str) -> bool:
    """Every word of the phrase is written in the text (any order)."""
    phrase_words = words(phrase)
    return bool(phrase_words) and phrase_words <= words(text)


def rrf(rankings: list[list[int]], k: int) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, 1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return scores


def _tsquery(text: str) -> str | None:
    words = {w.lower() for w in _WORD.findall(text) if len(w) > 1 or not w.isascii()}
    return " | ".join(sorted(words)) or None


@dataclass
class _Phrase:
    symptom_id: int
    text: str
    matrix: np.ndarray


@dataclass
class _Scored:
    symptom_id: int
    score: float  # mean token match (0-1), used for ranking
    phrase: str
    weakest: float = 0.0  # worst-matched token of the phrase
    literal: bool = False  # every word of the phrase is written in the text
    via: str = "text"
    original_score: float | None = None

    @property
    def passes(self) -> bool:
        """Relevance gate. A phrase counts only if all of it is in the text: written word
        for word, or every token matched closely (a paraphrase). An average alone lets a
        phrase in on one strong word - "child fever" for any text that says "fever"."""
        return self.literal or (
            self.weakest >= settings.ai_token_floor_score
            and self.score >= settings.ai_gate_min_score
        )

    def rank_key(self) -> tuple[bool, float]:
        return (self.passes, self.score)


@dataclass
class _Run:
    trace: list[TraceStep] = field(default_factory=list)

    def step(
        self,
        key: str,
        title: str,
        summary: str,
        rows: list[dict[str, Any]] | None = None,
        skipped: bool = False,
    ) -> None:
        self.trace.append(
            TraceStep(key=key, title=title, summary=summary, rows=rows or [], skipped=skipped)
        )


# --- retrieval ------------------------------------------------------------------------------


async def _hybrid(
    session: AsyncSession, queries: list[str], vectors: list[np.ndarray]
) -> tuple[dict[int, float], list[dict[str, Any]]]:
    """Symptom ids by RRF over every (query, leg) ranking, plus trace rows."""
    k = settings.ai_candidates_per_leg
    rankings: list[list[int]] = []
    seen_rows: dict[int, dict[str, Any]] = {}
    for query, vector in zip(queries, vectors, strict=True):
        dense = (
            await session.execute(
                select(SearchDocument.entity_id, SearchDocument.content)
                .where(SearchDocument.entity_type == SYMPTOM)
                .order_by(SearchDocument.embedding.cosine_distance(vector.tolist()))
                .limit(k)
            )
        ).all()
        rankings.append(_dedupe([r.entity_id for r in dense]))
        for rank, r in enumerate(dense[:5], 1):
            seen_rows.setdefault(
                r.entity_id, {"leg": "dense", "query": query, "phrase": r.content, "rank": rank}
            )
        tsq = _tsquery(query)
        if tsq:
            query_ts = func.to_tsquery("simple", tsq)
            lexical = (
                await session.execute(
                    select(SearchDocument.entity_id, SearchDocument.content)
                    .where(
                        SearchDocument.entity_type == SYMPTOM, SearchDocument.tsv.op("@@")(query_ts)
                    )
                    .order_by(func.ts_rank(SearchDocument.tsv, query_ts).desc())
                    .limit(k)
                )
            ).all()
            rankings.append(_dedupe([r.entity_id for r in lexical]))
            for rank, r in enumerate(lexical[:5], 1):
                seen_rows.setdefault(
                    r.entity_id,
                    {"leg": "lexical", "query": query, "phrase": r.content, "rank": rank},
                )
    fused = rrf(rankings, settings.ai_rrf_k)
    rows = [
        {**seen_rows.get(sid, {}), "symptom_id": sid, "rrf": round(score, 4)}
        for sid, score in sorted(fused.items(), key=lambda kv: -kv[1])[:12]
    ]
    return fused, rows


def _dedupe(ids: list[int]) -> list[int]:
    return list(dict.fromkeys(ids))


async def _phrases(session: AsyncSession, symptom_ids: list[int]) -> list[_Phrase]:
    if not symptom_ids:
        return []
    rows = (
        await session.execute(
            select(SearchDocument.entity_id, SearchDocument.content, SearchDocument.colbert).where(
                SearchDocument.entity_type == SYMPTOM, SearchDocument.entity_id.in_(symptom_ids)
            )
        )
    ).all()
    return [
        _Phrase(r.entity_id, r.content, colbert_from_bytes(r.colbert, settings.embedding_dims))
        for r in rows
    ]


def _rerank(phrases: list[_Phrase], text: np.ndarray, text_str: str) -> dict[int, _Scored]:
    """Best phrase per symptom: a phrase that passes the gate first, then the higher score."""
    best: dict[int, _Scored] = {}
    for p in phrases:
        matches = token_matches(p.matrix, text)
        scored = _Scored(
            p.symptom_id,
            float(matches.mean()),
            p.text,
            weakest=float(matches.min()),
            literal=phrase_present(p.text, text_str),
        )
        current = best.get(p.symptom_id)
        if current is None or scored.rank_key() > current.rank_key():
            best[p.symptom_id] = scored
    return best


async def _rephrase(text: str, vocabulary: list[str]) -> list[str]:
    llm = get_llm()
    system = (
        "You help a hospital website search its symptom catalog. Rewrite the patient's words as "
        f"up to {settings.ai_rephrase_variants} short alternative phrasings that use the "
        "catalog's vocabulary. Keep the meaning exactly: do not add symptoms, do not guess a "
        "disease, do not answer. Only use a catalog entry that means the same thing - the same "
        "body part and the same problem. If no catalog entry means what the patient describes "
        "(another body part, another kind of problem, or not a symptom at all), do NOT map it to "
        'the nearest entry: return {"variants": []}. '
        'Return JSON: {"variants": ["..."]}.\n'
        "Catalog vocabulary: " + "; ".join(vocabulary)
    )
    data = await llm.chat_json(system, text, max_tokens=200, purpose="symptom_rephrase")
    variants = data.get("variants") if isinstance(data, dict) else None
    if not isinstance(variants, list):
        raise AIUnavailable("rephrase: no variants")
    out = []
    for v in variants:
        if isinstance(v, str) and v.strip() and v.strip().lower() != text.strip().lower():
            out.append(" ".join(v.split())[:200])
    return out[: settings.ai_rephrase_variants]


# --- interpret ------------------------------------------------------------------------------


async def interpret(session: AsyncSession, text: str) -> InterpretResponse:
    run = _Run()
    symptoms = (await session.scalars(select(Symptom).where(Symptom.is_active.is_(True)))).all()
    by_id = {s.id: s for s in symptoms}

    # 1. Red-flag rules on the text as written: no model involved, cannot be talked out of it.
    red_terms = [rules._terms(s) for s in symptoms if s.is_red_flag]
    red_hits = rules.match_free_text(text, red_terms)
    run.step(
        "red_flag_text",
        "Warning-sign rules (your words)",
        f"{len(red_hits)} warning sign(s) matched by the clinician-reviewed keyword rules.",
        [{"symptom": by_id[i].name} for i in sorted(red_hits)],
    )

    try:
        llm = get_llm()
        parts = clauses(text)
        dense_vectors = await llm.embed(parts)
        text_matrix = (await llm.embed_colbert([text]))[0]
    except AIUnavailable as exc:
        return _interpret_fallback(run, text, by_id, red_hits, str(exc))

    # 2. Hybrid retrieval.
    fused, hybrid_rows = await _hybrid(session, parts, dense_vectors)
    for row in hybrid_rows:
        symptom = by_id.get(row.pop("symptom_id"))
        row["symptom"] = symptom.name if symptom else "?"
    run.step(
        "hybrid",
        "Hybrid search (meaning + keywords)",
        f"Text split into {len(parts)} part(s): {' | '.join(parts)}. "
        f"{len(fused)} candidate symptom(s) from the dense and keyword searches, fused by RRF.",
        hybrid_rows,
    )

    # 3. Rerank every phrase of every candidate against the full text.
    candidate_ids = [sid for sid in fused if sid in by_id]
    scored = _rerank(await _phrases(session, candidate_ids), text_matrix, text)
    ranked = sorted(scored.values(), key=lambda s: (not s.passes, -s.score))
    run.step(
        "rerank",
        "Rerank (ColBERT phrase match)",
        "Each candidate scored by how fully one of its phrases appears in your text (0-1).",
        [
            {
                "symptom": by_id[s.symptom_id].name,
                "phrase": s.phrase,
                "score": round(s.score, 3),
                "weakest_token": round(s.weakest, 3),
                "written_in_text": s.literal,
            }
            for s in ranked[:10]
        ],
    )

    # 4. Relevance gate.
    kept = [s for s in ranked if s.passes]
    run.step(
        "gate",
        "Relevance gate",
        f"Kept {len(kept)} symptom(s): every word of the phrase is in your text, or every token "
        f"matches at least {settings.ai_token_floor_score} with an average of at least "
        f"{settings.ai_gate_min_score}.",
        [
            {
                "symptom": by_id[s.symptom_id].name,
                "phrase": s.phrase,
                "decision": "kept" if s.passes else "dropped",
            }
            for s in ranked[:8]
        ],
    )

    # 5. Corrective round, only when nothing passed but something came close.
    best = ranked[0].score if ranked else 0.0
    if not kept and best >= settings.ai_rephrase_min_best_score:
        kept = await _corrective(session, run, text, text_matrix, by_id)
    elif not kept:
        run.step(
            "rephrase",
            "Rephrase (AI)",
            f"Skipped: the best candidate scored {best:.3f}, under "
            f"{settings.ai_rephrase_min_best_score} - nothing in the text looks like a symptom.",
            skipped=True,
        )

    kept = kept[: settings.ai_max_symptoms]
    # 6. Red-flag rules again, on the symptoms found.
    red_ids = set(red_hits) | {s.symptom_id for s in kept if by_id[s.symptom_id].is_red_flag}
    run.step(
        "red_flag_symptoms",
        "Warning-sign rules (symptoms found)",
        f"{len(red_ids)} warning sign(s) in total.",
        [{"symptom": by_id[i].name} for i in sorted(red_ids)],
    )
    return InterpretResponse(
        mode="ai",
        symptoms=[
            InterpretedSymptom(
                id=s.symptom_id,
                name=by_id[s.symptom_id].name,
                score=round(s.score, 3),
                matched_phrase=s.phrase,
                via=s.via,
            )
            for s in kept
        ],
        urgent_warning=rules.urgent_warning([by_id[i] for i in sorted(red_ids)]),
        disclaimer=rules.DISCLAIMER,
        trace=run.trace,
    )


async def _corrective(
    session: AsyncSession, run: _Run, text: str, text_matrix: np.ndarray, by_id: dict[int, Symptom]
) -> list[_Scored]:
    vocabulary = sorted(s.name for s in by_id.values())
    try:
        variants = await _rephrase(text, vocabulary)
        if not variants:
            run.step(
                "rephrase",
                "Rephrase (AI)",
                "The AI found nothing in your text that the symptom catalog covers.",
            )
            return []
        llm = get_llm()
        vectors = await llm.embed(variants)
        variant_matrices = await llm.embed_colbert(variants)
    except AIUnavailable as exc:
        run.step("rephrase", "Rephrase (AI)", f"Skipped: {exc}.", skipped=True)
        return []

    fused, _ = await _hybrid(session, variants, vectors)
    phrases = await _phrases(session, [sid for sid in fused if sid in by_id])
    best_variant: dict[int, _Scored] = {}
    for variant, matrix in zip(variants, variant_matrices, strict=True):
        for sid, scored in _rerank(phrases, matrix, variant).items():
            if sid not in best_variant or scored.rank_key() > best_variant[sid].rank_key():
                best_variant[sid] = scored
    against_original = _rerank(phrases, text_matrix, text)
    floor = settings.ai_rephrase_floor_score
    accepted: list[_Scored] = []
    rows = []
    for s in sorted(best_variant.values(), key=lambda s: (not s.passes, -s.score))[:8]:
        original = against_original[s.symptom_id].score
        ok = s.passes and original >= floor
        rows.append(
            {
                "symptom": by_id[s.symptom_id].name,
                "phrase": s.phrase,
                "score_rephrased": round(s.score, 3),
                "score_original": round(original, 3),
                "decision": "kept" if ok else "dropped",
            }
        )
        if ok:
            s.via, s.original_score = "rephrase", original
            accepted.append(s)
    run.step(
        "rephrase",
        "Rephrase (AI) + verification",
        f"Nothing passed the gate, so the AI rephrased your text: {' | '.join(variants)}. "
        "A symptom found this way is kept only if it passes the gate on the rephrasing "
        f"AND still scores at least {floor} on your own words.",
        rows,
    )
    return accepted


def _interpret_fallback(
    run: _Run, text: str, by_id: dict[int, Symptom], red_hits: set[int], reason: str
) -> InterpretResponse:
    matched = rules.match_free_text(text, [rules._terms(s) for s in by_id.values()])
    run.step(
        "fallback",
        "Rule-only matching",
        f"AI search unavailable ({reason}); matched " "symptom names and synonyms word for word.",
        [{"symptom": by_id[i].name} for i in sorted(matched)],
    )
    red_ids = red_hits | {i for i in matched if by_id[i].is_red_flag}
    return InterpretResponse(
        mode="rule_fallback",
        symptoms=[
            InterpretedSymptom(
                id=i, name=by_id[i].name, score=None, matched_phrase=None, via="rules"
            )
            for i in sorted(matched)
        ],
        urgent_warning=rules.urgent_warning([by_id[i] for i in sorted(red_ids)]),
        disclaimer=rules.DISCLAIMER,
        trace=run.trace,
    )


# --- recommend ------------------------------------------------------------------------------


async def recommend(
    session: AsyncSession, symptom_ids: list[int], context_text: str | None, explain: bool
) -> RecommendationResponse:
    run = _Run()
    # 7. Specialties from the active rules only - the same scoring as the rule-only checker.
    base = await rules.recommend(session, symptom_ids, None)
    run.step(
        "rules",
        "Specialty rules",
        "Specialties scored only by the clinician-maintained symptom -> specialty rules.",
        [
            {"specialty": s.name, "score": s.score, "because_of": ", ".join(s.matched_symptoms)}
            for s in base.specialties
        ],
    )
    mode = "ai"
    try:
        doctors = await _rank_doctors(
            session, run, [s.specialty_id for s in base.specialties], context_text
        )
    except AIUnavailable as exc:
        mode = "rule_fallback"
        run.step("doctors", "Doctor ranking", f"Profile relevance skipped ({exc}).", skipped=True)
        doctors = await _rank_doctors(
            session, run, [s.specialty_id for s in base.specialties], None
        )

    explanations: list[SpecialtyExplanation] = []
    summary = None
    if explain and base.specialties:
        try:
            summary, explanations = await _explain(base, context_text)
            run.step(
                "explain",
                "Explanation (AI)",
                "The AI explained the ranking it was given; specialty ids were checked.",
            )
        except AIUnavailable as exc:
            run.step("explain", "Explanation (AI)", f"Skipped: {exc}.", skipped=True)
    return base.model_copy(
        update={
            "mode": mode,
            "doctors": doctors,
            "explanation": summary,
            "specialty_explanations": explanations,
            "trace": run.trace,
        }
    )


async def _next_free_slots(session: AsyncSession, doctor_ids: list[int]) -> dict[int, datetime]:
    if not doctor_ids:
        return {}
    now = utcnow()
    earliest = now + timedelta(minutes=settings.booking_min_lead_minutes)
    horizon = now + timedelta(days=settings.booking_horizon_days)
    occupancy = (
        select(func.count(Appointment.id))
        .where(
            Appointment.slot_id == DoctorSlot.id,
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        )
        .correlate(DoctorSlot)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(DoctorSlot.doctor_id, func.min(DoctorSlot.start_time))
            .where(
                DoctorSlot.doctor_id.in_(doctor_ids),
                DoctorSlot.is_open.is_(True),
                DoctorSlot.erp_id.is_not(None),
                DoctorSlot.start_time >= earliest,
                DoctorSlot.start_time < horizon,
                occupancy < DoctorSlot.capacity,
                DoctorSlot.erp_booked_count < DoctorSlot.capacity,
            )
            .group_by(DoctorSlot.doctor_id)
        )
    ).all()
    return {doctor_id: start for doctor_id, start in rows}


async def _relevance(
    session: AsyncSession, doctor_ids: list[int], context_text: str
) -> dict[int, float]:
    text_matrix = (await get_llm().embed_colbert([context_text]))[0]
    rows = (
        await session.execute(
            select(SearchDocument.entity_id, SearchDocument.colbert).where(
                SearchDocument.entity_type == DOCTOR, SearchDocument.entity_id.in_(doctor_ids)
            )
        )
    ).all()
    return {
        r.entity_id: text_coverage(
            text_matrix, colbert_from_bytes(r.colbert, settings.embedding_dims)
        )
        for r in rows
    }


async def _rank_doctors(
    session: AsyncSession, run: _Run, specialty_ids: list[int], context_text: str | None
) -> list[DoctorRecommendation]:
    per_specialty: dict[int, list[Doctor]] = {}
    for specialty_id in specialty_ids:
        items, _ = await directory_repo.list_doctors(
            session, specialty_id=specialty_id, page=1, page_size=50
        )
        per_specialty[specialty_id] = list(items)
    all_ids = [d.id for docs in per_specialty.values() for d in docs]
    relevance = await _relevance(session, all_ids, context_text) if context_text else {}
    slots = await _next_free_slots(session, all_ids)

    w_rel = settings.ai_weight_relevance if relevance else 0.0
    w_rating, w_avail = settings.ai_weight_rating, settings.ai_weight_availability
    total = (w_rel + w_rating + w_avail) or 1.0
    now = utcnow()
    horizon_days = settings.booking_horizon_days
    out: list[DoctorRecommendation] = []
    trace_rows = []
    for specialty_id in specialty_ids:
        # Raw ColBERT relevance sits in a narrow band (~0.4-0.55); min-max it within the
        # specialty so it can be weighed against rating and availability.
        raw = [relevance.get(d.id, 0.0) for d in per_specialty[specialty_id]]
        low, high = (min(raw), max(raw)) if raw else (0.0, 0.0)
        ranked = []
        for d in per_specialty[specialty_id]:
            raw_rel = relevance.get(d.id, 0.0)
            rel = (raw_rel - low) / (high - low) if high - low > 0.01 else 0.5
            rating = float(d.rating_avg) / 5 if d.rating_count else 0.5  # unrated = neutral
            next_slot = slots.get(d.id)
            avail = (
                max(0.0, 1 - (next_slot - now).total_seconds() / 86400 / horizon_days)
                if next_slot
                else 0.0
            )
            score = (w_rel * rel + w_rating * rating + w_avail * avail) / total
            ranked.append((score, rel, rating, avail, next_slot, d, raw_rel))
        ranked.sort(key=lambda r: (-r[0], r[5].id))
        for score, rel, rating, avail, next_slot, d, raw_rel in ranked[
            : settings.ai_doctors_per_specialty
        ]:
            out.append(
                DoctorRecommendation(
                    doctor_id=d.id,
                    full_name=d.full_name,
                    title=d.title,
                    specialty_id=specialty_id,
                    department_id=d.department_id,
                    department_name=d.department.name,
                    hospital_id=d.hospital_id,
                    hospital_name=d.hospital.name,
                    rating_avg=float(d.rating_avg),
                    rating_count=d.rating_count,
                    next_available=next_slot,
                    score=round(score, 3),
                    score_relevance=round(rel, 3) if relevance else None,
                    score_rating=round(rating, 3),
                    score_availability=round(avail, 3),
                )
            )
            trace_rows.append(
                {
                    "specialty": d.department.specialty.name,
                    "doctor": d.full_name,
                    "colbert": round(raw_rel, 3) if relevance else None,
                    "relevance": round(rel, 3) if relevance else None,
                    "rating": round(rating, 3),
                    "availability": round(avail, 3),
                    "score": round(score, 3),
                }
            )
    run.step(
        "doctors",
        "Doctor ranking",
        "Published doctors of each specialty, ranked by "
        + (
            f"profile relevance (ColBERT, scaled 0-1 within the specialty) x{w_rel}, "
            if relevance
            else ""
        )
        + f"rating x{w_rating} and next free slot x{w_avail}.",
        trace_rows,
    )
    return out


async def _explain(
    base: RecommendationResponse, context_text: str | None
) -> tuple[str | None, list[SpecialtyExplanation]]:
    language = "Vietnamese" if language_of(context_text) == "vi" else "English"
    facts = {
        "symptoms": [s.name for s in base.matched_symptoms],
        "specialties": [
            {"specialty_id": s.specialty_id, "name": s.name, "matched_symptoms": s.matched_symptoms}
            for s in base.specialties
        ],
    }
    key = (
        "ai:explain:"
        + hashlib.sha256(
            json.dumps([language, facts], sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
    )
    cached = await redis_client.get(key)
    if cached:
        data = json.loads(cached)
    else:
        system = (
            "You explain a hospital website's specialty suggestions to a patient. The ranking is "
            "already decided by rules; explain it, do not change it, do not add specialties, do "
            "not diagnose or name diseases, do not give treatment advice. For each specialty write "
            "one plain sentence linking it to the patient's symptoms. Then one short overall "
            f"sentence. Write in {language}. Return JSON: "
            '{"summary": "...", "specialties": [{"specialty_id": 0, "reason": "..."}]}'
        )
        data = await get_llm().chat_json(
            system, json.dumps(facts, ensure_ascii=False), max_tokens=400, purpose="explain"
        )
        if not isinstance(data, dict):
            raise AIUnavailable("explain: not an object")
    allowed = {s.specialty_id for s in base.specialties}
    explanations = []
    for item in data.get("specialties") or []:
        if not isinstance(item, dict):
            continue
        sid, reason = item.get("specialty_id"), item.get("reason")
        if sid in allowed and isinstance(reason, str) and reason.strip():
            explanations.append(SpecialtyExplanation(specialty_id=sid, reason=reason.strip()))
            allowed.discard(sid)
    summary = data.get("summary") if isinstance(data.get("summary"), str) else None
    if not cached:
        await redis_client.set(
            key, json.dumps(data, ensure_ascii=False), ex=settings.ai_explanation_cache_seconds
        )
    return summary, explanations
