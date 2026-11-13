# CareBook: Healthcare Appointment Platform

A patient-facing discovery, booking and payment platform. It implements the requirements in [.claude/plans/business.md](.claude/plans/business.md) (FRD v1.2) with the stack described in [.claude/plans/implement.md](.claude/plans/implement.md). The UI follows [.claude/design/design-guidelines.md](.claude/design/design-guidelines.md). [.claude/plans/integration-status.md](.claude/plans/integration-status.md) lists which integrations are real and which are simulated.

## Quick start

```bash
cp .env.example .env        # optional; every value has a dev default
docker compose up -d --build
docker compose run --rm backend python -m app.commands.erp_cutover --apply  # bootstrap ERP catalog & open booking gate
make seed-loadtest          # optional: 200 load-test patients for k6
```

| URL | What |
|---|---|
| http://localhost:8080 | Web app |
| http://localhost:8080/api/docs | OpenAPI (Swagger) |
| http://localhost:3000 | Grafana (admin / admin), folder *Healthcare* |
| http://localhost:9090 | Prometheus |
| http://localhost:8100/docs | Mock ERP: manage catalog/slots & simulate confirm / check-in / complete (dev only) |

Seeded accounts: `admin@example.com` / `Admin12345!` and `patient@example.com` / `Patient12345!`. The demo patient has one completed appointment, so you can try the review flow straight away.

## Try the main flow

1. Sign in as the demo patient, open **Doctors**, pick a doctor, then choose a date and an open ERP-managed slot.
2. Reserve a place in the slot. CareBook holds a temporary reservation, submits the slot ID/version and booking reference to the hospital ERP, and confirms the booking once the ERP accepts (showing the booking reference with a check-in QR code and separate appointment, payment and check-in statuses).
3. Click **Pay by bank transfer** (the fee is the consultation fee synced from the hospital ERP). The payment page shows a VietQR code and the transfer content (payment code, `CB` + 8 characters). Without a real transfer, simulate the bank notification with `python scripts/sepay_fake_transfer.py <payment_code> <amount>`; the page turns to **Paid** within a few seconds. An unpaid confirmed booking is released `PAYMENT_HOLD_MINUTES` (15) after confirmation.
4. Open the demo patient's seeded completed appointment to try the review flow, or use Mock ERP Swagger (`http://localhost:8100/docs`) to simulate check-in and completion on a newly confirmed booking.

## Layout

```
backend/            FastAPI app: api/ (routers) -> services/ (logic) -> repositories/ (DB)
                    integrations/ (ERP adapters), core/ (config, logging, metrics),
                    alembic/ (migrations), tests/
frontend/           React + TS + Vite SPA, served by nginx, which also proxies /api
                    src/ (pages, components, api client), e2e/ (Playwright)
mock-erp/           Simulated hospital ERP/HIS (SQLite-backed catalog, shared slots, bookings, signed webhooks)
k6/                 Load scenarios (browse, symptoms, booking, contention, admin, mixed)
monitoring/         Prometheus, Loki, Alloy, Grafana provisioning + dashboards
postgres/init/      SQL run on first start (creates the healthcare_test database)
scripts/            api_smoke.py (the API smoke test behind `make smoke`),
                    sepay_fake_transfer.py (fake SePay "money in" webhook)
openapi.json        OpenAPI snapshot from `make openapi`; source for `make gen-client`
.claude/plans/      business.md (FRD), implement.md (implementation plan) and
                    integration-status.md (what is real and what is simulated)
.claude/design/     Design boards (HTML, PDF, PNG) and design-guidelines.md, the text spec
                    behind frontend/tailwind.config.js and frontend/src/index.css
docker-compose.yml  Full stack; docker-compose.override.yml adds dev hot reload and ports
```

## Key design points

- **Capacity protection.** Availability is revalidated under doctor/slot locks and verified by the ERP inside an SQLite transaction. PostgreSQL prevents overlapping slot intervals and protects each reservation position; shared slots permit reservations up to their ERP-configured capacity.
- **ERP-authoritative confirmation.** Bookings start as `PENDING` locally and transition to `CONFIRMED` only when the ERP accepts. Timeouts stay `PENDING` for background reconciliation; rejections or cancellations release capacity immediately.
- **Separate statuses** (BR-07). Appointment status, payment status and check-in status are tracked separately. Check-in status is written only by the ERP (BR-11).
- **ERP-managed directory and scheduling.** Hospital directory, consultation types/fees and dated shared-capacity slots are managed in the hospital ERP (`mock-erp`) and synchronized into CareBook. Admin Directory and Schedules pages are read-only, while mutation endpoints enforce `403 ErpOwnedData`.
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

## ERP-owned scheduling

Hospital directory, consultation types/fees and shared-capacity slots come from the hospital ERP.
Admins can view synchronized records, manage users/reviews/refunds and inspect audit logs.
Only the ERP may change doctor information or schedules; the backend rejects admin writes.

Before starting the updated backend against an existing database, follow the
[ERP cutover guide](docs/erp-cutover.md). The migration preserves existing data and requires an explicit,
verified cutover before new reservations are enabled. Mock ERP Swagger is available at
http://localhost:8100/docs; no separate hospital UI is needed for the demo.
