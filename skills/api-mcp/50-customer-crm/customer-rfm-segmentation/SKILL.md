---
name: customer-rfm-segmentation
description: "Phân khúc toàn bộ khách hàng Haravan theo mô hình RFM (Recency, Frequency, Monetary) để tối ưu chăm sóc và Haraloyalty."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 50-customer-crm
layer: L1
wave: 1
mode: read
risk: low
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
  confirmation_required: false
  separate_turn: false
  max_records: 5000
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

# Haravan Customer RFM Segmentation

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này phân khúc toàn bộ tập khách hàng Haravan theo mô hình **RFM (Recency – Frequency – Monetary)** sử dụng phương pháp chia điểm ngũ phân vị (Quintile 1–5) trên lịch sử đơn hàng thành công. Kết quả chia khách hàng thành **8 phân khúc hành động rõ ràng** (`Champions`, `Loyal`, `Potential Loyalist`, `New Customers`, `Promising`, `Need Attention`, `At Risk`, `Hibernating`) giúp đội CRM thiết kế kịch bản Zalo ZNS, Email Automation và hạng thành viên **Haraloyalty** đúng đối tượng thay vì bắn tin đồng loạt.

**Tiêu chí hoàn thành (Definition of Done):**
- Tổng hợp đúng 3 chỉ số `R` (ngày từ đơn gần nhất), `F` (số đơn thành công), `M` (tổng chi tiêu thuần VND) trong `lookback_days`, đã loại trừ đơn hủy/hoàn toàn phần.
- Chia điểm ngũ phân vị 1–5 cho từng chiều (xử lý tốt phân phối lệch khi đa số khách chỉ có `F = 1`), ánh xạ ra bảng 8 phân khúc kèm `% khách`, `% doanh thu`, `AOV` và gợi ý hành động.
- Xuất danh sách `customer_id` theo phân khúc **ẩn toàn bộ PII** (không tên, không SĐT, không email).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_customers`, `com.read_orders` |
| **Endpoints** | `GET /com/customers.json`, `GET /com/orders.json` |

**Ví dụ chạy nhanh qua `scripts/hrv_ops.py`:**
```bash
python3 scripts/hrv_ops.py rfm
python3 scripts/hrv_ops.py --demo rfm
```

**JSON Response trích xuất từ `GET /com/orders.json`:**
```json
{
  "orders": [
    {
      "id": 1482041122,
      "created_at": "2026-04-02T09:15:00Z",
      "cancelled_at": null,
      "financial_status": "paid",
      "total_price": 1240000.0,
      "total_discounts": 100000.0,
      "customer": { "id": 70122 }
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `365` | Cửa sổ lịch sử đơn hàng tính RFM (`90`–`730` ngày). |
| `exclude_cancelled` | boolean | No | `true` | Loại trừ đơn `cancelled_at != null` và `financial_status == "refunded"`. |
| `exclude_channels` | array[string] | No | `[]` | Tùy chọn bỏ qua đơn sàn TMĐT nếu không có định danh khách hàng riêng. |
| `scoring_mode` | enum | No | `"quintile"` | `quintile` (chia 5 phần bằng nhau theo dữ liệu shop) hoặc `fixed_vn` (ngưỡng cố định cho shop nhỏ < 100 khách). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Tính 3 chiều RFM cho từng `customer_id`:**
   - $R_i = \lfloor (\text{Now}_{\text{UTC+7}} - \max(\text{order.created\_at}_i)) / 86400 \rfloor$ (số ngày từ đơn gần nhất; **càng nhỏ càng tốt**).
   - $F_i = \text{count}(\text{orders thành công của khách } i \text{ trong lookback\_days})$ (**càng lớn càng tốt**).
   - $M_i = \sum (\text{total\_price} - \text{refunded\_amount})$ (**càng lớn càng tốt**).
2. **Chấm điểm Quintile (1–5):**
   - Với `R`: Chia 5 phân vị ngược (20% mới mua nhất = `5`, 20% lâu nhất = `1`).
   - Với `M`: Chia 5 phân vị thuận (20% chi cao nhất = `5`, 20% thấp nhất = `1`).
   - Với `F` (xử lý lệch phổ biến tại TMĐT VN khi 60–75% khách chỉ có `F = 1`): Gán `F_score = 1` cho `F = 1`, sau đó chia 4 mức (`2, 3, 4, 5`) theo tứ phân vị trên tập khách mua lại (`F >= 2`) để tránh lỗi trùng ranh giới quintile.
3. **Ma trận Ánh xạ 8 Phân khúc RFM:**
   - `Champions`: $R \ge 4,\; F \ge 4,\; M \ge 4$
   - `Loyal`: $R \ge 3,\; F \ge 3,\; M \ge 3$ (ngoài Champions)
   - `Potential Loyalist`: $R \ge 4,\; F \in \{2, 3\}$
   - `New Customers`: $R = 5,\; F = 1$
   - `Promising`: $R = 4,\; F = 1$
   - `Need Attention`: $R = 3,\; F \in \{1, 2\}$
   - `At Risk`: $R \le 2,\; F \ge 3$ (hoặc $R \le 2,\; M \ge 4$)
   - `Hibernating`: Các trường hợp còn lại ($R \le 2,\; F \le 2$).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Bảng Phân khúc RFM Khách hàng (365 ngày — 2.450 khách hàng hợp lệ):**
| Phân khúc RFM | Số khách | % Khách | Doanh thu thuần (VND) | % Doanh thu | AOV TB (VND) | Kịch bản chăm sóc đề xuất |
| --- | --- | --- | --- | --- | --- | --- |
| `Champions` | 196 | 8.0% | 1.482.000.000 | 34.2% | 1.120.000 | Đặc quyền VIP Haraloyalty, mở bán sớm, không cần giảm giá sâu |
| `Loyal` | 343 | 14.0% | 1.125.000.000 | 26.0% | 820.000 | Upsell combo, tích điểm nâng hạng |
| `Potential Loyalist` | 294 | 12.0% | 518.000.000 | 12.0% | 640.000 | Voucher Freeship đơn kế tiếp để khóa thói quen mua lại |
| `At Risk` | 220 | 9.0% | 610.000.000 | 14.1% | 890.000 | **Ưu tiên cứu gấp:** ZNS cá nhân hóa + mã giảm 15% có hạn 7 ngày |
| `New Customers` | 412 | 16.8% | 265.000.000 | 6.1% | 510.000 | Chuỗi onboarding 21 ngày hướng dẫn sử dụng sản phẩm |
| `Hibernating` | 640 | 26.1% | 198.000.000 | 4.6% | 420.000 | Chỉ remarketing dịp Mega Sale (tránh đốt ngân sách ZNS) |

```json
{
  "skill": "customer-rfm-segmentation",
  "lookback_days": 365,
  "total_customers_scored": 2450,
  "total_net_revenue_vnd": 4330000000,
  "segments": [
    {
      "segment": "Champions",
      "customer_count": 196,
      "customer_share_pct": 8.0,
      "revenue_vnd": 1482000000,
      "revenue_share_pct": 34.2,
      "avg_order_value_vnd": 1120000,
      "sample_customer_ids": [70122, 70188, 70241]
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Chỉ đọc và phân tích; không tự ý ghi đè tag khách hàng hay kích hoạt chiến dịch gửi tin.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Tuyệt đối chỉ xuất `customer_id` trong JSON/báo cáo nhóm; không xuất danh sách SĐT/email thô ra CSV.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_customers` hoặc `com.read_orders` | Dừng, liệt kê chính xác scope bị thiếu. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `/com/`. |
| `422 Unprocessable` | `created_at_min` sai định dạng | Chuyển sang ISO-8601 (`+07:00`). |
| `429 Too Many Requests` | Quét 5.000 đơn + 5.000 khách hàng | Sử dụng `hrv_client.py` tự throttle ≤ 4 req/s và exponential backoff. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Lệch số liệu giữa `customer.total_spent` và tổng đơn trong `lookback_days`:** Trường `customer.total_spent` trên Haravan là tổng trọn đời (lifetime) và đôi khi còn cộng cả đơn chưa hoàn tất hoặc chưa trừ hoàn tiền một phần. Phải **tính trực tiếp R, F, M từ `orders.json`** thay vì tin hoàn toàn vào `customers.json`.
2. **Shop mới vận hành hoặc cỡ mẫu < 100 khách hàng:** Chia quintile 5 bậc trên mẫu nhỏ sẽ tạo ra các nhóm rỗng hoặc méo ngưỡng; tự động chuyển sang `scoring_mode: "fixed_vn"` (vd `R <= 30d`, `F >= 3`, `M >= 3.000.000đ`) và ghi chú rõ trong báo cáo.
3. **Khách mua sỉ (B2B) kéo lệch ngưỡng Monetary:** 2–3 đại lý mua 200 triệu/năm có thể làm sai lệch phân vị `M`; nên tách riêng khách có tag `B2B-Si` / `dai-ly` hoặc dùng quintile theo hạng (rank-based) thay vì khoảng chia đều (equal-width).

## 8. Liên kết Workflow & Skill kế tiếp
- **Đồng bộ phân khúc RFM thành tag khách hàng trên Haravan:** Chuyển `customer_id` từng nhóm sang `customer-tag-note-proposal`.
- **Theo dõi sát nhóm VIP có nguy cơ rời bỏ (`At Risk`):** Chuyển sang `customer-vip-churn-watchlist`.
