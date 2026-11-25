---
name: order-cancel-restock-critical
description: "Hủy đơn hàng và hoàn kho có kiểm soát (/com/orders/{id}/cancel.json) — yêu cầu dry-run, xác nhận kho chưa lấy hàng và separate-turn approval."
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
    - "GET https://apis.haravan.com/com/orders/{order_id}/fulfillments.json"
    - "POST https://apis.haravan.com/com/orders/{order_id}/cancel.json"
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

# Haravan Order Cancel & Restock (Critical L3 Mutation)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này thực hiện **hủy đơn hàng và hoàn tồn kho có kiểm soát** trên Haravan (`/com/orders/{id}/cancel.json`). Đây là thao tác **L3 Critical không thể đảo ngược (irreversible)** — Haravan không hỗ trợ mở lại đơn sau khi hủy. Quy trình được thiết kế để chặn đứng 3 rủi ro nghiêm trọng nhất tại kho Việt Nam: (1) hủy đơn khi kho đã đóng gói hoặc shipper đã lấy hàng, (2) hủy đơn đã thanh toán chuyển khoản/VNPay/MoMo mà quên luồng hoàn tiền, và (3) tự động gửi email hủy làm khách hoang mang.

**Tiêu chí hoàn thành (Definition of Done):**
- Mọi `order_id` (≤ 25 đơn) đã qua kiểm tra kép `GET /com/orders/{id}.json` + `GET /com/orders/{id}/fulfillments.json`.
- Đã loại trừ 100% đơn đang vận chuyển (`delivering`/`delivered`), đơn đã hủy, hoặc đơn chưa có xác nhận `warehouse_verified_not_picked: true`.
- Đã sinh Backup JSON + Dry-Run Preview, nhận được **xác nhận tường minh ở lượt hội thoại riêng (`separate_turn: true`)**, chạy tuần tự với `partial_failure_policy: stop` và gọi lại `GET` xác minh `cancelled_at != null`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.write_orders` |
| **Endpoints** | `GET /com/orders/{order_id}.json`, `GET /com/orders/{order_id}/fulfillments.json`, `POST /com/orders/{order_id}/cancel.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=False)  # Chỉ đặt False ở lượt sau khi đã duyệt
order = client.get(f"/com/orders/{order_id}.json")["order"]
fulfillments = client.get(f"/com/orders/{order_id}/fulfillments.json")["fulfillments"]
res = client.post(f"/com/orders/{order_id}/cancel.json", json_body=payload)
```

**JSON Request Payload (`POST /com/orders/1482088120/cancel.json`):**
```json
{
  "reason": "customer",
  "email": false,
  "restock": true,
  "note": "Hủy theo yêu cầu khách qua CSKH - Đã xác nhận kho chưa picking (Ref: CSKH-20260410)"
}
```

**JSON Response Payload (HTTP 200 OK):**
```json
{
  "order": {
    "id": 1482088120,
    "name": "#109188",
    "cancelled_at": "2026-04-10T10:05:14Z",
    "cancel_reason": "customer",
    "financial_status": "voided",
    "fulfillment_status": "unshipped",
    "total_price": 1250000.0
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `order_ids` | array[integer] | Yes | — | Danh sách `order_id` cần hủy; tối đa `25` đơn/lần chạy. |
| `reason` | enum | Yes | `"customer"` | Một trong: `customer` (khách đổi ý), `inventory` (hết hàng), `fraud` (nghi gian lận), `other`. |
| `restock` | boolean | No | `true` | Hoàn số lượng sản phẩm về tồn kho khả dụng (`qty_available`). |
| `notify_customer` | boolean | No | `false` | Gửi email hủy đơn cho khách (`email` trong payload); mặc định `false` để an toàn. |
| `warehouse_verified_not_picked` | boolean | Yes | `false` | Bắt buộc người vận hành xác nhận `true` (kho chưa đóng gói/bàn giao NVC) trước khi apply. |
| `dry_run` | boolean | Yes | `true` | Mặc định `true`; bắt buộc chạy preview trước khi thực thi ghi. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Kiểm tra giới hạn lô:** Chặn ngay nếu `len(order_ids) > 25` hoặc danh sách rỗng.
2. **Pre-Flight Safety Gate (bắt buộc cho từng `order_id`):**
   - Gọi `GET /com/orders/{id}.json` và `GET /com/orders/{id}/fulfillments.json`.
   - **Quy tắc chặn cứng (`HARD_BLOCK`):**
     - `cancelled_at != null` → `SKIP_ALREADY_CANCELLED`.
     - Có bất kỳ fulfillment đang hoạt động với `carrier_status_code` $\in$ `{"picking", "delivering", "delivered", "return"}` → `BLOCKED_IN_TRANSIT` (yêu cầu hủy vận đơn trên cổng NVC trước).
     - `source_name` $\in$ `{"shopee", "tiktok", "lazada"}` → `BLOCKED_MARKETPLACE` (đơn sàn phải hủy từ Seller Center để tránh phạt sao quả tạ).
   - **Quy tắc cảnh báo tài chính (`WARN_PREPAID`):** Nếu `financial_status` là `paid` hoặc `partially_paid`, gắn cờ nổi bật yêu cầu kế toán xử lý hoàn tiền chuyển khoản/VNPay/MoMo (skill này **không tự hoàn tiền**).
3. **Sinh Backup & Dry-Run Report:** Tạo `idempotency_key = sha256(f"cancel:{store_domain}:{order_id}:{reason}")[:16]`, xuất backup JSON (chụp toàn bộ `order` + `line_items` + `fulfillments`) và preview CSV qua `scripts/dry_run_report.py`.
4. **Separate-Turn Confirmation Gate:** Dừng hội thoại, trình bày bảng đơn hợp lệ + đơn bị chặn + tổng số lượng SKU sẽ hoàn kho, chờ người dùng xác nhận ở lượt kế tiếp.
5. **Thực thi tuần tự (`partial_failure_policy: stop`):** Gọi `POST /com/orders/{id}/cancel.json` lần lượt từng đơn. Gặp lỗi đầu tiên → **dừng ngay**, báo rõ đơn đã hủy, đơn lỗi và đơn chưa chạy.
6. **Post-Write Verification:** Gọi `GET /com/orders/{id}.json` xác nhận `cancelled_at != null` và `cancel_reason == reason`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Báo cáo Dry-Run Hủy Đơn & Hoàn Kho:**
| STT | Mã đơn | SĐT (Redacted) | Thanh toán | Vận đơn hiện tại | Tổng tiền (VND) | Trạng thái Pre-flight | Dự kiến Restock |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `#109188` | `090****612` | COD (`pending`) | Chưa tạo | 1.250.000 | `ELIGIBLE` | +2 SKU (Kho 101) |
| 2 | `#109190` | `091****305` | VNPay (`paid`) | Chưa tạo | 850.000 | `ELIGIBLE (WARN_PREPAID)` | +1 SKU (Kho 101) |
| 3 | `#109195` | `098****774` | COD (`pending`) | GHN (`delivering`) | 540.000 | `BLOCKED_IN_TRANSIT` | 0 (Bỏ qua) |

```json
{
  "skill": "order-cancel-restock-critical",
  "mode": "dry_run",
  "separate_turn_required": true,
  "warehouse_verified_not_picked": false,
  "summary": { "requested": 3, "eligible": 2, "warn_prepaid": 1, "blocked": 1, "cancelled": 0 },
  "backup_artifact": "artifacts/order-cancel-restock-critical_20260410_backup.json",
  "orders": [
    {
      "order_id": 1482088120,
      "order_name": "#109188",
      "phone_redacted": "090****612",
      "financial_status": "pending",
      "status": "ELIGIBLE",
      "restock": true,
      "idempotency_key": "c71a92e04b3f118a"
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Giới hạn cứng:** `max_records: 25`, `dry_run: true`, `confirmation_required: true`, `separate_turn: true`, `partial_failure_policy: stop`.
- **Mẫu Prompt Xác nhận Bắt buộc (Separate-Turn Approval):**
  > 🚨 **CẢNH BÁO L3 CRITICAL — HỦY ĐƠN HÀNG (KHÔNG THỂ ĐẢO NGƯỢC)**
  > - Cửa hàng: `<store_domain>` | Backup JSON: `artifacts/..._backup.json`
  > - Số đơn sẽ hủy vĩnh viễn: **X đơn** (`restock: true`, `notify_customer: false`) | Trong đó có **Y đơn đã thanh toán trước** cần hoàn tiền thủ công.
  > - Xác nhận vật lý: Bạn xác nhận **kho chưa đóng gói / chưa bàn giao shipper** cho toàn bộ X đơn trên?
  > - Để thực thi, vui lòng phản hồi chính xác: **`XÁC NHẬN HỦY X ĐƠN — KHO CHƯA PICKING — <store_domain>`**.
- **Rollback (`supported: false`):** Không thể mở lại đơn đã hủy trên Haravan. Nếu hủy nhầm, nhân viên phải tạo lại Draft Order mới từ file Backup JSON và đối chiếu lại tồn kho/thanh toán.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng ngay, không retry. |
| `403 Forbidden` | Thiếu `com.write_orders` | Dừng ngay, yêu cầu cấp quyền tối thiểu. |
| `404 Not Found` | `order_id` không tồn tại | Dừng theo `partial_failure_policy: stop`, kiểm tra lại danh sách ID. |
| `422 Unprocessable` | Đơn đã đóng (`closed`), đã hủy, hoặc có fulfillment chưa hủy | Dừng ngay, in lỗi chi tiết từ Haravan; không tự ý ép hủy vận đơn. |
| `429 Too Many Requests` | Vượt leaky bucket (80 req / 4 req/s) | Backoff tự động qua `hrv_client.py` (1s → 2s → 4s). |

**Tình huống biên thực tế tại Việt Nam:**
1. **Kho đã in phiếu giao hàng / dán mã vận đơn nhưng chưa quét bàn giao trên hệ thống:** Trạng thái API vẫn là `readytopick` nhưng hàng đã nằm trong bao giao cho shipper GHN/GHTK. Đó là lý do tham số `warehouse_verified_not_picked: true` bắt buộc phải có xác nhận từ thủ kho.
2. **Đơn đã thanh toán một phần (đặt cọc chuyển khoản 200k + COD phần còn lại):** Haravan không tự động hoàn tiền cọc về tài khoản ngân hàng khách khi gọi `/cancel.json`; kế toán phải căn cứ cờ `WARN_PREPAID` để hoàn cọc thủ công và lưu ủy nhiệm chi.
3. **Đơn có sử dụng mã giảm giá 1 lần / điểm Haraloyalty:** Việc hủy đơn có thể không tự động hoàn lại lượt dùng mã khuyến mãi tùy cấu hình app; cần ghi chú cho CSKH nếu khách đặt lại đơn mới.

## 8. Liên kết Workflow & Skill kế tiếp
- **Trước khi chạy:** Xác minh chi tiết đơn qua `order-lookup-summary` hoặc lọc đơn nghi bom hàng từ `order-risk-cod-boom-signals` (nhưng chỉ hủy sau khi CSKH gọi xác nhận thất bại/khách yêu cầu hủy).
- **Sau khi chạy:** Theo dõi tác động tài chính tại `finance-refund-rate-analysis` và nguyên nhân hoàn/hủy tại `returns-reason-restock-proposal`.
