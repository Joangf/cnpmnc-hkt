"""Add is_edited to reviews table.

Revision ID: 0011_review_is_edited
Revises: 0010_sepay_payments
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_review_is_edited"
down_revision = "0010_sepay_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS is_edited BOOLEAN DEFAULT FALSE NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("reviews", "is_edited")

