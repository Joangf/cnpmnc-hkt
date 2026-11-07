"""Admin-managed shared doctor slots; preserve ERP reservations at position one."""

import sqlalchemy as sa

from alembic import op

revision = "0007_manual_doctor_slots"
down_revision = "0006_drop_doctor_fee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("doctors", sa.Column(
        "scheduling_mode", sa.String(32), nullable=False, server_default="ERP"
    ))
    op.create_check_constraint(
        "ck_doctors_scheduling_mode", "doctors", "scheduling_mode IN ('ERP', 'MANUAL')"
    )
    op.create_table(
        "doctor_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_with_buffer", sa.DateTime(timezone=True), nullable=False),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("id", "doctor_id", name="uq_doctor_slots_id_doctor"),
        sa.CheckConstraint("end_time > start_time", name="ck_doctor_slots_time_range"),
        sa.CheckConstraint("capacity > 0", name="ck_doctor_slots_capacity"),
        sa.CheckConstraint("buffer_minutes BETWEEN 0 AND 120", name="ck_doctor_slots_buffer"),
        sa.CheckConstraint("version > 0", name="ck_doctor_slots_version"),
        sa.CheckConstraint(
            "end_with_buffer = end_time + buffer_minutes * INTERVAL '1 minute'",
            name="ck_doctor_slots_reserved_end",
        ),
    )
    op.create_index("ix_doctor_slots_doctor_start", "doctor_slots", ["doctor_id", "start_time"])
    # Closed rows still reserve their interval, so reopening cannot create conflicting slots.
    op.execute("""
        ALTER TABLE doctor_slots ADD CONSTRAINT no_slot_overlap
        EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_with_buffer, '[)') WITH &&)
    """)
    op.add_column("appointments", sa.Column("slot_id", sa.Integer(), nullable=True))
    op.add_column("appointments", sa.Column(
        "reservation_position", sa.Integer(), nullable=False, server_default="1"
    ))
    op.create_foreign_key(
        "fk_appointments_slot_doctor", "appointments", "doctor_slots",
        ["slot_id", "doctor_id"], ["id", "doctor_id"],
    )
    op.create_index("ix_appointments_slot_id", "appointments", ["slot_id"])
    op.create_index(
        "uq_appointments_patient_active_slot", "appointments", ["patient_id", "slot_id"],
        unique=True,
        postgresql_where=sa.text("slot_id IS NOT NULL AND status IN ('PENDING', 'CONFIRMED')"),
    )
    op.create_check_constraint(
        "ck_appointments_position", "appointments", "reservation_position > 0"
    )
    op.create_check_constraint(
        "ck_appointments_erp_position", "appointments",
        "slot_id IS NOT NULL OR reservation_position = 1",
    )
    op.drop_constraint("no_overlap", "appointments")
    op.execute("""
        ALTER TABLE appointments ADD CONSTRAINT no_overlap EXCLUDE USING gist (
            doctor_id WITH =, reservation_position WITH =,
            tstzrange(start_time, end_with_buffer, '[)') WITH &&
        ) WHERE (status IN ('PENDING', 'CONFIRMED'))
    """)


def downgrade() -> None:
    # Restoring the legacy constraint is impossible while shared active bookings overlap.
    # Let PostgreSQL reject that downgrade atomically instead of deleting appointments.
    op.drop_constraint("no_overlap", "appointments")
    op.execute("""
        ALTER TABLE appointments ADD CONSTRAINT no_overlap EXCLUDE USING gist (
            doctor_id WITH =, tstzrange(start_time, end_with_buffer) WITH &&
        ) WHERE (status IN ('PENDING', 'CONFIRMED'))
    """)
    op.drop_constraint("ck_appointments_erp_position", "appointments", type_="check")
    op.drop_constraint("ck_appointments_position", "appointments", type_="check")
    op.drop_index("uq_appointments_patient_active_slot", table_name="appointments")
    op.drop_index("ix_appointments_slot_id", table_name="appointments")
    op.drop_constraint("fk_appointments_slot_doctor", "appointments", type_="foreignkey")
    op.drop_column("appointments", "reservation_position")
    op.drop_column("appointments", "slot_id")
    op.drop_table("doctor_slots")
    op.drop_constraint("ck_doctors_scheduling_mode", "doctors", type_="check")
    op.drop_column("doctors", "scheduling_mode")
