"""Verify the manual-only transition on a populated disposable database."""

import os
import subprocess
import sys
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import Appointment, AuditLog, Doctor, DoctorSlot
from app.models.enums import SchedulingMode
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


async def test_manual_only_upgrade_preserves_appointments_and_prepared_slots(sessions):
    migrate("downgrade", "0008_merge_heads")
    try:
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
            before = (await session.execute(select(Appointment.__table__).where(
                Appointment.id == appointment_id
            ))).mappings().one()
            slot_before = (await session.execute(select(DoctorSlot.__table__).where(
                DoctorSlot.id == slot_id
            ))).mappings().one()
        migrate("upgrade", "head")
        async with sessions() as session:
            doctor = await session.get(Doctor, ids.doctor)
            assert doctor.scheduling_mode == SchedulingMode.MANUAL
            after = (await session.execute(select(Appointment.__table__).where(
                Appointment.id == appointment_id
            ))).mappings().one()
            slot_after = (await session.execute(select(DoctorSlot.__table__).where(
                DoctorSlot.id == slot_id
            ))).mappings().one()
            assert dict(after) == dict(before)
            assert dict(slot_after) == dict(slot_before)
            audit = await session.scalar(select(AuditLog).where(
                AuditLog.entity_id == str(ids.doctor),
                AuditLog.action == "doctor.scheduling_manual_only",
            ))
            assert audit is not None
            assert audit.details == {"from": "ERP", "to": "MANUAL"}
    finally:
        migrate("upgrade", "head")
