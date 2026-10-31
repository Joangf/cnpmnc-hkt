"""Basic operational reporting (FRD 4.14)."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, PatientProfile, Payment, RecommendationLog, Specialty
from app.schemas.admin import PaymentStatusSummary, ReportSummary, SpecialtyStat


async def summary(
    session: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> ReportSummary:
    appt_stmt = select(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status)
    pay_stmt = select(
        Payment.status, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)
    ).group_by(Payment.status)
    spec_stmt = (
        select(Specialty.id, Specialty.name, func.count(RecommendationLog.id).label("n"))
        .join(RecommendationLog, RecommendationLog.specialty_id == Specialty.id)
        .group_by(Specialty.id, Specialty.name)
        .order_by(func.count(RecommendationLog.id).desc())
        .limit(10)
    )
    if date_from:
        appt_stmt = appt_stmt.where(Appointment.start_time >= date_from)
        pay_stmt = pay_stmt.where(Payment.created_at >= date_from)
        spec_stmt = spec_stmt.where(RecommendationLog.created_at >= date_from)
    if date_to:
        appt_stmt = appt_stmt.where(Appointment.start_time < date_to)
        pay_stmt = pay_stmt.where(Payment.created_at < date_to)
        spec_stmt = spec_stmt.where(RecommendationLog.created_at < date_to)

    appointments = {
        str(status): int(count) for status, count in (await session.execute(appt_stmt)).all()
    }
    payments = [
        PaymentStatusSummary(status=status, count=int(count), total_amount=Decimal(total))
        for status, count, total in (await session.execute(pay_stmt)).all()
    ]
    specialties = [
        SpecialtyStat(specialty_id=sid, name=name, count=int(n))
        for sid, name, n in (await session.execute(spec_stmt)).all()
    ]
    total_patients = await session.scalar(select(func.count(PatientProfile.id)))
    return ReportSummary(
        appointments_by_status=appointments,
        payments_by_status=payments,
        top_specialties=specialties,
        total_patients=int(total_patients or 0),
        generated_at=datetime.now(UTC),
    )
