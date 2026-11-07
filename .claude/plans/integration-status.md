# Integration status

FRD section 3.3 (assumption 4) requires the project to state which functions are simulated and which are actually integrated. This file is the record.

| Capability | Status | Implementation | Swap point |
|---|---|---|---|
| Doctor schedules / availability | **Simulated** | `mock-erp` generates Mon–Sat 08:00–11:30 and 13:30–17:00 windows (clinic time). The backend syncs them into `doctor_schedules` every 10 min. | `backend/app/integrations/erp/http.py` |
| Booking acceptance (BR-02) | **Simulated** | `mock-erp` `POST /bookings` runs its own overlap check. `MOCK_ERP_MODE=sync` confirms immediately; `async` confirms about 5 s later by webhook. `MOCK_ERP_REJECT_RATE` injects rejections. | `ErpAdapter.create_booking` |
| Status changes (confirm / complete / no-show / cancel) | **Simulated** | Pushed by `mock-erp` to `POST /api/v1/integrations/erp/events` (HMAC-signed). Trigger them manually from `http://localhost:8100/docs` → *simulate*. | `app/api/v1/integrations.py` |
| Check-in status (BR-11) | **Simulated** | Comes only from the ERP webhook (`/simulate/bookings/{ref}/check-in`). Patients can never set it. | same |
| Reconciliation | Real (platform side) | A poller resolves bookings left `PENDING` after an ERP timeout. They expire after 15 min if the ERP has no record of them. | `app/services/erp_sync.py` |
| Online payment | **Real** (VietQR + SePay) | The patient transfers to the SePay-monitored account (`SEPAY_ACCOUNT` at `SEPAY_BANK`) by scanning a VietQR image; the transfer content is the payment code. SePay reports the money by webhook (`POST /api/v1/payments/sepay-webhook`, `Authorization: Apikey <SEPAY_WEBHOOK_API_KEY>`), and a poller asks the SePay User API every `SEPAY_POLL_SECONDS` when `SEPAY_API_TOKEN` is set, so localhost works without a public URL. Unpaid confirmed bookings are released `PAYMENT_HOLD_MINUTES` after confirmation. In dev, `scripts/sepay_fake_transfer.py` stands in for the bank. | `backend/app/services/sepay.py`, `backend/app/services/payments.py` |
| Refunds | **Manual** | Always 100%, only when a paid appointment is cancelled or rejected. The patient submits their bank account; an admin pays it out from the bank app using the refund QR on the Refunds page and marks it done. Cancelling never refunds automatically. | `backend/app/services/refunds.py` |
| Notifications | Real (in-app only) | Stored in the `notifications` table. There is no email or SMS channel yet (FR-NOT-04). In dev, the password-reset token is returned in the API response instead of being emailed. | `app/services/notifications.py` |
| Symptom → specialty rules | **Placeholder content** | Rule engine is real; the seed rules and warning signs are **not clinically reviewed** (OQ-06). | `app/seed.py`, admin tooling TBD |
| Medical records (FR-HIS-03) | Not implemented | Out of MVP scope; only appointment history is shown. | n/a |

## Open questions that change the adapters

- **OQ-01/02**: real ERP API and source of truth. Implement a new `ErpAdapter`; the business logic does not change.
- **OQ-03**: pay before or after confirmation. Decided: only after confirmation, within `PAYMENT_HOLD_MINUTES`.
- **OQ-05**: payment provider. Decided: VietQR bank transfer monitored by SePay (`services/sepay.py`).
- **OQ-09**: cancellation and refund policy. `CANCELLATION_CUTOFF_HOURS`; refunds are full and manual (see above).
