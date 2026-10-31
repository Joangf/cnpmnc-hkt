"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _enum() -> sa.String:
    return sa.String(32)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", _enum(), nullable=False),
        sa.Column("account_status", _enum(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "patient_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("address", sa.String(255)),
        *_timestamps(),
    )

    op.create_table(
        "specialties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "hospitals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("facility_type", _enum(), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(255)),
        sa.Column("website", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_hospitals_name", "hospitals", ["name"])
    op.create_index("ix_hospitals_city", "hospitals", ["city"])

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id"), nullable=False),
        sa.Column("specialty_id", sa.Integer(), sa.ForeignKey("specialties.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_departments_hospital_id", "departments", ["hospital_id"])
    op.create_index("ix_departments_specialty_id", "departments", ["specialty_id"])

    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("title", sa.String(100)),
        sa.Column("qualifications", sa.Text()),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("introduction", sa.Text()),
        sa.Column("consultation_fee", sa.Numeric(12, 2)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("erp_doctor_id", sa.String(64), unique=True),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=False),
        sa.Column("rating_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_doctors_hospital_id", "doctors", ["hospital_id"])
    op.create_index("ix_doctors_department_id", "doctors", ["department_id"])
    op.create_index("ix_doctors_full_name", "doctors", ["full_name"])

    op.create_table(
        "appointment_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("fee_override", sa.Numeric(12, 2)),
        sa.Column("specialty_id", sa.Integer(), sa.ForeignKey("specialties.id")),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id")),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("duration_minutes > 0", name="ck_appointment_types_duration_positive"),
        sa.CheckConstraint("buffer_minutes >= 0", name="ck_appointment_types_buffer_non_negative"),
    )
    op.create_index("ix_appointment_types_specialty_id", "appointment_types", ["specialty_id"])
    op.create_index("ix_appointment_types_doctor_id", "appointment_types", ["doctor_id"])

    op.create_table(
        "doctor_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_appointments", sa.Integer()),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("source", _enum(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_time > start_time", name="ck_doctor_schedules_range"),
    )
    op.create_index(
        "ix_doctor_schedules_doctor_start", "doctor_schedules", ["doctor_id", "start_time"]
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_reference", sa.String(16), nullable=False, unique=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column(
            "appointment_type_id",
            sa.Integer(),
            sa.ForeignKey("appointment_types.id"),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_with_buffer", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("status_reason", sa.String(500)),
        sa.Column("check_in_status", _enum(), nullable=False),
        sa.Column("erp_booking_id", sa.String(64)),
        sa.Column("reason_for_visit", sa.String(1000)),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("end_time > start_time", name="ck_appointments_time_range"),
        sa.CheckConstraint("end_with_buffer >= end_time", name="ck_appointments_buffer_range"),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index("ix_appointments_erp_booking_id", "appointments", ["erp_booking_id"])
    op.create_index("ix_appointments_doctor_start", "appointments", ["doctor_id", "start_time"])
    # FR-BOOK-05 / NFR-06: the database rejects overlapping active bookings atomically.
    op.execute(
        """
        ALTER TABLE appointments ADD CONSTRAINT no_overlap
        EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_with_buffer) WITH &&)
        WHERE (status IN ('PENDING', 'CONFIRMED'))
        """
    )

    op.create_table(
        "appointment_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(32), nullable=False),
        sa.Column("from_value", sa.String(64)),
        sa.Column("to_value", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("source", _enum(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_appointment_status_history_appointment_id",
        "appointment_status_history",
        ["appointment_id"],
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_reference", sa.String(64), unique=True),
        sa.Column("checkout_url", sa.String(500)),
        sa.Column("failure_reason", sa.String(500)),
        sa.Column("last_event_id", sa.String(64)),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("refunded_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_payments_appointment_id", "payments", ["appointment_id"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("status", _enum(), nullable=False),
        sa.Column("moderated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("moderation_note", sa.String(500)),
        *_timestamps(),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
    )
    op.create_index("ix_reviews_patient_id", "reviews", ["patient_id"])
    op.create_index("ix_reviews_doctor_id", "reviews", ["doctor_id"])

    op.create_table(
        "symptoms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("keywords", sa.String(500)),
        sa.Column("is_red_flag", sa.Boolean(), nullable=False),
        sa.Column("red_flag_message", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "symptom_specialty_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "symptom_id",
            sa.Integer(),
            sa.ForeignKey("symptoms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "specialty_id",
            sa.Integer(),
            sa.ForeignKey("specialties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.UniqueConstraint("symptom_id", "specialty_id", name="uq_symptom_specialty"),
    )
    op.create_index(
        "ix_symptom_specialty_rules_symptom_id", "symptom_specialty_rules", ["symptom_id"]
    )
    op.create_index(
        "ix_symptom_specialty_rules_specialty_id", "symptom_specialty_rules", ["specialty_id"]
    )

    op.create_table(
        "recommendation_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "specialty_id",
            sa.Integer(),
            sa.ForeignKey("specialties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendation_logs_created_at", "recommendation_logs", ["created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("type", _enum(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("link", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("actor_id", sa.Integer()),
        sa.Column("actor_type", _enum(), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("request_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    for table in (
        "audit_logs",
        "notifications",
        "recommendation_logs",
        "symptom_specialty_rules",
        "symptoms",
        "reviews",
        "payments",
        "appointment_status_history",
        "appointments",
        "doctor_schedules",
        "appointment_types",
        "doctors",
        "departments",
        "hospitals",
        "specialties",
        "patient_profiles",
        "users",
    ):
        op.drop_table(table)
