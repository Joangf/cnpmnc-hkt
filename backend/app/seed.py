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
from typing import NotRequired, TypedDict

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
    DoctorSlot,
    Hospital,
    PatientProfile,
    Payment,
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
    PaymentStatus,
    SchedulingMode,
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


class HospitalSeed(TypedDict):
    name: str
    facility_type: FacilityType
    address: str
    city: str
    phone: str
    email: str
    description: str
    departments: list[str]
    website: NotRequired[str]
    avatar_url: NotRequired[str]


HOSPITALS: list[HospitalSeed] = [
    {
        "name": "HKT Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "address": "12 HKT Street, District 1",
        "city": "Ho Chi Minh City",
        "phone": "+842800000001",
        "email": "contact@hkt-hospital.example",
        "website": "https://hkt-hospital.example",
        "avatar_url": "https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?auto=format&fit=crop&w=800&q=80",
        "description": "HKT General Hospital provides medical services to the community.",
        "departments": [
            "General Internal Medicine",
            "Respiratory Medicine",
            "Cardiology",
            "Gastroenterology",
            "Dermatology",
            "Ophthalmology",
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
            "Neurology",
            "Pediatrics",
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
APPOINTMENT_TYPES: list[tuple[str, str, int, int, Decimal | None, str | None]] = [
    ("General Consultation", "Standard consultation fee.", 60, 0, Decimal("200000"), None),
]

SPECIALTY_HOURLY_SLOTS: dict[str, int] = {
    "General Internal Medicine": 4,
    "Pediatrics": 4,
    "Dermatology": 4,
    "Respiratory Medicine": 3,
    "Gastroenterology": 3,
    "Ophthalmology": 3,
    "Otorhinolaryngology (ENT)": 3,
    "Cardiology": 2,
    "Orthopedics": 2,
    "Rheumatology": 2,
    "Neurology": 2,
}

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
        updated = False
        for data in HOSPITALS:
            existing = await session.scalar(select(Hospital).where(Hospital.name == data["name"]))
            if existing and not existing.avatar_url:
                existing.avatar_url = data.get("avatar_url")
                existing.website = existing.website or data.get("website")
                existing.description = data.get("description") or existing.description
                updated = True
        if updated:
            await session.commit()
            print("backfilled hospital avatars and descriptions")
        else:
            print("directory already seeded")
        return

    specialties = {name: Specialty(name=name, description=desc) for name, desc in SPECIALTIES}
    session.add_all(specialties.values())
    await session.flush()

    index = 0
    dept_index = 0
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
                description=(
                    f"{specialty_name} Department at {hospital.name}: consultation, examination and "
                    "specialist treatment."
                ),
                location=f"Floor {(dept_index % 4) + 1}, Building {chr(65 + dept_index % 3)}",
            )
            dept_index += 1
            session.add(department)
            await session.flush()
            doctor_count = (
                3
                if specialty_name
                in (
                    "General Internal Medicine",
                    "Respiratory Medicine",
                    "Cardiology",
                    "Dermatology",
                    "Orthopedics",
                    "Pediatrics",
                )
                else 2
            )
            for _ in range(doctor_count):
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
                        erp_doctor_id=f"ERP-D{index:04d}",
                        scheduling_mode=SchedulingMode.MANUAL,
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
        end_with_buffer=end,
        status=AppointmentStatus.COMPLETED,
        check_in_status=CheckInStatus.CHECKED_IN,
        reason_for_visit="Demo appointment",
        fee_amount=appointment_type.fee_override or Decimal("200000"),
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


async def _seed_refund_test_appointments(session: AsyncSession, patient_id: int) -> None:
    """Seeds two CONFIRMED + PAID appointments for the demo patient to test refunds:
    1. HK-REFUND-USR1: For testing cancellation by the patient directly on the web.
    2. HK-REFUND-ERP2: For testing rejection / cancellation from the hospital ERP.
    """
    existing_refs = set(
        (
            await session.scalars(
                select(Appointment.booking_reference).where(
                    Appointment.booking_reference.in_(["HK-REFUND-USR1", "HK-REFUND-ERP2"])
                )
            )
        ).all()
    )

    doctors = (await session.scalars(select(Doctor).order_by(Doctor.id).limit(2))).all()
    if not doctors:
        return
    doctor1 = doctors[0]
    doctor2 = doctors[1] if len(doctors) > 1 else doctors[0]

    appointment_type = await session.scalar(
        select(AppointmentType)
        .where(AppointmentType.specialty_id.is_(None))
        .order_by(AppointmentType.id)
        .limit(1)
    )
    if appointment_type is None:
        appointment_type = await session.scalar(select(AppointmentType).limit(1))
    if appointment_type is None:
        return

    fee = appointment_type.fee_override or Decimal("200000")

    # 1. Test case: Patient cancellation
    if "HK-REFUND-USR1" not in existing_refs:
        day1 = (datetime.now(clinic_tz()) + timedelta(days=3)).date()
        start1 = datetime.combine(day1, time(9, 0), tzinfo=clinic_tz()).astimezone(UTC)
        end1 = start1 + timedelta(minutes=appointment_type.duration_minutes)

        apt1 = Appointment(
            booking_reference="HK-REFUND-USR1",
            patient_id=patient_id,
            doctor_id=doctor1.id,
            appointment_type_id=appointment_type.id,
            start_time=start1,
            end_time=end1,
            end_with_buffer=end1,
            status=AppointmentStatus.CONFIRMED,
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            reason_for_visit="Test refund: Patient cancellation flow",
            fee_amount=fee,
            currency=settings.currency,
            erp_booking_id="ERP-REFUND-0001",
        )
        session.add(apt1)
        await session.flush()

        for field, old, new, src in (
            ("status", None, AppointmentStatus.PENDING, StatusSource.PATIENT),
            ("status", AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, StatusSource.ERP),
        ):
            session.add(
                AppointmentStatusHistory(
                    appointment_id=apt1.id,
                    field=field,
                    from_value=old,
                    to_value=new,
                    source=src,
                )
            )

        pay1 = Payment(
            appointment_id=apt1.id,
            amount=fee,
            currency=settings.currency,
            status=PaymentStatus.PAID,
            payment_code="CBRFTEST01",
            paid_at=datetime.now(UTC) - timedelta(hours=2),
            provider_reference="SEPAY_RF_001",
        )
        session.add(pay1)
        print("seeded refund test appointment HK-REFUND-USR1 (Patient cancel test)")

    # 2. Test case: Hospital rejection
    if "HK-REFUND-ERP2" not in existing_refs:
        day2 = (datetime.now(clinic_tz()) + timedelta(days=4)).date()
        start2 = datetime.combine(day2, time(14, 0), tzinfo=clinic_tz()).astimezone(UTC)
        end2 = start2 + timedelta(minutes=appointment_type.duration_minutes)

        apt2 = Appointment(
            booking_reference="HK-REFUND-ERP2",
            patient_id=patient_id,
            doctor_id=doctor2.id,
            appointment_type_id=appointment_type.id,
            start_time=start2,
            end_time=end2,
            end_with_buffer=end2,
            status=AppointmentStatus.CONFIRMED,
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            reason_for_visit="Test refund: Hospital ERP rejection flow",
            fee_amount=fee,
            currency=settings.currency,
            erp_booking_id="ERP-REFUND-0002",
        )
        session.add(apt2)
        await session.flush()

        for field, old, new, src in (
            ("status", None, AppointmentStatus.PENDING, StatusSource.PATIENT),
            ("status", AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, StatusSource.ERP),
        ):
            session.add(
                AppointmentStatusHistory(
                    appointment_id=apt2.id,
                    field=field,
                    from_value=old,
                    to_value=new,
                    source=src,
                )
            )

        pay2 = Payment(
            appointment_id=apt2.id,
            amount=fee,
            currency=settings.currency,
            status=PaymentStatus.PAID,
            payment_code="CBRFTEST02",
            paid_at=datetime.now(UTC) - timedelta(hours=3),
            provider_reference="SEPAY_RF_002",
        )
        session.add(pay2)
        print("seeded refund test appointment HK-REFUND-ERP2 (Hospital rejection test)")

    await session.commit()


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


async def _seed_manual_doctor_slots(session: AsyncSession) -> None:
    """Seeds 1-hour shared-capacity DoctorSlots for initial cutover to the hospital ERP."""
    existing = await session.scalar(select(func.count(DoctorSlot.id)))
    if existing and existing > 0:
        return

    doctor_rows = (
        await session.execute(
            select(Doctor, Specialty.name)
            .join(Department, Doctor.department_id == Department.id)
            .join(Specialty, Department.specialty_id == Specialty.id)
            .where(Doctor.is_active.is_(True))
        )
    ).all()
    if not doctor_rows:
        return

    slots_to_add: list[DoctorSlot] = []
    today = (datetime.now(clinic_tz())).date()
    morning = [
        (time(8, 0), time(9, 0)),
        (time(9, 0), time(10, 0)),
        (time(10, 0), time(11, 0)),
        (time(11, 0), time(12, 0)),
    ]
    afternoon = [
        (time(13, 0), time(14, 0)),
        (time(14, 0), time(15, 0)),
        (time(15, 0), time(16, 0)),
        (time(16, 0), time(17, 0)),
    ]
    slot_times = morning + afternoon

    for day_offset in range(0, 15):
        day = today + timedelta(days=day_offset)
        if day.weekday() == 6:  # Sunday closed
            continue
        for doctor, spec_name in doctor_rows:
            day_windows = slot_times
            if (
                day.weekday() == 5
                and doctor.erp_doctor_id
                and doctor.erp_doctor_id[-1:].isdigit()
                and int(doctor.erp_doctor_id[-1]) % 2
            ):
                day_windows = morning
            cap = SPECIALTY_HOURLY_SLOTS.get(spec_name, 3)
            for start_t, end_t in day_windows:
                start_dt = datetime.combine(day, start_t, tzinfo=clinic_tz()).astimezone(UTC)
                end_dt = datetime.combine(day, end_t, tzinfo=clinic_tz()).astimezone(UTC)
                slots_to_add.append(
                    DoctorSlot(
                        doctor_id=doctor.id,
                        start_time=start_dt,
                        end_time=end_dt,
                        end_with_buffer=end_dt,
                        buffer_minutes=0,
                        capacity=cap,
                        is_open=True,
                        version=1,
                    )
                )

    session.add_all(slots_to_add)
    await session.commit()
    print(f"seeded {len(slots_to_add)} doctor slots across {len(doctor_rows)} doctors")


async def main(loadtest_users: int) -> None:
    async with SessionLocal() as session:
        from app.models import ErpSyncState

        state = await session.get(ErpSyncState, 1)
        if not state or not state.ready:
            await _seed_directory(session)
            await _seed_manual_doctor_slots(session)
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
            await _seed_refund_test_appointments(session, profile_id)
        if loadtest_users:
            await _seed_loadtest_users(session, loadtest_users)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--loadtest-users", type=int, default=0)
    asyncio.run(main(parser.parse_args().loadtest_users))
