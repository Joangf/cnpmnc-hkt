"""SQLAlchemy entities (FRD section 9). Importing this package registers every mapper."""

from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.directory import Department, Doctor, Hospital, Specialty
from app.models.erp import ErpSyncState
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.review import Review, ReviewReport
from app.models.scheduling import AppointmentType, DoctorSchedule, DoctorSlot
from app.models.search import DoctorReviewSummary, SearchDocument
from app.models.symptom import RecommendationLog, Symptom, SymptomSpecialtyRule
from app.models.user import PatientProfile, User

__all__ = [
    "ErpSyncState",
    "Appointment",
    "AppointmentStatusHistory",
    "AppointmentType",
    "AuditLog",
    "Base",
    "Department",
    "Doctor",
    "DoctorReviewSummary",
    "DoctorSchedule",
    "DoctorSlot",
    "Hospital",
    "Notification",
    "PatientProfile",
    "Payment",
    "RecommendationLog",
    "Review",
    "ReviewReport",
    "SearchDocument",
    "Specialty",
    "Symptom",
    "SymptomSpecialtyRule",
    "User",
]
