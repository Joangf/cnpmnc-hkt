"""add avatar_url to hospitals

Revision ID: 0003_hospital_avatar_url
Revises: 0002_optional_dob_phone
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_hospital_avatar_url"
down_revision: str | None = "0002_optional_dob_phone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("hospitals", sa.Column("avatar_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("hospitals", "avatar_url")
