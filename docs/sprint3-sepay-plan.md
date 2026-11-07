# Sprint 3 — Thanh toán VietQR + SePay: implementation plan

Phạm vi: SCRUM-27, 28, 29, 30, 31, 32. Mốc code: `origin/master` 270566f.
Mục tiêu duy nhất: app chạy được, đủ tính năng, demo được bằng tiền thật (2.000đ) qua ngrok.
Mọi phần "cho đẹp" đều bị cắt.

---

## 1. Những gì đã chốt

| # | Quyết định |
|---|---|
| D1 | Bỏ hẳn `mock-payment` và lớp adapter `PaymentGateway`. Chỉ có SePay. |
| D2 | Cấu hình bằng env, không có bảng cấu hình: `SEPAY_ACCOUNT=SEPNK33418`, `SEPAY_BANK=OCB`, `SEPAY_ACCOUNT_NAME=NGUYEN TAN KHANG`, `SEPAY_WEBHOOK_API_KEY`, `SEPAY_API_TOKEN`, `PAYMENT_CODE_PREFIX=CB`, `PAYMENT_HOLD_MINUTES=15`, `SEPAY_POLL_SECONDS=15`. Giá trị thật đặt ở default trong compose và `.env.example`, không nằm trong `config.py`. |
| D3 | Mỗi lần thanh toán có một **mã thanh toán** riêng: `CB` + 8 ký tự `[A-Z0-9]`, UNIQUE. Mã này chính là nội dung chuyển khoản. |
| D4 | QR là ảnh `https://vietqr.app/img?acc=SEPNK33418&bank=OCB&amount=<amount>&des=<payment_code>`. Backend tạo URL, frontend chỉ việc hiện `<img>`. |
| D5 | Ghi nhận tiền về bằng 2 đường cùng gọi `apply_transfer()`: (a) webhook `POST /api/v1/payments/sepay-webhook`, header `Authorization: Apikey <key>`; (b) job hỏi SePay User API mỗi 15 giây, chỉ chạy khi có `SEPAY_API_TOKEN` và đang có payment chờ. Có đường (b) thì localhost chạy được không cần URL public. Đường (a) dùng khi demo qua ngrok. |
| D6 | **Giữ slot chờ thanh toán.** Khi lịch chuyển sang CONFIRMED và `fee_amount > 0`, đặt `appointment.payment_due_at = now + PAYMENT_HOLD_MINUTES`. Job hết hạn tự huỷ lịch (huỷ ERP, chuyển CANCELLED, nguồn SYSTEM) nếu quá `payment_due_at + 60s` mà chưa PAID. Slot được giải phóng vì ràng buộc `no_overlap` chỉ áp cho PENDING/CONFIRMED. |
| D7 | QR hết hạn đúng lúc lịch hết hạn: `payment.expires_at = appointment.payment_due_at`. Chỉ có một nút chỉnh là `PAYMENT_HOLD_MINUTES`. |
| D8 | Chỉ thanh toán khi lịch đã CONFIRMED. Xoá cờ `PAYMENT_REQUIRES_CONFIRMATION`. Mock ERP chế độ sync xác nhận ngay nên người dùng không phải chờ. |
| D9 | `PaymentStatus`: `UNPAID` (chỉ là giá trị suy ra, không lưu), `PENDING`, `PAID`, `EXPIRED`, `REFUNDED`. Bỏ `FAILED`; migration chuyển các dòng FAILED cũ thành EXPIRED. |
| D10 | Khớp tiền: đúng mã và đúng số tiền thì PAID. Sai số tiền thì giữ PENDING, ghi `failure_reason`. Tiền về cho payment đã EXPIRED, kể cả khi lịch đã bị huỷ, vẫn PAID vì tiền thật đã về; bệnh nhân sau đó yêu cầu hoàn. Cùng giao dịch SePay gửi lại (`provider_reference` trùng) thì bỏ qua. Chuyển khoản lần hai cho payment đã PAID: ghi audit `payment.duplicate_transfer` rồi bỏ qua, bệnh viện tự xử lý trên SePay. |
| D11 | Bấm "Thanh toán" nhiều lần: nếu đã có payment PENDING còn hạn thì trả lại chính nó. Bỏ Idempotency-Key Redis cho payment (vẫn giữ cho booking). |
| D12 | **Hoàn tiền** để thẳng trên bảng `payments`, không có bảng `refunds`. Luôn hoàn 100%, mỗi payment một yêu cầu đang mở. `refund_status`: `REQUESTED → COMPLETED / REJECTED`; bị REJECTED thì được gửi lại. Điều kiện: payment PAID và lịch ở trạng thái CANCELLED hoặc REJECTED. |
| D13 | Huỷ lịch **không** tự hoàn tiền. Bỏ `refund_if_paid` và `REFUND_ON_CANCELLATION`. Huỷ lịch và hoàn tiền là 2 thao tác riêng (đúng AC 31-7). |
| D14 | Admin hoàn tiền thủ công: trang Refunds hiện QR `https://img.vietqr.io/image/<bin>-<acc>-compact2.png?amount=..&addInfo=<refund_reference>&accountName=..` tới tài khoản bệnh nhân. Admin chuyển khoản bằng app OCB rồi bấm "Đã chuyển" (có thể nhập mã giao dịch) hoặc "Từ chối" kèm lý do. Không xác nhận qua webhook tiền ra, vì OCB cần gói SMS. |
| D15 | Ngân hàng của bệnh nhân: frontend lấy danh sách từ `https://api.vietqr.io/v2/banks`, lưu `bin` và `shortName`. Lấy danh sách lỗi thì cho nhập tay. |
| D16 | Seed thêm loại khám `"Payment Test (2,000 VND)"`, phí 2000, áp dụng cho mọi bác sĩ. |
| D17 | Demo: `ngrok http 8080` rồi đặt webhook SePay là `https://<ngrok>/api/v1/payments/sepay-webhook`, xác thực API Key. |

## 2. Kết quả audit

### 2a. Ảnh hưởng tới các luồng khác (phải xử lý)

| Luồng | Hiện trạng | Việc phải làm | Ai |
|---|---|---|---|
| Đặt lịch / giữ slot | Không có hạn thanh toán: lịch CONFIRMED giữ slot tới tận giờ khám dù không trả tiền | D6: thêm `payment_due_at`, hook trong `booking.transition()` khi CONFIRMED, thêm job hết hạn | A |
| ERP xác nhận chậm (async, webhook, reconcile) | Mọi đường đều đi qua `booking.transition()` | Đặt hạn trong `transition()` để cả 3 đường đều có hạn | A |
| Bệnh nhân huỷ lịch | Huỷ xong gọi `refund_if_paid` (hoàn tự động qua mock) | Bỏ hoàn tự động. Payment PENDING của lịch chuyển EXPIRED. Sửa câu chữ ở CancelCard | A (backend), B (câu chữ) |
| ERP/bệnh viện từ chối hoặc huỷ sau khi đã trả tiền | Payment giữ PAID, không có gì xảy ra | Lịch CANCELLED/REJECTED + payment PAID thì `can_request_refund=true` | C |
| Tiền về sau khi lịch đã bị huỷ do quá hạn | Không xảy ra được (mock) | D10: vẫn PAID và cho phép yêu cầu hoàn | A |
| Hết hạn và tiền về cùng lúc | — | Job chạy theo thứ tự: hỏi SePay trước, rồi mới xét hết hạn. Có thêm 60s ân hạn. Khoá dòng (`FOR UPDATE`) cả trên appointment lẫn payment | A |
| Bộ nhớ đệm availability | Huỷ lịch có gọi `availability.invalidate` | Job hết hạn cũng phải gọi | A |
| Báo cáo admin `payments_by_status` | GROUP BY theo status | Tự hiện EXPIRED, không cần sửa. Nhãn ở dashboard dùng `humanize`, vẫn đúng | — |
| Grafana `payments_total{status}` | Có trong dashboard | Vẫn tăng metric `PAYMENTS` | A |
| Thông báo | Dùng `PAYMENT_RESULT` | Dùng lại cho: đã nhận tiền, sai số tiền, hoàn xong, hoàn bị từ chối. Thông báo huỷ do quá hạn đi theo `transition()` kèm lý do | A, C |
| nginx | Có `location /mock-payment/` | **Phải xoá**, nếu không nginx không khởi động được khi service mock-payment không còn | A |
| CSP | Không có `img-src` | Ảnh QR từ vietqr.app / img.vietqr.io không bị chặn | — |
| `PUBLIC_BASE_URL` | Backend chỉ dùng cho return URL của mock | Xoá khỏi config backend. Script vẫn đọc từ env | A |
| Cookie qua ngrok (https) | `cookie_secure` | Không ảnh hưởng | — |
| `scripts/api_smoke.py` | Đi qua trang checkout mock, `/simulate`, mong REFUNDED sau khi huỷ | Viết lại phần thanh toán bằng webhook giả. Phần hoàn tiền làm theo D12–D14 | A, sau đó C |
| `k6/scenarios/patient_booking.js:60-72` | Gọi `/mock-payment/.../simulate` | Gửi webhook giả có Apikey | A |
| `frontend/e2e/flows.spec.ts:53-105` | Trang sandbox, `/payments/result`, mong 'Payment: Refunded' sau khi huỷ | Viết lại: trang QR → webhook giả qua `request.post` → 'Payment: Paid' → huỷ → yêu cầu hoàn → admin hoàn | C (cuối cùng) |
| `backend/tests` | Chưa test nào đụng payment | Thêm `test_payments.py` (A) và `test_refunds.py` (C) | A, C |
| Docs | README:34,39; `.claude/plans/integration-status.md:12,20-22` | Cập nhật mô tả | A |

### 2b. Ponytail-audit (phần cắt bỏ, cắt nhiều nhất xếp trước)

```
delete: service mock-payment (app.py, Dockerfile, requirements). Không thay bằng gì, test dùng webhook giả. [mock-payment/, docker-compose.yml:68-77,89-90,105-106, docker-compose.override.yml:31-33]
yagni: interface PaymentGateway chỉ có 1 bản cài đặt, kèm factory, app.state và GatewayDep. Thay bằng module services/sepay.py chỉ có hàm. [integrations/payment/*, integrations/__init__.py:21-27, api/deps.py:67-72, main.py:19,58,66, booking.py:36,349]
delete: refund_if_paid (hoàn tự động khi huỷ) cùng REFUND_ON_CANCELLATION. Thay bằng hoàn thủ công D12-D14. [services/payments.py:196-245, config.py, compose:20]
delete: Idempotency-Key Redis cho payment. Thay bằng dùng lại payment PENDING còn hạn (D11). [services/payments.py:34-56, api/v1/payments.py:28, endpoints.ts:81-82]
delete: PaymentResultPage (trang quay về sau redirect). Thay bằng PaymentPage có QR và tự cập nhật. [frontend/src/pages/PaymentResultPage.tsx, App.tsx:21,48]
delete: cột provider, checkout_url, last_event_id; trạng thái FAILED; schema PaymentInitResponse. Thay bằng PaymentOut cho mọi response. [models/payment.py, schemas/payments.py]
delete: config payment_base_url, payment_webhook_secret, payment_timeout_seconds, payment_requires_confirmation, public_base_url; lỗi PaymentGatewayUnavailable. [config.py:55-63, errors.py:68-71, compose:12-14,18, .env.example:11-13,30-32]
delete: proxy /mock-payment. [frontend/nginx.conf:24-28, frontend/vite.config.ts:11-14]
yagni (không làm): bảng bank_transactions, bảng refunds, hoàn một phần, bảng payment_accounts/refund_policies, trạng thái hoàn APPROVED/PROCESSING, tham số ?refresh=true.
giữ lại: core/security.verify_signature (ERP dùng), services/idempotency.py (booking dùng), metric PAYMENTS (Grafana dùng).
net: khoảng -600 dòng (mock-payment 162, adapter 162, phần cũ của payments.py khoảng 200, PaymentResultPage 59), bỏ 1 service docker và 0 dependency mới (httpx đã có sẵn).
```

## 3. Hợp đồng chung (Phase 0 tạo ra, sau đó đóng băng)

### 3a. DB: migration `backend/alembic/versions/0007_sepay_payments.py` (down_revision `0006_drop_doctor_fee`)

`payments`:
- xoá cột `provider`, `checkout_url`, `last_event_id`
- thêm `payment_code VARCHAR(16) NOT NULL UNIQUE` (các dòng cũ backfill `'LEGACY' || id`)
- thêm `expires_at TIMESTAMPTZ NULL`
- giữ `provider_reference VARCHAR(64) UNIQUE`, giờ dùng để lưu `id` giao dịch SePay
- thêm `refund_status VARCHAR(32) NULL`, `refund_reference VARCHAR(16) UNIQUE NULL`, `refund_bank_bin VARCHAR(8)`, `refund_bank_name VARCHAR(64)`, `refund_account_number VARCHAR(32)`, `refund_account_name VARCHAR(128)`, `refund_reason VARCHAR(500)` (lý do bệnh nhân ghi), `refund_note VARCHAR(500)` (lý do từ chối hoặc mã giao dịch admin nhập), `refund_requested_at TIMESTAMPTZ`. Cột `refunded_at` đã có sẵn.
- `UPDATE payments SET status='EXPIRED' WHERE status='FAILED'`

`appointments`: thêm `payment_due_at TIMESTAMPTZ NULL` và index `(status, payment_due_at)`.

### 3b. Enum (`models/enums.py`)
```python
class PaymentStatus(StrEnum): UNPAID, PENDING, PAID, EXPIRED, REFUNDED
class RefundStatus(StrEnum):  REQUESTED, COMPLETED, REJECTED
```

### 3c. API (OpenAPI là nguồn sự thật; frontend sinh `schema.d.ts` từ đây)

`PaymentOut` dùng cho mọi response về payment:
```
id, appointment_id, booking_reference, status: PaymentStatus, amount, currency,
payment_code, expires_at|null, qr_image_url, bank_code, account_number, account_name,
provider_reference|null, failure_reason|null, paid_at|null, created_at,
refund_status: RefundStatus|null, refund_reference|null, refund_bank_name|null,
refund_account_number|null, refund_account_name|null, refund_reason|null, refund_note|null,
refund_requested_at|null, refunded_at|null
```
`AdminRefundOut = PaymentOut + patient_name, patient_email, refund_qr_image_url|null`

| Method + path | operationId | Body | Trả về | Lỗi | Ai |
|---|---|---|---|---|---|
| POST `/appointments/{id}/payments` | initiatePayment | — | 201 PaymentOut (dùng lại PENDING còn hạn) | 404; 409 `PaymentNotRequired` / `PaymentNotAllowed` / `AlreadyPaid` / `PaymentWindowClosed` | A |
| GET `/payments/{id}` | getPayment | — | PaymentOut (chỉ chủ lịch xem được) | 404 | A |
| POST `/payments/sepay-webhook` | receiveSepayWebhook | JSON webhook SePay | 200 `{"success": true}` | 401 `InvalidApiKey` | A |
| POST `/payments/{id}/refund-request` | requestRefund | `{bank_bin, bank_name, account_number, account_name, reason?}` | PaymentOut | 404; 409 `RefundNotAllowed` / `RefundAlreadyRequested` | C |
| GET `/admin/refunds?refund_status=&page=&page_size=` | adminListRefunds | — | Page[AdminRefundOut] | 401/403 | C |
| POST `/admin/refunds/{payment_id}/complete` | adminCompleteRefund | `{note?}` | AdminRefundOut | 404; 409 `InvalidState` | C |
| POST `/admin/refunds/{payment_id}/reject` | adminRejectRefund | `{reason}` | AdminRefundOut | 404; 409 `InvalidState` | C |

Xoá `POST /payments/callback`.

Thêm vào `AppointmentSummary`: `payment_due_at|null`.
Thêm vào `AppointmentDetail`: `can_request_refund: bool`.
`PaymentSummary` (trong `AppointmentDetail.payments`): thêm `payment_code`, `expires_at`, `refund_status`.

Định dạng webhook SePay (JSON): `id:int, gateway, transactionDate "YYYY-MM-DD HH:MM:SS" (giờ VN), accountNumber, subAccount|null, code|null, content, transferType "in"|"out", transferAmount:int, accumulated, referenceCode, description`.

### 3d. Phase 0 làm sẵn những gì (một commit trên branch nền)
Backend:
- Model, migration và enum như 3a/3b.
- `schemas/payments.py` (PaymentOut, AdminRefundOut, RefundRequestIn, RefundCompleteIn, RefundRejectIn, SepayWebhookIn) và `schemas/appointments.py`.
- `presenters.payment_out()`, `admin_refund_out()` và `_summary_fields` / `appointment_detail` bản cuối cùng. Riêng `can_request_refund` gọi `policies.can_request_refund()`, Phase 0 viết luôn hàm này.
- Field mới trong `config.py`, mục SePay trong compose và `.env.example`, dòng seed loại khám 2.000đ.
- `api/v1/payments.py` và file mới `api/v1/refunds.py` đủ mọi endpoint ở 3c với đúng chữ ký và response_model, phần thân `raise NotImplementedError`. Đăng ký router.

Frontend:
- Sinh lại `schema.d.ts`, cập nhật `types.ts`, `endpoints.ts`, `contract.ts`.
- Tạo file stub: `pages/PaymentPage.tsx`, `components/RefundPanel.tsx`, `pages/admin/AdminRefundsPage.tsx`.
- Nối dây: `App.tsx` thêm route `payments/:id` và `admin/refunds`, xoá route `payments/result` và file PaymentResultPage. `AdminNav.tsx` thêm mục Refunds. `AppointmentDetailPage` gắn `<RefundPanel appointment={a} onDone={refresh} />`.

Phase 0 phải pass `ruff`, `mypy` và `npm run typecheck`. App phải khởi động được: endpoint stub trả 500, các luồng cũ vẫn chạy.

**Phase 0 đã làm thêm so với dự kiến** (để A khỏi phải đụng):
- Gỡ toàn bộ gateway cũ: `integrations/payment/`, `build_payment_gateway`, `GatewayDep`, `app.state.payment_gateway`, lỗi `PaymentGatewayUnavailable`, config cũ (`payment_*`, `public_base_url`, `internal_base_url`, `refund_on_cancellation`, `payment_requires_confirmation`).
- `booking.cancel_appointment` không còn tham số gateway và không còn gọi `refund_if_paid`. Có comment đánh dấu chỗ A chuyển payment PENDING sang EXPIRED.
- Gỡ `mock-payment/` khỏi repo, compose, override, nginx, vite. `.env.example` có mục SePay.
- `services/sepay.py` đã có `payment_qr_url()` và `refund_qr_url()`, presenter dùng chúng.
- `services/payments.py` và `services/refunds.py` là skeleton đúng chữ ký (thân `raise NotImplementedError`). Route ở `api/v1/payments.py` và `api/v1/refunds.py` đã hoàn chỉnh.
- `policies.py` đã có bản cuối của `can_pay` (có hạn thanh toán, chỉ khi CONFIRMED), `refundable_payment()` và `can_request_refund()` (thêm điều kiện chưa check-in, theo commit c0abc76 trên master).
- Seed: hàm `_ensure_appointment_types()` thêm các loại khám còn thiếu theo tên, nên DB đã seed sẵn cũng có loại 2.000đ.
- Frontend: `PaymentResultPage` đã xoá; PaymentCard tối giản (gọi `pay`, điều hướng sang `/payments/:id`). Trang stub `PaymentPage`, `RefundPanel`, `AdminRefundsPage` đã nối route, nav và chỗ gắn panel. `npm ci` và `npm run build` đã chạy (sửa lỗi trang web 500 do `frontend/dist` rỗng).
- Stack chung `cnpmnc-qa` (port 8080) đã dựng lại với override: backend `--reload`, web mount `frontend/dist`.

**File đóng băng sau Phase 0** (muốn sửa thì làm theo quy trình ở mục 6): migration 0007, `models/payment.py`, `models/appointment.py`, `models/enums.py`, `schemas/payments.py`, `schemas/appointments.py`, `api/presenters.py`, `core/config.py`, `services/policies.py`, `api/v1/refunds.py`, `frontend/src/api/*`, `App.tsx`, `AdminNav.tsx`.

## 4. Chia việc cho 3 session (mỗi file chỉ có một chủ)

### Session A: lõi thanh toán (SCRUM-28, 29 và phần giữ slot của 27)
Prefix commit: `SCRUM-28:` / `SCRUM-29:`.

| File | Việc |
|---|---|
| `backend/app/services/sepay.py` (Phase 0 đã có 2 hàm tạo URL QR) | Thêm: `new_payment_code()` dùng `secrets`; `extract_code(code, content)` bằng regex `PREFIX[A-Z0-9]{8}` trên chuỗi đã viết hoa và bỏ khoảng trắng; `check_api_key(header)` dùng `hmac.compare_digest`; `async fetch_transactions(since: datetime)` gọi `GET {SEPAY_API_BASE}/transactions/list?transaction_date_min=..&limit=200`, header `Authorization: Bearer <token>`, trả `list[BankTransfer]` (các field `id, amount_in, transaction_content, code, transaction_date`). Chỉ dùng hàm và một dataclass `BankTransfer`; không viết class adapter. |
| `backend/app/services/payments.py` | Viết lại. `initiate_payment(session, patient, appointment_id)`: kiểm quyền sở hữu, phí > 0, lịch CONFIRMED, chưa PAID; nếu `payment_due_at < now` thì báo `PaymentWindowClosed`; dùng lại PENDING còn hạn; nếu không thì tạo payment mới với `expires_at = payment_due_at`. `apply_transfer(session, t: BankTransfer) -> str` theo D10: khoá dòng payment theo `payment_code`, ghi audit, gửi thông báo, tăng metric `PAYMENTS`. `handle_webhook(session, body, headers)`. `sync_transfers(session) -> bool`: no-op nếu không có token hoặc không có payment PENDING / EXPIRED trong 24 giờ qua. `expire_unpaid(session, redis, erp) -> bool` theo D6: chọn `FOR UPDATE SKIP LOCKED`; ERP lỗi thì bỏ qua lịch đó, lần sau thử lại; chuyển payment PENDING thành EXPIRED. `get_for_patient` giữ nguyên. Xoá `refund_if_paid`. |
| `backend/app/repositories/payments.py` | `get_by_code_for_update`, `pending_or_recent(session, since)` |
| `backend/app/repositories/appointments.py` | `list_payment_overdue(session, before)`: CONFIRMED, `payment_due_at < before`, không có payment PAID/REFUNDED, có `FOR UPDATE SKIP LOCKED` |
| `backend/app/api/v1/payments.py` | Route đã xong ở Phase 0; chỉ sửa nếu cần. Webhook luôn trả `{"success": true}` khi key đúng, kể cả khi không khớp mã, để SePay không gửi lại. |
| `backend/app/services/booking.py` | Trong `transition()`: khi `new_status == CONFIRMED` và `fee_amount > 0` thì đặt `payment_due_at`. Tách phần huỷ thành `cancel(session, redis, erp, appointment, *, reason, source, actor_id=None)` để `cancel_appointment` (bệnh nhân) và `expire_unpaid` cùng dùng; hàm này chuyển payment PENDING thành EXPIRED. (Phase 0 đã bỏ gateway và `refund_if_paid`.) |
| `backend/app/services/jobs.py` | Thêm job `"payments"` mỗi `SEPAY_POLL_SECONDS`: `await sync_transfers(s)` rồi `await expire_unpaid(s, redis, erp)` |
| `backend/app/services/jobs.py` cần `redis`/`erp` | `start_background_jobs(app)` đã có `app.state.erp`; redis lấy từ `app.core.redis.redis_client` |
| `scripts/sepay_fake_transfer.py` (mới) | `python scripts/sepay_fake_transfer.py <payment_code> <amount> [--base http://localhost:8080] [--id N]`: gửi webhook giả với `Apikey $SEPAY_WEBHOOK_API_KEY` (mặc định `dev-sepay-key`) |
| `scripts/api_smoke.py` | Viết lại khối thanh toán (:179, :212-235, :280-297, :317-320) dùng webhook giả. Khối huỷ+hoàn (:261-278) đổi thành: huỷ xong thì vẫn `PAID` và `can_request_refund`; C sẽ viết thêm phần hoàn. |
| `k6/scenarios/patient_booking.js:60-72` | Gửi webhook giả |
| `backend/tests/test_payments.py` (mới) | Đủ các nhánh: khớp, sai số tiền, gửi lặp, tiền về trễ sau EXPIRED, sai key, dùng lại PENDING, quá hạn thì huỷ lịch và giải phóng slot, ERP lỗi thì lần sau thử lại. Theo mẫu fixture của `test_scheduling_integration.py`. |
| `README.md`, `.claude/plans/integration-status.md` | Cập nhật mục thanh toán |

**Mốc A1** (làm sớm nhất có thể, rồi nhắn B): initiate, get và webhook chạy thật trên branch nền.

### Session B: giao diện thanh toán (SCRUM-27, 30)
Prefix commit: `SCRUM-30:` / `SCRUM-27:`. Chỉ đụng frontend. Session B chạy `npm run build -- --watch` cho cả nhóm (mục 5).

| File | Việc |
|---|---|
| `frontend/src/pages/PaymentPage.tsx` | Route `/payments/:id`. Gồm: ảnh QR `qr_image_url`; thẻ thông tin (ngân hàng, số TK, chủ TK, số tiền, nội dung = `payment_code`), mỗi dòng có nút copy dùng `navigator.clipboard`; đồng hồ đếm ngược tới `expires_at`; `useQuery(refetchInterval: 3000 khi PENDING)`. PAID thì hiện màn hình thành công và link tới lịch hẹn. EXPIRED thì đọc lịch hẹn: nếu `can_pay` thì có nút "Tạo mã mới" (gọi `pay` rồi điều hướng sang payment mới), nếu không thì báo "Lịch đã huỷ do quá hạn thanh toán". Có `failure_reason` (sai số tiền) thì hiện Notice. Lỗi mạng thì hiện ErrorAlert và nút thử lại, trạng thái hiện tại giữ nguyên. Ghi rõ "Hệ thống chỉ xác nhận khi ngân hàng báo tiền về". |
| `frontend/src/pages/AppointmentDetailPage.tsx` | PaymentCard: nút "Thanh toán bằng chuyển khoản" → `api.appointments.pay(id)` → `navigate('/payments/'+res.id)`. Nếu đang có payment PENDING thì nút đổi thành "Tiếp tục thanh toán". Hiện "Thanh toán trước {giờ} để giữ lịch" khi có `payment_due_at`. Bỏ `newIdempotencyKey`. Bảng lịch sử payment hiện thêm `payment_code` và EXPIRED. CancelCard: khi PAID đổi câu thành "Huỷ lịch không tự hoàn tiền. Sau khi huỷ bạn có thể gửi yêu cầu hoàn tiền." Polling đã có sẵn (:26-29), giữ nguyên. **Không** đụng dòng `<RefundPanel …/>`. |
| `frontend/src/pages/AppointmentsPage.tsx` | Nhắc "Cần thanh toán trước HH:mm" khi CONFIRMED, chưa PAID và có `payment_due_at` |
| `frontend/src/components/StatusBadge.tsx` | Thêm style EXPIRED; bỏ FAILED (vẫn còn ở dòng 20) |
| `frontend/src/pages/admin/AdminDashboardPage.tsx` | Chỉ sửa nếu còn chỗ nhắc FAILED |

Phát triển giao diện trước dựa trên hợp đồng. Khi A nhắn mốc A1 thì kiểm tra thật bằng `scripts/sepay_fake_transfer.py`; code của A đã có sẵn trong thư mục chung, không phải kéo về.

### Session C: hoàn tiền (SCRUM-31, 32) và tích hợp cuối
Prefix commit: `SCRUM-31:` / `SCRUM-32:`.

| File | Việc |
|---|---|
| `backend/app/services/refunds.py` (mới) | `request_refund(session, patient, payment_id, data)`: kiểm chủ sở hữu, `policies.can_request_refund`, khoá dòng `FOR UPDATE`, sinh `refund_reference = "RF" + 8 ký tự`, `refund_status = REQUESTED`, ghi audit, thông báo cho bệnh nhân. Gửi lại khi đang REQUESTED/COMPLETED thì báo `RefundAlreadyRequested`. `list_refunds(...)`. `complete(session, admin, payment_id, note)`: REQUESTED → COMPLETED, `payment.status = REFUNDED`, `refunded_at`, ghi audit, thông báo. `reject(session, admin, payment_id, reason)`: REQUESTED → REJECTED, thông báo. `refund_qr_image_url(payment)` theo D14. |
| `backend/app/api/v1/refunds.py` | Viết thân 4 endpoint (phía admin dùng `AdminUser` từ `api/deps.py`) |
| `backend/app/repositories/refunds.py` (mới) | `list_refunds`. Để file riêng để không đụng file của A. |
| `frontend/src/components/RefundPanel.tsx` | Khi `can_request_refund`: form gồm chọn ngân hàng (D15), số TK, tên chủ TK (tự viết hoa), lý do; hiện chính sách "Hoàn 100% số tiền đã thanh toán khi lịch bị huỷ/từ chối; bệnh viện chuyển khoản thủ công". Nếu đã có `refund_status` thì hiện trạng thái, mã hoàn, lý do từ chối; bị REJECTED thì cho gửi lại. Gửi xong gọi `onDone()`. |
| `frontend/src/pages/admin/AdminRefundsPage.tsx` | Bộ lọc trạng thái (mặc định REQUESTED); bảng bệnh nhân / mã lịch / số tiền / ngân hàng / số TK / mã hoàn; mở chi tiết thì hiện ảnh `refund_qr_image_url`, nút "Đã chuyển" (kèm ô ghi chú) và "Từ chối" (bắt buộc nhập lý do) |
| `backend/tests/test_refunds.py` (mới) | Điều kiện được hoàn, không phải chủ thì 404, gửi lặp thì 409, hai yêu cầu đồng thời chỉ một cái thắng, complete/reject, bị reject thì gửi lại được |
| **Sau khi A và B báo xong:** `frontend/e2e/flows.spec.ts:53-105`, `scripts/api_smoke.py` (khối hoàn tiền) | Viết lại E2E: đặt lịch, trang QR, webhook giả (`request.post` có Apikey), 'Payment: Paid', huỷ, yêu cầu hoàn, admin hoàn, 'Payment: Refunded'. Viết thêm khối hoàn tiền vào smoke. |

## 5. Git và chạy thử: một thư mục, một branch, không merge

Cả 3 session cùng làm trong `/home/pc/proj/cnpmnc-hkt`, cùng branch `feature/sprint3-sepay`. Commit của 3 session nối tiếp nhau trên cùng branch nên không bao giờ phải merge. Đổi lại phải giữ kỷ luật vì 3 session dùng chung working tree **và chung git index**.

**Luật git (bắt buộc với mọi session):**
1. **Cấm** `git checkout/switch`, `stash`, `reset`, `rebase`, `pull`, `merge`, `clean`, `restore` khi các session khác còn đang chạy. Những lệnh này đổi file của người khác ngay dưới chân họ.
2. **Cấm** `git add -A`, `git add .`, `git commit -a`. Chỉ commit file của mình, theo đúng đường dẫn:
   - file đã có: `git commit -m "SCRUM-28: ..." -- path/a.py path/b.py`. Cú pháp `-- <paths>` chỉ commit đúng các file đó, kể cả khi session khác đã stage file của họ.
   - file mới: `git add path/new.py && git commit -m "..." -- path/new.py path/a.py`
   - Gặp `index.lock exists` thì đợi vài giây rồi chạy lại. **Không** xoá file lock.
3. Chỉ sửa file mình là chủ (mục 4). File đóng băng thì theo mục 6.
4. Push: ai cũng được `git push origin feature/sprint3-sepay`. Push bị từ chối (non-fast-forward) nghĩa là có người push từ chỗ khác: dừng lại và báo người dùng, không pull/rebase.
5. Migration chỉ có đúng một file (0007, do Phase 0 tạo). Session nào cần đổi DB thì theo mục 6.

**Stack chung (một cho cả nhóm, có hot reload):**
- Stack đang chạy ở port 8080 (project `cnpmnc-qa`) chỉ dùng compose gốc, không có hot reload. Sau Phase 0 thì dựng lại một lần bằng `make up` để có override: backend chạy `--reload` và mount `backend/app`, web mount `frontend/dist`. Phase 0 làm việc này; các session khác không tự `down`/`up` stack.
- Backend tự reload khi có file thay đổi. Code đang viết dở của session khác có thể làm backend lỗi tạm thời: xem `docker compose logs backend --tail 30`, lỗi ở file của ai thì nhắn người đó.
- Frontend: session B chạy `cd frontend && npm run build -- --watch` (nền) để `dist/` luôn mới. Các session khác chỉ cần reload trình duyệt.
- Test backend chạy trong container: `docker compose exec backend pytest -q tests/test_payments.py` (DB `healthcare_test` riêng). Chỉ chạy file test của mình, vì test chạy song song trên cùng DB test sẽ đè nhau. Chạy toàn bộ bộ test chỉ ở mốc cuối và báo trước.
- Lint/typecheck theo file của mình: `ruff check <files>`, `mypy app`, `npm run typecheck`. Lỗi trong file của người khác thì không phải việc của mình.

**Thử tiền thật (cuối sprint, sau khi cả 3 báo xong):**
1. Điền `SEPAY_WEBHOOK_API_KEY` và `SEPAY_API_TOKEN` vào `.env`.
2. Chạy `ngrok http 8080`.
3. Trên my.sepay.vn: tạo webhook URL `https://<ngrok>/api/v1/payments/sepay-webhook`, chọn sự kiện "Có tiền vào", lọc theo VA SEPNK33418, xác thực API Key.
4. Đặt lịch với loại khám "Payment Test (2,000 VND)", quét QR, chuyển 2.000đ, xác nhận lịch chuyển PAID.
5. Tắt ngrok, chuyển khoản lại để kiểm tra đường hỏi User API.
6. Mở PR `feature/sprint3-sepay` → `master`.

## 6. Phối hợp giữa các session

Các session Claude Code trên cùng máy nhắn được cho nhau: gọi `ListAgents` để xem tên (`cnpmnc-hkt-NN`), rồi `SendMessage({to: "<tên>", message})`.

1. **Khi bắt đầu:** gửi cho 2 session còn lại `"[S3-A] online: <tên session>"`.
2. **Nhắn khi:** đạt mốc (A1), xong phần của mình, bị chặn vì cần thứ người khác làm, backend hoặc typecheck vỡ do file của người khác, hoặc cần đổi hợp đồng.
3. **Đổi file đóng băng:** nhắn cả hai session nội dung muốn đổi, đợi trả lời, rồi người đề xuất tự sửa và commit riêng (chỉ các file hợp đồng; nếu đổi API thì sinh lại `schema.d.ts`). Commit xong nhắn kèm hash commit.
4. **Không sửa file của session khác.** Thấy lỗi thì nhắn chủ file.
5. Nếu không nhắn được, ghi chú vào commit message, và người dùng sẽ chuyển lời.

## 7. Rủi ro còn mở

- Định dạng `transaction_date_min` và trường `sub_account` của User API SePay: tài liệu ghi không rõ. A in thử response thật bằng token ở lần chạy đầu và điều chỉnh. Không lọc theo số tài khoản; chỉ khớp theo mã thanh toán.
- `vietqr.app` nhận `bank=OCB` và số VA có chữ (đã thấy trong ví dụ của SePay). `img.vietqr.io` cho QR hoàn tiền dùng BIN; C cần thử với một tài khoản thật.
- Bệnh nhân chuyển sai nội dung (thiếu mã) thì không tự khớp được. Hệ thống ghi log `payment_unmatched_transfer`, admin xử lý trên SePay. Đây là giới hạn đã chấp nhận.
- Lịch có `payment_due_at = NULL` (CONFIRMED trước khi có migration) sẽ không bao giờ tự hết hạn. Chấp nhận được.
