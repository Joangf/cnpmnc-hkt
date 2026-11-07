"""Verify the manual-only transition on a populated disposable database."""

import os
import subprocess
import sys
from datetime import timedelta

import pytest
from sqlalchemy import select, text

from app.models import AuditLog, DoctorSlot
from tests import test_scheduling_integration as scheduling_tests

migrated = scheduling_tests.migrated
sessions = scheduling_tests.sessions
pytestmark = pytest.mark.skipif(
    not scheduling_tests.TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set"
)


def migrate(*args):
    subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=scheduling_tests.BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": scheduling_tests.TEST_DATABASE_URL}, check=True,
    )


async def _row(sessions, table: str, row_id: int) -> dict:
    """Raw row, independent of the ORM mapping (which follows the newest schema)."""
    async with sessions() as session:
        query = text(f"SELECT * FROM {table} WHERE id = :id")
        result = await session.execute(query, {"id": row_id})
        return dict(result.mappings().one())


async def test_manual_only_upgrade_preserves_appointments_and_prepared_slots(sessions):
    # Seed at head (the ORM matches the newest schema), then rewind to just before the
    # manual-only migration. Later migrations (e.g. 0010 payments) are undone as well, so rows
    # are compared raw and only 0009 is re-applied for the comparison.
    async with sessions() as session:
        ids = await scheduling_tests.seed(session)
    appointment_id = await scheduling_tests.reserve(sessions, ids)
    async with sessions() as session:
        prepared = DoctorSlot(
            doctor_id=ids.doctor, start_time=ids.start + timedelta(hours=5),
            end_time=ids.start + timedelta(hours=6),
            end_with_buffer=ids.start + timedelta(hours=6, minutes=10),
            buffer_minutes=10, capacity=5,
        )
        session.add(prepared)
        await session.commit()
        slot_id = prepared.id
    migrate("downgrade", "0008_merge_heads")
    try:
        before = await _row(sessions, "appointments", appointment_id)
        slot_before = await _row(sessions, "doctor_slots", slot_id)
        assert (await _row(sessions, "doctors", ids.doctor))["scheduling_mode"] == "ERP"
        migrate("upgrade", "0009_manual_only_scheduling")
        assert (await _row(sessions, "doctors", ids.doctor))["scheduling_mode"] == "MANUAL"
        assert await _row(sessions, "appointments", appointment_id) == before
        assert await _row(sessions, "doctor_slots", slot_id) == slot_before
        async with sessions() as session:
            audit = await session.scalar(select(AuditLog).where(
                AuditLog.entity_id == str(ids.doctor),
                AuditLog.action == "doctor.scheduling_manual_only",
            ))
            assert audit is not None
            assert audit.details == {"from": "ERP", "to": "MANUAL"}
    finally:
        migrate("upgrade", "head")
