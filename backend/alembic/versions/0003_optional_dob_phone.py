"""make date_of_birth and phone_number optional

Revision ID: 0003_optional_dob_phone
Revises: 0002_drop_doctor_fee
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_optional_dob_phone"
down_revision: str | None = "0002_drop_doctor_fee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("patient_profiles", "date_of_birth", existing_type=sa.Date(), nullable=True)
    op.alter_column("patient_profiles", "phone_number", existing_type=sa.String(20), nullable=True)


def downgrade() -> None:
    # Rows created without these values get placeholders so the NOT NULL constraint can return.
    op.execute(
        "UPDATE patient_profiles SET date_of_birth = DATE '1900-01-01' WHERE date_of_birth IS NULL"
    )
    op.execute("UPDATE patient_profiles SET phone_number = '' WHERE phone_number IS NULL")
    op.alter_column("patient_profiles", "date_of_birth", existing_type=sa.Date(), nullable=False)
    op.alter_column("patient_profiles", "phone_number", existing_type=sa.String(20), nullable=False)

