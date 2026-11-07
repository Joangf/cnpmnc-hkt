"""Sprint 3: VietQR + SePay bank-transfer payments, manual refunds, payment hold on appointments.

Revision ID: 0009_sepay_payments
Revises: 0008_merge_heads
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_sepay_payments"
down_revision = "0008_merge_heads"
branch_labels = None
depends_on = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.drop_column("payments", "provider")
    op.drop_column("payments", "checkout_url")
    op.drop_column("payments", "last_event_id")

    op.add_column("payments", sa.Column("payment_code", sa.String(16)))
    op.execute("UPDATE payments SET payment_code = 'LEGACY' || id")
    op.alter_column("payments", "payment_code", nullable=False)
    op.create_unique_constraint("uq_payments_payment_code", "payments", ["payment_code"])
    op.add_column("payments", sa.Column("expires_at", _TZ))
    op.execute("UPDATE payments SET status = 'EXPIRED' WHERE status = 'FAILED'")

    op.add_column("payments", sa.Column("refund_status", sa.String(32)))
    op.add_column("payments", sa.Column("refund_reference", sa.String(16)))
    op.create_unique_constraint("uq_payments_refund_reference", "payments", ["refund_reference"])
    op.add_column("payments", sa.Column("refund_bank_bin", sa.String(8)))
    op.add_column("payments", sa.Column("refund_bank_name", sa.String(64)))
    op.add_column("payments", sa.Column("refund_account_number", sa.String(32)))
    op.add_column("payments", sa.Column("refund_account_name", sa.String(128)))
    op.add_column("payments", sa.Column("refund_reason", sa.String(500)))
    op.add_column("payments", sa.Column("refund_note", sa.String(500)))
    op.add_column("payments", sa.Column("refund_requested_at", _TZ))

    op.add_column("appointments", sa.Column("payment_due_at", _TZ))
    op.create_index(
        "ix_appointments_status_payment_due", "appointments", ["status", "payment_due_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_status_payment_due", table_name="appointments")
    op.drop_column("appointments", "payment_due_at")

    for column in (
        "refund_requested_at",
        "refund_note",
        "refund_reason",
        "refund_account_name",
        "refund_account_number",
        "refund_bank_name",
        "refund_bank_bin",
    ):
        op.drop_column("payments", column)
    op.drop_constraint("uq_payments_refund_reference", "payments", type_="unique")
    op.drop_column("payments", "refund_reference")
    op.drop_column("payments", "refund_status")

    op.execute("UPDATE payments SET status = 'FAILED' WHERE status = 'EXPIRED'")
    op.drop_column("payments", "expires_at")
    op.drop_constraint("uq_payments_payment_code", "payments", type_="unique")
    op.drop_column("payments", "payment_code")

    op.add_column("payments", sa.Column("last_event_id", sa.String(64)))
    op.add_column("payments", sa.Column("checkout_url", sa.String(500)))
    op.add_column(
        "payments",
        sa.Column("provider", sa.String(32), nullable=False, server_default="mock"),
    )
