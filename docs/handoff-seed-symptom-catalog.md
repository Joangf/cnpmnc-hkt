# Handoff: seed thêm danh mục triệu chứng trên máy demo

> Gửi Claude trên máy teammate: đọc hết file này trước khi chạy lệnh nào.
> Máy này dùng để **demo**, có **DB thật của CareBook** và **DB của mock ERP** đang chạy.
> Chỉ đọc và ghi đúng phạm vi mô tả bên dưới. Mọi bước ghi dữ liệu phải hỏi người dùng trước.

## 1. Mục tiêu

Danh mục triệu chứng cho AI symptom search mới có 23 triệu chứng, nên các câu như
"tôi không ăn uống, tôi đang trầm cảm" hay "mất ngủ, chóng mặt" ra 0 triệu chứng.
Nhiệm vụ: thêm **34 triệu chứng, khoảng 155 từ đồng nghĩa Việt/Anh và 51 rule** gắn vào
**11 chuyên khoa đang có**. Không thêm chuyên khoa, khoa hay bác sĩ mới.

- Dữ liệu: `backend/app/seed_data/symptom_catalog_extra.json`
- Lệnh: `python -m app.commands.seed_symptom_catalog` (chạy trong container backend)
  - **Chỉ thêm**, idempotent (chạy lại không đổi gì). Triệu chứng được khớp theo tên.
    Không xoá gì, không đổi trọng số, red-flag hay chỉnh sửa có sẵn của admin.
  - Chỉ ghi vào `symptoms`, `symptom_specialty_rules` và index `search_documents`.
    **Chỉ đọc** bảng `specialties`.
  - Danh bạ (hospitals, specialties, departments, doctors, slots) thuộc mock ERP.
    Lệnh này không ghi vào các bảng đó và không gọi mock ERP.
  - Có `--dry-run` để xem trước.

## 2. Tuyệt đối không làm

- Không `docker compose down -v`, không xoá volume nào (`postgres-data`, `mock-erp-data`…).
- Không chạy `python -m app.commands.erp_cutover`, không gọi các API `/simulate/*` của mock ERP.
- Không sửa tay bảng hospitals, specialties, departments, doctors, doctor_slots, appointments.
- Không `git reset --hard`, `git stash`, `git checkout -- .` trên thay đổi của người dùng.
  Working tree bẩn thì dừng lại và hỏi.
- Không ghi API key vào file nào ngoài `.env`, và không in key ra màn hình.
- Không sửa ticket Jira.

## 3. Kiểm tra trước (chỉ đọc)

Chạy ở thư mục gốc repo:

```bash
git status --short                 # phải sạch; bẩn thì hỏi người dùng
git branch --show-current
git log --oneline -3
docker compose ls                  # tìm tên project của stack (thường là "healthcare")
```

Từ đây gọi `P=<tên project>` và dùng `docker compose -p $P ...` cho mọi lệnh.

```bash
docker compose -p $P ps                                           # backend, postgres, mock-erp, web phải Up
docker compose -p $P exec -T backend alembic current              # xem revision hiện tại
docker compose -p $P exec -T postgres psql -U healthcare -d healthcare -tAc \
  "select count(*) from symptoms; select name from specialties where is_active order by name;"
```

Ghi lại các con số này để báo cáo.

## 4. Lấy code

Code nằm trên nhánh `feature/ai-symptom-review`. Nhánh này còn có AI search, tóm tắt review,
Sprint 6 và Postgres có pgvector.

```bash
git fetch origin
git checkout feature/ai-symptom-review
git pull --ff-only
ls backend/app/commands/seed_symptom_catalog.py backend/app/seed_data/symptom_catalog_extra.json
```

Nếu máy đang ở nhánh khác mà nhánh đó có commit chưa push, **hỏi người dùng** trước khi checkout.

### Cấu hình `.env` (AI search)

Thiếu các biến này thì seed vẫn chạy, nhưng tìm kiếm chỉ khớp từ nguyên văn, không có AI.
Kiểm tra xem đã có chưa, **không in giá trị key ra màn hình**:

```bash
grep -E '^(LLM_BASE_URL|LLM_MODEL|EMBEDDING_MODEL|RERANK_MODEL)=' .env
grep -c '^LLM_API_KEY=.' .env      # 1 = đã có key
```

Giá trị cần có (key xin chủ nhóm gửi riêng, không dán vào chat công khai):

```
LLM_BASE_URL=https://dev-ai-api.dbiz.com/v1
LLM_API_KEY=<xin riêng>
LLM_MODEL=deepseek-v4-flash
EMBEDDING_MODEL=embedding          # KHÔNG dùng "bge-m3": key này bị 403 với tên đó
RERANK_MODEL=embedding-colbert
```

## 5. Dựng lại stack (hỏi người dùng trước)

Nhánh này đổi image Postgres sang `postgres/Dockerfile` (Postgres 16.4 Alpine + pgvector, cùng
base với image cũ) và thêm migration `0014`–`0016`. **Volume giữ nguyên, dữ liệu không mất.**

```bash
docker compose -p $P up -d --build
docker compose -p $P exec -T backend alembic current      # phải là 0016_review_reports (head)
docker compose -p $P logs backend --tail 50
```

Log có thể có dòng `Overlapping legacy interval ... cutover aborted` hoặc
`ERP migration is not complete`. Đây là lỗi có sẵn của luồng cutover ERP, không liên quan,
**đừng tìm cách sửa**. Chỉ dừng lại nếu backend không lên.

## 6. Backup, xem trước, áp dụng

```bash
# backup đúng 2 bảng sẽ ghi
docker compose -p $P exec -T postgres pg_dump -U healthcare -d healthcare --data-only \
  -t symptoms -t symptom_specialty_rules > symptoms_backup_$(date +%Y%m%d_%H%M).sql

# xem trước: không lưu gì
docker compose -p $P exec -T backend python -m app.commands.seed_symptom_catalog --dry-run
```

Dòng cuối phải giống thế này:

```
dry run: nothing was saved
symptoms_added=34 synonyms_added=155 rules_added=51 warnings=0
```

- `warnings>0` kèm dòng `! rule ... no such specialty`: tên chuyên khoa trên máy này khác tên
  trong file JSON. Báo người dùng, **không sửa DB**. Nếu được đồng ý thì sửa tên trong file JSON.
- `symptoms_added` nhỏ hơn 34: một phần đã được seed từ trước. Không sao, lệnh chỉ thêm phần còn thiếu.

Cho người dùng xem kết quả dry-run và **hỏi xác nhận**, rồi mới chạy thật:

```bash
docker compose -p $P exec -T backend python -m app.commands.seed_symptom_catalog
```

Kết quả mong đợi: dòng `AI search index updated`, rồi tới các con số như trên.
Chạy lại lần hai phải ra toàn số 0.

## 7. Kiểm tra

```bash
docker compose -p $P exec -T postgres psql -U healthcare -d healthcare -tAc \
  "select count(*) from symptoms; select entity_type, count(*) from search_documents group by 1;"
```

Sau khi seed có 57 triệu chứng. `search_documents` có khoảng 350 dòng `symptom`,
còn số dòng `doctor` bằng số bác sĩ đang hiển thị. Nếu chưa đủ thì đợi khoảng 1 phút để job index chạy lại.

Thử các câu dưới đây. Chỉ bước giải thích mới gọi DeepSeek nên rất ít tốn token:

```bash
for t in "tôi không ăn uống, tôi đang trầm cảm" "dạo này mất ngủ, hay chóng mặt" \
         "huyết áp cao, phù chân" "đi ngoài ra máu" "nôn nóng muốn đi khám" "tôi bị đau răng"; do
  curl -s -X POST http://localhost:8080/api/v1/symptoms/interpret \
    -H 'Content-Type: application/json' -d "{\"text\":\"$t\"}" |
  python3 -c "import json,sys;d=json.load(sys.stdin);print('$t','->',d['mode'],[s['name'] for s in d['symptoms']],'URGENT' if d['urgent_warning'] else '')"
done
```

| Câu nhập | Kết quả mong đợi |
|---|---|
| tôi không ăn uống, tôi đang trầm cảm | Loss of appetite, Low mood |
| dạo này mất ngủ, hay chóng mặt | Dizziness, Trouble sleeping |
| huyết áp cao, phù chân | High blood pressure, Leg swelling |
| đi ngoài ra máu | Blood in stool (+ URGENT), có thể kèm Diarrhea |
| nôn nóng muốn đi khám | rỗng ("nôn nóng" là sốt ruột, không phải nôn) |
| tôi bị đau răng | rỗng (ngoài phạm vi) |

`mode` phải là `ai`. Nếu ra `rule_fallback` thì `.env` thiếu `LLM_*` hoặc key sai (xem mục 4).

Cuối cùng mở `http://localhost:8080/symptoms` trên trình duyệt, gõ câu đầu tiên, bấm
"3. Suggest specialties and doctors". Kết quả phải ra chuyên khoa kèm danh sách bác sĩ.

## 8. Rollback (chỉ khi người dùng yêu cầu)

```bash
docker compose -p $P exec -T postgres psql -U healthcare -d healthcare -v ON_ERROR_STOP=1 \
  -c "BEGIN; TRUNCATE symptom_specialty_rules, symptoms; COMMIT;"
docker compose -p $P exec -T postgres psql -U healthcare -d healthcare -v ON_ERROR_STOP=1 \
  < symptoms_backup_<thời-gian>.sql
```

Index AI tự dọn các triệu chứng đã bị gỡ trong vòng 1 phút. Cách này đã chạy thử:
về lại 23 triệu chứng, seed lại vẫn được.

## 9. Báo cáo lại cho người dùng

- Nhánh và commit đang chạy, `alembic current`.
- Số triệu chứng trước và sau, kết quả dry-run và kết quả chạy thật (dòng cuối của mỗi lần).
- Bảng kết quả 6 câu thử, và `mode` (`ai` hay `rule_fallback`).
- Tên file backup.
- Mọi cảnh báo hoặc lỗi gặp phải, nguyên văn.

## Ghi chú cho người làm demo

- Mapping triệu chứng → chuyên khoa là **giả lập cho đồ án**, chưa qua bác sĩ duyệt (FRD 4.7.1).
  Trầm cảm/lo âu được gắn vào Nội tổng quát và Thần kinh, vì bệnh viện chưa có khoa Tâm thần.
- Muốn thêm hay sửa triệu chứng thì sửa file JSON rồi chạy lại lệnh, hoặc vào
  Admin → Symptom rules. Không phải sửa code.
