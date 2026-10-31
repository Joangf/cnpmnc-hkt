"""Idempotent demo and load-test data.

    python -m app.seed                       # directory, rules, admin + demo patient
    python -m app.seed --loadtest-users 200  # also loadtest1..N@example.com

All hospitals, doctors and contact details are fictional. Symptom rules and warning
signs are placeholders and MUST be reviewed by a qualified clinician (FRD 4.7.1, OQ-06).
"""

import argparse
import asyncio
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.security import generate_booking_reference, hash_password
from app.models import (
    Appointment,
    AppointmentStatusHistory,
    AppointmentType,
    Department,
    Doctor,
    Hospital,
    PatientProfile,
    Specialty,
    Symptom,
    SymptomSpecialtyRule,
    User,
)
from app.models.enums import (
    AccountStatus,
    AppointmentStatus,
    CheckInStatus,
    FacilityType,
    StatusSource,
    UserRole,
)
from app.services.availability import clinic_tz

SPECIALTIES = [
    ("General Internal Medicine", "First point of contact for general adult health concerns."),
    ("Respiratory Medicine", "Lungs and breathing."),
    ("Cardiology", "Heart and circulation."),
    ("Gastroenterology", "Digestive system."),
    ("Dermatology", "Skin, hair and nails."),
    ("Ophthalmology", "Eyes and vision."),
    ("Orthopedics", "Bones, joints and muscles."),
    ("Rheumatology", "Inflammatory joint and autoimmune conditions."),
    ("Otorhinolaryngology (ENT)", "Ear, nose and throat."),
    ("Neurology", "Brain and nervous system."),
    ("Pediatrics", "Children's health."),
]

HOSPITALS = [
    {
        "name": "Riverside General Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "address": "12 Riverside Avenue, District 1",
        "city": "Ho Chi Minh City",
        "phone": "+842800000001",
        "email": "contact@riverside-general.example",
        "description": "Fictional multi-specialty hospital used for demonstration.",
        "departments": [
            "General Internal Medicine",
            "Respiratory Medicine",
            "Cardiology",
            "Gastroenterology",
            "Neurology",
            "Orthopedics",
        ],
    },
    {
        "name": "Lotus Skin & Eye Clinic",
        "facility_type": FacilityType.CLINIC,
        "address": "88 Lotus Street, District 3",
        "city": "Ho Chi Minh City",
        "phone": "+842800000002",
        "email": "hello@lotus-clinic.example",
        "description": "Fictional outpatient clinic for dermatology and ophthalmology.",
        "departments": ["Dermatology", "Ophthalmology"],
    },
    {
        "name": "Green Valley Medical Center",
        "facility_type": FacilityType.HOSPITAL,
        "address": "5 Green Valley Road, Cau Giay",
        "city": "Hanoi",
        "phone": "+842400000003",
        "email": "info@greenvalley-medical.example",
        "description": "Fictional regional medical center.",
        "departments": [
            "General Internal Medicine",
            "Pediatrics",
            "Otorhinolaryngology (ENT)",
            "Rheumatology",
            "Orthopedics",
            "Respiratory Medicine",
        ],
    },
]

FAMILY_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vo", "Dang", "Bui"]
GIVEN_NAMES = [
    "Minh An",
    "Thu Ha",
    "Quoc Bao",
    "Lan Anh",
    "Duc Huy",
    "Ngoc Mai",
    "Thanh Tung",
    "Bich Ngoc",
    "Gia Khanh",
    "Hai Yen",
]

# (name, description, duration, buffer, fee_override, specialty name or None)
APPOINTMENT_TYPES = [
    ("Standard consultation", "General consultation.", 20, 10, None, None),
    ("Extended consultation", "For complex or multiple concerns.", 30, 10, None, None),
    (
        "Follow-up visit",
        "Review of a previous consultation or test results.",
        15,
        5,
        Decimal("150000"),
        None,
    ),
    (
        "Skin procedure consultation",
        "Assessment before a minor skin procedure.",
        40,
        10,
        None,
        "Dermatology",
    ),
    (
        "Comprehensive eye examination",
        "Vision and eye health check.",
        30,
        10,
        None,
        "Ophthalmology",
    ),
]

# (name, keywords, [(specialty, weight)], red_flag_message)  -- PENDING CLINICAL REVIEW
SYMPTOMS: list[tuple[str, str, list[tuple[str, float]], str | None]] = [
    (
        "Persistent cough",
        "cough,coughing",
        [("Respiratory Medicine", 1.0), ("General Internal Medicine", 0.3)],
        None,
    ),
    (
        "Shortness of breath",
        "breathless,short of breath,difficulty breathing",
        [("Respiratory Medicine", 1.0), ("Cardiology", 0.6)],
        "Severe or sudden difficulty breathing needs urgent medical attention.",
    ),
    (
        "Chest pain",
        "chest tightness,chest pressure",
        [("Cardiology", 1.0), ("General Internal Medicine", 0.3)],
        "Chest pain can be a sign of a serious heart problem.",
    ),
    ("Palpitations", "racing heart,irregular heartbeat", [("Cardiology", 1.0)], None),
    ("Skin rash", "rash,hives", [("Dermatology", 1.0)], None),
    ("Itching", "itchy,itch", [("Dermatology", 0.8)], None),
    ("Acne", "pimples,breakouts", [("Dermatology", 1.0)], None),
    (
        "Joint pain",
        "knee pain,arthritis,painful joints",
        [("Orthopedics", 0.8), ("Rheumatology", 0.8)],
        None,
    ),
    ("Morning joint stiffness", "stiff joints", [("Rheumatology", 1.0)], None),
    ("Back pain", "lower back pain,backache", [("Orthopedics", 1.0)], None),
    ("Eye discomfort", "eye pain,red eye,eye irritation", [("Ophthalmology", 1.0)], None),
    ("Blurred vision", "blurry vision,blurred", [("Ophthalmology", 1.0)], None),
    (
        "Sudden loss of vision",
        "vision loss,cannot see",
        [("Ophthalmology", 1.0), ("Neurology", 0.6)],
        "Sudden loss of vision is a medical emergency.",
    ),
    (
        "Stomach pain",
        "abdominal pain,stomach ache,stomachache",
        [("Gastroenterology", 1.0), ("General Internal Medicine", 0.3)],
        None,
    ),
    ("Heartburn", "acid reflux,indigestion", [("Gastroenterology", 1.0)], None),
    ("Diarrhea", "loose stools", [("Gastroenterology", 1.0)], None),
    (
        "Sore throat",
        "throat pain",
        [("Otorhinolaryngology (ENT)", 1.0), ("General Internal Medicine", 0.3)],
        None,
    ),
    ("Ear pain", "earache", [("Otorhinolaryngology (ENT)", 1.0)], None),
    ("Headache", "migraine", [("Neurology", 0.8), ("General Internal Medicine", 0.5)], None),
    (
        "Sudden weakness or numbness on one side",
        "numbness,slurred speech,facial drooping",
        [("Neurology", 1.0)],
        "Sudden one-sided weakness, numbness or difficulty speaking can be signs of a stroke.",
    ),
    ("Fever", "high temperature", [("General Internal Medicine", 1.0), ("Pediatrics", 0.3)], None),
    ("Fever in a child", "child fever,baby fever", [("Pediatrics", 1.0)], None),
    ("Fatigue", "tired,tiredness,exhaustion", [("General Internal Medicine", 1.0)], None),
]


async def _seed_directory(session: AsyncSession) -> None:
    if await session.scalar(select(func.count(Specialty.id))):
        print("directory already seeded")
        return

    specialties = {name: Specialty(name=name, description=desc) for name, desc in SPECIALTIES}
    session.add_all(specialties.values())
    await session.flush()

    index = 0
    for data in HOSPITALS:
        dept_names = data["departments"]
        hospital = Hospital(**{k: v for k, v in data.items() if k != "departments"})
        session.add(hospital)
        await session.flush()
        for specialty_name in dept_names:
            department = Department(
                hospital_id=hospital.id,
                specialty_id=specialties[specialty_name].id,
                name=f"{specialty_name} Department",
            )
            session.add(department)
            await session.flush()
            for _ in range(2):
                index += 1
                family = FAMILY_NAMES[index % len(FAMILY_NAMES)]
                given = GIVEN_NAMES[(index * 3) % len(GIVEN_NAMES)]
                full_name = f"{family} {given}"
                session.add(
                    Doctor(
                        hospital_id=hospital.id,
                        department_id=department.id,
                        full_name=f"Dr. {full_name}",
                        title="MD, PhD" if index % 3 == 0 else "MD",
                        qualifications=(
                            f"Doctor of Medicine; specialist training in {specialty_name}."
                        ),
                        experience_years=5 + (index * 7) % 20,
                        introduction=(
                            f"Fictional {specialty_name.lower()} specialist at {hospital.name}, "
                            "focused on clear explanations and shared decisions."
                        ),
                        consultation_fee=Decimal(200000 + (index % 4) * 50000),
                        erp_doctor_id=f"ERP-D{index:04d}",
                    )
                )

    for name, desc, duration, buffer, fee, type_specialty in APPOINTMENT_TYPES:
        session.add(
            AppointmentType(
                name=name,
                description=desc,
                duration_minutes=duration,
                buffer_minutes=buffer,
                fee_override=fee,
                specialty_id=specialties[type_specialty].id if type_specialty else None,
            )
        )

    for name, keywords, rules, red_flag in SYMPTOMS:
        symptom = Symptom(
            name=name,
            keywords=keywords,
            is_red_flag=red_flag is not None,
            red_flag_message=red_flag,
        )
        session.add(symptom)
        await session.flush()
        for specialty_name, weight in rules:
            session.add(
                SymptomSpecialtyRule(
                    symptom_id=symptom.id,
                    specialty_id=specialties[specialty_name].id,
                    weight=weight,
                )
            )

    await session.commit()
    print(f"seeded {len(SPECIALTIES)} specialties, {len(HOSPITALS)} facilities, {index} doctors")


async def _ensure_user(
    session: AsyncSession, email: str, password: str, role: UserRole, profile: PatientProfile | None
) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        account_status=AccountStatus.ACTIVE,
    )
    if profile is not None:
        user.profile = profile
    session.add(user)
    await session.commit()
    print(f"created {role.lower()} account")
    return user


async def _seed_demo_history(session: AsyncSession, patient_id: int) -> None:
    """One completed past appointment so the review flow can be demonstrated."""
    if await session.scalar(
        select(func.count(Appointment.id)).where(Appointment.patient_id == patient_id)
    ):
        return
    doctor = await session.scalar(select(Doctor).order_by(Doctor.id).limit(1))
    appointment_type = await session.scalar(
        select(AppointmentType)
        .where(AppointmentType.specialty_id.is_(None))
        .order_by(AppointmentType.id)
        .limit(1)
    )
    if doctor is None or appointment_type is None:
        return
    day = (datetime.now(clinic_tz()) - timedelta(days=7)).date()
    start = datetime.combine(day, time(9, 0), tzinfo=clinic_tz()).astimezone(UTC)
    end = start + timedelta(minutes=appointment_type.duration_minutes)
    appointment = Appointment(
        booking_reference=generate_booking_reference(),
        patient_id=patient_id,
        doctor_id=doctor.id,
        appointment_type_id=appointment_type.id,
        start_time=start,
        end_time=end,
        end_with_buffer=end + timedelta(minutes=appointment_type.buffer_minutes),
        status=AppointmentStatus.COMPLETED,
        check_in_status=CheckInStatus.CHECKED_IN,
        reason_for_visit="Demo appointment",
        fee_amount=doctor.consultation_fee or Decimal("0"),
        currency=settings.currency,
        erp_booking_id="ERP-DEMO-0001",
    )
    session.add(appointment)
    await session.flush()
    for field, old, new in (
        ("status", None, AppointmentStatus.PENDING),
        ("status", AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED),
        ("check_in_status", CheckInStatus.NOT_CHECKED_IN, CheckInStatus.CHECKED_IN),
        ("status", AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED),
    ):
        session.add(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                field=field,
                from_value=old,
                to_value=new,
                source=StatusSource.PATIENT if old is None else StatusSource.ERP,
            )
        )
    await session.commit()
    print("seeded demo appointment history")


async def _seed_loadtest_users(session: AsyncSession, count: int) -> None:
    existing = set(
        (
            await session.scalars(
                select(User.email).where(User.email.like("loadtest%@example.com"))
            )
        ).all()
    )
    password_hash = hash_password(settings.loadtest_password)  # same password: hash once
    created = 0
    for i in range(1, count + 1):
        email = f"loadtest{i}@example.com"
        if email in existing:
            continue
        user = User(
            email=email,
            password_hash=password_hash,
            role=UserRole.PATIENT,
            account_status=AccountStatus.ACTIVE,
        )
        user.profile = PatientProfile(
            full_name=f"Load Test {i}", date_of_birth=date(1990, 1, 1), phone_number=f"+8490{i:07d}"
        )
        session.add(user)
        created += 1
    await session.commit()
    print(f"created {created} load-test users ({len(existing)} already existed)")


async def main(loadtest_users: int) -> None:
    async with SessionLocal() as session:
        await _seed_directory(session)
        await _ensure_user(
            session, settings.admin_email, settings.admin_password, UserRole.ADMIN, None
        )
        patient = await _ensure_user(
            session,
            settings.demo_patient_email,
            settings.demo_patient_password,
            UserRole.PATIENT,
            PatientProfile(
                full_name="Demo Patient",
                date_of_birth=date(1995, 5, 20),
                phone_number="+84901234567",
            ),
        )
        profile_id = await session.scalar(
            select(PatientProfile.id).where(PatientProfile.user_id == patient.id)
        )
        if profile_id:
            await _seed_demo_history(session, profile_id)
        if loadtest_users:
            await _seed_loadtest_users(session, loadtest_users)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--loadtest-users", type=int, default=0)
    asyncio.run(main(parser.parse_args().loadtest_users))
