"""merge optional dob/phone and department publication heads

Revision ID: 0004_merge_heads
Revises: 0002_optional_dob_phone, 0003_hkt_hospital_english
Create Date: 2026-11-07
"""

from collections.abc import Sequence

revision: str = "0004_merge_heads"
down_revision: str | Sequence[str] | None = (
    "0002_optional_dob_phone",
    "0003_hkt_hospital_english",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
