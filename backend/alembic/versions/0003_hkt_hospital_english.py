"""rename the demo hospital to English

Revision ID: 0003_hkt_hospital_english
Revises: 0002_department_publication
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_hkt_hospital_english"
down_revision: str | None = "0002_department_publication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE hospitals SET
            name = 'HKT Hospital',
            address = '12 HKT Street, District 1',
            city = 'Ho Chi Minh City',
            email = 'contact@hkt-hospital.example',
            description = 'HKT General Hospital provides medical services to the community.'
        WHERE name = 'Bệnh viện HKT'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE hospitals SET
            name = 'Bệnh viện HKT',
            address = '12 Đường HKT, Quận 1',
            city = 'Thành phố Hồ Chí Minh',
            email = 'contact@benhvien-hkt.example',
            description = 'Bệnh viện đa khoa HKT cung cấp dịch vụ khám chữa bệnh cho người dân.'
        WHERE name = 'HKT Hospital'
        """
    )
