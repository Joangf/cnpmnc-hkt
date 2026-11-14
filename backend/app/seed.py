"""Idempotent demo and load-test data.

    python -m app.seed                       # directory, rules, admin + demo patient
    python -m app.seed --loadtest-users 200  # also loadtest1..N@example.com

All hospitals, doctors and contact details are fictional. Symptom rules and warning
signs are placeholders and MUST be reviewed by a qualified clinician (FRD 4.7.1, OQ-06).
"""

import argparse
import asyncio
import random
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import NotRequired, TypedDict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
    Review,
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
    ReviewStatus,
    SchedulingMode,
    StatusSource,
    UserRole,
)
from app.repositories import reviews as review_repo
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

# Each doctor's main focus, by specialty (fictional; bilingual so Vietnamese searches match).
# The n-th doctor of a department gets the n-th entry.
DOCTOR_FOCUS: dict[str, list[str]] = {
    "General Internal Medicine": [
        "fever, fatigue and general check-ups (sốt, mệt mỏi, khám tổng quát)",
        "high blood pressure and diabetes follow-up (huyết áp cao, tiểu đường)",
        "unexplained weight loss and long-lasting tiredness (sụt cân, mệt mỏi kéo dài)",
    ],
    "Respiratory Medicine": [
        "asthma and chronic cough (hen suyễn, ho kéo dài)",
        "shortness of breath and COPD (khó thở, phổi tắc nghẽn mạn tính)",
        "lung infections and pneumonia follow-up (viêm phổi, nhiễm trùng hô hấp)",
    ],
    "Cardiology": [
        "chest pain and coronary artery disease (đau ngực, bệnh mạch vành)",
        "palpitations and heart rhythm disorders (hồi hộp, rối loạn nhịp tim)",
        "heart failure and high blood pressure (suy tim, tăng huyết áp)",
    ],
    "Gastroenterology": [
        "acid reflux, heartburn and stomach pain (trào ngược, ợ nóng, đau dạ dày)",
        "diarrhoea, bloating and irritable bowel (tiêu chảy, đầy bụng, đại tràng kích thích)",
        "endoscopy and liver disease (nội soi tiêu hoá, bệnh gan)",
    ],
    "Dermatology": [
        "acne and skin care for teenagers (mụn trứng cá, chăm sóc da)",
        "rashes, hives and eczema (phát ban, mề đay, chàm, ngứa da)",
        "hair loss and nail problems (rụng tóc, bệnh móng)",
    ],
    "Ophthalmology": [
        "blurred vision and glasses prescriptions (mờ mắt, cận thị, đo kính)",
        "red, painful or irritated eyes (đau mắt đỏ, viêm kết mạc)",
        "cataract and glaucoma (đục thuỷ tinh thể, tăng nhãn áp)",
    ],
    "Orthopedics": [
        "knee and joint pain, sports injuries (đau khớp gối, chấn thương thể thao)",
        "back and neck pain, spine problems (đau lưng, đau cổ, cột sống)",
        "fractures and bone health (gãy xương, loãng xương)",
    ],
    "Rheumatology": [
        "rheumatoid arthritis and morning joint stiffness (viêm khớp dạng thấp, cứng khớp)",
        "gout and swollen joints (bệnh gút, sưng khớp)",
        "lupus and other autoimmune conditions (lupus, bệnh tự miễn)",
    ],
    "Otorhinolaryngology (ENT)": [
        "sore throat and tonsillitis (đau họng, viêm amidan)",
        "ear pain, ear infections and hearing (đau tai, viêm tai, nghe kém)",
        "sinusitis and blocked nose (viêm xoang, nghẹt mũi)",
    ],
    "Neurology": [
        "headache and migraine (đau đầu, đau nửa đầu)",
        "stroke prevention and numbness (phòng đột quỵ, tê yếu tay chân)",
        "dizziness, sleep problems and memory (chóng mặt, mất ngủ, trí nhớ)",
    ],
    "Pediatrics": [
        "fever and common infections in children (trẻ sốt, nhiễm trùng thường gặp)",
        "child growth, nutrition and vaccination (dinh dưỡng, tiêm chủng cho trẻ)",
        "coughs, colds and asthma in children (trẻ ho, cảm lạnh, hen ở trẻ)",
    ],
}
_OLD_INTRO_END = "focused on clear explanations and shared decisions."


def doctor_introduction(specialty: str, hospital: str, position: int) -> str:
    focus = DOCTOR_FOCUS.get(specialty) or ["general consultations"]
    return (
        f"Fictional {specialty.lower()} specialist at {hospital}. "
        f"Main focus: {focus[position % len(focus)]}."
    )


# Fictional demo reviews: (specialty of the doctor, [(rating, comment)]) - for the AI summary.
DEMO_REVIEWS: list[tuple[str, list[tuple[int, str]]]] = [
    (
        "Cardiology",
        [
            (5, "The doctor explained my ECG results very carefully and clearly."),
            (5, "Very dedicated: asked about my history in detail and gave careful advice."),
            (3, "A good doctor, but I had to wait almost an hour to be seen."),
            (4, "Thorough examination, but the waiting room was rather crowded."),
            (2, "The wait was far too long and the consultation felt rushed because of the number of patients."),
        ],
    ),
    (
        "Dermatology",
        [
            (5, "Very effective acne treatment; my skin improved a lot after a month."),
            (4, "Gentle doctor who gave detailed skin-care advice."),
            (5, "Prescribed only what was needed without overusing strong medication."),
            (3, "Effective, but the cost of the medication was a bit high."),
        ],
    ),
    (
        "Respiratory Medicine",
        [
            (5, "Very patient, explained my asthma inhaler step by step."),
            (4, "Good doctor, the follow-up plan for my cough was clear."),
            (2, "The appointment started 40 minutes late."),
            (5, "Kind and thorough, answered all my questions."),
        ],
    ),
]

# (name, description, duration, buffer, fee_override, specialty name or None)
APPOINTMENT_TYPES: list[tuple[str, str, int, int, Decimal | None, str | None]] = [
    ("General Consultation", "Standard consultation fee.", 60, 0, Decimal("2000"), None),
]

SEED_SLOT_DAYS = 45  # how many days ahead of today the seed keeps slots for

MIN_SLOT_CAPACITY, MAX_SLOT_CAPACITY = 1, 3  # patients per hourly slot (random per slot)

# (name, keywords, [(specialty, weight)], red_flag_message)  -- PENDING CLINICAL REVIEW
SYMPTOMS: list[tuple[str, str, list[tuple[str, float]], str | None]] = [
    (
        "Persistent cough",
        "cough,coughing,ho,ho khan,ho có đờm,ho kéo dài,ho dai dẳng",
        [("Respiratory Medicine", 1.0), ("General Internal Medicine", 0.3)],
        None,
    ),
    (
        "Shortness of breath",
        "breathless,short of breath,difficulty breathing,"
        "khó thở,hụt hơi,thở gấp,thở dốc,hơi thở ngắn",
        [("Respiratory Medicine", 1.0), ("Cardiology", 0.6)],
        "Severe or sudden difficulty breathing needs urgent medical attention.",
    ),
    (
        "Chest pain",
        "chest tightness,chest pressure,đau ngực,tức ngực,nặng ngực,đau thắt ngực",
        [("Cardiology", 1.0), ("General Internal Medicine", 0.3)],
        "Chest pain can be a sign of a serious heart problem.",
    ),
    (
        "Palpitations",
        "racing heart,irregular heartbeat,hồi hộp,tim đập nhanh,đánh trống ngực,tim đập không đều",
        [("Cardiology", 1.0)],
        None,
    ),
    (
        "Skin rash",
        "rash,hives,phát ban,nổi mẩn,nổi mề đay,mẩn đỏ,nổi mụn nước",
        [("Dermatology", 1.0)],
        None,
    ),
    ("Itching", "itchy,itch,ngứa,ngứa ngáy,ngứa da", [("Dermatology", 0.8)], None),
    ("Acne", "pimples,breakouts,mụn,mụn trứng cá,nổi mụn", [("Dermatology", 1.0)], None),
    (
        "Joint pain",
        "knee pain,arthritis,painful joints,đau khớp,đau khớp gối,đau đầu gối,viêm khớp,nhức khớp",
        [("Orthopedics", 0.8), ("Rheumatology", 0.8)],
        None,
    ),
    (
        "Morning joint stiffness",
        "stiff joints,cứng khớp buổi sáng,cứng khớp",
        [("Rheumatology", 1.0)],
        None,
    ),
    (
        "Back pain",
        "lower back pain,backache,đau lưng,đau thắt lưng,mỏi lưng",
        [("Orthopedics", 1.0)],
        None,
    ),
    (
        "Eye discomfort",
        "eye pain,red eye,eye irritation,đau mắt,đỏ mắt,cộm mắt,ngứa mắt,khó chịu ở mắt",
        [("Ophthalmology", 1.0)],
        None,
    ),
    (
        "Blurred vision",
        "blurry vision,blurred,mờ mắt,mắt mờ,nhìn mờ,nhìn không rõ",
        [("Ophthalmology", 1.0)],
        None,
    ),
    (
        "Sudden loss of vision",
        "vision loss,cannot see,mất thị lực đột ngột,đột nhiên không nhìn thấy,mù đột ngột",
        [("Ophthalmology", 1.0), ("Neurology", 0.6)],
        "Sudden loss of vision is a medical emergency.",
    ),
    (
        "Stomach pain",
        "abdominal pain,stomach ache,stomachache,đau bụng,đau dạ dày,đau bao tử,đau thượng vị",
        [("Gastroenterology", 1.0), ("General Internal Medicine", 0.3)],
        None,
    ),
    (
        "Heartburn",
        "acid reflux,indigestion,ợ nóng,ợ chua,trào ngược dạ dày,khó tiêu,đầy bụng,chướng bụng",
        [("Gastroenterology", 1.0)],
        None,
    ),
    (
        "Diarrhea",
        "loose stools,tiêu chảy,đi ngoài,phân lỏng,đi cầu nhiều lần",
        [("Gastroenterology", 1.0)],
        None,
    ),
    (
        "Sore throat",
        "throat pain,đau họng,viêm họng,rát họng",
        [("Otorhinolaryngology (ENT)", 1.0), ("General Internal Medicine", 0.3)],
        None,
    ),
    ("Ear pain", "earache,đau tai,nhức tai,ù tai", [("Otorhinolaryngology (ENT)", 1.0)], None),
    (
        "Headache",
        "migraine,đau đầu,nhức đầu,đau nửa đầu,choáng đầu",
        [("Neurology", 0.8), ("General Internal Medicine", 0.5)],
        None,
    ),
    (
        "Sudden weakness or numbness on one side",
        "numbness,slurred speech,facial drooping,"
        "yếu nửa người,tê nửa người,méo miệng,nói ngọng đột ngột,đột quỵ",
        [("Neurology", 1.0)],
        "Sudden one-sided weakness, numbness or difficulty speaking can be signs of a stroke.",
    ),
    (
        "Fever",
        "high temperature,sốt,sốt cao,nóng sốt,ớn lạnh",
        [("General Internal Medicine", 1.0), ("Pediatrics", 0.3)],
        None,
    ),
    (
        "Fever in a child",
        "child fever,baby fever,trẻ bị sốt,bé bị sốt,con bị sốt,sốt ở trẻ em",
        [("Pediatrics", 1.0)],
        None,
    ),
    (
        "Fatigue",
        "tired,tiredness,exhaustion,mệt mỏi,uể oải,kiệt sức,mệt",
        [("General Internal Medicine", 1.0)],
        None,
    ),
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
        await _backfill_doctor_focus(session)
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
            for position in range(doctor_count):
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
                        introduction=doctor_introduction(specialty_name, hospital.name, position),
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


async def _backfill_doctor_focus(session: AsyncSession) -> None:
    """Older seeds gave every doctor the same introduction; give each a main focus."""
    doctors = (
        (
            await session.scalars(
                select(Doctor)
                .where(Doctor.introduction.like(f"%{_OLD_INTRO_END}"))
                .options(
                    joinedload(Doctor.hospital),
                    joinedload(Doctor.department).joinedload(Department.specialty),
                )
                .order_by(Doctor.department_id, Doctor.id)
            )
        )
        .unique()
        .all()
    )
    positions: dict[int, int] = {}
    for doctor in doctors:
        position = positions.get(doctor.department_id, 0)
        positions[doctor.department_id] = position + 1
        doctor.introduction = doctor_introduction(
            doctor.department.specialty.name, doctor.hospital.name, position
        )
    if doctors:
        await session.commit()
        print(f"backfilled the main focus of {len(doctors)} doctors")


async def _seed_demo_reviews(session: AsyncSession, patient_id: int) -> None:
    """Completed past visits with fictional reviews, so the AI review summary has material."""
    if await session.scalar(
        select(func.count(Appointment.id)).where(Appointment.erp_booking_id.like("ERP-DEMO-R%"))
    ):
        return
    appointment_type = await session.scalar(
        select(AppointmentType)
        .where(AppointmentType.specialty_id.is_(None))
        .order_by(AppointmentType.id)
    )
    if appointment_type is None:
        return
    count = 0
    for specialty_name, reviews in DEMO_REVIEWS:
        doctor = await session.scalar(
            select(Doctor)
            .join(Department, Department.id == Doctor.department_id)
            .join(Specialty, Specialty.id == Department.specialty_id)
            .where(Specialty.name == specialty_name, Doctor.is_active.is_(True))
            .order_by(Doctor.id)
            .limit(1)
        )
        if doctor is None:
            continue
        for days_ago, (rating, comment) in enumerate(reviews, start=10):
            count += 1
            day = (datetime.now(clinic_tz()) - timedelta(days=days_ago)).date()
            start = datetime.combine(day, time(10, 0), tzinfo=clinic_tz()).astimezone(UTC)
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
                erp_booking_id=f"ERP-DEMO-R{count:03d}",
            )
            session.add(appointment)
            await session.flush()
            session.add(
                Review(
                    appointment_id=appointment.id,
                    patient_id=patient_id,
                    doctor_id=doctor.id,
                    rating=rating,
                    comment=comment,
                    status=ReviewStatus.PUBLISHED,
                )
            )
        await session.flush()
        await review_repo.recompute_doctor_rating(session, doctor.id)
    await session.commit()
    print(f"seeded {count} demo reviews")


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
        fee_amount=appointment_type.fee_override or Decimal("2000"),
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

    fee = appointment_type.fee_override or Decimal("2000")

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


_MORNING = [(time(h, 0), time(h + 1, 0)) for h in (8, 9, 10, 11)]
_AFTERNOON = [(time(h, 0), time(h + 1, 0)) for h in (13, 14, 15, 16)]


def _candidate_slots(
    erp_doctor_id: str | None,
) -> list[tuple[datetime, datetime, int]]:
    """Hourly (start, end, capacity) windows for the next SEED_SLOT_DAYS days, in UTC."""
    today = datetime.now(clinic_tz()).date()
    result: list[tuple[datetime, datetime, int]] = []
    for day_offset in range(SEED_SLOT_DAYS):
        day = today + timedelta(days=day_offset)
        if day.weekday() == 6:  # Sunday closed
            continue
        windows = _MORNING + _AFTERNOON
        # Variety: doctors with an odd number don't work Saturday afternoons.
        if (
            day.weekday() == 5
            and erp_doctor_id
            and erp_doctor_id[-1:].isdigit()
            and int(erp_doctor_id[-1]) % 2
        ):
            windows = _MORNING
        for start_t, end_t in windows:
            result.append(
                (
                    datetime.combine(day, start_t, tzinfo=clinic_tz()).astimezone(UTC),
                    datetime.combine(day, end_t, tzinfo=clinic_tz()).astimezone(UTC),
                    random.randint(MIN_SLOT_CAPACITY, MAX_SLOT_CAPACITY),
                )
            )
    return result


async def _seed_erp_slots() -> int:
    """After cutover the hospital ERP owns schedules: add missing slots through its API
    (never directly in the local DB, or slot versions/capacity drift from the ERP)."""
    import httpx

    now = datetime.now(UTC)
    added = 0
    async with httpx.AsyncClient(base_url=settings.erp_base_url, timeout=30) as client:
        response = await client.get("/catalog")
        response.raise_for_status()
        catalog = response.json()
        taken: dict[str, list[tuple[datetime, datetime]]] = {}
        for slot in catalog["slots"]:
            taken.setdefault(slot["doctor_id"], []).append(
                (datetime.fromisoformat(slot["start_time"]), datetime.fromisoformat(slot["end_time"]))
            )
        for doctor in catalog["doctors"]:
            if not doctor["data"].get("is_active", True):
                continue
            doctor_id = doctor["id"]
            for start, end, capacity in _candidate_slots(doctor_id):
                if start <= now or any(start < e and s0 < end for s0, e in taken.get(doctor_id, ())):
                    continue
                slot_id = f"seed-{doctor_id}-{start:%Y%m%dT%H%M}"[:64]
                put = await client.put(
                    f"/slots/{slot_id}",
                    json={
                        "id": slot_id,
                        "doctor_id": doctor_id,
                        "start_time": start.isoformat(),
                        "end_time": end.isoformat(),
                        "capacity": capacity,
                        "is_open": True,
                        "version": 1,
                    },
                )
                put.raise_for_status()
                taken.setdefault(doctor_id, []).append((start, end))
                added += 1
    print(f"seeded {added} ERP slots via the ERP API")
    return added


async def _seed_manual_doctor_slots(session: AsyncSession) -> None:
    """Before ERP cutover: seed hourly slots locally (cutover pushes them to the ERP)."""
    doctor_rows = (
        await session.scalars(select(Doctor).where(Doctor.is_active.is_(True)))
    ).all()
    if not doctor_rows:
        return
    # Idempotent top-up: skip candidates overlapping an existing slot.
    existing: dict[int, list[tuple[datetime, datetime]]] = {}
    for doctor_id, start, end in (
        await session.execute(
            select(DoctorSlot.doctor_id, DoctorSlot.start_time, DoctorSlot.end_with_buffer).where(
                DoctorSlot.end_with_buffer >= datetime.now(UTC) - timedelta(days=1)
            )
        )
    ).all():
        existing.setdefault(doctor_id, []).append((start, end))
    slots_to_add = [
        DoctorSlot(
            doctor_id=doctor.id,
            start_time=start,
            end_time=end,
            end_with_buffer=end,
            buffer_minutes=0,
            capacity=capacity,
            is_open=True,
            version=1,
        )
        for doctor in doctor_rows
        for start, end, capacity in _candidate_slots(doctor.erp_doctor_id)
        if not any(start < e and s0 < end for s0, e in existing.get(doctor.id, ()))
    ]
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
        elif await _seed_erp_slots():
            from app.integrations import build_erp_adapter
            from app.services import erp_sync

            erp = build_erp_adapter()
            try:
                await erp_sync.sync_schedules(session, erp)  # pull the new slots back
            finally:
                await erp.aclose()
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
            await _seed_demo_reviews(session, profile_id)
        if loadtest_users:
            await _seed_loadtest_users(session, loadtest_users)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--loadtest-users", type=int, default=0)
    asyncio.run(main(parser.parse_args().loadtest_users))
