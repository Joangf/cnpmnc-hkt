"""merge translate seed text and manual doctor slots heads

Revision ID: 0008_merge_heads
Revises: 0008_translate_seed_text
Create Date: 2026-11-07
"""

from collections.abc import Sequence

revision: str = "0008_merge_heads"
# Linearised: 0006_translate_seed_text was renamed to 0008_translate_seed_text (420a546) and now
# follows 0007_manual_doctor_slots, so this former merge point is a no-op step after it. Kept so
# databases already stamped "0008_merge_heads" still resolve.
down_revision: str | Sequence[str] | None = "0008_translate_seed_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
