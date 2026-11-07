# CareBook: Healthcare Appointment Platform

A patient-facing discovery, booking and payment platform. It implements the requirements in [.claude/plans/business.md](.claude/plans/business.md) (FRD v1.2) with the stack described in [.claude/plans/implement.md](.claude/plans/implement.md). The UI follows [.claude/design/design-guidelines.md](.claude/design/design-guidelines.md). [.claude/plans/integration-status.md](.claude/plans/integration-status.md) lists which integrations are real and which are simulated.

## Quick start

```bash
cp .env.example .env        # optional; every value has a dev default
docker compose up -d --build
make seed-loadtest          # optional: 200 load-test patients for k6
```

| URL | What |
|---|---|
| http://localhost:8080 | Web app |
| http://localhost:8080/api/docs | OpenAPI (Swagger) |
| http://localhost:3000 | Grafana (admin / admin), folder *Healthcare* |
| http://localhost:9090 | Prometheus |
| http://localhost:8100/docs | Mock ERP: simulate confirm / check-in / complete (dev only) |

Seeded accounts: `admin@example.com` / `Admin12345!` and `patient@example.com` / `Patient12345!`. The demo patient has one completed appointment, so you can try the review flow straight away.

## Try the main flow

1. Sign in as the demo patient, open **Doctors**, pick a doctor, then choose a type, a date and a time.
2. Request the booking. The mock ERP confirms it, and the page shows the booking reference with separate appointment, payment and check-in statuses.
3. Click **Pay online**, then **Pay now** on the sandbox page. You land back on the result page.
4. In http://localhost:8100/docs, call `POST /simulate/bookings/{ref}/check-in` and then `.../status` with `{"status":"COMPLETED"}`. The appointment page updates, and a review form appears.

## Layout

```
backend/            FastAPI app: api/ (routers) -> services/ (logic) -> repositories/ (DB)
                    integrations/ (ERP + payment adapters), core/ (config, logging, metrics),
                    alembic/ (migrations), tests/
frontend/           React + TS + Vite SPA, served by nginx, which also proxies /api
                    src/ (pages, components, api client), e2e/ (Playwright)
mock-erp/           Simulated hospital ERP/HIS (schedules, bookings, signed status webhooks)
mock-payment/       Sandbox payment gateway (checkout page, signed callbacks, refunds)
k6/                 Load scenarios (browse, symptoms, booking, contention, admin, mixed)
monitoring/         Prometheus, Loki, Alloy, Grafana provisioning + dashboards
postgres/init/      SQL run on first start (creates the healthcare_test database)
scripts/            api_smoke.py, the API smoke test behind `make smoke`
openapi.json        OpenAPI snapshot from `make openapi`; source for `make gen-client`
.claude/plans/      business.md (FRD), implement.md (implementation plan) and
                    integration-status.md (what is real and what is simulated)
.claude/design/     Design boards (HTML, PDF, PNG) and design-guidelines.md, the text spec
                    behind frontend/tailwind.config.js and frontend/src/index.css
docker-compose.yml  Full stack; docker-compose.override.yml adds dev hot reload and ports
```

## Key design points

- **No double booking.** Availability is revalidated on submit. A Postgres `EXCLUDE USING gist` constraint on `(doctor_id, tstzrange(start, end+buffer))` rejects overlaps atomically, and the API returns `409`. The constraint is created in `alembic/versions/0001_initial.py`.
- **"Confirmed" means the ERP accepted it** (BR-02). A booking is inserted as `PENDING` and only changes to `CONFIRMED` after the ERP accepts it. If the ERP times out, the booking stays `PENDING` and a reconciler resolves it later.
- **Separate statuses** (BR-07). Appointment status, payment status and check-in status are tracked separately. Check-in status is written only by the ERP (BR-11).
- **Configurable scheduling** (BR-05). Duration, buffer and fee live on `AppointmentType`, which can be global, per specialty or per doctor. Slot generation is a pure function (`services/scheduling.py`).
- **Observability.** Each request gets an `X-Request-ID`. Logs are JSON with PII redacted, and you can filter the Grafana log panel by request ID. The business counters are `bookings_total`, `payments_total` and `erp_call_duration_seconds`.

## Common tasks

```bash
make test                 # backend pytest (incl. constraint race test) + frontend vitest
make smoke                # API smoke test: ~90 checks across every flow (needs RESEND_API_KEY empty)
make e2e                  # Playwright browser tests (book -> pay -> cancel, admin, symptom checker)
make lint                 # ruff, mypy, tsc (tsc also checks frontend types against the OpenAPI contract)
make gen-client           # regenerate frontend/src/api/schema.d.ts from OpenAPI; commit it
make loadtest             # k6 mixed realistic traffic (13 min) -> Grafana "Healthcare Load Test"
make loadtest TIME_SCALE=0.1  # same profile compressed to ~80 s
make contention           # 50 VUs race for one slot: expect exactly one 201
make migration m="..."    # autogenerate an Alembic migration
```

Frontend dev with hot reload: `cd frontend && npm install && npm run dev` (http://localhost:5173, proxies to the dev-exposed backend on :8000).

## Scheduling constraints (SCRUM-21)

Admins manage duration and buffer in **Directory → Appointment types**, including global,
specialty, and doctor scopes. Duration is 5–480 whole minutes; buffer is 0–120 whole minutes.
When both doctor and specialty are selected, they must match. The seeded standard consultation
is 20 minutes with a 10-minute buffer. Missing or invalid appointment types and missing schedules
never create bookable offers.

**Directory → Doctors → Capacity per work window** sets the total number of pending or confirmed
bookings permitted in each ERP work window, shared across all appointment types. The migration
backfills existing doctors to **1**, and new doctors also default to **1** until an admin raises it.
Capacity is a positive integer. A positive ERP limit further restricts the local limit (the smaller
limit wins); an absent ERP limit uses the doctor's finite limit, while zero or invalid ERP limits
close the window. This does not allow overlapping consultations for the same doctor.

Capacity counts appointment starts in `[window start, window end)`. Cancelled and rejected
appointments release capacity. Duration plus buffer must fit completely inside the work window,
and existing reserved intervals and blocked periods are respected.

Changes apply to subsequent offers and new bookings. Existing appointment times, buffers and
statuses are preserved. Lowering capacity below existing bookings stops further offers without
cancelling those bookings. Browsing uses a short-lived cache keyed by persisted settings; booking
always rechecks the database under a doctor lock. A displayed slot is not a reservation.
Failed saves roll back settings and their audit record together and report an error.

Apply `alembic upgrade head` before starting the updated backend. Scheduling integration tests
use `TEST_DATABASE_URL`; point it only at a disposable database, since the existing overlap test
resets its schema.

## Manual shared slots

Open **Administration → Schedules**, select a doctor and date, and create a slot with start/end
times, a buffer, and capacity. For example, 08:00–08:30 with capacity 5 permits five different
patients to reserve that exact interval. Times use the configured clinic timezone; slots and their
buffers must fit within one clinic day and cannot overlap, including closed slots.

Every doctor defaults to **ERP** scheduling. Admins can prepare manual slots while ERP mode is
active, then switch the doctor to **Manual** once there are no upcoming or ongoing pending/confirmed
appointments. In Manual mode, only manually created open slots are offered. Their capacities
replace the ERP work-window limit. Appointment types continue to supply service/fee metadata;
manual slot times and buffers define the reservation interval.

Manual reservations are confirmed immediately in CareBook. They do not call the ERP, and ERP
sync, reconciliation and webhooks cannot alter them. Existing cancellation/payment/refund rules
still apply. Manual check-in/completion controls and recurring/bulk schedules are not included.

The admin list shows booked and remaining places. Booked slots retain their start/end/buffer;
capacity and open/closed state can change. Lowering capacity below occupancy preserves existing
appointments and stops new offers. One patient can hold only one active reservation per slot.
Cancelling releases a place. Availability is a short-lived offer, rechecked under database locks
when booking; stale slot versions return a conflict and the patient is prompted to select again.

Migration `0007_manual_doctor_slots` preserves existing appointments at reservation position 1
and adds per-slot positions for shared bookings. Its downgrade refuses overlapping active shared
reservations rather than deleting appointments. Apply migrations before starting the new backend.
