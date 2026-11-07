# QA-Scrum Kit

Hệ thống agent hỗ trợ Scrum trên Jira (project `SCRUM`), trọng tâm là kiểm thử theo ISTQB.
Gồm 6 lệnh (skill, `.claude/skills/`), 5 agent (`.claude/agents/`) và `tools/jira.py` (kết nối Jira bằng API token, không cần MCP).
Mọi quy ước nằm ở `CLAUDE.md` ở gốc repo.

## Lệnh theo sự kiện Scrum
| Sự kiện | Lệnh | Ghi lên Jira? |
|---|---|---|
| Backlog refinement | `/refine FR-BOOK-04 FR-BOOK-05` | Tạo Story (sau khi bạn duyệt) |
| Sprint planning | `/plan-sprint` | Gán sprint (sau khi nhóm chốt) |
| Daily scrum | `/daily` | Không |
| Phát triển + QA | `/qa SCRUM-45` | Comment, bug `[BUG]`, chuyển trạng thái |
| Sprint review | `/review` | Không |
| Retrospective | `/retro` | Tạo Task cải tiến (sau khi nhóm chốt) |

## Vòng làm việc mỗi ticket
1. Nhận ticket → `/qa SCRUM-xx` → agent viết **TEST PLAN** lên Jira (hoặc hỏi PO nếu AC mơ hồ).
2. Code theo TEST PLAN. **Không sửa file trong `tests/`.**
3. Code xong, `make up` cho stack chạy → `/qa SCRUM-xx` → agent viết test, chạy test + regression.
   - PASS → agent hỏi bạn xác nhận chuyển **Done**.
   - FAIL do code → agent tạo bug `[BUG] SCRUM-xx: ...` giao cho bạn, ticket về In Progress. Sửa xong lặp lại bước 3.
   - Ticket là Subtask → bug nằm dưới Task cha, có link "relates to" về ticket (Jira không cho Subtask lồng nhau).

## Ba bộ test trong repo — đừng nhầm
| Thư mục | Ai viết | Chạy |
|---|---|---|
| `tests/` (gốc repo) | agent `/qa`, kiểm thử hộp đen qua HTTP | `pytest` ở gốc repo |
| `backend/tests/` | dev, unit/integration trong container | `make test` |
| `frontend/e2e/` | dev, Playwright TypeScript | `make e2e` |

## Cài đặt (mỗi thành viên, 1 lần)
1. Cài Claude Code, Docker, [uv](https://docs.astral.sh/uv/).
2. Tạo môi trường Python cho test và Jira:
   ```
   uv venv .venv --python 3.12
   uv pip install --python .venv/bin/python -r requirements-test.txt
   .venv/bin/playwright install chromium      # ~150 MB, chỉ cần cho test E2E
   ```
3. `cp .env.example .env` rồi điền 3 dòng `JIRA_*` (xem mục dưới). Các biến khác giữ mặc định.
4. Kiểm tra: `source .venv/bin/activate && python tools/jira.py whoami` → thấy `"ok": true`.
5. Luôn mở Claude Code **sau khi** đã `source .venv/bin/activate`, để `python`/`pytest` của agent dùng đúng môi trường.
   Trong Claude Code, gõ `/daily` → thấy bảng sprint là agent dùng được Jira.

### Lấy Jira API token
1. Vào https://id.atlassian.com/manage-profile/security/api-tokens (đăng nhập tài khoản Jira).
2. **Create API token** (loại KHÔNG có scope), đặt tên `carebook-agent`, chọn hạn dùng → Create.
3. **Copy ngay** — token chỉ hiện một lần. Dán vào `JIRA_API_TOKEN` trong `.env`.
4. `JIRA_EMAIL` = email đăng nhập Jira. `JIRA_BASE_URL=https://hcmut-team-kr7ef8ao.atlassian.net`.
- Lỗi 401: sai email/token. Lỗi 403/CAPTCHA: đăng nhập Jira trên web một lần rồi thử lại.
- Token là mật khẩu của bạn: không gửi chat, không commit (`.env` đã nằm trong `.gitignore`).

## Chạy test (không cần Claude Code)
```
make up                # stack ở http://localhost:8080
source .venv/bin/activate
pytest                 # toàn bộ test của agent
pytest -m smoke        # luồng chính
pytest -k scrum_45     # test của 1 ticket
```
Máy đã có Postgres/Redis khác chiếm cổng 5432/6379, hoặc có bản checkout khác cũng dùng tên project `healthcare`:
`docker compose -p cnpmnc-qa -f docker-compose.yml up -d --build` (chỉ mở cổng 8080, đủ cho test của agent).

Test chạy trên DB dev và tự tạo dữ liệu không trùng. **Không** đặt `TEST_DATABASE_URL` trỏ vào DB `healthcare`:
khi biến này có giá trị, `tests/conftest.py` TRUNCATE mọi bảng trước mỗi test.
