---
name: marketing-cart-recovery-zns
description: "Phân tích đơn bỏ quên/chưa thanh toán và lập đề xuất kịch bản nhắc giỏ hàng 3 chạm (1h / 24h / 72h) qua Email và Zalo ZNS."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 70-marketing-omnichannel
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_customers
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
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

# Haravan Abandoned Cart Recovery Playbook (Email & Zalo ZNS)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Khôi phục doanh thu bị rò rỉ từ các đơn hàng khách đã điền thông tin nhưng chưa hoàn tất thanh toán online (chuyển khoản ngân hàng, VNPay, MoMo, ZaloPay) hoặc đơn bỏ dở trong vòng `72` giờ gần nhất bằng kịch bản 3 chạm chuẩn hành vi người dùng Việt Nam (Zalo ZNS + Email).
- **Ngữ cảnh Haravan:** Tại Việt Nam, tỷ lệ mở Email chỉ ~15–20% trong khi Zalo ZNS đạt > 75% tỷ lệ đọc trong 15 phút đầu. Trên Haravan, đơn chọn thanh toán online nhưng chưa trả tiền sẽ ở trạng thái `financial_status: "pending"` và `cancelled_status: "uncancelled"`. Nếu không lọc trùng khách đã đặt lại đơn mới (thường chuyển sang COD), tin nhắn nhắc sẽ gây phản cảm và tốn phí ZNS (~200–350đ/tin).
- **Definition of Done (DoD):**
  1. Thu thập và lọc danh sách đơn đủ điều kiện (giới hạn `max_records <= 100`), loại trừ 100% khách đã có đơn thành công trong `24h` gần nhất.
  2. Phân bổ từng đơn vào đúng nhịp chạm (`Touch 1: 1h`, `Touch 2: 24h`, `Touch 3: 72h`) kèm nội dung mẫu Zalo ZNS (tuân thủ quy định không chứa từ ngữ spam của Zalo OA) và Email.
  3. Sinh file Proposal JSON/CSV qua `scripts/dry_run_report.py` đã che toàn bộ PII (`090****567`, `ng***@gmail.com`) để đội Marketing duyệt trước khi gửi.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_customers` |
| **Endpoints** | `GET /com/orders.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from datetime import datetime, timedelta, timezone
from scripts.hrv_client import HaravanClient, redact_phone, redact_email

client = HaravanClient(dry_run=True)
since = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")
orders = client.paginate(
    surface="com",
    path="/orders.json",
    resource_key="orders",
    params={"created_at_min": since, "financial_status": "pending", "status": "open"},
    limit=50,
    max_pages=10,
)
```

**Ví dụ JSON Response thực tế từ `GET /com/orders.json`:**
```json
{
  "orders": [
    {
      "id": 1492088310,
      "order_number": "#10482",
      "created_at": "2026-11-25T03:10:00+07:00",
      "financial_status": "pending",
      "gateway": "Thanh toán chuyển khoản ngân hàng (VietQR)",
      "total_price": "785000",
      "customer": { "id": 8839201, "first_name": "Minh", "last_name": "Nguyễn", "phone": "0901234567", "email": "minh.ng@gmail.com" },
      "line_items": [{ "title": "Giày Chạy Bộ Ultralight - Size 42", "quantity": 1, "price": "785000" }]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_hours` | `integer` | Không | `72` | Phạm vi `1..168` giờ. Số giờ lùi lại tính từ thời điểm hiện tại (`Asia/Ho_Chi_Minh`). |
| `min_cart_value_vnd` | `integer` | Không | `300000` | Giá trị đơn tối thiểu (`>= 0`) để đáng chi phí gửi ZNS chăm sóc. |
| `exclude_cod` | `boolean` | Không | `true` | Loại trừ đơn COD (`gateway` chứa `COD`/`nhận hàng`) vì đơn COD chờ xác nhận chứ không phải bỏ quên thanh toán. |
| `max_records` | `integer` | Không | `100` | Bắt buộc `<= 100` theo giới hạn an toàn tầng L2. |
| `dry_run` | `boolean` | Bắt buộc | `true` | Luôn giữ `true` khi tạo proposal; không tự gửi tin nhắn qua API ngoài. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Lọc ứng viên (Eligible Orders):**
   - Lấy đơn có `financial_status == "pending"`, `cancelled_status == "uncancelled"`, `total_price >= min_cart_value_vnd`, và nếu `exclude_cod=true` thì bỏ qua đơn có `gateway` chứa `COD`.
2. **Khử trùng thông minh (Anti-Spam Deduplication):**
   - Tải thêm các đơn `financial_status in ("paid", "partially_paid")` hoặc đơn COD đã xác nhận trong `24h` qua.
   - Nếu `customer.id` hoặc số điện thoại (so sánh qua hash nội bộ, không in raw) đã đặt thành công đơn có ít nhất 1 `variant_id` trùng khớp -> **LOẠI BỎ**.
3. **Phân tầng Kịch bản ZNS & Email 3 Chạm (1h / 24h / 72h):**
   - **Chạm 1 (`1h <= age < 24h`) — Nhắc nhẹ & Hỗ trợ thanh toán:** Không tặng mã giảm giá (tránh tạo thói quen bỏ giỏ săn mã). Kênh: **Zalo ZNS (Template Giao dịch)**. Nội dung: nhắc giữ hàng 24h + link/mã VietQR thanh toán nhanh + hotline hỗ trợ.
   - **Chạm 2 (`24h <= age < 48h`) — Giải tỏa rào cản & Niềm tin:** Kênh: **Email + Zalo OA**. Nội dung: giải đáp đổi trả trong 7 ngày, chính sách kiểm hàng trước khi nhận, gợi ý chuyển sang COD nếu gặp lỗi cổng ngân hàng.
   - **Chạm 3 (`48h <= age <= 72h`) — Đòn bẩy chuyển đổi cuối:** Chỉ áp dụng cho đơn `total_price >= 500,000 VND`. Kênh: **Zalo ZNS / Email**. Nội dung: đề xuất tặng mã Freeship hoặc giảm 5% (hạn 24h) — *mã phải được tạo riêng qua skill `marketing-promo-code-proposal`*.
4. **Ước tính Doanh thu Khôi phục & Chi phí ZNS:**
   $$\text{Recoverable Revenue (Est.)} = \sum (\text{total\_price} \times r_{\text{touch}}), \quad r_{1h}=18\%,\; r_{24h}=9\%,\; r_{72h}=5\%$$
   $$\text{Est. ZNS Cost} = N_{\text{zns}} \times 300\text{ VND}$$
5. **Xuất Proposal & Backup:** Gọi `write_dry_run_artifact()` lưu file `hrv-marketing-cart-recovery-zns-<ts>.backup.json` và `.preview.csv` với toàn bộ SĐT/Email đã qua `redact_phone()` / `redact_email()`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Đề xuất Khôi phục Giỏ hàng / Đơn chưa thanh toán (72h gần nhất)
- **Đơn đủ điều kiện:** 28 đơn (đã loại 7 khách đặt lại đơn COD) | **Tổng giá trị giỏ:** 24,650,000 VND
- **Doanh thu khôi phục ước tính:** ~3,120,000 VND | **Chi phí ZNS dự kiến:** ~8,400 VND

| Nhịp chạm | Số đơn | Giá trị giỏ (VND) | Kênh đề xuất | Thông điệp chính |
| --- | ---: | ---: | --- | --- |
| Chạm 1 (1h–24h) | 12 | 10,800,000 | Zalo ZNS (Giao dịch) | Nhắc giữ đơn + hướng dẫn quét VietQR / đổi sang COD |
| Chạm 2 (24h–48h) | 9 | 7,950,000 | Email + Zalo OA | Cam kết đổi trả 7 ngày, hỗ trợ chọn size |
| Chạm 3 (48h–72h) | 7 | 5,900,000 | Zalo ZNS + Email | Đề xuất ưu đãi Freeship (chờ duyệt tạo mã riêng) |

**Mẫu ZNS Chạm 1 (tham khảo):**
> Xin chào Anh/Chị {{customer_name}}, đơn hàng {{order_number}} trị giá {{total_price}}đ tại Shop đang được giữ đến {{hold_until}}. Anh/Chị có thể hoàn tất thanh toán qua VietQR hoặc phản hồi "COD" để đổi sang thanh toán khi nhận hàng.
```

```json
{
  "skill": "marketing-cart-recovery-zns",
  "dry_run": true,
  "summary": { "eligible_orders": 28, "deduped_orders": 7, "total_cart_value_vnd": 24650000, "est_recovery_vnd": 3120000 },
  "proposals": [
    { "order_id": 1492088310, "order_number": "#10482", "touch_stage": "1h", "channel": "zalo_zns", "customer_phone_redacted": "090****567", "customer_email_redacted": "mi***@gmail.com", "total_price_vnd": 785000 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run & Xác nhận (L2):** Bắt buộc `dry_run: true`, `confirmation_required: true`, `max_records <= 100`. Skill chỉ lập danh sách đề xuất và kịch bản; **tuyệt đối không tự gọi API Zalo ZNS/Email** và **không tự tạo mã khuyến mãi** trong cùng bước.
- **Bảo vệ PII (`pii_level: customer`):** Áp dụng `redact_phone()` và `redact_email()` trên mọi báo cáo Markdown, JSON và CSV preview. Không xuất raw danh sách SĐT (`export_allowed: false`).
- **Rollback & Backup:** Lưu snapshot proposal qua `scripts/dry_run_report.py`. Nếu sau đó đội Marketing gắn tag `cart-recovery-sent` lên đơn hàng mà cần hoàn tác, dùng `governance-rollback-executor`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng chạy, không lưu proposal rỗng, báo người dùng cập nhật `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_orders` hoặc `com.read_customers` | Yêu cầu cấp đủ 2 quyền đọc tối thiểu. |
| `404 Not Found` | Endpoint sai hoặc `order_id` đã xóa | Bỏ qua bản ghi lỗi, ghi nhận vào cảnh báo. |
| `422 Unprocessable` | Định dạng `created_at_min` sai chuẩn ISO-8601 | Chuẩn hóa timestamp sang UTC `YYYY-MM-DDTHH:MM:SSZ`. |
| `429 Too Many Requests` | Quét quá nhanh khi đơn nhiều trong Mega Sale | `HaravanClient` tự backoff `1s -> 2s -> 4s`; hạ `limit=50`. |

- **Edge Case 1 — Khách thanh toán chuyển khoản nhưng kế toán chưa bấm "Xác nhận đã thanh toán":** Nếu chỉ dựa vào `financial_status: pending` có thể nhắc nhầm khách đã chuyển tiền rồi. Luôn kiểm tra trường `note` hoặc `tags` xem có dấu hiệu `da-ck` / `cho-duyet-ck` để loại trừ.
- **Edge Case 2 — Đơn thiếu số điện thoại (chỉ có email):** Gắn `channel: "email_only"` thay vì Zalo ZNS để tránh lỗi template ZNS khi gửi.
- **Edge Case 3 — Giờ yên tĩnh (Quiet Hours 21:30–08:00 UTC+7):** Zalo ZNS hạn chế gửi tin tiếp thị ban đêm và dễ gây khó chịu cho khách. Nếu chạy skill sau 21:00, bắt buộc gắn `scheduled_send_window: "08:30-10:00 next day"`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Tạo mã Freeship/Voucher cho Chạm 3 (72h):** Chuyển sang `marketing-promo-code-proposal` (L2) để tạo mã có hạn dùng ngắn (`ends_at`) và giới hạn lượt dùng.
- **Đánh dấu khách đã chăm sóc để tránh gửi trùng:** Chuyển sang `customer-tag-note-proposal` (L2) sau khi được duyệt.
- **Kiểm tra đơn COD rủi ro trước khi chuyển đổi từ online sang COD:** Kết hợp `order-cod-risk-scorer` (L1) nếu đơn có giá trị cao (> 2.000.000 VND).
