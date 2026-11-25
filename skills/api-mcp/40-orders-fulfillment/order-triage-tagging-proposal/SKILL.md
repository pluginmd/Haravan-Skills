---
name: order-triage-tagging-proposal
description: "Phân loại và đề xuất gắn nhãn (tags) hàng loạt cho đơn hàng Haravan (/com/orders/{id}/tags.json) theo kênh, rủi ro COD, VIP hoặc yêu cầu xuất hóa đơn."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 40-orders-fulfillment
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.write_orders
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "POST https://apis.haravan.com/com/orders/{order_id}/tags.json"
    - "DELETE https://apis.haravan.com/com/orders/{order_id}/tags.json"
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

# Haravan Order Triage & Automated Tagging Proposal

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này tự động hóa quy trình **phân luồng đơn hàng (Order Triage)** trên Haravan bằng hệ thống nhãn (`tags`) chuẩn hóa: `cod-verify` (đơn COD rủi ro cao cần CSKH gọi), `vip-order` (ưu tiên đóng gói trước), `xuat-vat` (đơn có yêu cầu xuất hóa đơn điện tử GTGT), `giao-hoa-toc` (đơn nội thành giao 2h), và `don-si` (đơn giá trị/số lượng lớn). Nhờ đó kho và kế toán chỉ cần lọc theo tag trong Haravan Admin thay vì mở từng đơn đọc ghi chú.

**Tiêu chí hoàn thành (Definition of Done):**
- Quét đơn hàng trong `lookback_hours` (tối đa `100` đơn/lô), áp dụng `tagging_rules` để sinh danh sách diff `add_tags` / `remove_tags` mà **không làm mất tag vận hành hiện có**.
- Tạo Backup JSON + Preview CSV qua `scripts/dry_run_report.py` với `dry_run: true` mặc định và nhận xác nhận người dùng trước khi gọi `POST`/`DELETE`.
- Gọi lại `GET /com/orders/{id}.json` xác minh tag mới đã được lưu đúng sau khi apply.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.write_orders` |
| **Endpoints** | `GET /com/orders.json`, `POST /com/orders/{order_id}/tags.json`, `DELETE /com/orders/{order_id}/tags.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=False)  # Chỉ False sau khi duyệt preview
client.post(f"/com/orders/{order_id}/tags.json", json_body={"tags": "vip-order,xuat-vat"})
```

**JSON Request Payload (`POST /com/orders/1482099012/tags.json`):**
```json
{
  "tags": "vip-order,xuat-vat"
}
```

**JSON Response Payload (HTTP 200 OK):**
```json
{
  "order": {
    "id": 1482099012,
    "name": "#109201",
    "tags": "harasocial, vip-order, xuat-vat"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `tagging_rules` | array[object] | No | Bộ luật chuẩn VN | Danh sách `{rule_id, condition, add_tags, remove_tags}`. Nếu bỏ trống dùng 5 luật mặc định. |
| `lookback_hours` | integer | No | `24` | Phạm vi đơn cần phân loại (`1`–`168` giờ). |
| `protected_tag_prefixes` | array[string] | No | `["shopee-","tiktok-","lazada-","ghn-","ghtk-","erp-"]` | Không bao giờ được xóa hoặc sửa các tag hệ thống có prefix này. |
| `max_records` | integer | No | `100` | Giới hạn cứng ≤ `100` đơn/lần chạy. |
| `dry_run` | boolean | Yes | `true` | Mặc định `true` để tạo preview diff + backup trước khi ghi. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Đánh giá Bộ luật Phân loại Mặc định (Default Triage Rules):**
   - `RULE_VAT`: `order.note` hoặc `note_attributes` khớp regex `(mst|mã số thuế|hóa đơn|vat|cty|công ty)` → thêm `xuat-vat`.
   - `RULE_VIP`: `customer.tags` chứa `VIP` hoặc `total_price >= 5000000` → thêm `vip-order`.
   - `RULE_COD_VERIFY`: Điểm từ `order-risk-cod-boom-signals` $\ge 60$ → thêm `cod-verify`.
   - `RULE_EXPRESS`: `shipping_lines[].title` chứa `(hỏa tốc|ahamove|grab|nowship|2h)` → thêm `giao-hoa-toc`.
   - `RULE_WHOLESALE`: Tổng số lượng `sum(line_items.quantity) >= 15` → thêm `don-si`.
2. **Chuẩn hóa & Hợp nhất Tag (Idempotent Set Merge):**
   - Tách `existing_tags = {t.strip().lower() for t in order.tags.split(",") if t.strip()}`.
   - Tính `to_add = desired_add - existing_tags`; `to_remove = (desired_remove & existing_tags) - protected_tags`.
   - Nếu `to_add` và `to_remove` đều rỗng → đánh dấu `NO_OP` (không gọi API ghi).
3. **Dry-Run & Backup:** Lưu nguyên văn `order.tags` cũ vào `backup_<ts>.json` qua `scripts/dry_run_report.py` để hỗ trợ rollback 100%.
4. **Thực thi & Xác minh:** Sau khi người dùng duyệt preview, gọi `POST /com/orders/{id}/tags.json` (và `DELETE` nếu có `to_remove`) tuần tự với `partial_failure_policy: stop`, sau đó `GET` kiểm tra lại chuỗi `tags`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Bảng Preview Gắn Tag Đơn Hàng (Dry-Run — 24h qua):**
| STT | Mã đơn | SĐT (Redacted) | Tag hiện có | Tag thêm mới | Tag gỡ bỏ | Luật khớp |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `#109201` | `090****412` | `harasocial` | `+vip-order`, `+xuat-vat` | — | `RULE_VIP`, `RULE_VAT` |
| 2 | `#109215` | `090****567` | — | `+cod-verify` | — | `RULE_COD_VERIFY` |
| 3 | `#109222` | `093****901` | `shopee-express` | `+giao-hoa-toc` | — | `RULE_EXPRESS` |

```json
{
  "skill": "order-triage-tagging-proposal",
  "mode": "dry_run",
  "total_scanned": 86,
  "total_changes": 14,
  "backup_artifact": "artifacts/order-triage-tagging-proposal_20260410_backup.json",
  "rollback_supported": true,
  "proposals": [
    {
      "order_id": 1482099012,
      "order_name": "#109201",
      "phone_redacted": "090****412",
      "tags_before": ["harasocial"],
      "add_tags": ["vip-order", "xuat-vat"],
      "remove_tags": [],
      "matched_rules": ["RULE_VIP", "RULE_VAT"]
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Giới hạn L2 Proposal:** `dry_run: true`, `confirmation_required: true`, `max_records: 100`, `partial_failure_policy: stop`.
- **Bảo vệ Tag hệ thống:** Không bao giờ xóa tag có tiền tố của sàn TMĐT (`shopee-`, `tiktok-`, `lazada-`) hoặc app vận chuyển/ERP, vì nhiều luồng đồng bộ kho dựa vào các tag này.
- **Quy trình Rollback (`supported: true`):** Đọc file `backup_<ts>.json`, gọi `DELETE /com/orders/{id}/tags.json` với danh sách `add_tags` đã thêm và `POST` lại các `remove_tags` (nếu có) để khôi phục chính xác trạng thái cũ.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng ngay, yêu cầu kiểm tra token. |
| `403 Forbidden` | Thiếu scope `com.write_orders` | Dừng ngay, báo quyền thiếu. |
| `404 Not Found` | `order_id` không tồn tại | Dừng theo `partial_failure_policy: stop`, ghi log. |
| `422 Unprocessable` | Chuỗi tag chứa ký tự đặc biệt không hợp lệ hoặc vượt độ dài | Chỉ dùng ký tự `[a-z0-9-]`, độ dài mỗi tag ≤ 40 ký tự. |
| `429 Too Many Requests` | Gắn tag 100 đơn liên tiếp | `hrv_client.py` tự throttle ≤ 4 req/s và backoff khi gặp 429. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Khách viết ghi chú tiếng Việt có dấu / viết tắt không đồng nhất ("xuất HĐ", "lấy VAT cty", "MST: 031..."):** Luật `RULE_VAT` phải chuẩn hóa Unicode/lowercase và bắt cả cụm viết tắt `hđ`, `hdgtgt`, `mst` để tránh sót đơn cần xuất hóa đơn điện tử.
2. **Đơn bị hủy trước khi chạy triage:** Nên loại trừ đơn `cancelled_at != null` khỏi luật `vip-order`/`giao-hoa-toc` để kho không nhìn nhầm đơn cần đóng gói gấp.
3. **Tag phân biệt hoa thường trên Haravan:** Một số nhân viên gắn tay `VIP-Order` trong khi luật gắn `vip-order`; so sánh theo `lowercase` trước khi thêm để tránh trùng lặp gây rối bộ lọc Haravan Admin.

## 8. Liên kết Workflow & Skill kế tiếp
- **Đầu vào rủi ro COD:** Nhận danh sách đơn rủi ro từ `order-risk-cod-boom-signals`.
- **Đầu ra kế toán thuế:** Các đơn gắn tag `xuat-vat` được tổng hợp cuối tháng bởi `finance-tax-vat-summary`.
- **Đầu ra xuất kho:** Các đơn sạch (không có `cod-verify`) chuyển sang `fulfillment-bulk-create-critical`.
