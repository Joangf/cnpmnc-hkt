"""Model -> response schema mapping. Expects the relationships named in each docstring loaded."""

from datetime import UTC, datetime

from app.core.config import settings
from app.models import (
    Appointment,
    AppointmentType,
    Department,
    Doctor,
    Hospital,
    Payment,
    Review,
    User,
)
from app.models.enums import DepartmentVisibility
from app.schemas.admin import AdminUserOut, AppointmentTypeAdminOut, DepartmentAdminOut
from app.schemas.appointments import (
    AdminAppointmentOut,
    AppointmentDetail,
    AppointmentSummary,
    PaymentSummary,
    StatusHistoryOut,
)
from app.schemas.auth import UserMe
from app.schemas.common import RefOut
from app.schemas.directory import (
    AppointmentTypeOut,
    DepartmentOut,
    DepartmentPublicDetail,
    DepartmentSummary,
    DoctorDetail,
    DoctorSummary,
    HospitalDetail,
    HospitalSummary,
    SpecialtyOut,
)
from app.schemas.payments import PaymentOut
from app.schemas.profile import ProfileOut
from app.schemas.reviews import AdminReviewOut, ReviewPublic
from app.services import policies


def user_me(user: User) -> UserMe:
    """Needs: user.profile."""
    profile = user.profile
    return UserMe(
        id=user.id,
        email=user.email,
        role=user.role,
        account_status=user.account_status,
        full_name=profile.full_name if profile else None,
        patient_id=profile.id if profile else None,
    )


def profile_out(user: User) -> ProfileOut:
    """Needs: user.profile (non-null)."""
    profile = user.profile
    assert profile is not None
    return ProfileOut(
        id=profile.id,
        email=user.email,
        full_name=profile.full_name,
        date_of_birth=profile.date_of_birth,
        phone_number=profile.phone_number,
        address=profile.address,
    )


def admin_user(user: User) -> AdminUserOut:
    """Needs: user.profile."""
    return AdminUserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        account_status=user.account_status,
        full_name=user.profile.full_name if user.profile else None,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def department_out(department: Department) -> DepartmentOut:
    """Needs: department.specialty."""
    return DepartmentOut(
        id=department.id,
        hospital_id=department.hospital_id,
        name=department.name,
        description=department.description,
        location=department.location,
        specialty=SpecialtyOut.model_validate(department.specialty),
        is_active=department.is_active,
    )


def department_admin_out(department: Department) -> DepartmentAdminOut:
    """Needs: department.specialty."""
    return DepartmentAdminOut(
        **department_out(department).model_dump(),
        visibility=department.visibility,
    )


def _active_doctors(department: Department) -> list[Doctor]:
    return sorted((d for d in department.doctors if d.is_active), key=lambda d: d.full_name)


def department_summary(department: Department) -> DepartmentSummary:
    """Needs: department.hospital, department.specialty, department.doctors."""
    return DepartmentSummary(
        id=department.id,
        name=department.name,
        description=department.description,
        location=department.location,
        hospital=RefOut(id=department.hospital.id, name=department.hospital.name),
        specialty=SpecialtyOut.model_validate(department.specialty),
        doctor_count=len(_active_doctors(department)),
    )


def department_public_detail(department: Department) -> DepartmentPublicDetail:
    """Needs: department.hospital/specialty and doctor hospital/department."""
    return DepartmentPublicDetail(
        **department_summary(department).model_dump(),
        doctors=[doctor_summary(d) for d in _active_doctors(department)],
    )


def hospital_summary(hospital: Hospital, *, include_inactive: bool = False) -> HospitalSummary:
    """Needs: hospital.departments[].specialty."""
    departments = [
        d
        for d in hospital.departments
        if include_inactive
        or (d.is_active and d.visibility == DepartmentVisibility.PUBLIC)
    ]
    specialties = {d.specialty.id: d.specialty for d in departments if d.specialty.is_active}
    return HospitalSummary(
        id=hospital.id,
        name=hospital.name,
        facility_type=hospital.facility_type,
        address=hospital.address,
        city=hospital.city,
        phone=hospital.phone,
        email=hospital.email,
        avatar_url=hospital.avatar_url,
        description=hospital.description,
        is_active=hospital.is_active,
        specialties=[
            SpecialtyOut.model_validate(s)
            for s in sorted(specialties.values(), key=lambda s: s.name)
        ],
    )


def hospital_detail(hospital: Hospital, *, include_inactive: bool = False) -> HospitalDetail:
    summary = hospital_summary(hospital, include_inactive=include_inactive)
    departments = sorted(
        (
            d
            for d in hospital.departments
            if include_inactive
            or (d.is_active and d.visibility == DepartmentVisibility.PUBLIC)
        ),
        key=lambda d: d.name,
    )
    return HospitalDetail(
        **summary.model_dump(),
        website=hospital.website,
        departments=[department_out(d) for d in departments],
    )


def doctor_summary(doctor: Doctor) -> DoctorSummary:
    """Needs: doctor.hospital, doctor.department.specialty."""
    return DoctorSummary(
        id=doctor.id,
        full_name=doctor.full_name,
        title=doctor.title,
        experience_years=doctor.experience_years,
        consultation_fee=doctor.consultation_fee,
        currency=settings.currency,
        rating_avg=doctor.rating_avg,
        rating_count=doctor.rating_count,
        avatar_url=doctor.avatar_url,
        hospital=RefOut(id=doctor.hospital.id, name=doctor.hospital.name),
        department=RefOut(id=doctor.department.id, name=doctor.department.name),
        specialty=RefOut(id=doctor.department.specialty.id, name=doctor.department.specialty.name),
        is_active=doctor.is_active,
    )


def doctor_detail(doctor: Doctor) -> DoctorDetail:
    return DoctorDetail(
        **doctor_summary(doctor).model_dump(),
        qualifications=doctor.qualifications,
        introduction=doctor.introduction,
        erp_doctor_id=doctor.erp_doctor_id,
    )


def appointment_type_out(appointment_type: AppointmentType, doctor: Doctor) -> AppointmentTypeOut:
    return AppointmentTypeOut(
        id=appointment_type.id,
        name=appointment_type.name,
        description=appointment_type.description,
        duration_minutes=appointment_type.duration_minutes,
        buffer_minutes=appointment_type.buffer_minutes,
        fee=policies.effective_fee(doctor, appointment_type),
        currency=settings.currency,
        is_active=appointment_type.is_active,
    )


def appointment_type_admin(appointment_type: AppointmentType) -> AppointmentTypeAdminOut:
    return AppointmentTypeAdminOut(
        id=appointment_type.id,
        name=appointment_type.name,
        description=appointment_type.description,
        duration_minutes=appointment_type.duration_minutes,
        buffer_minutes=appointment_type.buffer_minutes,
        fee=appointment_type.fee_override,
        currency=settings.currency,
        is_active=appointment_type.is_active,
        fee_override=appointment_type.fee_override,
        specialty_id=appointment_type.specialty_id,
        doctor_id=appointment_type.doctor_id,
    )


def _summary_fields(appointment: Appointment) -> dict:
    """Needs: doctor.hospital, doctor.department, appointment_type, payments."""
    doctor = appointment.doctor
    return {
        "id": appointment.id,
        "booking_reference": appointment.booking_reference,
        "status": appointment.status,
        "status_reason": appointment.status_reason,
        "check_in_status": appointment.check_in_status,
        "payment_status": policies.payment_status_of(appointment.payments),
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "doctor": RefOut(id=doctor.id, name=doctor.full_name),
        "hospital": RefOut(id=doctor.hospital.id, name=doctor.hospital.name),
        "department": RefOut(id=doctor.department.id, name=doctor.department.name),
        "appointment_type": RefOut(
            id=appointment.appointment_type.id, name=appointment.appointment_type.name
        ),
        "fee_amount": appointment.fee_amount,
        "currency": appointment.currency,
    }


def appointment_summary(appointment: Appointment) -> AppointmentSummary:
    return AppointmentSummary(**_summary_fields(appointment))


def admin_appointment(appointment: Appointment) -> AdminAppointmentOut:
    return AdminAppointmentOut(**_summary_fields(appointment), patient_id=appointment.patient_id)


def appointment_detail(appointment: Appointment, now: datetime | None = None) -> AppointmentDetail:
    """Additionally needs: history, review."""
    now = now or datetime.now(UTC)
    return AppointmentDetail(
        **_summary_fields(appointment),
        reason_for_visit=appointment.reason_for_visit,
        history=[StatusHistoryOut.model_validate(h) for h in appointment.history],
        payments=[PaymentSummary.model_validate(p) for p in appointment.payments],
        can_cancel=policies.can_cancel(appointment, now),
        can_pay=policies.can_pay(appointment),
        can_review=policies.can_review(appointment),
        has_review=appointment.review is not None,
        cancellation_deadline=policies.cancellation_deadline(appointment.start_time),
    )


def payment_out(payment: Payment) -> PaymentOut:
    """Needs: payment.appointment."""
    return PaymentOut(
        id=payment.id,
        appointment_id=payment.appointment_id,
        booking_reference=payment.appointment.booking_reference,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        provider_reference=payment.provider_reference,
        failure_reason=payment.failure_reason,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
    )


def review_public(review: Review) -> ReviewPublic:
    return ReviewPublic(
        id=review.id, rating=review.rating, comment=review.comment, created_at=review.created_at
    )


def admin_review(review: Review) -> AdminReviewOut:
    """Needs: review.doctor."""
    return AdminReviewOut(
        id=review.id,
        appointment_id=review.appointment_id,
        doctor_id=review.doctor_id,
        rating=review.rating,
        comment=review.comment,
        status=review.status,
        created_at=review.created_at,
        doctor_name=review.doctor.full_name,
        patient_id=review.patient_id,
        moderation_note=review.moderation_note,
    )
