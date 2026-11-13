"""ERP identities and a safe, explicit cutover gate. No reservations are rewritten."""

import sqlalchemy as sa

from alembic import op

revision = "0011_erp_owned_slots"
down_revision = "0010_sepay_payments"
branch_labels = None
depends_on = None
TABLES = ("specialties", "hospitals", "departments", "doctors", "appointment_types", "doctor_slots")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("erp_id", sa.String(64), nullable=True))
        op.create_unique_constraint(f"uq_{table}_erp_id", table, ["erp_id"])
        op.add_column(table, sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "doctor_slots",
        sa.Column("erp_booked_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "erp_sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ready", sa.Boolean(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
    )
    op.execute("INSERT INTO erp_sync_state (id, ready) VALUES (1, false)")


def downgrade():
    op.drop_table("erp_sync_state")
    op.drop_column("doctor_slots", "erp_booked_count")
    for table in reversed(TABLES):
        op.drop_constraint(f"uq_{table}_erp_id", table, type_="unique")
        op.drop_column(table, "synced_at")
        op.drop_column(table, "erp_id")
