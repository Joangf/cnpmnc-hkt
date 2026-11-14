"""Symptom catalog and symptom -> specialty rules (SCRUM-43). ADMIN only; every change audited.

Rules are disabled rather than deleted. A failed update leaves the last valid ruleset in
place (the transaction is rolled back). Changes reach the AI search index within one
`search_index_interval_seconds`, and the next recommendation uses the new rules at once.
"""

import asyncio

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, SessionDep
from app.core.db import SessionLocal
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import Specialty, Symptom, SymptomSpecialtyRule
from app.schemas.common import error_responses
from app.schemas.symptoms import (
    AdminRuleCreate,
    AdminRuleOut,
    AdminRuleUpdate,
    AdminSymptomCreate,
    AdminSymptomOut,
    AdminSymptomUpdate,
)
from app.services import audit, search_index

router = APIRouter(prefix="/admin", tags=["admin"], responses=error_responses(401, 403))


async def _reindex_soon() -> None:
    async with SessionLocal() as session:
        await search_index.sync_index(session)


def _schedule_reindex() -> None:
    asyncio.get_running_loop().create_task(_reindex_soon())


async def _load_symptom(session: AsyncSession, symptom_id: int) -> Symptom:
    symptom = await session.get(Symptom, symptom_id)
    if symptom is None:
        raise NotFound("Symptom not found.")
    return symptom


async def _symptom_out(session: AsyncSession, symptom_id: int) -> AdminSymptomOut:
    rules = (
        await session.scalars(
            select(SymptomSpecialtyRule)
            .where(SymptomSpecialtyRule.symptom_id == symptom_id)
            .order_by(SymptomSpecialtyRule.weight.desc(), SymptomSpecialtyRule.id)
        )
    ).all()
    specialties = {
        s.id: s.name
        for s in (
            await session.scalars(
                select(Specialty).where(Specialty.id.in_([r.specialty_id for r in rules]))
            )
        ).all()
    }
    symptom = await _load_symptom(session, symptom_id)
    return AdminSymptomOut(
        id=symptom.id,
        name=symptom.name,
        keywords=symptom.keywords,
        description=symptom.description,
        is_red_flag=symptom.is_red_flag,
        red_flag_message=symptom.red_flag_message,
        is_active=symptom.is_active,
        rules=[
            AdminRuleOut(
                id=r.id,
                symptom_id=r.symptom_id,
                specialty_id=r.specialty_id,
                specialty_name=specialties.get(r.specialty_id, "?"),
                weight=r.weight,
                is_active=r.is_active,
            )
            for r in rules
        ],
    )


async def _ensure_unique_name(session: AsyncSession, name: str, exclude_id: int | None) -> None:
    stmt = select(Symptom.id).where(func.lower(Symptom.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Symptom.id != exclude_id)
    if await session.scalar(stmt):
        raise Conflict(f"A symptom named '{name}' already exists.", code="DuplicateName")


async def _active_specialty(session: AsyncSession, specialty_id: int) -> Specialty:
    specialty = await session.get(Specialty, specialty_id)
    if specialty is None:
        raise ValidationFailed(
            f"Specialty #{specialty_id} does not exist.", code="InvalidReference"
        )
    if not specialty.is_active:
        raise ValidationFailed(
            f"Specialty '{specialty.name}' is inactive.", code="InvalidReference"
        )
    return specialty


async def _commit(session: AsyncSession, message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict(message, code="WriteRejected") from exc


def _check_red_flag(is_red_flag: bool, message: str | None) -> None:
    if is_red_flag and not (message or "").strip():
        raise ValidationFailed("A warning-sign symptom needs a warning message.")


@router.get("/symptoms", response_model=list[AdminSymptomOut], operation_id="adminListSymptoms")
async def admin_list_symptoms(admin: AdminUser, session: SessionDep) -> list[AdminSymptomOut]:
    ids = (await session.scalars(select(Symptom.id).order_by(Symptom.name))).all()
    return [await _symptom_out(session, i) for i in ids]


@router.post(
    "/symptoms",
    status_code=status.HTTP_201_CREATED,
    response_model=AdminSymptomOut,
    operation_id="adminCreateSymptom",
    responses=error_responses(409, 422),
)
async def admin_create_symptom(
    payload: AdminSymptomCreate, admin: AdminUser, session: SessionDep
) -> AdminSymptomOut:
    _check_red_flag(payload.is_red_flag, payload.red_flag_message)
    await _ensure_unique_name(session, payload.name, None)
    symptom = Symptom(**payload.model_dump())
    session.add(symptom)
    await session.flush()
    audit.record(session, "symptom.created", "symptom", symptom.id, actor_id=admin.id)
    await _commit(session, "A symptom with this name already exists.")
    _schedule_reindex()
    return await _symptom_out(session, symptom.id)


@router.patch(
    "/symptoms/{symptom_id}",
    response_model=AdminSymptomOut,
    operation_id="adminUpdateSymptom",
    responses=error_responses(404, 409, 422),
)
async def admin_update_symptom(
    symptom_id: int, payload: AdminSymptomUpdate, admin: AdminUser, session: SessionDep
) -> AdminSymptomOut:
    symptom = await _load_symptom(session, symptom_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        if not changes["name"]:
            raise ValidationFailed("'name' cannot be empty.")
        await _ensure_unique_name(session, changes["name"], symptom_id)
    _check_red_flag(
        changes.get("is_red_flag", symptom.is_red_flag),
        changes.get("red_flag_message", symptom.red_flag_message),
    )
    for field, value in changes.items():
        if field in ("is_red_flag", "is_active") and value is None:
            raise ValidationFailed(f"'{field}' cannot be empty.")
        setattr(symptom, field, value)
    audit.record(
        session,
        "symptom.updated",
        "symptom",
        symptom_id,
        actor_id=admin.id,
        details={"fields": sorted(changes)},
    )
    await _commit(session, "A symptom with this name already exists.")
    _schedule_reindex()
    return await _symptom_out(session, symptom_id)


@router.post(
    "/symptoms/{symptom_id}/rules",
    status_code=status.HTTP_201_CREATED,
    response_model=AdminSymptomOut,
    operation_id="adminCreateSymptomRule",
    responses=error_responses(404, 409, 422),
)
async def admin_create_rule(
    symptom_id: int, payload: AdminRuleCreate, admin: AdminUser, session: SessionDep
) -> AdminSymptomOut:
    await _load_symptom(session, symptom_id)
    await _active_specialty(session, payload.specialty_id)
    existing = await session.scalar(
        select(SymptomSpecialtyRule).where(
            SymptomSpecialtyRule.symptom_id == symptom_id,
            SymptomSpecialtyRule.specialty_id == payload.specialty_id,
        )
    )
    if existing is not None:
        # One mapping per (symptom, specialty): edit or re-enable it instead (documented policy).
        raise Conflict(
            "This symptom already maps to that specialty. Edit or re-enable the existing rule.",
            code="DuplicateRule",
        )
    rule = SymptomSpecialtyRule(
        symptom_id=symptom_id, specialty_id=payload.specialty_id, weight=payload.weight
    )
    session.add(rule)
    await session.flush()
    audit.record(
        session,
        "symptom_rule.created",
        "symptom_rule",
        rule.id,
        actor_id=admin.id,
        details={
            "symptom_id": symptom_id,
            "specialty_id": payload.specialty_id,
            "weight": payload.weight,
        },
    )
    await _commit(session, "This symptom already maps to that specialty.")
    return await _symptom_out(session, symptom_id)


@router.patch(
    "/symptom-rules/{rule_id}",
    response_model=AdminSymptomOut,
    operation_id="adminUpdateSymptomRule",
    responses=error_responses(404, 422),
)
async def admin_update_rule(
    rule_id: int, payload: AdminRuleUpdate, admin: AdminUser, session: SessionDep
) -> AdminSymptomOut:
    rule = await session.get(SymptomSpecialtyRule, rule_id)
    if rule is None:
        raise NotFound("Rule not found.")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None:
            raise ValidationFailed(f"'{field}' cannot be empty.")
        setattr(rule, field, value)
    if changes.get("is_active"):
        await _active_specialty(session, rule.specialty_id)  # no re-enabling into a dead specialty
    audit.record(
        session, "symptom_rule.updated", "symptom_rule", rule_id, actor_id=admin.id, details=changes
    )
    await _commit(session, "The rule could not be saved.")
    return await _symptom_out(session, rule.symptom_id)
