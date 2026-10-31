"""API smoke test against the running compose stack (through nginx), ~90 checks.

Run with `make smoke` after `docker compose up -d`. Creates its own test data.
"""

import os
import re
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx

BASE = os.getenv("SMOKE_BASE_URL", "http://localhost:8080")
API = f"{BASE}/api/v1"
ERP = os.getenv("SMOKE_ERP_URL", "http://localhost:8100")
failures: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))
    if not cond:
        failures.append(name)


def client() -> httpx.Client:
    return httpx.Client(base_url=API, timeout=15)


def login(c: httpx.Client, email: str, password: str) -> str:
    r = c.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    token = r.json()["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return token


def find_slot(c: httpx.Client, doctor_id: int, offset_start: int = 2) -> tuple[int, str, str]:
    types = c.get(f"/doctors/{doctor_id}/appointment-types").json()
    for offset in range(offset_start, 14):
        day = (datetime.now(UTC) + timedelta(hours=7, days=offset)).date().isoformat()
        r = c.get(
            f"/doctors/{doctor_id}/availability", params={"date": day, "appointment_type_id": types[0]["id"]}
        )
        slots = r.json()["slots"]
        if slots:
            return types[0]["id"], slots[len(slots) // 2]["start_time"], day
    raise RuntimeError("no slot")


# --- Guest discovery -----------------------------------------------------------------------
guest = client()
r = guest.get("/hospitals")
check("list hospitals", r.status_code == 200 and r.json()["total"] == 3, r.text[:200])
hospital = r.json()["items"][0]
check("hospital has specialties", len(hospital["specialties"]) > 0)
check("hospital detail", guest.get(f"/hospitals/{hospital['id']}").status_code == 200)
check("filter hospitals by specialty", guest.get("/hospitals", params={"specialty_id": 5}).status_code == 200)
r = guest.get("/doctors", params={"page_size": 100})
check("list doctors", r.status_code == 200 and r.json()["total"] == 28, r.text[:200])
doctors = r.json()["items"]
check(
    "search doctors by name",
    guest.get("/doctors", params={"q": doctors[0]["full_name"][4:10]}).json()["total"] >= 1,
)
check("doctor detail", guest.get(f"/doctors/{doctors[0]['id']}").status_code == 200)
check(
    "unknown doctor -> 404 error contract",
    guest.get("/doctors/99999").json().get("error", {}).get("code") == "NotFound",
)
r = guest.get("/symptoms")
check("list symptoms", r.status_code == 200 and len(r.json()) > 10)
symptoms = {s["name"]: s["id"] for s in r.json()}
r = guest.post(
    "/symptoms/recommendations",
    json={"symptom_ids": [symptoms["Persistent cough"], symptoms["Shortness of breath"]]},
)
rec = r.json()
check(
    "recommendation top = respiratory",
    r.status_code == 200 and rec["specialties"][0]["name"] == "Respiratory Medicine",
    rec,
)
check(
    "recommendation has departments + disclaimer",
    bool(rec["departments"]) and "not a medical diagnosis" in rec["disclaimer"],
)
check("red flag warning shown", rec["urgent_warning"] is not None)
r = guest.post("/symptoms/recommendations", json={"free_text": "I have an itchy rash"})
check("free-text -> dermatology", r.json()["specialties"][0]["name"] == "Dermatology", r.text[:300])
check("empty recommendation -> 422", guest.post("/symptoms/recommendations", json={}).status_code == 422)
check("guest cannot book -> 401", guest.post("/appointments", json={}).status_code == 401)
check("X-Request-ID header", bool(guest.get("/specialties").headers.get("x-request-id")))

# --- Registration validation ---------------------------------------------------------------
reg = client()
email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
r = reg.post(
    "/auth/register",
    json={
        "email": email,
        "password": "short",
        "full_name": "A",
        "date_of_birth": "2999-01-01",
        "phone_number": "12",
    },
)
check(
    "register validation -> 422 with details",
    r.status_code == 422 and len(r.json()["error"]["details"]) >= 3,
    r.text[:300],
)
r = reg.post(
    "/auth/register",
    json={
        "email": email,
        "password": "Secret123",
        "full_name": "Smoke Tester",
        "date_of_birth": "1990-02-03",
        "phone_number": "+84 912 345 678",
    },
)
check("register -> 201 + refresh cookie", r.status_code == 201 and "refresh_token" in r.cookies, r.text[:300])
check(
    "duplicate email -> 409",
    reg.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Secret123",
            "full_name": "Smoke Tester",
            "date_of_birth": "1990-02-03",
            "phone_number": "+84912345678",
        },
    ).status_code
    == 409,
)
r = reg.post("/auth/refresh")
check("refresh via cookie", r.status_code == 200, r.text[:200])
reg.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
r = reg.get("/profile")
check(
    "profile phone normalised",
    r.status_code == 200 and r.json()["phone_number"] == "+84912345678",
    r.text[:200],
)
r = reg.patch("/profile", json={"address": "1 Test Street"})
check("update profile", r.status_code == 200 and r.json()["address"] == "1 Test Street")
check("profile null name -> 422", reg.patch("/profile", json={"full_name": None}).status_code == 422)

# --- Booking ---------------------------------------------------------------------------------
patient = client()
login(patient, "patient@example.com", "Patient12345!")
doctor_id = doctors[0]["id"]
type_id, start, day = find_slot(patient, doctor_id)
key = uuid.uuid4().hex
body = {
    "doctor_id": doctor_id,
    "appointment_type_id": type_id,
    "start_time": start,
    "reason_for_visit": "Smoke test",
}
r = patient.post("/appointments", json=body, headers={"Idempotency-Key": key})
check("create appointment -> 201", r.status_code == 201, r.text[:300])
appt = r.json()
check("appointment confirmed by ERP", appt["status"] == "CONFIRMED", appt.get("status"))
check("booking reference format", re.fullmatch(r"HK[A-Z2-9]{8}", appt["booking_reference"]) is not None)
check("statuses separate", appt["payment_status"] == "UNPAID" and appt["check_in_status"] == "NOT_CHECKED_IN")
r = patient.post("/appointments", json=body, headers={"Idempotency-Key": key})
check(
    "idempotent retry returns same appointment",
    r.status_code == 201 and r.json()["id"] == appt["id"],
    r.text[:200],
)
r = reg.post("/appointments", json=body)
check(
    "other patient same slot -> 409",
    r.status_code == 409 and r.json()["error"]["code"] in ("SlotTaken", "SlotUnavailable"),
    r.text[:200],
)
avail = patient.get(
    f"/doctors/{doctor_id}/availability", params={"date": day, "appointment_type_id": type_id}
).json()
check("booked slot no longer offered", start not in [s["start_time"] for s in avail["slots"]])
check(
    "other patient cannot see appointment -> 404", reg.get(f"/appointments/{appt['id']}").status_code == 404
)
check(
    "list upcoming",
    any(
        a["id"] == appt["id"]
        for a in patient.get("/appointments", params={"scope": "upcoming"}).json()["items"]
    ),
)
check(
    "history has 2 status rows",
    [h["to_value"] for h in appt["history"]] == ["PENDING", "CONFIRMED"],
    appt["history"],
)

# --- Payment -------------------------------------------------------------------------------
r = patient.post(f"/appointments/{appt['id']}/payments")
check("initiate payment -> 201", r.status_code == 201, r.text[:300])
pay = r.json()
check("checkout url via nginx", pay["checkout_url"].startswith(f"{BASE}/mock-payment/checkout/"), pay)
page = httpx.get(pay["checkout_url"])
check("checkout page renders", page.status_code == 200 and "SANDBOX" in page.text)
ref = pay["checkout_url"].rsplit("/", 1)[1]
r = httpx.post(f"{pay['checkout_url'].rsplit('/', 1)[0]}/{ref}/complete", data={"outcome": "success"})
check(
    "checkout completes -> 303 to return url",
    r.status_code == 303 and f"payment_id={pay['payment_id']}" in r.headers["location"],
    r.headers,
)
r = patient.get(f"/payments/{pay['payment_id']}")
check("payment PAID after callback", r.json()["status"] == "PAID", r.text[:200])
check(
    "appointment still CONFIRMED (BR-07)",
    patient.get(f"/appointments/{appt['id']}").json()["status"] == "CONFIRMED",
)
check(
    "pay again -> 409 AlreadyPaid",
    patient.post(f"/appointments/{appt['id']}/payments").json()["error"]["code"] == "AlreadyPaid",
)

# --- ERP-driven check-in / completion / review ---------------------------------------------
r = httpx.post(f"{ERP}/simulate/bookings/{appt['booking_reference']}/check-in")
check("ERP check-in webhook accepted", r.json().get("webhook_status") == 200, r.text[:300])
r = httpx.post(f"{ERP}/simulate/bookings/{appt['booking_reference']}/status", json={"status": "COMPLETED"})
check("ERP completion webhook accepted", r.json().get("webhook_status") == 200, r.text[:300])
detail = patient.get(f"/appointments/{appt['id']}").json()
check(
    "appointment COMPLETED + CHECKED_IN",
    detail["status"] == "COMPLETED" and detail["check_in_status"] == "CHECKED_IN",
    detail,
)
check("can_review true", detail["can_review"])
r = patient.post(
    f"/appointments/{appt['id']}/review", json={"rating": 5, "comment": "Very clear explanations."}
)
check("create review -> 201", r.status_code == 201, r.text[:200])
check(
    "duplicate review -> 409",
    patient.post(f"/appointments/{appt['id']}/review", json={"rating": 4}).status_code == 409,
)
doc = guest.get(f"/doctors/{doctor_id}").json()
check("doctor rating updated", doc["rating_count"] >= 1 and float(doc["rating_avg"]) > 0, doc)
check("public review listed", guest.get(f"/doctors/{doctor_id}/reviews").json()["total"] >= 1)

# --- Cancel with refund ----------------------------------------------------------------------
type_id2, start2, _ = find_slot(patient, doctors[1]["id"], offset_start=3)
appt2 = patient.post(
    "/appointments",
    json={"doctor_id": doctors[1]["id"], "appointment_type_id": type_id2, "start_time": start2},
).json()
pay2 = patient.post(f"/appointments/{appt2['id']}/payments").json()
ref2 = pay2["checkout_url"].rsplit("/", 1)[1]
httpx.post(f"{BASE}/mock-payment/api/checkouts/{ref2}/simulate", json={"outcome": "success"})
r = patient.post(f"/appointments/{appt2['id']}/cancel", json={"reason": "Smoke test"})
check("cancel -> CANCELLED", r.status_code == 200 and r.json()["status"] == "CANCELLED", r.text[:300])
check("paid appointment refunded", r.json()["payment_status"] == "REFUNDED", r.json().get("payment_status"))
day2 = (datetime.fromisoformat(start2) + timedelta(hours=7)).date().isoformat()
avail2 = guest.get(
    f"/doctors/{doctors[1]['id']}/availability", params={"date": day2, "appointment_type_id": type_id2}
).json()
check("cancelled slot offered again", start2 in [s["start_time"] for s in avail2["slots"]])
check("cancel again -> 409", patient.post(f"/appointments/{appt2['id']}/cancel", json={}).status_code == 409)

# --- Failed payment then retry ---------------------------------------------------------------
type_id3, start3, _ = find_slot(patient, doctors[2]["id"], offset_start=4)
appt3 = patient.post(
    "/appointments",
    json={"doctor_id": doctors[2]["id"], "appointment_type_id": type_id3, "start_time": start3},
).json()
p3 = patient.post(f"/appointments/{appt3['id']}/payments").json()
httpx.post(
    f"{BASE}/mock-payment/api/checkouts/{p3['checkout_url'].rsplit('/', 1)[1]}/simulate",
    json={"outcome": "fail"},
)
d3 = patient.get(f"/appointments/{appt3['id']}").json()
check(
    "failed payment -> FAILED and can retry",
    d3["payment_status"] == "FAILED" and d3["can_pay"],
    d3["payment_status"],
)
check("retry payment -> 201", patient.post(f"/appointments/{appt3['id']}/payments").status_code == 201)

# --- Notifications ---------------------------------------------------------------------------
n = patient.get("/notifications").json()
types_seen = {i["type"] for i in n["items"]}
check(
    "notifications created",
    {"BOOKING_SUBMITTED", "APPOINTMENT_STATUS", "PAYMENT_RESULT", "CHECK_IN"} <= types_seen,
    types_seen,
)
check("mark all read -> 204", patient.post("/notifications/read-all").status_code == 204)
check("unread now 0", patient.get("/notifications").json()["unread_count"] == 0)

# --- Webhook security ------------------------------------------------------------------------
r = httpx.post(
    f"{API}/integrations/erp/events",
    json={"event_id": "x"},
    headers={"x-erp-timestamp": str(int(time.time())), "x-erp-signature": "bad"},
)
check("unsigned ERP webhook -> 401", r.status_code == 401, r.text[:200])
r = httpx.post(
    f"{API}/payments/callback", content=b"{}", headers={"x-mock-timestamp": "1", "x-mock-signature": "bad"}
)
check("unsigned payment callback -> 401", r.status_code == 401, r.text[:200])

# --- Admin -----------------------------------------------------------------------------------
check("patient cannot access admin -> 403", patient.get("/admin/users").status_code == 403)
admin = client()
login(admin, "admin@example.com", "Admin12345!")
s = admin.get("/admin/reports/summary").json()
check("report summary", s["appointments_by_status"].get("CONFIRMED", 0) >= 1 and s["total_patients"] >= 2, s)
check("admin users list", admin.get("/admin/users", params={"q": "smoke"}).json()["total"] >= 1)
reviews = admin.get("/admin/reviews").json()["items"]
r = admin.patch(f"/admin/reviews/{reviews[0]['id']}", json={"status": "HIDDEN", "note": "smoke"})
check("moderate review", r.status_code == 200 and r.json()["status"] == "HIDDEN", r.text[:200])
public_ids = [x["id"] for x in guest.get(f"/doctors/{reviews[0]['doctor_id']}/reviews").json()["items"]]
check("hidden review not public", reviews[0]["id"] not in public_ids, public_ids)
admin.patch(f"/admin/reviews/{reviews[0]['id']}", json={"status": "PUBLISHED"})
r = admin.post(
    "/admin/hospitals",
    json={"name": "Smoke Clinic", "address": "9 Test Rd", "city": "Da Nang", "facility_type": "CLINIC"},
)
check("admin create hospital", r.status_code == 201, r.text[:300])
hid = r.json()["id"]
r = admin.patch(f"/admin/hospitals/{hid}", json={"is_active": False})
check("admin deactivate hospital", r.status_code == 200 and r.json()["is_active"] is False)
check("inactive hospital hidden from guests", guest.get(f"/hospitals/{hid}").status_code == 404)
check(
    "admin null name -> 422", admin.patch(f"/admin/hospitals/{hid}", json={"name": None}).status_code == 422
)
for entity in ("specialties", "departments", "doctors", "appointment-types", "hospitals"):
    check(f"admin list {entity}", admin.get(f"/admin/{entity}").status_code == 200)
r = admin.post(
    "/admin/appointment-types",
    json={"name": "Smoke type", "duration_minutes": 25, "buffer_minutes": 5, "specialty_id": 1},
)
check("admin create appointment type", r.status_code == 201, r.text[:300])
check("admin appointments", admin.get("/admin/appointments").json()["total"] >= 3)
check("audit log populated", admin.get("/admin/audit-logs").json()["total"] > 10)
r = admin.post("/admin/integrations/erp/sync-schedules")
check(
    "manual schedule sync",
    r.status_code == 200 and r.json()["success"] and r.json()["doctors_synced"] == 28,
    r.text[:200],
)
u = admin.get("/admin/users", params={"q": email}).json()["items"][0]
check(
    "deactivate user",
    admin.patch(f"/admin/users/{u['id']}", json={"account_status": "INACTIVE"}).status_code == 200,
)
check("deactivated user's token rejected", reg.get("/profile").status_code == 401)
check(
    "deactivated user cannot log in -> 403",
    client().post("/auth/login", json={"email": email, "password": "Secret123"}).status_code == 403,
)

# --- Logout / password reset -----------------------------------------------------------------
pr = client()
r = pr.post("/auth/password-reset/request", json={"email": "patient@example.com"})
token = r.json().get("dev_reset_token")
check("password reset token (dev)", bool(token), r.text)
check(
    "reset confirm",
    pr.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "Patient12345!"}
    ).status_code
    == 200,
)
check(
    "reset token single use",
    pr.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "Patient12345!"}
    ).status_code
    == 422,
)
lo = client()
login(lo, "patient@example.com", "Patient12345!")
check("logout -> 204", lo.post("/auth/logout").status_code == 204)
check("refresh after logout -> 401", lo.post("/auth/refresh").status_code == 401)

# --- SPA routes ------------------------------------------------------------------------------
for path in ("/", "/doctors/1", "/appointments/1", "/admin"):
    r = httpx.get(BASE + path)
    check(f"SPA route {path}", r.status_code == 200 and '<div id="root">' in r.text)

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
