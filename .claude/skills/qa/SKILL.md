---
name: qa
description: Workflow QA đầy đủ cho một ticket Jira SCRUM — thiết kế test theo ISTQB, viết test tự động, chạy test + regression, phân loại lỗi, tạo bug và cập nhật trạng thái trên Jira. Dùng khi người dùng gõ /qa SCRUM-xx hoặc nói muốn test, kiểm thử, QA một ticket/story/task.
---
# /qa <SCRUM-xx>

Đối số: mã ticket trong $ARGUMENTS (ví dụ `SCRUM-12`). Thiếu → hỏi lại.
Đọc CLAUDE.md trước (quy ước Jira, DoD, khối [ĐIỀN SAU]). Thao tác Jira dùng `python tools/jira.py` (bảng lệnh trong CLAUDE.md).

## 0. Đọc ticket
Lấy: tiêu đề, mô tả (AC), loại, ticket cha, trạng thái, label, comment, subtask, links.
Tìm comment bắt đầu bằng `TEST PLAN`, và bug của ticket: các mục trong `subtasks` VÀ `links` có tiêu đề `[BUG]`.

## 1. Chọn giai đoạn
| Điều kiện | Giai đoạn |
|---|---|
| Chưa có comment TEST PLAN | A. THIẾT KẾ |
| Có TEST PLAN, trạng thái To Do / In Progress | Hỏi người dùng: "Code xong chưa? Chuyển In Review để QA?" Có → chuyển `In Review`, sang B. Không → dừng |
| Trạng thái In Review | B. KIỂM THỬ |
| Trạng thái Done | Chỉ chạy regression (bước B3) và báo cáo, không đổi Jira |

## A. THIẾT KẾ
1. Gọi subagent `test-designer`, truyền nguyên văn AC + mã ticket.
2. Thêm comment vào ticket: toàn bộ khối `TEST PLAN — ...` mà agent trả về.
3. Nếu QUESTIONS khác "Không có": thêm label `needs-clarification`, comment riêng các câu hỏi
   (mở đầu "@PO cần làm rõ AC:"). Báo người dùng: chờ PO trả lời rồi chạy lại /qa sau khi PO sửa AC.
4. Dừng. Báo người dùng số TC, phân bổ theo kỹ thuật và cấp test.

## B. KIỂM THỬ
1. Cập nhật hợp đồng API: chạy lệnh "Lấy OpenAPI" trong CLAUDE.md.
2. Nếu chưa có file `tests/**/test_scrum_<số>_*.py`, hoặc có TC chưa có hàm test tương ứng:
   gọi subagent `test-automator`, truyền khối TEST PLAN.
3. Gọi subagent `test-executor` với số ticket.
   - `APP NOT RUNNING` → báo người dùng bật app, dừng. Không đổi Jira.
4. RESULT = PASS → sang B6.
5. RESULT = FAIL → gọi subagent `bug-triager`, truyền khối FAILURES + TEST PLAN. Với từng test:
   - TEST_BUG → gọi `test-automator` sửa đúng test đó, quay lại B3. Tối đa 2 vòng; quá 2 vòng → coi như cần người xem, báo người dùng.
   - ENV_ISSUE → báo người dùng, không tạo bug.
   - PRODUCT_BUG → tạo bug theo quy ước Bug trong CLAUDE.md (dùng đúng dòng "Tạo bug" ứng với loại ticket):
     tiêu đề `[BUG] <SCRUM-xx>: <mô tả trong BUG TITLE>`, label `bug`, `--assignee @<SCRUM-xx>`,
     ticket là Subtask thì `--parent <ticket cha>` + `--link <SCRUM-xx>`.
     Mô tả gồm `TICKET: <SCRUM-xx>`, `TEST: <tên test>`, STEPS, EXPECTED, ACTUAL, SEVERITY, SUSPECT.
   Sau đó: comment `QA REPORT: FAIL` (mẫu dưới), chuyển ticket về `In Progress`. Dừng.
6. PASS:
   - Với mỗi bug `[BUG]` của ticket (bước 0) chưa Done: nếu test ghi ở dòng `TEST:` nay đã PASS → comment "Đã kiểm lại: PASS", chuyển bug đó `Done`.
   - Kiểm tra DoD trong CLAUDE.md. Đạt → comment `QA REPORT: PASS`, thêm label `qa-passed`,
     rồi HỎI người dùng xác nhận trước khi chuyển ticket sang `Done`.

## Mẫu comment QA REPORT
```
QA REPORT: PASS | FAIL — <ngày giờ>
Test của ticket: <x>/<y> | Regression: <x>/<y>
Test do agent sửa (TEST_BUG): <n>
Bug mới: <danh sách SCRUM-xx [BUG] ... (severity)>  (hoặc "Không có")
Bug đã đóng: <danh sách>  (hoặc "Không có")
```

## Giới hạn
- Không sửa code trong BACKEND_DIR/FRONTEND_DIR. Sửa bug là việc của dev.
- Không xóa issue, không sửa AC, không tự chuyển Done khi chưa được người dùng xác nhận.
- Cuối mỗi lần chạy, tóm tắt cho người dùng: giai đoạn đã chạy, thay đổi trên Jira, việc tiếp theo.
