---
name: marketing-winback-campaign
description: "Xây dựng chiến dịch kéo lại khách hàng ngủ đông (Hibernating/At-Risk) từ dữ liệu RFM Haravan với thông điệp và ưu đãi phân tầng."
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
    - com.read_customers
    - com.read_orders
  endpoints:
    - "GET https://apis.haravan.com/com/customers.json"
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

# Haravan Customer Win-Back Campaign Planner

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Tái kích hoạt nhóm khách hàng cũ đang ngủ đông (`At-Risk` & `Hibernating`, chưa quay lại mua từ `60` đến `180` ngày) với chi phí thấp hơn 4–6 lần so với chạy quảng cáo tìm khách mới (CAC), thông qua ưu đãi phân tầng theo giá trị vòng đời khách hàng (LTV).
- **Ngữ cảnh Haravan:** Dữ liệu khách hàng Haravan (`/com/customers.json`) kết hợp lịch sử đơn (`/com/orders.json`) cho phép xác định chính xác ngày mua gần nhất (`last_order_date`), số đơn thành công (`orders_count`), tổng chi tiêu (`total_spent`) và kênh mua quen thuộc (`web`, `pos`, `harasocial`). Thay vì phát cùng một mã giảm giá cho toàn bộ tệp (gây bào mòn biên lợi nhuận), chiến dịch Win-Back cần tách riêng VIP ngủ đông và khách phổ thông.
- **Definition of Done (DoD):**
  1. Xác định tập khách hàng đủ điều kiện (giới hạn `max_records <= 100` cho mỗi đợt proposal), loại trừ khách có đơn hoàn/hủy cao hoặc đang có khiếu nại.
  2. Phân nhóm thành `Tier A — VIP At-Risk` và `Tier B — Standard Hibernating`, kèm kịch bản thông điệp đa kênh (Zalo ZNS, Email, Harasocial Inbox) và mô hình dự báo ROI.
  3. Xuất Proposal JSON/CSV qua `scripts/dry_run_report.py` đã che toàn bộ PII (`redact_phone`, `redact_email`) chờ duyệt trước khi gắn tag hoặc tạo mã giảm giá.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_customers`, `com.read_orders` |
| **Endpoints** | `GET /com/customers.json`, `GET /com/orders.json` |

**Ví dụ gọi qua `scripts/hrv_client.py` (kết hợp phân tích RFM từ `hrv_ops.py rfm`):**
```python
from scripts.hrv_client import HaravanClient, redact_phone, redact_email

client = HaravanClient(dry_run=True)
customers = client.paginate(
    surface="com",
    path="/customers.json",
    resource_key="customers",
    params={"fields": "id,first_name,last_name,phone,email,orders_count,total_spent,tags,last_order_id"},
    limit=50,
    max_pages=20,
)
```

**Ví dụ JSON Response thực tế từ `GET /com/customers.json?limit=1`:**
```json
{
  "customers": [
    {
      "id": 8821045,
      "first_name": "Lan",
      "last_name": "Trần",
      "phone": "0912345678",
      "email": "lan.tran@company.vn",
      "orders_count": 5,
      "total_spent": "6450000",
      "tags": "VIP, mua-online",
      "last_order_id": 1410293844
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `inactive_days_min` | `integer` | Không | `60` | Số ngày tối thiểu từ đơn mua gần nhất (`>= 30`). |
| `inactive_days_max` | `integer` | Không | `180` | Số ngày tối đa (`> inactive_days_min`, khuyến nghị `<= 365`). |
| `vip_spent_threshold_vnd` | `integer` | Không | `3000000` | Ngưỡng tổng chi tiêu tích lũy (VND) để xếp vào nhóm `Tier A — VIP At-Risk`. |
| `exclude_tags` | `array[string]` | Không | `["blacklist", "boom-hang", "do-not-contact"]` | Danh sách tag khách hàng bắt buộc loại trừ khỏi chiến dịch. |
| `max_records` | `integer` | Không | `100` | Tối đa `100` khách hàng/lần lập proposal. |
| `dry_run` | `boolean` | Bắt buộc | `true` | Luôn giữ `true` ở bước lập kế hoạch. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Tính Recency thực tế từ lịch sử đơn hàng:**
   - Đối chiếu `last_order_id` hoặc đơn hoàn tất gần nhất (`financial_status == "paid"` và `cancelled_status == "uncancelled"`) để tính:
     $$\text{Recency (ngày)} = \text{Today}_{\text{UTC+7}} - \text{last\_completed\_order\_date}$$
   - Lọc khách thỏa mãn `inactive_days_min <= Recency <= inactive_days_max` và không mang tag trong `exclude_tags`.
2. **Phân tầng Ưu đãi (Tiered Offer Strategy):**
   - **Tier A — VIP At-Risk (`total_spent >= vip_spent_threshold_vnd` hoặc `orders_count >= 3`):**
     - *Kênh:* Chăm sóc 1-1 qua Harasocial / Zalo OA cá nhân hóa.
     - *Ưu đãi:* Quà tặng kèm hoặc Freeship + Voucher giảm `12%` (đơn tối thiểu = `0.9 * AOV_khách`), hạn `7 ngày`.
     - *Mục tiêu:* Giữ cảm giác được trân trọng, không phá giá thương hiệu.
   - **Tier B — Standard Hibernating (1–2 đơn cũ, `total_spent < vip_spent_threshold_vnd`):**
     - *Kênh:* Zalo ZNS + Email tự động.
     - *Ưu đãi:* Voucher giảm cố định `50,000đ` cho đơn từ `499,000đ`, hạn `5 ngày`.
3. **Dự báo Hiệu quả & ROI Chiến dịch (Operational Estimate):**
   $$\text{Est. Orders} = N_A \cdot 0.14 + N_B \cdot 0.06$$
   $$\text{Est. Revenue} = (N_A \cdot 0.14 \cdot \text{AOV}_A) + (N_B \cdot 0.06 \cdot \text{AOV}_B)$$
   $$\text{Est. Cost} = (N_A + N_B) \cdot 300\text{đ (ZNS)} + \text{Est. Discount Cost}$$
   $$\text{Projected ROI} = \frac{\text{Est. Gross Profit} - \text{Est. Cost}}{\text{Est. Cost}}$$
4. **Xuất Proposal:** Lưu danh sách khách hàng đề xuất (đã redact PII) qua `write_dry_run_artifact()`. Không tự gắn tag, không tự tạo mã, không tự gửi tin.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Kế hoạch Chiến dịch Win-Back Khách Hàng Ngủ Đông (60–180 ngày)
- **Tệp mục tiêu hợp lệ:** 84 khách (đã loại 11 khách tag `boom-hang`/hủy đơn cao)
- **Doanh thu kỳ vọng (Operational Estimate):** ~11,450,000 VND | **Chi phí ZNS + Ưu đãi:** ~1,420,000 VND

| Phân tầng | Số khách | Tiêu chí | Kênh tiếp cận | Ưu đãi đề xuất | Tỷ lệ quay lại kỳ vọng |
| --- | ---: | --- | --- | --- | ---: |
| Tier A — VIP At-Risk | 24 | Chi tiêu ≥ 3tr hoặc ≥ 3 đơn | Harasocial + Zalo OA | Quà tặng + Mã `VIPBACK12` (hạn 7 ngày) | 14% (~3–4 đơn) |
| Tier B — Standard | 60 | 1–2 đơn, 60–180 ngày | Zalo ZNS + Email | Mã `QUAYLAI50K` đơn ≥ 499k (hạn 5 ngày) | 6% (~3–4 đơn) |

> *Tuyên bố tài chính:* Dự báo doanh thu và ROI là ước tính vận hành phục vụ lập kế hoạch, không phải cam kết doanh thu chắc chắn.
```

```json
{
  "skill": "marketing-winback-campaign",
  "dry_run": true,
  "window_days": [60, 180],
  "segments": {
    "tier_a_vip": { "count": 24, "avg_ltv_vnd": 5200000, "suggested_tag": "winback-202611-vip", "est_orders": 3.4 },
    "tier_b_standard": { "count": 60, "avg_ltv_vnd": 890000, "suggested_tag": "winback-202611-std", "est_orders": 3.6 }
  },
  "sample_customers_redacted": [
    { "customer_id": 8821045, "tier": "tier_a_vip", "recency_days": 94, "phone": "091****678", "email": "la***@company.vn", "total_spent_vnd": 6450000 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Tách biệt trách nhiệm (Separation of Concerns):** Skill chỉ lập kế hoạch và chọn tệp (`dry_run: true`, `confirmation_required: true`, `max_records <= 100`). Việc gắn tag khách hàng phải qua `customer-tag-note-proposal`, việc tạo mã giảm giá phải qua `marketing-promo-code-proposal`.
- **Bảo vệ PII (`pii_level: customer`):** Bắt buộc che SĐT và email trong mọi output (`export_allowed: false`). Không xuất file CSV chứa SĐT gốc khi chưa được duyệt riêng theo `policies/pii-handling.md`.
- **Rollback:** Nếu bước gắn tag kế tiếp cần hoàn tác, sử dụng file `*.backup.json` kèm `governance-rollback-executor`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng chạy, yêu cầu cập nhật `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_customers` hoặc `com.read_orders` | Yêu cầu cấp đủ 2 scope đọc. |
| `404 Not Found` | `last_order_id` bị lưu trữ/xóa | Tra cứu lại qua `GET /com/orders.json?customer_id={id}&limit=5`. |
| `422 Unprocessable` | `inactive_days_min >= inactive_days_max` | Kiểm tra validation tham số trước khi gọi API. |
| `429 Too Many Requests` | Tải lịch sử đơn cho nhiều khách vượt tốc độ | Dùng `HaravanClient` backoff và ưu tiên tải bulk đơn theo khoảng ngày thay vì gọi N+1 theo từng khách. |

- **Edge Case 1 — Khách mua sản phẩm vòng đời dài (đồ gia dụng, nệm, xe đạp):** 60 ngày là quá sớm để gọi là "ngủ đông". Agent cần hỏi hoặc điều chỉnh `inactive_days_min` (ví dụ `180–365` ngày) tùy ngành hàng.
- **Edge Case 2 — Khách mua qua sàn Shopee/TikTok Shop có SĐT bị ẩn (`***`) trên Haravan:** Sàn TMĐT thường che thông tin liên hệ của khách. Loại bỏ các khách có `phone` chứa `*` hoặc rỗng khỏi danh sách gửi Zalo ZNS.
- **Edge Case 3 — Khách vừa có đơn hoàn trả/khiếu nại gần đây:** Nếu đơn gần nhất bị `cancelled` hoặc `refunded`, không đưa vào kịch bản Win-Back đại trà mà chuyển sang đội CSKH xử lý riêng.

## 8. Liên kết Workflow & Skill kế tiếp

- **Phân khúc RFM tổng thể trước khi lập chiến dịch:** Chạy `customer-rfm-segmentation` (L1) hoặc `python3 scripts/hrv_ops.py rfm`.
- **Gắn tag phân nhóm khách hàng sau khi duyệt:** Chuyển sang `customer-tag-note-proposal` (L2).
- **Tạo mã ưu đãi riêng cho Tier A và Tier B:** Chuyển sang `marketing-promo-code-proposal` (L2).
