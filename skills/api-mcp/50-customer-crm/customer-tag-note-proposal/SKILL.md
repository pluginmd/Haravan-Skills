---
name: customer-tag-note-proposal
description: "Đề xuất gắn tag phân hạng (VIP, Loyal, Churn-Risk, B2B-Si) và ghi chú chăm sóc hàng loạt cho khách hàng (/com/customers/{id}.json)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 50-customer-crm
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_customers
    - com.write_customers
  endpoints:
    - "GET https://apis.haravan.com/com/customers/{customer_id}.json"
    - "PUT https://apis.haravan.com/com/customers/{customer_id}.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 100
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Customer Tier Tagging & Note Update Proposal

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này đồng bộ kết quả phân tích CRM (`customer-rfm-segmentation`, `customer-vip-churn-watchlist`, `customer-duplicate-phone-finder`) vào trường `tags` và `note` của hồ sơ khách hàng trên Haravan (`/com/customers/{id}.json`). Khi khách nhắn tin qua **Harasocial** hoặc thanh toán tại **HaraRetail POS**, nhân viên bán hàng sẽ thấy ngay hạng khách (`rfm-champions`, `vip-churn-risk`, `b2b-si`) cùng ghi chú chăm sóc mà không làm mất lịch sử ghi chú cũ của CSKH hay tag tích điểm của **Haraloyalty**.

**Tiêu chí hoàn thành (Definition of Done):**
- Đọc nguyên trạng `tags` và `note` của tối đa `100` khách hàng qua `GET /com/customers/{id}.json`.
- Thực hiện phép hợp nhất an toàn (**set merge** cho `tags`, **append-only** kèm timestamp cho `note`), tuyệt đối không xóa tag hệ thống (`haraloyalty-*`, `zns-*`) hay ghi đè mất `note` cũ.
- Xuất Backup JSON + Preview Diff (đã che PII) qua `scripts/dry_run_report.py`, chờ người dùng duyệt rồi mới `PUT` và gọi `GET` xác minh sau ghi.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_customers`, `com.write_customers` |
| **Endpoints** | `GET /com/customers/{customer_id}.json`, `PUT /com/customers/{customer_id}.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=False)  # Chỉ False sau khi duyệt preview
cur = client.get(f"/com/customers/{customer_id}.json")["customer"]
res = client.put(f"/com/customers/{customer_id}.json", json_body=payload)
```

**JSON Request Payload (`PUT /com/customers/70122.json`):**
```json
{
  "customer": {
    "id": 70122,
    "tags": "haraloyalty-gold, rfm-champions, vip-2026",
    "note": "Thích giao giờ hành chính.\n[2026-04-10 CRM] Phân hạng RFM Champions (LTV 4.85M, 6 đơn)."
  }
}
```

**JSON Response Payload (HTTP 200 OK):**
```json
{
  "customer": {
    "id": 70122,
    "tags": "haraloyalty-gold, rfm-champions, vip-2026",
    "note": "Thích giao giờ hành chính.\n[2026-04-10 CRM] Phân hạng RFM Champions (LTV 4.85M, 6 đơn).",
    "updated_at": "2026-04-10T10:42:18Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `updates_file` | string (path/JSON) | Yes | — | Danh sách `(customer_id, add_tags?, remove_tags?, note_append?)`; tối đa `100` khách/lần. |
| `replace_exclusive_prefix` | string | No | `"rfm-"` | Tự động gỡ tag cũ cùng prefix (vd gỡ `rfm-loyal` khi gắn `rfm-champions`) để tránh 1 khách mang 2 hạng RFM cùng lúc. |
| `protected_tag_prefixes` | array[string] | No | `["haraloyalty-","zns-","erp-","blacklist"]` | Cấm xóa các tag thuộc hệ thống tích điểm/CSKH quan trọng. |
| `dry_run` | boolean | Yes | `true` | Mặc định `true`; bắt buộc sinh preview + backup trước khi ghi. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Đọc trạng thái gốc (`GET`):** Với mỗi `customer_id` (≤ 100), tải `tags` và `note` hiện tại, lưu toàn bộ vào `backup_<ts>.json`.
2. **Hợp nhất `tags` an toàn (Non-Destructive Tag Merge):**
   - `existing = [t.strip() for t in (cur["tags"] or "").split(",") if t.strip()]`.
   - Nếu có `replace_exclusive_prefix` và `add_tags` chứa tag mang prefix đó → tự đưa các tag cũ cùng prefix vào `effective_remove` (trừ tag thuộc `protected_tag_prefixes`).
   - `final_tags = sorted_preserve_order((existing - effective_remove) | add_tags)`.
3. **Nối `note` chống trùng lặp (Idempotent Note Append):**
   - Nếu `note_append` đã tồn tại nguyên văn trong `cur["note"]` → bỏ qua để đảm bảo chạy lại không nhân đôi dòng ghi chú.
   - Nếu chưa có → nối thêm `\n[YYYY-MM-DD CRM] <note_append>`, kiểm tra tổng độ dài không vượt giới hạn trường `note` của Haravan (≤ 2.000 ký tự).
4. **Dry-Run & Apply:** Trình bày bảng diff (chỉ dùng `customer_id` + SĐT redacted), chờ duyệt, gọi `PUT /com/customers/{id}.json` với `partial_failure_policy: stop` và gọi lại `GET` xác minh.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Bảng Preview Cập nhật Tag & Ghi chú Khách hàng (Dry-Run — 35 khách hàng):**
| Customer ID | SĐT (Redacted) | Tags trước | Tags sau đề xuất | Ghi chú nối thêm (`note_append`) |
| --- | --- | --- | --- | --- |
| `70122` | `090****567` | `haraloyalty-gold, rfm-loyal` | `haraloyalty-gold, rfm-champions, vip-2026` | `[2026-04-10 CRM] Phân hạng RFM Champions` |
| `70419` | `098****312` | `rfm-champions` | `rfm-at-risk, vip-churn-risk` | `[2026-04-10 CRM] Quá 68 ngày chưa mua lại` |
| `78941` | `090****567` | `harasocial` | `harasocial, dup-review` | `[2026-04-10 CRM] Trùng SĐT với hồ sơ #70122` |

```json
{
  "skill": "customer-tag-note-proposal",
  "mode": "dry_run",
  "total_requested": 35,
  "total_changes": 32,
  "skipped_no_op": 3,
  "backup_artifact": "artifacts/customer-tag-note-proposal_20260410_backup.json",
  "rollback_supported": true,
  "proposals": [
    {
      "customer_id": 70122,
      "phone_redacted": "090****567",
      "tags_before": "haraloyalty-gold, rfm-loyal",
      "tags_after": "haraloyalty-gold, rfm-champions, vip-2026",
      "note_appended": true
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Giới hạn L2 Proposal:** `dry_run: true`, `confirmation_required: true`, `max_records: 100`, `partial_failure_policy: stop`.
- **Chống ghi đè mất dữ liệu:** Trên Haravan, `PUT /com/customers/{id}.json` gửi trường `tags` và `note` ở dạng **thay thế toàn bộ chuỗi**. Vì vậy bắt buộc phải đọc `GET` trước, hợp nhất chuỗi cũ + mới rồi mới gửi `PUT`.
- **Rollback (`supported: true`):** Dùng `backup_<ts>.json` gọi lại `PUT /com/customers/{id}.json` với đúng cặp `(tags_before, note_before)` để khôi phục nguyên trạng 100%.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.write_customers` | Dừng, báo thiếu quyền ghi khách hàng. |
| `404 Not Found` | `customer_id` đã bị xóa/gộp trước đó | Dừng theo `partial_failure_policy: stop`, ghi log ID lỗi. |
| `422 Unprocessable` | Chuỗi `tags` hoặc `note` vượt quá độ dài tối đa của Haravan | Kiểm tra giới hạn ký tự trước khi `PUT`; không cắt ngang `note` cũ. |
| `429 Too Many Requests` | Cập nhật 100 khách liên tiếp (200 request GET+PUT) | `hrv_client.py` tự throttle ≤ 4 req/s và backoff khi gặp 429. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Gắn nhầm tag kích hoạt Automation Marketing / Zalo ZNS:** Một số shop cài Haravan Automation tự động gửi tin nhắn ZNS ngay khi khách được gắn tag `vip-churn-risk`. Trong bước Dry-Run, Agent phải nhắc người vận hành kiểm tra xem tag mới có nối với luồng gửi tin tự động nào không.
2. **Xung đột hạng thành viên cũ & mới:** Nếu không bật `replace_exclusive_prefix: "rfm-"`, một khách có thể vừa mang tag `rfm-champions` từ quý trước vừa mang `rfm-at-risk` của quý này, gây nhiễu bộ lọc CSKH.
3. **Ghi chú CSKH có chứa dấu phẩy/xuống dòng hoặc ký tự tiếng Việt UTF-8:** Luôn gửi `Content-Type: application/json; charset=utf-8` và bảo toàn xuống dòng `\n` để không làm dính chữ trong Harasocial.

## 8. Liên kết Workflow & Skill kế tiếp
- **Đầu vào:** Nhận danh sách `customer_id` từ `customer-rfm-segmentation`, `customer-vip-churn-watchlist`, hoặc `customer-duplicate-phone-finder`.
- **Đầu ra:** Tag khách hàng sau khi đồng bộ sẽ được `order-triage-tagging-proposal` đọc lại để tự động gắn tag `vip-order` cho các đơn hàng mới.
