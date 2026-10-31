"""Rule-based symptom -> specialty recommendation (FRD 4.7). Not a diagnosis (BR-10).

The mapping rules and warning signs in the seed data MUST be reviewed by a qualified
healthcare professional before real use (FRD 4.7.1, OQ-06).
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import RECOMMENDATIONS
from app.models import RecommendationLog, Specialty, Symptom, SymptomSpecialtyRule
from app.repositories import directory as directory_repo
from app.schemas.symptoms import (
    RecommendationResponse,
    RecommendedDepartment,
    SpecialtyRecommendation,
    SymptomOut,
)

DISCLAIMER = (
    "These suggestions are for navigation only and are not a medical diagnosis. "
    "They are based on simple predefined rules. Please consult a qualified healthcare "
    "professional about your symptoms."
)
MAX_SPECIALTIES = 3


@dataclass(frozen=True, slots=True)
class RuleRow:
    symptom_id: int
    specialty_id: int
    weight: float


@dataclass(slots=True)
class SpecialtyScore:
    specialty_id: int
    score: float = 0.0
    symptom_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SymptomTerms:
    symptom_id: int
    terms: tuple[str, ...]


def score_specialties(selected: set[int], rules: Iterable[RuleRow]) -> list[SpecialtyScore]:
    scores: dict[int, SpecialtyScore] = {}
    for rule in rules:
        if rule.symptom_id not in selected:
            continue
        entry = scores.setdefault(rule.specialty_id, SpecialtyScore(rule.specialty_id))
        entry.score += rule.weight
        entry.symptom_ids.append(rule.symptom_id)
    return sorted(scores.values(), key=lambda s: (-s.score, s.specialty_id))


def match_free_text(text: str, symptoms: Iterable[SymptomTerms]) -> set[int]:
    """Whole-word, case-insensitive match of symptom names/keywords in free text."""
    normalized = " ".join(text.lower().split())
    matched: set[int] = set()
    for symptom in symptoms:
        for term in symptom.terms:
            term = term.strip().lower()
            if term and re.search(rf"\b{re.escape(term)}\b", normalized):
                matched.add(symptom.symptom_id)
                break
    return matched


def _terms(symptom: Symptom) -> SymptomTerms:
    keywords = [k for k in (symptom.keywords or "").split(",") if k.strip()]
    return SymptomTerms(symptom.id, (symptom.name, *keywords))


async def recommend(
    session: AsyncSession, symptom_ids: Sequence[int], free_text: str | None
) -> RecommendationResponse:
    symptoms = (await session.scalars(select(Symptom).where(Symptom.is_active.is_(True)))).all()
    by_id = {s.id: s for s in symptoms}

    selected = {i for i in symptom_ids if i in by_id}
    if free_text:
        selected |= match_free_text(free_text, [_terms(s) for s in symptoms])

    rule_rows = (
        await session.execute(
            select(
                SymptomSpecialtyRule.symptom_id,
                SymptomSpecialtyRule.specialty_id,
                SymptomSpecialtyRule.weight,
            )
            .join(Specialty, Specialty.id == SymptomSpecialtyRule.specialty_id)
            .where(
                Specialty.is_active.is_(True), SymptomSpecialtyRule.symptom_id.in_(sorted(selected))
            )
        )
    ).all()
    scored = score_specialties(selected, [RuleRow(*row) for row in rule_rows])[:MAX_SPECIALTIES]

    specialty_ids = [s.specialty_id for s in scored]
    specialties = {
        s.id: s
        for s in (
            await session.scalars(select(Specialty).where(Specialty.id.in_(specialty_ids)))
        ).all()
    }
    departments = await directory_repo.departments_for_specialties(session, specialty_ids)

    red_flags = [by_id[i] for i in sorted(selected) if by_id[i].is_red_flag]
    urgent_warning = None
    if red_flags:
        messages = dict.fromkeys(
            s.red_flag_message or f"'{s.name}' can be a warning sign." for s in red_flags
        )
        urgent_warning = (
            " ".join(messages)
            + f" If symptoms are severe or sudden, call {settings.emergency_number} or go to the"
            " nearest emergency department now."
        )

    for item in scored:
        session.add(RecommendationLog(specialty_id=item.specialty_id))
        RECOMMENDATIONS.labels(specialty=specialties[item.specialty_id].name).inc()
    await session.commit()

    return RecommendationResponse(
        matched_symptoms=[SymptomOut.model_validate(by_id[i]) for i in sorted(selected)],
        specialties=[
            SpecialtyRecommendation(
                specialty_id=item.specialty_id,
                name=specialties[item.specialty_id].name,
                score=round(item.score, 2),
                matched_symptoms=[by_id[i].name for i in item.symptom_ids],
            )
            for item in scored
        ],
        departments=[
            RecommendedDepartment(
                department_id=d.id,
                department_name=d.name,
                hospital_id=d.hospital.id,
                hospital_name=d.hospital.name,
                city=d.hospital.city,
                specialty_id=d.specialty_id,
            )
            for d in departments
        ],
        urgent_warning=urgent_warning,
        disclaimer=DISCLAIMER,
    )
