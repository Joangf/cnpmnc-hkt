"""department publication status and public location

Revision ID: 0002_department_publication
Revises: 0001_initial
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_department_publication"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("departments", sa.Column("location", sa.String(100)))
    op.add_column(
        "departments",
        sa.Column(
            "visibility",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'PUBLIC'"),
        ),
    )

    # Keep the existing demo data useful after the upgrade: give every current
    # department a public floor/location and rename the demo hospital.
    op.execute(
        "UPDATE departments SET location = 'Tầng ' || (((id - 1) % 5) + 1) "
        "WHERE location IS NULL"
    )
    op.execute(
        "UPDATE hospitals SET name = 'Bệnh viện HKT' "
        "WHERE name = 'Riverside General Hospital'"
    )


def downgrade() -> None:
    op.drop_column("departments", "visibility")
    op.drop_column("departments", "location")
