# CareBook — Quy ước làm việc với agent

Web đặt lịch khám cho một bệnh viện. Stack: FastAPI + React + PostgreSQL (+ Redis, mock ERP, mock payment), chạy bằng Docker Compose.
Tài liệu yêu cầu: `docs/FRD.md` (symlink tới `.claude/plans/business.md`, FRD v1.2). Hợp đồng API: `docs/openapi.json` (FastAPI sinh tự động, không commit).
Hướng dẫn cài đặt kit agent cho thành viên: `docs/qa-scrum-kit.md`.
Thiết kế UI: `.claude/design/design-guidelines.md`.

## [ĐIỀN SAU] — thông số phụ thuộc repo (chỉ sửa ở đây)
- BACKEND_DIR: `backend/` (test nội bộ của dev ở `backend/tests/`, chạy bằng `make test` — KHÔNG phải bộ test của agent)
- FRONTEND_DIR: `frontend/` (E2E TypeScript của dev ở `frontend/e2e/` — KHÔNG phải bộ test của agent)
- Lệnh chạy cả hệ thống: `make up` (= `docker compose up -d --build`). Backend tự seed khi khởi động.
- API_BASE_URL: `http://localhost:8080` — mọi endpoint nằm dưới `/api/v1/...` (nginx proxy sang backend)
- WEB_BASE_URL: `http://localhost:8080`
- Kiểm tra app đang chạy: `curl -sf http://localhost:8080/api/openapi.json > /dev/null`
- Lấy OpenAPI: `curl -fsS http://localhost:8080/api/openapi.json -o docs/openapi.json`
- Tài khoản seed: admin `admin@example.com` / `Admin12345!`, bệnh nhân `patient@example.com` / `Patient12345!` (xem `.env.example`).
- TEST_DATABASE_URL: để trống. Test chạy trên stack dev và tự tạo dữ liệu không trùng (uuid).
  Đặt biến này sẽ TRUNCATE mọi bảng của DB đó trước mỗi test — tuyệt đối không trỏ vào DB `healthcare`.
- Python cho test/Jira: `.venv/` ở gốc repo (`source .venv/bin/activate` trước khi mở Claude Code).

## Jira
Mọi thao tác Jira dùng `python tools/jira.py <lệnh>` (in ra JSON). Cấu hình trong `.env` (không commit).
| Việc | Lệnh |
|---|---|
| Kiểm tra kết nối | `python tools/jira.py whoami` |
| Đọc ticket (AC, comment, subtask) | `python tools/jira.py get SCRUM-12` |
| Tìm theo JQL | `python tools/jira.py search "project = SCRUM AND sprint in openSprints()"` |
| Thêm comment dài | ghi ra file tạm rồi `python tools/jira.py comment SCRUM-12 --file /tmp/c.md` |
| Tạo bug (ticket là Task/Story) | `python tools/jira.py create --type Subtask --parent SCRUM-12 --summary "[BUG] SCRUM-12: ..." --labels bug --assignee @SCRUM-12 --description-file /tmp/bug.md` |
| Tạo bug (ticket là Subtask, vd SCRUM-45 thuộc SCRUM-11) | `python tools/jira.py create --type Subtask --parent SCRUM-11 --summary "[BUG] SCRUM-45: ..." --labels bug --assignee @SCRUM-45 --link SCRUM-45 --description-file /tmp/bug.md` |
| Tạo story/task | `python tools/jira.py create --type Story --summary "..." --description-file F --labels must` |
| Chuyển trạng thái | `python tools/jira.py transition SCRUM-12 "In Review"` |
| Label | `python tools/jira.py label SCRUM-12 --add qa-passed --remove needs-clarification` |
| Sprint | `python tools/jira.py sprints`, `python tools/jira.py move-to-sprint <id> SCRUM-12 SCRUM-13` |
Lệnh lỗi → đọc thông báo JSON trong stderr, báo người dùng, KHÔNG thử đoán cách khác.

- Project key: `SCRUM` (CareBook, team-managed). Sprint: "SCRUM Sprint N".
- Trạng thái: `To Do` → `In Progress` → `In Review` → `Done`.
- Loại issue: Epic, Story, Task, Subtask. Ước lượng: trường "Story point estimate".
- Cách nhóm tổ chức: Task = một tính năng (SCRUM-1…11), Subtask = user story có AC + người làm (đây là ticket thường đem đi /qa).
- **Bug:** project chưa có loại Bug. Quy ước: **Subtask** tiêu đề `[BUG] <mã ticket lỗi>: <mô tả>`, label `bug`,
  giao cho người được giao của ticket lỗi.
  - Ticket lỗi là Task/Story → bug là Subtask của chính ticket đó.
  - Ticket lỗi là Subtask (Jira không cho Subtask lồng nhau) → bug là Subtask của **Task cha**, kèm link "relates to" ticket lỗi.
  - Bug của một ticket = subtask `[BUG]` của nó + issue `[BUG]` trong `links` của nó (`jira.py get`).
  (Nếu PO thêm loại Bug thì đổi quy ước ở đây.)
- Label dùng chung: `needs-clarification` (AC chưa rõ), `qa-passed`, `bug`.
- Agent KHÔNG được xóa issue, KHÔNG sửa AC, KHÔNG đổi người được giao.
  Agent chỉ: đọc, thêm comment, tạo Subtask/Story khi được yêu cầu, chuyển trạng thái theo quy tắc dưới.

## Definition of Ready (DoR) — đủ điều kiện kéo vào sprint
1. Có AC dạng Given/When/Then, không có label `needs-clarification`.
2. Có comment "TEST PLAN" do `/qa` tạo.
3. Có Story point estimate.

## Definition of Done (DoD) — đủ điều kiện chuyển Done
1. Mọi test case trong TEST PLAN đã có test tự động và PASS.
2. Toàn bộ bộ test cũ (regression) vẫn PASS.
3. Không còn bug `[BUG]` nào của ticket (subtask hoặc issue được link) chưa Done.
4. Có comment "QA REPORT: PASS" do `/qa` tạo.

## Quy ước test
- Một lệnh duy nhất: `pytest` (cấu hình ở `pytest.ini`).
- API test: `tests/api/`, E2E test: `tests/e2e/` (pytest-playwright).
- File theo ticket: `test_scrum_<số>_<chủ đề>.py`, ví dụ `test_scrum_12_booking.py`.
- Tên hàm theo test case: `test_tc_<số ticket>_<số TC>_<mô tả>`, ví dụ `test_tc_12_03_adjacent_slot_ok`.
- Docstring mỗi test ghi: mã TC, AC liên quan, kỹ thuật thiết kế.
- Marker: `@pytest.mark.smoke` cho luồng chính, `@pytest.mark.e2e` cho E2E.
- E2E chỉ dành cho luồng sống còn: đăng ký, đặt lịch, thanh toán, hủy lịch, đánh giá.

## Nguyên tắc
- Agent đề xuất, người quyết định.
- Kiểm thử độc lập: agent viết test KHÔNG đọc code xử lý trong BACKEND_DIR/FRONTEND_DIR,
  chỉ dựa vào AC, TEST PLAN và `docs/openapi.json`.
- Khi đang code tính năng, KHÔNG sửa file trong `tests/` để test xanh. Test sai thì báo để `/qa` xử lý.
- Mọi commit ghi mã Jira ở đầu: `SCRUM-12: ...`.
