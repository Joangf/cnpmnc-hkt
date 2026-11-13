"""Integration tests for 15-min PENDING holds, shared hourly windows, and booking guardrails."""

import uuid
from datetime import UTC, datetime, timedelta

from app.integrations.erp.base import ErpBookingResult
from app.models import (
    Appointment,
    AppointmentType,
    Doctor,
    PatientProfile,
    User,
)
from app.models.enums import AppointmentStatus
from app.services import availability, erp_catalog, payments
from app.services.sepay import BankTransfer
from tests import test_erp_owned_slots as erp_tests

context = erp_tests.context
sessions = erp_tests.sessions
migrated = erp_tests.migrated
catalog = erp_tests.catalog
pytestmark = erp_tests.pytestmark


async def _new_patient(sessions) -> tuple[int, dict[str, str]]:
    from app.core.security import create_access_token

    async with sessions() as session:
        user = User(email=f"{uuid.uuid4().hex}@test.local", password_hash="unused")
        user.profile = PatientProfile(full_name="Second Patient")
        session.add(user)
        await session.commit()
        token = create_access_token(user.id, "PATIENT")
        return user.profile.id, {"Authorization": f"Bearer {token}"}


async def test_paid_hold_decrements_releases_on_cancel_confirms_on_payment_and_blocks_same_day(
    catalog, sessions
):
    ids, client, _, erp, snapshot = catalog
    snapshot["slots"][0]["capacity"] = 2
    async with sessions() as session:
        await erp_catalog.sync_catalog(session, erp)

    offer = (await erp_tests.offers(client, ids))[0]
    assert offer["capacity"] == 2
    assert offer["remaining_places"] == 2

    # 1. Request paid booking -> PENDING held 15 min, slot decremented, payment immediately open.
    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            **ids.payload(),
            "slot_id": offer["slot_id"],
            "slot_version": offer["version"],
        },
        headers=ids.headers("PATIENT"),
    )
    assert create_resp.status_code == 201, create_resp.text
    appt_id = create_resp.json()["id"]
    erp.create_booking.assert_not_awaited()

    detail = (
        await client.get(f"/api/v1/appointments/{appt_id}", headers=ids.headers("PATIENT"))
    ).json()
    assert detail["status"] == "PENDING"
    assert detail["payment_due_at"] is not None
    assert detail["can_pay"] is True
    assert detail["can_cancel"] is True
    assert (await erp_tests.offers(client, ids))[0]["remaining_places"] == 1

    # 2. Cancelling unpaid PENDING hold releases slot locally without calling ERP cancel.
    cancel_resp = await client.post(
        f"/api/v1/appointments/{appt_id}/cancel",
        json={},
        headers=ids.headers("PATIENT"),
    )
    assert cancel_resp.status_code == 200, cancel_resp.text
    erp.cancel_booking.assert_not_awaited()
    assert (await erp_tests.offers(client, ids))[0]["remaining_places"] == 2

    # 3. Re-book, initiate payment, settle via bank transfer -> submits to ERP & becomes CONFIRMED.
    create_resp2 = await client.post(
        "/api/v1/appointments",
        json={
            **ids.payload(),
            "slot_id": offer["slot_id"],
            "slot_version": offer["version"],
        },
        headers=ids.headers("PATIENT"),
    )
    assert create_resp2.status_code == 201, create_resp2.text
    appt_id2 = create_resp2.json()["id"]

    pay_resp = await client.post(
        f"/api/v1/appointments/{appt_id2}/payments", headers=ids.headers("PATIENT")
    )
    assert pay_resp.status_code == 201, pay_resp.text
    pay_data = pay_resp.json()

    async with sessions() as session:
        appt2 = await session.get(Appointment, appt_id2)
        transfer = BankTransfer(
            id=f"tx-{uuid.uuid4().hex[:8]}",
            amount_in=appt2.fee_amount,
            transaction_content=pay_data["payment_code"],
            code=pay_data["payment_code"],
            transaction_date=datetime.now(UTC),
        )
        outcome = await payments.apply_transfer(session, transfer, erp=erp)
        assert outcome == "paid"
        await session.refresh(appt2)
        assert appt2.status == AppointmentStatus.CONFIRMED
        assert appt2.payment_due_at is None
        req = erp.create_booking.call_args.args[0]
        assert req.slot_id == snapshot["slots"][0]["id"]
        assert req.slot_version == 1

    # 4. Same patient cannot book another active slot with the same doctor on the same day.
    slot2_start = ids.start + timedelta(hours=1)
    snapshot["slots"].append(
        {
            "id": f"slot2-{uuid.uuid4().hex[:6]}",
            "doctor_id": snapshot["doctors"][0]["id"],
            "start_time": slot2_start.isoformat(),
            "end_time": (slot2_start + timedelta(hours=1)).isoformat(),
            "capacity": 2,
            "is_open": True,
            "version": 1,
            "booked_count": 0,
        }
    )
    async with sessions() as session:
        await erp_catalog.sync_catalog(session, erp)
    day_offers = await erp_tests.offers(client, ids)
    second_offer = next(o for o in day_offers if o["slot_id"] != offer["slot_id"])
    dup_resp = await client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": ids.doctor,
            "appointment_type_id": ids.type,
            "start_time": second_offer["start_time"],
            "slot_id": second_offer["slot_id"],
            "slot_version": second_offer["version"],
        },
        headers=ids.headers("PATIENT"),
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "AlreadyBookedSameDay"


async def test_zero_slots_expiry_restore_cross_doctor_overlap_and_past_lead_time(
    catalog, sessions
):
    ids, client, redis, erp, snapshot = catalog
    snapshot["slots"][0]["capacity"] = 2
    async with sessions() as session:
        await erp_catalog.sync_catalog(session, erp)

    offer = (await erp_tests.offers(client, ids))[0]
    p2_id, p2_headers = await _new_patient(sessions)

    # Two patients fill capacity=2 window -> availability STILL returns the slot with remaining_places=0.
    r1 = await client.post(
        "/api/v1/appointments",
        json={**ids.payload(), "slot_id": offer["slot_id"], "slot_version": offer["version"]},
        headers=ids.headers("PATIENT"),
    )
    r2 = await client.post(
        "/api/v1/appointments",
        json={**ids.payload(), "slot_id": offer["slot_id"], "slot_version": offer["version"]},
        headers=p2_headers,
    )
    assert r1.status_code == 201 and r2.status_code == 201
    full_offers = await erp_tests.offers(client, ids)
    assert len(full_offers) == 1
    assert full_offers[0]["remaining_places"] == 0

    # Expiring unpaid hold returns slot to remaining_places=1.
    async with sessions() as session:
        appt1 = await session.get(Appointment, r1.json()["id"])
        appt1.payment_due_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
        await payments.expire_unpaid(session, redis, erp)
    assert (await erp_tests.offers(client, ids))[0]["remaining_places"] == 1

    # Second doctor at overlapping time is blocked with 409 PatientTimeConflict for Patient 2.
    other_doc_erp = f"doc2-{uuid.uuid4().hex[:6]}"
    other_type_erp = f"type2-{uuid.uuid4().hex[:6]}"
    other_slot_erp = f"slot-doc2-{uuid.uuid4().hex[:6]}"
    snapshot["doctors"].append(
        {
            "id": other_doc_erp,
            "data": {
                "full_name": "Dr. Overlap Test",
                "department_id": snapshot["departments"][0]["id"],
            },
        }
    )
    snapshot["appointment_types"].append(
        {
            "id": other_type_erp,
            "data": {
                "name": "Standard Overlap",
                "duration_minutes": 30,
                "fee_override": "100000",
                "doctor_id": other_doc_erp,
            },
        }
    )
    snapshot["slots"].append(
        {
            "id": other_slot_erp,
            "doctor_id": other_doc_erp,
            "start_time": ids.start.isoformat(),
            "end_time": (ids.start + timedelta(minutes=30)).isoformat(),
            "capacity": 2,
            "is_open": True,
            "version": 1,
            "booked_count": 0,
        }
    )
    async with sessions() as session:
        await erp_catalog.sync_catalog(session, erp)
        from sqlalchemy import select

        other_doc = await session.scalar(select(Doctor).where(Doctor.erp_id == other_doc_erp))
        other_type = await session.scalar(
            select(AppointmentType).where(AppointmentType.erp_id == other_type_erp)
        )
        other_doc_id = other_doc.id
        other_type_id = other_type.id
    other_offers = (
        await client.get(
            f"/api/v1/doctors/{other_doc_id}/availability",
            params={"date": ids.day.isoformat(), "appointment_type_id": other_type_id},
        )
    ).json()["slots"]
    overlap_resp = await client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": other_doc_id,
            "appointment_type_id": other_type_id,
            "start_time": other_offers[0]["start_time"],
            "slot_id": other_offers[0]["slot_id"],
            "slot_version": other_offers[0]["version"],
        },
        headers=p2_headers,
    )
    assert overlap_resp.status_code == 409
    assert overlap_resp.json()["error"]["code"] == "PatientTimeConflict"

    # Today's <60m lead-time slot shows is_past=True in availability & rejects booking with LeadTimeTooShort.
    tz = availability.clinic_tz()
    soon_start = (datetime.now(tz) + timedelta(minutes=30)).replace(second=0, microsecond=0)
    today = soon_start.date()
    if soon_start.date() == (soon_start + timedelta(minutes=30)).date():
        soon_slot_erp = f"soon-{uuid.uuid4().hex[:6]}"
        snapshot["slots"].append(
            {
                "id": soon_slot_erp,
                "doctor_id": snapshot["doctors"][0]["id"],
                "start_time": soon_start.astimezone(UTC).isoformat(),
                "end_time": (soon_start + timedelta(minutes=30)).astimezone(UTC).isoformat(),
                "capacity": 2,
                "is_open": True,
                "version": 1,
                "booked_count": 0,
            }
        )
        async with sessions() as session:
            await erp_catalog.sync_catalog(session, erp)
        today_offers = (
            await client.get(
                f"/api/v1/doctors/{ids.doctor}/availability",
                params={"date": today.isoformat(), "appointment_type_id": ids.type},
            )
        ).json()["slots"]
        soon_offer = next(
            o for o in today_offers if o["start_time"] == soon_start.astimezone(UTC).isoformat().replace("+00:00", "Z")
            or datetime.fromisoformat(o["start_time"]) == soon_start.astimezone(UTC)
        )
        assert soon_offer["is_past"] is True
        too_soon = await client.post(
            "/api/v1/appointments",
            json={
                "doctor_id": ids.doctor,
                "appointment_type_id": ids.type,
                "start_time": soon_offer["start_time"],
                "slot_id": soon_offer["slot_id"],
                "slot_version": soon_offer["version"],
            },
            headers=ids.headers("PATIENT"),
        )
        assert too_soon.status_code == 422
        assert too_soon.json()["error"]["code"] == "LeadTimeTooShort"
