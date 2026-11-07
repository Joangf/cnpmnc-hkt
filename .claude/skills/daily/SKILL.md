---
name: daily
description: Tóm tắt daily scrum từ Jira cho sprint đang chạy — từng thành viên đã xong gì, đang làm gì, ticket kẹt, bug đang mở. Dùng khi người dùng gõ /daily hoặc hỏi tình hình sprint, ai đang làm gì, có gì bị kẹt.
---
# /daily

Thao tác Jira dùng `python tools/jira.py` (bảng lệnh trong CLAUDE.md).

Chỉ ĐỌC Jira, không ghi gì.

1. Lấy ticket sprint đang chạy: JQL `project = SCRUM AND sprint in openSprints()`.
2. Nhóm theo người được giao. Với mỗi người:
   - **Xong 24h qua:** JQL `project = SCRUM AND status changed to Done after -1d`.
   - **Đang làm:** In Progress / In Review.
   - **Kẹt:** In Progress hoặc In Review không cập nhật quá 2 ngày; hoặc có label `needs-clarification`.
   - **Bug đang mở:** subtask `[BUG]` chưa Done được giao cho người đó (kèm severity).
3. Cuối bảng: số story point đã Done / tổng sprint, số ngày còn lại của sprint.

Đầu ra: một bảng theo người + 1–3 dòng "Cần gỡ ngay" (bug Critical, ticket kẹt lâu nhất, câu hỏi chờ PO).
Ngắn gọn, đọc trong 1 phút.
