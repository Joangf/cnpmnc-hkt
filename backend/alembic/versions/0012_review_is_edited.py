"""Add is_edited to reviews table.

Revision ID: 0012_review_is_edited
Revises: 0011_erp_owned_slots
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_review_is_edited"
down_revision = "0011_erp_owned_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS is_edited BOOLEAN DEFAULT FALSE NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("reviews", "is_edited")
