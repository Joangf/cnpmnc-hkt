"""drop doctor consultation fee

Revision ID: 0006_drop_doctor_fee
Revises: 0005_merge_scheduling_heads
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_drop_doctor_fee"
down_revision: str | None = "0005_merge_scheduling_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE doctors DROP COLUMN IF EXISTS consultation_fee")


def downgrade() -> None:
    op.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS consultation_fee NUMERIC(12, 2)")
