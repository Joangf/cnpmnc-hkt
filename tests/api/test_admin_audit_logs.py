"""API tests for the admin audit log (FR-ADM-05, NFR-10).

The suite runs against the live dev stack and creates its own users so the assertions do
not depend on seed data. Registration is used because ERP-owned admin writes are blocked
while the ERP cutover is incomplete.
"""

from __future__ import annotations

import os
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest


def _login(api, email: str, password: str) -> dict[str, str]:
    response = api.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(api):
    return _login(
        api,
        os.getenv("ADMIN_EMAIL", "admin@example.com"),
        os.getenv("ADMIN_PASSWORD", "Admin12345!"),
    )


@pytest.fixture(scope="session")
def patient_headers(api):
    return _login(
        api,
        os.getenv("DEMO_PATIENT_EMAIL", "patient@example.com"),
        os.getenv("DEMO_PATIENT_PASSWORD", "Patient12345!"),
    )


@pytest.fixture(scope="module")
def registered_users(api):
    """Two fresh users; each writes `user.registration_started` and `user.registered`."""
    users: list[dict[str, object]] = []
    for index in range(2):
        email = f"audit-test-{uuid4().hex[:10]}@example.com"
        response = api.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "AuditTest123!",
                "full_name": f"Audit Test {index}",
            },
        )
        assert response.status_code == 201, response.text
        otp = response.json().get("dev_otp")
        if not otp:
            pytest.skip("dev_otp is not exposed; run against a dev stack with email disabled")
        verified = api.post(
            "/api/v1/auth/register/verify", json={"email": email, "otp": otp}
        )
        assert verified.status_code == 200, verified.text
        users.append({"email": email, "id": verified.json()["user"]["id"]})
    return users


def _clinic_today() -> str:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()


def test_tc_01_patient_cannot_read_audit_logs(api, patient_headers):
    """TC-01 | AC: only ADMIN may read audit logs (FR-ADM-05) | technique: role boundary."""
    response = api.get("/api/v1/admin/audit-logs", headers=patient_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "Forbidden"


def test_tc_02_rejects_inverted_date_range(api, admin_headers):
    """TC-02 | AC: invalid input is 422 (NFR-12) | technique: boundary values."""
    response = api.get(
        "/api/v1/admin/audit-logs",
        params={"date_from": "2026-12-31", "date_to": "2026-01-01"},
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "InvalidDateRange"


def test_tc_03_filters_by_actor_type(api, admin_headers, registered_users):
    """TC-03 | AC: filter by actor type (FR-ADM-05) | technique: equivalence partitioning."""
    user_page = api.get(
        "/api/v1/admin/audit-logs",
        params={"actor_type": "USER", "page_size": 100},
        headers=admin_headers,
    )
    assert user_page.status_code == 200
    assert user_page.json()["items"]
    assert {item["actor_type"] for item in user_page.json()["items"]} == {"USER"}

    system_page = api.get(
        "/api/v1/admin/audit-logs",
        params={"actor_type": "SYSTEM", "page_size": 100},
        headers=admin_headers,
    )
    assert system_page.status_code == 200
    assert {item["actor_type"] for item in system_page.json()["items"]} <= {"SYSTEM"}

    email = registered_users[0]["email"]
    actor_page = api.get(
        "/api/v1/admin/audit-logs",
        params={"actor": email, "actor_type": "USER", "page_size": 100},
        headers=admin_headers,
    )
    assert actor_page.status_code == 200
    assert actor_page.json()["total"] >= 2
    assert {item["actor_email"] for item in actor_page.json()["items"]} == {email}
    assert {item["actor_type"] for item in actor_page.json()["items"]} == {"USER"}


def test_tc_04_combines_actor_entity_action_and_date_filters(
    api, admin_headers, registered_users
):
    """TC-04 | AC: filters compose (FR-ADM-05) | technique: decision table."""
    user = registered_users[0]
    today = _clinic_today()
    response = api.get(
        "/api/v1/admin/audit-logs",
        params={
            "actor": user["email"],
            "actor_type": "USER",
            "entity_type": "user",
            "action": "user.registered",
            "date_from": today,
            "date_to": today,
            "page_size": 100,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["action"] == "user.registered"
    assert item["entity_type"] == "user"
    assert item["entity_id"] == str(user["id"])
    assert item["actor_email"] == user["email"]
    assert item["actor_type"] == "USER"


def test_tc_05_paginates_without_overlap(api, admin_headers, registered_users):
    """TC-05 | AC: audit log is paginated (FR-ADM-05) | technique: boundary values."""
    first = api.get(
        "/api/v1/admin/audit-logs",
        params={"actor_type": "USER", "page": 1, "page_size": 2},
        headers=admin_headers,
    )
    second = api.get(
        "/api/v1/admin/audit-logs",
        params={"actor_type": "USER", "page": 2, "page_size": 2},
        headers=admin_headers,
    )

    assert first.status_code == second.status_code == 200
    first_body, second_body = first.json(), second.json()
    assert first_body["total"] == second_body["total"] >= 4
    assert first_body["page"] == 1 and second_body["page"] == 2
    assert first_body["page_size"] == second_body["page_size"] == 2
    assert len(first_body["items"]) == 2
    assert {item["id"] for item in first_body["items"]}.isdisjoint(
        {item["id"] for item in second_body["items"]}
    )
