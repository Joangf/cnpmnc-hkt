---
name: review
description: Soạn báo cáo sprint review từ Jira — story đã Done/chưa Done, velocity, số liệu chất lượng QA, vi phạm Definition of Done. Dùng khi người dùng gõ /review hoặc cần báo cáo cuối sprint, sprint review, tổng kết sprint.
---
# /review [tên sprint]

Thao tác Jira dùng `python tools/jira.py` (bảng lệnh trong CLAUDE.md).

Mặc định: sprint đang chạy. Chỉ ĐỌC Jira.

1. Lấy toàn bộ ticket của sprint (Story, Task, Subtask).
2. Tiến độ: danh sách Done / chưa Done; story point Done (= velocity) / cam kết.
3. Chất lượng (đọc comment `QA REPORT` và subtask `[BUG]`):
   - Số ticket đã qua /qa; số lần QA FAIL trước khi PASS.
   - Bug tạo trong sprint: tổng, theo severity, đã đóng / còn mở.
   - Tổng test do agent sửa (TEST_BUG).
4. Vi phạm DoD: ticket Done nhưng thiếu label `qa-passed` hoặc còn `[BUG]` mở.
5. Danh sách demo: các Story Done kèm 1 câu mô tả giá trị cho người dùng.

Xuất markdown. Hỏi người dùng có muốn lưu vào `docs/sprint-reviews/<tên-sprint>.md` không.
