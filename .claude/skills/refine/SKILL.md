---
name: refine
description: Backlog refinement — soạn user story và AC từ FRD rồi tạo Story trên Jira SCRUM sau khi người dùng duyệt. Dùng khi người dùng gõ /refine, muốn viết story, tạo backlog từ FRD, chuốt backlog.
---
# /refine <mã FR hoặc nhóm FR>

Thao tác Jira dùng `python tools/jira.py` (bảng lệnh trong CLAUDE.md).

Ví dụ: `/refine FR-BOOK-04 FR-BOOK-05` hoặc `/refine FR-PAY`.

1. Gọi subagent `story-writer` với các mã FR trong $ARGUMENTS.
2. Kiểm tra trùng: tìm trên Jira story có TRACE cùng mã FR (JQL `project = SCRUM AND text ~ "<mã FR>"`). Trùng → báo, không tạo lại.
3. Hiển thị các story cho người dùng duyệt. Story có INVEST khác "OK" → nêu rõ, đề xuất tách/sửa.
4. Chỉ khi người dùng đồng ý: tạo Story trong SCRUM (backlog), mô tả gồm STORY, AC, TRACE; label theo PRIORITY (`must`/`should`/`could`).
5. Nhắc: để đạt DoR, chạy `/qa <mã>` cho từng story mới (tạo TEST PLAN) và cả nhóm ước lượng story point.
