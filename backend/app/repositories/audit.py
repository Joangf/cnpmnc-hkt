"""Read-side queries for the admin audit log (NFR-10, FR-ADM-05)."""

from datetime import datetime

from sqlalchemy import Select, String, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, AuditLog, PatientProfile, Payment, User
from app.models.enums import ActorType
from app.repositories.base import paginate


async def list_admin(
    session: AsyncSession,
    *,
    actor: str | None,
    actor_id: int | None,
    actor_type: ActorType | None,
    appointment: str | None,
    entity_type: str | None,
    entity_id: str | None,
    action: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[AuditLog], int]:
    stmt: Select[tuple[AuditLog]] = (
        select(AuditLog)
        .options(selectinload(AuditLog.actor).selectinload(User.profile))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if actor_type is not None:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if actor:
        pattern = f"%{actor.strip()}%"
        stmt = (
            stmt.join(AuditLog.actor)
            .outerjoin(PatientProfile, PatientProfile.user_id == User.id)
            .where(or_(User.email.ilike(pattern), PatientProfile.full_name.ilike(pattern)))
        )
    if appointment:
        # Accept either the numeric appointment id or the booking reference.
        ref = appointment.strip()
        match = Appointment.booking_reference == ref
        if ref.isdigit():
            match = or_(match, Appointment.id == int(ref))
        appointment_ids = select(Appointment.id).where(match)
        appointment_refs = select(cast(Appointment.id, String)).where(match)
        payment_ids = select(cast(Payment.id, String)).where(
            Payment.appointment_id.in_(appointment_ids)
        )
        # Booking, payment and refund rows all belong to the same appointment.
        stmt = stmt.where(
            or_(
                and_(
                    AuditLog.entity_type == "appointment",
                    AuditLog.entity_id.in_(appointment_refs),
                ),
                and_(AuditLog.entity_type == "payment", AuditLog.entity_id.in_(payment_ids)),
                AuditLog.details["appointment_id"].astext.in_(appointment_refs),
            )
        )
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at < date_to)
    return await paginate(session, stmt, page, page_size)
