"""translate seeded department text to English

Revision ID: 0008_translate_seed_text
Revises: 0007_manual_doctor_slots
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_translate_seed_text"
down_revision: str | None = "0007_manual_doctor_slots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE departments SET
            location = replace(replace(location, 'Tầng ', 'Floor '), 'Tòa ', 'Building ')
        WHERE location LIKE 'Tầng %' OR location LIKE '%Tòa %'
        """
    )
    op.execute(
        """
        UPDATE departments d SET
            description = d.name || ' at ' || h.name ||
                ': consultation, examination and specialist treatment.'
        FROM hospitals h
        WHERE d.hospital_id = h.id AND d.description LIKE 'Khoa %'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE departments SET
            location = replace(replace(location, 'Floor ', 'Tầng '), 'Building ', 'Tòa ')
        WHERE location LIKE 'Floor %' OR location LIKE '%Building %'
        """
    )
    op.execute(
        """
        UPDATE departments d SET
            description = 'Khoa ' || replace(d.name, ' Department', '') || ' tại ' || h.name ||
                ': tư vấn, thăm khám và điều trị chuyên khoa.'
        FROM hospitals h
        WHERE d.hospital_id = h.id AND d.description LIKE '%Department at %'
        """
    )
