"""Exercise the actual mock ERP ASGI app and its durable SQLite transactions."""

import asyncio
import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest


@pytest.fixture
async def hospital(tmp_path, monkeypatch):
    monkeypatch.setenv("ERP_DB_PATH", str(tmp_path / "erp.sqlite3"))
    path = Path(__file__).resolve().parents[2] / "mock-erp"
    if not path.exists():
        pytest.skip("Mock ERP source not available")
    monkeypatch.syspath_prepend(str(path))
    spec = importlib.util.spec_from_file_location("hospital_demo", path / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.LATENCY_MS = 0
    module._push = AsyncMock(return_value={"webhook_status": 200})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=module.app), base_url="http://erp"
    ) as client:
        yield client, module


async def prepare(client, capacity=5):
    r = await client.put(
        "/directory/doctors/D1",
        json={"id": "D1", "data": {"full_name": "Doctor", "is_active": True}},
    )
    assert r.status_code == 200, r.text
    start = (datetime.now(UTC) + timedelta(days=3)).replace(
        hour=1, minute=0, second=0, microsecond=0
    )
    slot = {
        "id": "S1",
        "doctor_id": "D1",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(minutes=30)).isoformat(),
        "capacity": capacity,
        "version": 1,
        "is_open": True,
    }
    r = await client.put("/slots/S1", json=slot)
    assert r.status_code == 200, r.text
    return r.json()


def body(slot, index):
    return {
        "booking_reference": f"BOOK{index}",
        "erp_doctor_id": "D1",
        "patient_ref": f"P{index}",
        "start_time": slot["start_time"],
        "end_time": slot["end_time"],
        "slot_id": "S1",
        "slot_version": slot["version"],
    }


async def test_mock_capacity_retry_and_persistence(hospital):
    client, module = hospital
    slot = await prepare(client)
    responses = await asyncio.gather(
        *(client.post("/bookings", json=body(slot, i)) for i in range(10))
    )
    assert sum(r.json()["status"] == "CONFIRMED" for r in responses) == 5
    same = await client.post("/bookings", json=body(slot, 0))
    assert same.json()["erp_booking_id"] == responses[0].json()["erp_booking_id"]
    # Every API request opens a new SQLite connection, so this reads persisted rows.
    assert len((await client.get("/bookings")).json()) == 10
    assert (await client.get("/catalog")).json()["slots"][0]["booked_count"] == 5
    from store import rows, transaction

    with transaction() as db:
        assert len(rows(db, "bookings")) == 10
    changed = await client.put(
        "/slots/S1",
        json={
            **slot,
            "end_time": (
                datetime.fromisoformat(slot["end_time"]) + timedelta(minutes=5)
            ).isoformat(),
        },
    )
    assert changed.status_code == 409


async def test_mock_cancellation_and_stale_slot(hospital):
    client, _ = hospital
    slot = await prepare(client, 1)
    booking = (await client.post("/bookings", json=body(slot, 1))).json()
    assert booking["status"] == "CONFIRMED"
    r = await client.post(f"/bookings/by-id/{booking['erp_booking_id']}/cancel", json={})
    assert r.status_code == 200
    assert (await client.post("/bookings", json=body(slot, 2))).json()["status"] == "CONFIRMED"
    updated = (await client.put("/slots/S1", json={**slot, "capacity": 2})).json()
    assert updated["version"] == 2
    assert (await client.post("/bookings", json=body(slot, 3))).json()["status"] == "REJECTED"
    assert (await client.post("/bookings", json=body(updated, 4))).json()["status"] == "CONFIRMED"


async def test_mock_checkin_and_complete(hospital):
    client, module = hospital
    slot = await prepare(client)
    await client.post("/bookings", json=body(slot, 1))
    assert (await client.post("/simulate/bookings/BOOK1/check-in")).status_code == 200
    assert (
        await client.post("/simulate/bookings/BOOK1/status", json={"status": "COMPLETED"})
    ).status_code == 200
    assert (await client.get("/bookings/BOOK1")).json()["status"] == "COMPLETED"
    assert module._push.call_count == 2
