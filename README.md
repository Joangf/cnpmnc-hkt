# CareBook: Healthcare Appointment Platform

A patient-facing discovery, booking and payment platform. It implements `business.md` (FRD v1.2) using the stack described in `implement.md`.

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
backend/        FastAPI app: api/ (routers) -> services/ (logic) -> repositories/ (DB)
                integrations/ (ERP + payment adapters), core/ (config, logging, metrics)
mock-erp/       Simulated hospital ERP/HIS (schedules, bookings, signed status webhooks)
mock-payment/   Sandbox payment gateway (checkout page, signed callbacks, refunds)
frontend/       React + TS + Vite SPA, served by nginx, which also proxies /api
k6/             Load scenarios (browse, symptoms, booking, contention, admin, mixed)
monitoring/     Prometheus, Loki, Alloy, Grafana provisioning + dashboards
docs/           integration-status.md: what is real and what is simulated
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
make smoke                # API smoke test: ~90 checks across every flow
make e2e                  # Playwright browser tests (book -> pay -> cancel, admin, symptom checker)
make lint                 # ruff, mypy, tsc (tsc also checks frontend types against the OpenAPI contract)
make gen-client           # regenerate frontend/src/api/schema.d.ts from OpenAPI; commit it
make loadtest             # k6 mixed realistic traffic (13 min) -> Grafana "Healthcare Load Test"
make loadtest TIME_SCALE=0.1  # same profile compressed to ~80 s
make contention           # 50 VUs race for one slot: expect exactly one 201
make migration m="..."    # autogenerate an Alembic migration
```

Frontend dev with hot reload: `cd frontend && npm install && npm run dev` (http://localhost:5173, proxies to the dev-exposed backend on :8000).
