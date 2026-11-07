"""drop doctor consultation fee

Revision ID: 0002_drop_doctor_fee
Revises: 0001_initial
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_drop_doctor_fee"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("doctors", "consultation_fee")


def downgrade() -> None:
    op.add_column("doctors", sa.Column("consultation_fee", sa.Numeric(12, 2), nullable=True))

