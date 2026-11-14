"""AI symptom search (pgvector index), review summaries, switchable symptom rules.

Revision ID: 0014_ai_symptom_search
Revises: 0013_audit_log_indexes
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

revision = "0014_ai_symptom_search"
down_revision = "0013_audit_log_indexes"
branch_labels = None
depends_on = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "search_documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("part", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("colbert", sa.LargeBinary, nullable=False),
        sa.Column(
            "tsv",
            TSVECTOR,
            sa.Computed("to_tsvector('simple', content)", persisted=True),
        ),
        sa.Column("updated_at", _TZ, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("entity_type", "entity_id", "part", name="uq_search_documents_entity"),
    )
    op.create_index("ix_search_documents_tsv", "search_documents", ["tsv"], postgresql_using="gin")
    op.create_table(
        "doctor_review_summaries",
        sa.Column(
            "doctor_id",
            sa.Integer,
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("points", sa.JSON, nullable=False),
        sa.Column("review_count", sa.Integer, nullable=False),
        sa.Column("review_set_hash", sa.String(64), nullable=False),
        sa.Column("generated_at", _TZ, nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "symptom_specialty_rules",
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("symptom_specialty_rules", "is_active")
    op.drop_table("doctor_review_summaries")
    op.drop_index("ix_search_documents_tsv", table_name="search_documents")
    op.drop_table("search_documents")
