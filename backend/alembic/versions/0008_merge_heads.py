"""merge translate seed text and manual doctor slots heads

Revision ID: 0008_merge_heads
Revises: 0006_translate_seed_text, 0007_manual_doctor_slots
Create Date: 2026-11-07
"""

from collections.abc import Sequence

revision: str = "0008_merge_heads"
down_revision: str | Sequence[str] | None = (
    "0006_translate_seed_text",
    "0007_manual_doctor_slots",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
