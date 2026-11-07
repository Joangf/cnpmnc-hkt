"""SCRUM-21: finite per-doctor work-window capacity.

Revision ID: 0004_doctor_scheduling_capacity
Revises: 0003_hospital_avatar_url
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_doctor_scheduling_capacity"
down_revision = "0003_hospital_avatar_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("max_appointments_per_window", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint(
        "ck_doctors_capacity_positive", "doctors", "max_appointments_per_window > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_doctors_capacity_positive", "doctors", type_="check")
    op.drop_column("doctors", "max_appointments_per_window")
