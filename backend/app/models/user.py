from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import AccountStatus, UserRole, enum_column


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole), default=UserRole.PATIENT)
    account_status: Mapped[AccountStatus] = mapped_column(
        enum_column(AccountStatus), default=AccountStatus.ACTIVE
    )
    last_login_at: Mapped[datetime | None]

    profile: Mapped[PatientProfile | None] = relationship(back_populates="user", lazy="raise")


class PatientProfile(TimestampMixin, Base):
    """Patient details. `id` is the patient identifier appointments refer to (FR-PRO-04)."""

    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    # Optional at registration; patients can add them later on their profile.
    date_of_birth: Mapped[date | None]
    phone_number: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="profile", lazy="raise")
