from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import FacilityType, enum_column


class Specialty(TimestampMixin, Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)


class Hospital(TimestampMixin, Base):
    """A hospital or clinic in the platform directory (FR-DIS-01, FR-CLN-01)."""

    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    facility_type: Mapped[FacilityType] = mapped_column(
        enum_column(FacilityType), default=FacilityType.HOSPITAL
    )
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    departments: Mapped[list[Department]] = relationship(back_populates="hospital", lazy="raise")


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"), index=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    hospital: Mapped[Hospital] = relationship(back_populates="departments", lazy="raise")
    specialty: Mapped[Specialty] = relationship(lazy="raise")
    doctors: Mapped[list[Doctor]] = relationship(back_populates="department", lazy="raise")


class Doctor(TimestampMixin, Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    title: Mapped[str | None] = mapped_column(String(100))
    qualifications: Mapped[str | None] = mapped_column(Text)
    experience_years: Mapped[int] = mapped_column(default=0)
    introduction: Mapped[str | None] = mapped_column(Text)
    consultation_fee: Mapped[Decimal | None]
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    # Identifier of this doctor in the hospital ERP/HIS; null = not integrated.
    erp_doctor_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    # Denormalised from published reviews (see services/reviews.recompute_doctor_rating).
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0"))
    rating_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    hospital: Mapped[Hospital] = relationship(lazy="raise")
    department: Mapped[Department] = relationship(back_populates="doctors", lazy="raise")
