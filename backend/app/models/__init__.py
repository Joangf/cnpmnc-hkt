"""SQLAlchemy entities (FRD section 9). Importing this package registers every mapper."""

from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.directory import Department, Doctor, Hospital, Specialty
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.review import Review
from app.models.scheduling import AppointmentType, DoctorSchedule
from app.models.symptom import RecommendationLog, Symptom, SymptomSpecialtyRule
from app.models.user import PatientProfile, User

__all__ = [
    "Appointment",
    "AppointmentStatusHistory",
    "AppointmentType",
    "AuditLog",
    "Base",
    "Department",
    "Doctor",
    "DoctorSchedule",
    "Hospital",
    "Notification",
    "PatientProfile",
    "Payment",
    "RecommendationLog",
    "Review",
    "Specialty",
    "Symptom",
    "SymptomSpecialtyRule",
    "User",
]
