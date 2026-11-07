"""Use admin-managed slots for all new offers; preserve existing reservations."""

import sqlalchemy as sa

from alembic import op

revision = "0009_manual_only_scheduling"
down_revision = "0008_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A single migration transaction changes the source and records the transition.
    # Updating the doctor timestamp also versions out previously cached ERP offers.
    op.execute("""
        WITH changed AS (
            UPDATE doctors SET scheduling_mode = 'MANUAL', updated_at = now()
            WHERE scheduling_mode <> 'MANUAL'
            RETURNING id
        )
        INSERT INTO audit_logs (actor_type, action, entity_type, entity_id, details, created_at)
        SELECT 'SYSTEM', 'doctor.scheduling_manual_only', 'doctor', id::text,
               '{"from": "ERP", "to": "MANUAL"}'::jsonb, now()
        FROM changed
    """)
    op.alter_column("doctors", "scheduling_mode", server_default=sa.text("'MANUAL'"))


def downgrade() -> None:
    # Do not guess prior modes or alter appointments created since the migration.
    op.alter_column("doctors", "scheduling_mode", server_default=sa.text("'ERP'"))
