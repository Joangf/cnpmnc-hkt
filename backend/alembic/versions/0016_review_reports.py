"""Patient reports of inappropriate reviews (SCRUM-50).

Revision ID: 0016_review_reports
Revises: 0015_vietnamese_symptom_synonyms
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_review_reports"
down_revision = "0015_vietnamese_symptom_synonyms"
branch_labels = None
depends_on = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "review_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("review_id", sa.Integer, sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("reporter_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("details", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.String(20)),
        sa.Column("resolved_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("resolved_at", _TZ),
        sa.Column("created_at", _TZ, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_review_reports_review_id", "review_reports", ["review_id"])
    op.create_index(
        "uq_review_reports_open",
        "review_reports",
        ["review_id", "reporter_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )


def downgrade() -> None:
    op.drop_table("review_reports")
