---
name: plan-sprint
description: Hỗ trợ sprint planning — tính velocity, kiểm tra Definition of Ready của backlog và đề xuất phạm vi sprint tiếp theo. Dùng khi người dùng gõ /plan-sprint hoặc nói lập kế hoạch sprint, chọn ticket cho sprint, sprint planning.
---
# /plan-sprint [tên sprint đích]

Thao tác Jira dùng `python tools/jira.py` (bảng lệnh trong CLAUDE.md).

Mặc định: sprint Future gần nhất (ví dụ "SCRUM Sprint 2").

1. Velocity: story point Done của các sprint đã đóng (lấy trung bình). Chưa có sprint nào đóng →
   dùng số point của sprint đang chạy làm tham chiếu và nói rõ đây là ước tính tạm.
2. Ứng viên: ticket trong backlog + ticket chưa Done của sprint hiện tại, theo thứ tự ưu tiên trên board.
3. Kiểm tra DoR (CLAUDE.md) cho từng ứng viên: có AC, có comment TEST PLAN, có Story point estimate,
   không có `needs-clarification`. Ghi rõ thiếu gì.
4. Đề xuất: chọn ticket đạt DoR theo thứ tự ưu tiên cho tới khi chạm velocity.
   Liệt kê riêng ticket ưu tiên cao nhưng chưa đạt DoR, kèm việc cần làm.
5. Người dùng/nhóm chốt. Lấy id sprint bằng `python tools/jira.py sprints`, rồi `python tools/jira.py move-to-sprint <id> <các mã>`.
