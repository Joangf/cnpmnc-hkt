# ERP ownership and migration

CareBook admins manage users, review moderation and manual refund processing, and read audit logs.
Hospital directory, consultation types/fees and shared slots are owned by the mock hospital ERP.
Directory/Schedules remain visible to admins, but their mutation APIs return `403 ErpOwnedData`.

## Deployment and existing data

Migration `0011_erp_owned_slots` adds stable ERP identities without deleting or renumbering records.
It initially closes the booking gate (`erp_sync_state.ready = false`). Keep the backend stopped while
performing cutover so bookings, incoming payments/webhooks and background jobs cannot race the export.
Retain the normal database backup before deploying. Never downgrade to discard ERP identities after cutover.

From the repository root, using your existing deployment environment:

```sh
docker compose stop backend
docker compose build backend mock-erp web
docker compose up -d mock-erp
docker compose run --rm backend python -m app.commands.erp_cutover
docker compose run --rm backend python -m app.commands.erp_cutover --apply
docker compose up -d backend web
```

The backend entrypoint applies Alembic migrations before invoking the command. The first cutover command
is a dry run; it prints counts and rolls back. `--apply` imports directory, slots and active appointments
into the persistent mock ERP, verifies mappings/bookings, mirrors the ERP snapshot locally, then opens
the booking gate. Existing payment deadlines, payments, refunds, reviews, appointment IDs and history
are preserved. No email, bank details or free-text visit reasons are sent to the mock ERP.

Exact bootstrap retries are safe. A pre-existing conflicting ERP record or overlapping legacy appointment
aborts with the gate closed; resolve the reported conflict rather than deleting records. Active legacy
window appointments get a matching slot or a new closed slot. Past/finished appointments remain local history.
Once the gate is open, cutover becomes a no-op; subsequent changes must originate in ERP.

The SQLite ERP database is stored in `mock-erp-data:/data/erp.sqlite3`. Keep this volume across restarts.
Do not use `docker compose down -v` to restart the application.

## Hospital-side demo without a separate UI

Open **http://localhost:8100/docs** (Docker publishes it on loopback only).

1. `GET /catalog` shows ERP IDs, directory data, slot versions and occupied places.
2. `PUT /directory/{kind}/{identifier}` replaces a hospital, specialty, department, doctor or appointment type.
   Body: `{"id":"the-ERP-ID","data":{...fields...}}`; foreign keys inside `data` use ERP IDs, not CareBook IDs.
   Use the matching object returned by `/catalog` as the template. Preserve its other fields when editing.
3. `PUT /slots/{identifier}` creates/updates a shared slot. Include `id`, `doctor_id`, aware `start_time` and
   `end_time`, positive `capacity`, `is_open`, and the current `version` when updating.
   The response supplies the new version. Occupied slots lock times; lowering capacity or closing
   preserves existing reservations. Overlapping intervals are rejected.
4. Use **Administration → Overview → Sync ERP data now**, or wait for the configured schedule-sync job.
   Directory and Schedules display the last successful sync. A malformed/failed snapshot does not erase data.
5. Book from a patient account. ERP confirms or rejects the request; repeated booking references are idempotent.
6. `POST /simulate/bookings/{reference}/check-in` and `/status` with `{"status":"COMPLETED"}` send signed
   webhooks to CareBook. Only completed appointments can be reviewed, once per appointment.

Demo endpoints belong to the simulated hospital service, not to CareBook admin permissions. Do not expose
this unauthenticated simulation service publicly. No separate ERP UI is included.

## Sync semantics and validation

A catalog snapshot includes every entity collection. Stable ERP IDs are upserted without changing local IDs.
Use explicit `is_active: false` / `is_open: false` to withdraw data; missing records are not hard-deleted.
The app retains local booking/payment history. Patient availability combines local reservations and the last
ERP occupancy snapshot; ERP performs the final capacity check. Patient pages refetch every 30 seconds.
ERP changes become visible after a successful periodic or manual sync, not by browser polling alone.

Focused regression suites:

```sh
# TEST_DATABASE_URL must identify a disposable PostgreSQL database.
cd backend
pytest -q tests/test_erp_owned_slots.py tests/test_mock_erp_shared.py
cd ../frontend
npm test
npm run typecheck
```

The mock-ERP test source must be alongside `backend` so its ASGI app can be exercised. These tests cover
permissions, repeated sync, rollback, shared capacity, stale versions, cancellation, webhook completion,
timeout reconciliation, persistent storage and preservation of existing reservations during cutover.
