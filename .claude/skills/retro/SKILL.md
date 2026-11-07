---
name: retro
description: Hỗ trợ sprint retrospective bằng dữ liệu Jira — phân tích bug, ticket bị trả về, AC phải làm rõ, rồi đề xuất việc cải tiến và tạo task trên Jira khi nhóm chốt. Dùng khi người dùng gõ /retro hoặc nói rút kinh nghiệm, retrospective, cải tiến sprint.
---
# /retro [tên sprint]

Thao tác Jira dùng `python tools/jira.py` (bảng lệnh trong CLAUDE.md).

Mặc định: sprint vừa kết thúc hoặc đang chạy.

1. Thu thập từ Jira:
   - Bug `[BUG]`: số lượng, severity, file nghi vấn (dòng SUSPECT) lặp lại nhiều nhất.
   - Số comment `QA REPORT: FAIL` (ticket bị trả về In Progress).
   - Số ticket từng có label `needs-clarification`.
   - Ticket chưa Done lúc hết sprint.
2. Trình bày 3 mục: **Làm tốt** / **Chưa tốt** / **Dữ liệu cho thấy** (mỗi mục ≤3 ý, có số liệu).
3. Đề xuất 2–3 việc cải tiến cụ thể, đo được ở sprint sau.
   Ví dụ: "AC phải qua /qa giai đoạn thiết kế trước planning" nếu nhiều `needs-clarification`.
4. Chờ nhóm chọn. Với mỗi việc được chọn → tạo Task trong SCRUM, label `retro-action`.
