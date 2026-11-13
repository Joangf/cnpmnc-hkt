"""Indexes for admin audit log filters (NFR-10, FR-ADM-05)."""

import sqlalchemy as sa

from alembic import op

revision = "0013_audit_log_indexes"
down_revision = "0012_review_is_edited"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index(
        "ix_audit_logs_details_appointment_id",
        "audit_logs",
        [sa.text("(details->>'appointment_id')")],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_details_appointment_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
