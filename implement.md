# Tech Stack Plan: Healthcare Appointment Platform

This plan maps the FRD v1.2 to a concrete stack. Everything starts with a single `docker compose up`. It follows the FRD's main constraints: the ERP/HIS boundary is explicit, payment is mocked behind adapters, availability is revalidated at booking time, and audit logging is built in.

## 1. Architecture overview

```
                ┌──────────────┐
  Browser ────► │  web (nginx) │──► React SPA (static)
                │  :80         │──► /api/*  ──► backend (FastAPI :8000)
                └──────────────┘                 │
                                                 ├──► postgres
                                                 ├──► redis (rate limit, idempotency, cache)
                                                 ├──► mock-erp (FastAPI :8100)    ← adapter
                                                 └──► mock-payment (FastAPI :8200) ← adapter
                                                          │ webhook callback
  Monitoring:                                             ▼
  backend /metrics ──► Prometheus ──┐               backend /payments/callback
  container stdout ──► Alloy ──► Loki ──► Grafana :3000 (dashboards + logs)
  k6 ──(remote write)──► Prometheus
```

nginx serves the SPA and reverse-proxies `/api`. The browser therefore uses a single origin, so you don't need CORS configuration and auth cookies stay simple.

## 2. Component choices

| Layer | Choice | Why / FRD link |
|---|---|---|
| Frontend | React + TypeScript + Vite, React Router, TanStack Query, react-hook-form + zod, Tailwind (or MUI) | Responsive SPA (NFR-07); zod mirrors backend validation (FR-PRO-03) |
| API client | Generated from OpenAPI via `openapi-typescript` + `openapi-fetch` (or Orval) | The frontend's types always match the backend contract |
| Backend | FastAPI (Python 3.12), Pydantic v2, SQLAlchemy 2 (async) + asyncpg, Alembic | OpenAPI is built in at `/docs`, `/redoc`, `/openapi.json` |
| Auth | Short-lived JWT access tokens plus a refresh token in an httpOnly cookie; Argon2 hashing (`pwdlib`) | NFR-01, NFR-02, RBAC for Guest/Patient/Admin |
| Database | PostgreSQL 16 | Transactions and exclusion constraints for double-booking prevention |
| Cache / misc | Redis | Rate limiting on login, idempotency keys for booking and payment, availability cache |
| ERP/HIS | `mock-erp` service behind an `ErpAdapter` interface | §3.3 assumption 3 and recommendation 6; you can swap it for a real API later |
| Payment | `mock-payment` service behind a `PaymentGateway` adapter, with HMAC-signed callbacks | FR-PAY-03/04; callback validation (NFR-11) |
| Metrics | `prometheus-fastapi-instrumentator` + Prometheus | Total requests, req/s, p95, p99 |
| Logs | `structlog` JSON to stdout → Grafana Alloy → Loki | Backend logs searchable in Grafana |
| Monitoring UI | Grafana with provisioned datasources and dashboards | The "monitoring site" |
| Load testing | k6 | Realistic user traffic |

## 3. Backend design

Use a layered structure that follows NFR-09:

```
backend/app/
  api/v1/          # routers: auth, profile, directory, availability, appointments,
                   #          symptoms, payments, reviews, notifications, admin
  schemas/         # Pydantic request/response models (drive OpenAPI)
  services/        # business logic: scheduling, booking, recommendation, review eligibility
  repositories/    # DB access
  integrations/    # erp/ (base.py, mock.py, http.py), payment/ (base.py, mock.py)
  core/            # config, security, logging, middleware, metrics
  models/          # SQLAlchemy entities (FRD §9)
```

**OpenAPI quality.** Tag every router, give every route a `response_model`, name operations explicitly (`operation_id="createAppointment"`), and document error responses (`409 SlotTaken`, `422`, `503 ErpUnavailable`). This produces clean generated client function names. It also gives you a proper error contract for NFR-12.

**Double-booking protection (FR-BOOK-05, NFR-06).** Rely on the database, not just application checks. A Postgres exclusion constraint rejects overlapping bookings atomically, even when two requests arrive in the same millisecond:

```sql
CREATE EXTENSION btree_gist;
ALTER TABLE appointment ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_with_buffer) WITH &&)
  WHERE (status IN ('PENDING','CONFIRMED'));
```

The booking service should then work in this order. It recomputes availability inside a transaction and inserts the appointment as `PENDING`. If the constraint is violated, it returns `409`. Otherwise it calls `ErpAdapter.create_booking()`, and only flips the appointment to `CONFIRMED` once the ERP accepts it (BR-02). An `Idempotency-Key` header prevents double-submits.

**Scheduling.** Slot generation follows FRD §4.4.1. Durations come from `AppointmentType`, with a configurable increment and buffer, and a slot is offered only if the full interval fits. Keep this logic as a pure function so it is easy to unit test.

**Status separation (BR-07).** Use `appointment.status` and `payment.status` as separate enums, plus `check_in_status`, which is written only by the ERP sync (BR-11).

**ERP sync.** Use a webhook endpoint (`/integrations/erp/events`) for the mock ERP to push status changes. A background poller can serve as a fallback. Each status change writes an `AuditLog` row and a `Notification` (FR-NOT-02, NFR-10).

**Logging middleware.** Each request gets a `request_id`, which is returned in the `X-Request-ID` header. Each log line includes `request_id`, `method`, `route`, `status`, `duration_ms` and `user_id` (but not email or name). Because this is healthcare data, add a redaction processor that strips PII fields (phone, DOB, symptoms text, tokens) from logs (NFR-03, NFR-04).

## 4. Monitoring

Grafana is provisioned from files, so the dashboard exists on first boot with no manual setup.

| Panel | PromQL |
|---|---|
| Total requests (selected range) | `sum(increase(http_requests_total[$__range]))` |
| Requests/s | `sum(rate(http_requests_total[1m]))`, optionally `by (handler)` |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |
| p99 latency | same with `0.99` |
| Error rate | `sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))` |
| Latency by endpoint | p95 `by (le, handler)` as a table |

Set explicit histogram buckets (e.g. 5 ms → 5 s). The defaults are too coarse for accurate p99.

The dashboard should also include two log panels: a Loki logs panel (`{service="backend"} | json`) and a logs-volume-by-level panel. Add a "Request ID" variable so you can click from a slow request straight to its log lines. A second dashboard can show k6 metrics (virtual users, iteration rate, k6-side p95/p99) during load tests.

You can add some business metrics cheaply as custom counters: `bookings_total{result="confirmed|conflict|rejected"}`, `payments_total{status}`, and `erp_call_duration_seconds`. These also cover FR-RPT-01/02 from an operations angle.

## 5. k6 traffic simulation

```
k6/
  lib/        # auth.js (login + token reuse), data.js (seed IDs), checks.js
  scenarios/
    guest_browse.js      # hospitals → departments → doctors → doctor detail
    symptom_flow.js      # pick symptoms → recommendations → browse matched doctors
    patient_booking.js   # login → availability → book → pay (mock) → view appointment
    slot_contention.js   # many VUs racing for the same slot; expect exactly one 201, rest 409
    admin_ops.js         # light admin listing / moderation
  mixed_realistic.js     # weighted mix of the above
  thresholds.json        # e.g. p(95)<300ms browse, p(99)<1s booking, errors<1%
```

For realistic traffic, use the `ramping-arrival-rate` executor to model daily peaks rather than fixed VUs. Weight the mix roughly 70% guest browsing, 15% symptom flow, 12% booking and 3% admin. Add randomized think time between steps (`sleep(randomBetween(1,5))`). Load test users come from a seed script (`make seed-loadtest`).

The `slot_contention` scenario is worth keeping. It shows that the exclusion constraint actually works under concurrency, which is good evidence for an academic report.

Run k6 as a compose service under a profile with `--out experimental-prometheus-rw`, so its results appear in Grafana next to the backend metrics:

```
docker compose --profile loadtest run k6 run /scripts/mixed_realistic.js
```

## 6. Docker Compose layout

```
repo/
  docker-compose.yml          # core + monitoring
  docker-compose.override.yml # dev: hot reload, source mounts, exposed ports
  .env.example
  Makefile                    # up, down, migrate, seed, test, loadtest, gen-client
  frontend/   (Dockerfile: node build → nginx)
  backend/    (Dockerfile: uv/pip, uvicorn; entrypoint runs alembic upgrade)
  mock-erp/
  mock-payment/
  k6/
  monitoring/
    prometheus/prometheus.yml
    loki/config.yml
    alloy/config.alloy        # docker log discovery → Loki, label by compose service
    grafana/provisioning/{datasources,dashboards}/ + dashboards/*.json
```

The services are `web`, `backend`, `postgres`, `redis`, `mock-erp`, `mock-payment`, `prometheus`, `loki`, `alloy`, `grafana`, and `k6` (profile: loadtest). Give postgres and redis healthchecks and make the backend use `depends_on: condition: service_healthy` so startup is deterministic. Persist postgres, prometheus, loki and grafana data in named volumes, and pin image versions.

The exposed ports in dev would be: the app on `:8080`, API docs on `:8080/api/docs`, Grafana on `:3000`, and Prometheus on `:9090`.

## 7. Quality and delivery

On the backend, use pytest with httpx `AsyncClient` against a Postgres test container, with unit tests for slot generation and the recommendation rules. On the frontend, use Vitest and React Testing Library, plus a few Playwright end-to-end tests for the booking flow.

A CI job should run lint, the tests, and a contract check: regenerate the TypeScript client and fail if the diff is non-empty. That catches any drift between frontend and backend. A short k6 smoke run against a compose stack in CI is optional.

Ruff, mypy, ESLint and Prettier can handle formatting and linting. Keep a `docs/integration-status.md` that states what is mocked and what is real, as FRD §3.3 assumption 4 requires.

## 8. Suggested build order

1. Compose skeleton, monitoring and the logging middleware, so you get observability from day one.
2. Auth, profile and directory endpoints, with the generated client wired into the SPA.
3. Scheduling, the booking flow and the mock ERP, together with the contention test.
4. Mock payment with callbacks.
5. Reviews, notifications and admin features.
6. Full k6 scenarios, threshold tuning and report screenshots.

FRD open questions OQ-01, OQ-03 and OQ-05 mostly affect the adapters. The adapter boundary lets you start building now and swap implementations later.

Would you like me to scaffold the repo next, starting with the compose file, monitoring provisioning and the FastAPI skeleton? That would involve generating files, so I'll wait for your go-ahead.