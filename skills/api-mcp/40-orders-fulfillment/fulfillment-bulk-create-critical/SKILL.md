---
name: fulfillment-bulk-create-critical
description: "Tạo vận đơn / cập nhật mã tracking hàng loạt (/com/orders/{id}/fulfillments.json) — yêu cầu dry-run, giới hạn ≤ 25 đơn và separate-turn approval."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 40-orders-fulfillment
layer: L3
wave: 3
mode: write
risk: critical
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.write_orders
  endpoints:
    - "GET https://apis.haravan.com/com/orders/{order_id}.json"
    - "POST https://apis.haravan.com/com/orders/{order_id}/fulfillments.json"
    - "PUT https://apis.haravan.com/com/fulfillments/{fulfillment_id}.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 25
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: true
---

# Haravan Bulk Fulfillment & Tracking Creation (Critical L3)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này thực hiện **tạo vận đơn / xác nhận xuất kho và gắn mã tracking hàng loạt** trên Haravan Commerce API (`/com/orders/{id}/fulfillments.json`) sau khi kho đã hoàn tất nhặt hàng, đóng gói và nhận mã vận đơn từ nhà vận chuyển ngoài (Viettel Post thủ công, J&T, Nhất Tín, hoặc đơn tự giao nội thành không đẩy tự động qua app GHN/GHTK tích hợp).

**Tiêu chí hoàn thành (Definition of Done):**
- Mọi `order_id` trong lô (≤ 25 đơn) đã được kiểm tra pre-flight qua `GET /com/orders/{id}.json` (chưa hủy, chưa fulfilled đủ, không còn tag `cod-verify`).
- Đã sinh artifact `dry_run` (Backup JSON + Preview CSV) kèm `idempotency_key` cho từng đơn và nhận được **xác nhận tường minh ở lượt hội thoại riêng (`separate_turn: true`)**.
- Thực thi tuần tự với `partial_failure_policy: stop`, gọi lại `GET` xác minh `fulfillment_status` và xuất Audit Log đầy đủ.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.write_orders` |
| **Endpoints** | `GET /com/orders/{order_id}.json`, `POST /com/orders/{order_id}/fulfillments.json`, `PUT /com/fulfillments/{fulfillment_id}.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=False)  # Chỉ đặt False sau khi có separate-turn approval
order = client.get(f"/com/orders/{order_id}.json")["order"]
res = client.post(f"/com/orders/{order_id}/fulfillments.json", json_body=payload)
```

**JSON Request Payload (`POST /com/orders/1482099012/fulfillments.json`):**
```json
{
  "fulfillment": {
    "location_id": 101,
    "tracking_number": "VTP8923410982",
    "tracking_company": "Viettel Post",
    "tracking_url": "https://viettelpost.com.vn/tra-cuu-hanh-trinh-don?id=VTP8923410982",
    "carrier_cod_status_code": "codpending",
    "notify_customer": false,
    "line_items": [
      { "id": 291004511, "quantity": 2 }
    ]
  }
}
```

**JSON Response Payload (HTTP 201 Created):**
```json
{
  "fulfillment": {
    "id": 88412093,
    "order_id": 1482099012,
    "status": "success",
    "location_id": 101,
    "tracking_company": "Viettel Post",
    "tracking_number": "VTP8923410982",
    "carrier_status_code": "readytopick",
    "carrier_cod_status_code": "codpending",
    "cod_amount": 640000.0,
    "created_at": "2026-04-10T09:15:22Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `fulfillments_file` | string (path/JSON) | Yes | — | Danh sách object `(order_id, tracking_number, tracking_company, location_id, line_items?)`; tối đa `25` bản ghi. |
| `notify_customer` | boolean | No | `false` | Gửi email/SMS thông báo giao hàng cho khách. Mặc định `false` để tránh spam nếu tracking chưa kích hoạt. |
| `update_existing_tracking` | boolean | No | `false` | Nếu `true`, cho phép dùng `PUT /com/fulfillments/{id}.json` cập nhật mã tracking cho vận đơn `pending`. |
| `block_tags` | array[string] | No | `["cod-verify","hold-stock"]` | Chặn tự động các đơn đang mang tag kiểm tra rủi ro/giữ hàng. |
| `dry_run` | boolean | Yes | `true` | Bắt buộc chạy `true` trước để sinh preview + backup; chỉ được `false` ở lượt sau khi đã duyệt. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Validation & Deduplication:** Kiểm tra `len(records) <= 25`. Loại trừ các dòng thiếu `tracking_number` hoặc trùng `tracking_number` trong cùng file.
2. **Pre-Flight Check (`GET /com/orders/{id}.json`):**
   - Chặn ngay (`BLOCKED`) nếu `cancelled_at != null`, `fulfillment_status == "fulfilled"`, hoặc `tags` chứa bất kỳ phần tử nào trong `block_tags`.
   - Kiểm tra `fulfillments[]` hiện có: nếu đã tồn tại vận đơn trùng `tracking_number` → đánh dấu `SKIP_IDEMPOTENT` (không tạo trùng).
   - Xác minh `location_id` hợp lệ và số lượng `line_items[i].fulfillable_quantity >= requested_quantity`.
3. **Sinh Idempotency Key & Dry-Run Artifact:**
   - Công thức: `idempotency_key = sha256(f"{store_domain}:{order_id}:{tracking_number}:{location_id}")[:16]`.
   - Gọi `scripts/dry_run_report.py` xuất `backup_<ts>.json` (chụp nguyên trạng `orders` trước khi ghi) và `preview_<ts>.csv`.
4. **Separate-Turn Gate:** Dừng hội thoại, trình bày bảng preview và mẫu xác nhận.
5. **Thực thi tuần tự (`partial_failure_policy: stop`):**
   - Gửi `POST /com/orders/{order_id}/fulfillments.json` với tốc độ ≤ 2 req/s.
   - Nếu gặp bất kỳ lỗi HTTP 4xx/5xx ở đơn thứ $k$: **dừng ngay lập tức**, không chạy đơn $k+1 \dots n$, ghi log rõ 3 nhóm: `succeeded`, `failed_at`, `not_attempted`.
6. **Post-Write Verification:** Gọi `GET /com/orders/{order_id}.json` cho từng đơn thành công để xác nhận `fulfillment_status` đã chuyển sang `fulfilled` hoặc `partial`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Báo cáo Dry-Run Preview (Tiếng Việt):**
| STT | Mã đơn | SĐT (Redacted) | Kho xuất | NVC | Mã tracking | Trạng thái Pre-flight | Hành động |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `#109201` | `090****412` | Kho HCM (101) | Viettel Post | `VTP8923410982` | `ELIGIBLE` | `CREATE_FULFILLMENT` |
| 2 | `#109202` | `098****119` | Kho HCM (101) | J&T Express | `JT8102938411` | `BLOCKED (tag: cod-verify)` | `SKIP` |
| 3 | `#109203` | `091****882` | Kho HN (102) | Tự giao | `NOITHANH-0410-03` | `SKIP_IDEMPOTENT` | `NO_OP` |

```json
{
  "skill": "fulfillment-bulk-create-critical",
  "mode": "dry_run",
  "separate_turn_required": true,
  "batch_summary": { "requested": 3, "eligible": 1, "blocked": 1, "skipped_idempotent": 1, "succeeded": 0, "failed": 0 },
  "backup_artifact": "artifacts/fulfillment-bulk-create-critical_20260410_backup.json",
  "results": [
    {
      "order_id": 1482099012,
      "order_name": "#109201",
      "phone_redacted": "090****412",
      "idempotency_key": "9f4c2a1e7b80d312",
      "status": "ELIGIBLE",
      "fulfillment_id": null,
      "error": null
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Giới hạn cứng:** `max_records: 25`, `dry_run: true`, `confirmation_required: true`, `separate_turn: true`, `partial_failure_policy: stop`.
- **Mẫu Prompt Xác nhận Bắt buộc (Separate-Turn Approval):**
  > ⚠️ **XÁC NHẬN L3 CRITICAL — TẠO VẬN ĐƠN HÀNG LOẠT**
  > - Cửa hàng: `<store_domain>` (`production`) | Backup: `artifacts/..._backup.json`
  > - Số đơn hợp lệ sẽ tạo vận đơn: **X / 25 đơn** | `notify_customer`: `false`
  > - Lưu ý: Hành động này **trừ tồn kho khả dụng** và đánh dấu xuất kho trên Haravan (`rollback.supported: false`).
  > - Để tiếp tục ở lượt này, vui lòng phản hồi chính xác: **`XÁC NHẬN TẠO X VẬN ĐƠN TRÊN <store_domain>`**.
- **Rollback & Bù trừ:** Haravan không hỗ trợ xóa hoàn toàn bản ghi fulfillment đã tạo; nếu tạo sai, phải hủy vận đơn qua Admin hoặc `POST /com/orders/{order_id}/fulfillments/{id}/cancel.json` và đối chiếu lại cổng NVC (GHN/GHTK/VTP) để tránh shipper vẫn qua lấy hàng.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn hoặc sai biến môi trường `HARAVAN_ACCESS_TOKEN` | Dừng ngay, không retry, báo kiểm tra lại token. |
| `403 Forbidden` | Thiếu scope `com.write_orders` | Dừng ngay, liệt kê scope thiếu theo `config/permissions.yaml`. |
| `404 Not Found` | `order_id` hoặc `location_id` không tồn tại | Dừng theo `partial_failure_policy: stop`, ghi log đơn lỗi. |
| `422 Unprocessable` | Đơn đã `fulfilled`, số lượng vượt `fulfillable_quantity`, hoặc tồn kho âm bị chặn | Dừng ngay, in chi tiết `errors` từ response body để kho kiểm tra. |
| `429 Too Many Requests` | Vượt leaky bucket (80 req / 4 req/s) | `hrv_client.py` tự backoff (1s → 2s → 4s), giảm concurrency về 1 req/s. |

**Tình huống biên thực tế tại Việt Nam:**
1. **GHN/GHTK đồng bộ tự động vs Viettel Post/J&T nhập tay:** Nếu cửa hàng đã cài app GHN/GHTK tự đẩy đơn, việc chạy bulk fulfillment cho cùng đơn sẽ tạo **2 vận đơn song song** gây trừ kho kép hoặc lệch đối soát COD. Pre-flight phải kiểm tra `fulfillments[]` hiện có trước khi tạo.
2. **Đơn giao một phần (Partial Fulfillment / Tách kho HN–HCM):** Một đơn có 2 SKU ở 2 kho khác nhau phải truyền rõ `line_items: [{id, quantity}]` kèm đúng `location_id`; nếu bỏ trống `line_items`, Haravan mặc định fulfill toàn bộ đơn từ 1 kho duy nhất.
3. **Đơn sàn TMĐT (Shopee/TikTok Shop/Lazada):** Không tự tạo fulfillment thủ công trên Haravan cho đơn sàn có `source_name` là `shopee`/`tiktok`/`lazada` vì trạng thái vận đơn do sàn quản lý đồng bộ 1 chiều; pre-flight cần cảnh báo và bỏ qua nếu không có cờ ghi đè.

## 8. Liên kết Workflow & Skill kế tiếp
- **Trước khi chạy:** Chạy `order-risk-cod-boom-signals` để lọc đơn bom hàng và `customer-address-correction-proposal` để chuẩn hóa địa giới hành chính.
- **Sau khi chạy:** Chạy `fulfillment-status-digest-wismo` sau 24–48h để theo dõi đơn kẹt chờ lấy hàng, và `finance-cod-reconciliation` vào cuối tuần để đối soát tiền COD với NVC.
