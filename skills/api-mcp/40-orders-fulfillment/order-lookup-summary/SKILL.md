---
name: order-lookup-summary
description: "Tra cứu nhanh chi tiết đơn hàng, trạng thái thanh toán, vận đơn và lịch sử giao dịch phục vụ CSKH (đã che PII khi xuất báo cáo)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 40-orders-fulfillment
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/orders/{order_id}.json"
    - "GET https://apis.haravan.com/com/orders/{order_id}/fulfillments.json"
    - "GET https://apis.haravan.com/com/orders/{order_id}/transactions.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 100
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---

# Haravan Order Lookup & CSKH Summary

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này cung cấp **hồ sơ 360° trong 1 màn hình** cho một đơn hàng Haravan (đặt từ Haraweb, Harasocial, HaraRetail POS, Shopee, TikTok Shop hoặc Lazada), giúp nhân viên CSKH trả lời khách trong vài giây: đơn đang ở khâu nào, đã thanh toán hay còn thu hộ COD bao nhiêu, mã vận đơn NVC nào, và đã có giao dịch hoàn tiền hay chưa.

**Tiêu chí hoàn thành (Definition of Done):**
- Tìm đúng đơn hàng từ `order_id`, mã hiển thị `#10245`, hoặc tra cứu theo số điện thoại đã chuẩn hóa (`+84`/`0`).
- Hợp nhất đủ 3 nguồn dữ liệu: `order` (sản phẩm, giảm giá, ghi chú, tag), `fulfillments` (mã tracking, trạng thái NVC), và `transactions` (lịch sử thanh toán/cọc/hoàn tiền).
- Redact đầy đủ PII (`090****567`, `ng***@gmail.com`, ẩn số nhà khi chia sẻ kênh chung) và tính chính xác số tiền COD còn phải thu.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/orders/{order_id}.json`, `GET /com/orders/{order_id}/fulfillments.json`, `GET /com/orders/{order_id}/transactions.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
order = client.get(f"/com/orders/{order_id}.json")["order"]
fulfillments = client.get(f"/com/orders/{order_id}/fulfillments.json")["fulfillments"]
txns = client.get(f"/com/orders/{order_id}/transactions.json")["transactions"]
```

**JSON Response tổng hợp từ `GET /com/orders/{id}/transactions.json`:**
```json
{
  "transactions": [
    {
      "id": 77102911,
      "order_id": 1482055001,
      "kind": "capture",
      "gateway": "Chuyển khoản ngân hàng",
      "status": "success",
      "amount": 200000.0,
      "created_at": "2026-04-08T04:12:00Z"
    },
    {
      "id": 77102989,
      "order_id": 1482055001,
      "kind": "pending",
      "gateway": "Thanh toán khi giao hàng (COD)",
      "status": "pending",
      "amount": 650000.0,
      "created_at": "2026-04-08T04:12:05Z"
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `order_id_or_name` | string / int | Conditional | — | `order_id` số nguyên (vd `1482055001`) hoặc mã đơn (vd `#109120`). Bắt buộc nếu không nhập `phone`. |
| `phone` | string | Conditional | — | SĐT khách hàng (hỗ trợ `090...`, `+8490...`, `8490...`) để lấy tối đa `recent_limit` đơn gần nhất. |
| `recent_limit` | integer | No | `5` | Số đơn gần nhất trả về khi tra cứu theo `phone` (`1`–`20`). |
| `include_timeline` | boolean | No | `true` | Gộp mốc thời gian tạo đơn → xác nhận → xuất kho → giao hàng. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Định danh đơn hàng (Lookup Resolution):**
   - Nếu đầu vào là chuỗi số $\ge 7$ chữ số → gọi trực tiếp `GET /com/orders/{order_id}.json`.
   - Nếu bắt đầu bằng `#` hoặc mã đơn ngắn → gọi `GET /com/orders.json?name=<name>&status=any`.
   - Nếu tra theo `phone` → chuẩn hóa SĐT về `0xxxxxxxxx`, quét `GET /com/orders.json?status=any` (trong giới hạn `max_records: 100` hoặc lọc theo khách) và sắp xếp giảm dần theo `created_at`.
2. **Tổng hợp tài chính & Công thức COD còn phải thu:**
   - $\text{PaidAmount} = \sum \text{txn.amount}$ với `kind` $\in$ `{"sale", "capture"}` và `status == "success"`.
   - $\text{RefundedAmount} = \sum \text{txn.amount}$ với `kind == "refund"` và `status == "success"`.
   - $\text{RemainingCOD} = \max(0, \text{total\_price} - \text{PaidAmount} - \text{RefundedAmount})$ (nếu đơn chưa hủy).
3. **Tổng hợp giao vận:** Lấy danh sách `fulfillments[]`, đánh dấu rõ vận đơn hiện hành (`active`) so với vận đơn đã hủy (`cancelled`), kèm link tra cứu NVC tương ứng.
4. **Che PII (Redaction):** Áp dụng `redact_phone()` (`090****567`), che email (`ng***@gmail.com`) và chỉ hiển thị `Quận/Huyện, Tỉnh/Thành` cho địa chỉ giao hàng.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Tóm tắt Đơn hàng CSKH — `#109120` (ID: `1482055001`):**
- **Kênh & Thời gian:** `harasocial` | Tạo lúc `08/04/2026 11:12 (UTC+7)` | Tag: `cod-verified, khach-quen`
- **Khách hàng (Redacted):** ID `70122` | SĐT: `090****567` | Khu vực: `Quận 1, TP. Hồ Chí Minh`
- **Thanh toán:** Đã cọc `200.000đ` (Chuyển khoản) | **Còn thu COD: `650.000đ`** | Tổng đơn: `850.000đ` (Giảm giá: `-50.000đ`, Ship: `30.000đ`)
- **Vận đơn hiện hành:** `GHN` — Mã `G89KLM11` | Trạng thái: `Đang giao hàng (delivering)` | Cập nhật: `09/04/2026 14:20`

| SKU | Sản phẩm | SL | Đơn giá (VND) | Thành tiền (VND) |
| --- | --- | --- | --- | --- |
| `TRA-200G` | Trà Thảo Mộc Thanh Nhiệt 200g | 2 | 185.000 | 370.000 |
| `MO-500ML` | Mật Ong Rừng Nguyên Chất 500ml | 1 | 500.000 | 500.000 |

```json
{
  "skill": "order-lookup-summary",
  "order": {
    "id": 1482055001,
    "name": "#109120",
    "source_name": "harasocial",
    "created_at_vn": "2026-04-08T11:12:00+07:00",
    "customer_id": 70122,
    "phone_redacted": "090****567",
    "email_redacted": "ng***@gmail.com",
    "area": "Quận 1, TP. Hồ Chí Minh",
    "financial_status": "partially_paid",
    "total_price_vnd": 850000,
    "paid_amount_vnd": 200000,
    "refunded_amount_vnd": 0,
    "remaining_cod_vnd": 650000,
    "fulfillment_status": "fulfilled",
    "active_tracking": { "carrier": "GHN", "tracking_number": "G89KLM11", "carrier_status": "delivering" }
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Chỉ gọi `GET`; không sửa ghi chú, không đổi địa chỉ, không hủy đơn và không tự gửi tin nhắn cho khách.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Tuân thủ `policies/pii-handling.md`; không hiển thị số điện thoại đầy đủ, email đầy đủ hay số nhà trong output Markdown/JSON.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng và báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, thông báo thiếu quyền đọc đơn hàng. |
| `404 Not Found` | `order_id` sai hoặc không thuộc shop hiện tại | Trả rõ không tìm thấy, gợi ý thử tra theo mã `#name` hoặc `phone`. |
| `422 Unprocessable` | Tham số query không hợp lệ | Kiểm tra URL-encoding cho ký tự `#` trong `name=%23109120`. |
| `429 Too Many Requests` | Quá giới hạn leaky bucket | Tự động retry backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Đơn đặt cọc chuyển khoản + COD phần còn lại (`partially_paid`):** Nếu chỉ đọc `total_price`, CSKH dễ báo nhầm số tiền thu hộ cho khách. Bắt buộc phải lấy `transactions.json` để trừ phần đã `capture` thành công.
2. **Đơn từ sàn TMĐT (Shopee/TikTok) bị ẩn SĐT thật (`*******`):** Sàn TMĐT che thông tin khách hàng khi đồng bộ về Haravan; không thể tra theo `phone` cho đơn sàn, cần yêu cầu CSKH cung cấp mã đơn sàn (`ref_order_number` hoặc `#name`).
3. **Một mã `#109120` xuất hiện ở trạng thái đã lưu trữ (`closed`) hoặc đã hủy (`cancelled`):** Mặc định `GET /com/orders.json` trên Haravan chỉ trả về `status=open`; **bắt buộc** luôn truyền `status=any` khi tìm kiếm theo tên đơn để không bị sót đơn cũ.

## 8. Liên kết Workflow & Skill kế tiếp
- **Nếu đơn giao chậm/lỗi NVC:** Chuyển sang `fulfillment-status-digest-wismo` để kiểm tra toàn tuyến.
- **Nếu khách yêu cầu đổi địa chỉ giao hàng:** Chuyển sang `customer-address-correction-proposal`.
- **Nếu khách yêu cầu hủy đơn (chưa xuất kho):** Chuyển sang `order-cancel-restock-critical`.
