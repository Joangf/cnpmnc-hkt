"""Keeps `search_documents` in step with the catalog: active symptoms and published doctors.

Runs at startup and as a periodic job, so admin edits and ERP directory syncs are picked
up without hooks. Only rows whose text changed are embedded again (by `content_hash`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.integrations.llm import AIUnavailable, get_llm
from app.models import Department, Doctor, SearchDocument, Symptom
from app.services import policies

logger = structlog.get_logger(__name__)

SYMPTOM = "symptom"
DOCTOR = "doctor"
_BATCH = 32


@dataclass(frozen=True, slots=True)
class SourceDoc:
    entity_type: str
    entity_id: int
    part: int
    content: str

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.entity_type, self.entity_id, self.part)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()


def symptom_phrases(symptom: Symptom) -> list[str]:
    """The name, then each synonym; case-insensitive duplicates dropped, order kept."""
    seen: set[str] = set()
    phrases = []
    for phrase in [symptom.name, *(symptom.keywords or "").split(",")]:
        phrase = " ".join(phrase.split())
        if phrase and phrase.lower() not in seen:
            seen.add(phrase.lower())
            phrases.append(phrase)
    return phrases


def doctor_text(doctor: Doctor) -> str:
    department = doctor.department
    parts = [
        " ".join(p for p in (doctor.title, doctor.full_name) if p),
        f"Specialty: {department.specialty.name}",
        f"{department.name}, {doctor.hospital.name}",
        doctor.qualifications or "",
        doctor.introduction or "",
    ]
    return ". ".join(p for p in parts if p)


async def source_documents(session: AsyncSession) -> list[SourceDoc]:
    symptoms = (await session.scalars(select(Symptom).where(Symptom.is_active.is_(True)))).all()
    doctors = (
        (
            await session.scalars(
                select(Doctor).options(
                    joinedload(Doctor.hospital),
                    joinedload(Doctor.department).joinedload(Department.specialty),
                )
            )
        )
        .unique()
        .all()
    )
    docs = [
        SourceDoc(SYMPTOM, s.id, part, phrase)
        for s in symptoms
        for part, phrase in enumerate(symptom_phrases(s))
    ]
    docs += [
        SourceDoc(DOCTOR, d.id, 0, doctor_text(d))
        for d in doctors
        if policies.doctor_is_published(d)
    ]
    return docs


def colbert_to_bytes(matrix: np.ndarray) -> bytes:
    return np.ascontiguousarray(matrix, dtype=np.float32).tobytes()


def colbert_from_bytes(raw: bytes, dims: int) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, dims)


async def sync_index(session: AsyncSession) -> bool:
    """Bring the index up to date. False when the AI gateway is off or failing (job retries)."""
    try:
        llm = get_llm()
    except AIUnavailable:
        return True  # AI not configured: nothing to index, nothing to retry
    wanted = {d.key: d for d in await source_documents(session)}
    existing = {
        (row.entity_type, row.entity_id, row.part): (row.id, row.content_hash)
        for row in (
            await session.execute(
                select(
                    SearchDocument.id,
                    SearchDocument.entity_type,
                    SearchDocument.entity_id,
                    SearchDocument.part,
                    SearchDocument.content_hash,
                )
            )
        ).all()
    }
    stale_ids = [row_id for key, (row_id, _) in existing.items() if key not in wanted]
    changed = [
        doc
        for key, doc in wanted.items()
        if key not in existing or existing[key][1] != doc.content_hash
    ]
    if stale_ids:
        await session.execute(delete(SearchDocument).where(SearchDocument.id.in_(stale_ids)))
    try:
        for start in range(0, len(changed), _BATCH):
            batch = changed[start : start + _BATCH]
            texts = [d.content for d in batch]
            dense = await llm.embed(texts)
            colbert = await llm.embed_colbert(texts)
            for doc, vector, matrix in zip(batch, dense, colbert, strict=True):
                if doc.key in existing:
                    row = await session.get(SearchDocument, existing[doc.key][0])
                    assert row is not None
                else:
                    row = SearchDocument(
                        entity_type=doc.entity_type, entity_id=doc.entity_id, part=doc.part
                    )
                    session.add(row)
                row.content = doc.content
                row.content_hash = doc.content_hash
                row.embedding = vector.tolist()
                row.colbert = colbert_to_bytes(matrix)
            await session.commit()
    except AIUnavailable as exc:
        await session.commit()  # keep the batches that did finish
        logger.warning("search_index_failed", error=str(exc))
        return False
    await session.commit()
    if stale_ids or changed:
        logger.info("search_index_synced", embedded=len(changed), removed=len(stale_ids))
    return True
