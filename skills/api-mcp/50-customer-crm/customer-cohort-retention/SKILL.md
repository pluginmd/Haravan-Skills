---
name: customer-cohort-retention
description: "Phân tích tỷ lệ mua lại (Repeat Purchase Rate) và bảng giữ chân theo tháng đầu mua hàng (Monthly Cohort Retention)."
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
    - com.read_orders
    - com.read_customers
  endpoints:
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

# Haravan Customer Cohort & Repeat-Purchase Analysis

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Tăng trưởng bền vững của một cửa hàng Haravan không chỉ đến từ chạy quảng cáo kéo khách mới mà đến từ **khả năng giữ chân và kích thích mua lại**. Skill này xây dựng **Ma trận Cohort Retention theo tháng (M0 → M6)**, đo lường Tỷ lệ mua lại (Repeat Purchase Rate), Doanh thu tích lũy trên mỗi khách (Cumulative LTV per Cohort) và **Khoảng cách ngày trung bình giữa đơn 1 và đơn 2 (Inter-Purchase Interval)** để chọn đúng thời điểm bắn chiến dịch ZNS/Remarketing.

**Tiêu chí hoàn thành (Definition of Done):**
- Thu thập đơn hàng thành công (loại trừ đơn hủy/hoàn toàn phần) trong tối thiểu `cohort_months` (mặc định 6 tháng, múi giờ `Asia/Ho_Chi_Minh`).
- Tính chính xác ma trận giữ chân `%` từ `M0` đến `M+N` cho từng nhóm tháng gia nhập, cùng chỉ số Repeat Purchase Rate và Median/Mean Inter-Purchase Interval (ngày).
- Chỉ xuất số liệu tổng hợp ẩn danh ở cấp độ Cohort (tuyệt đối không lộ PII khách hàng) và chỉ ra điểm rơi churn lớn nhất.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_customers` |
| **Endpoints** | `GET /com/orders.json` (filter `status=any`, `created_at_min`, `limit=50`) |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate(
    "/com/orders.json",
    params={"status": "any", "created_at_min": "2025-10-01T00:00:00+07:00", "limit": 50},
    data_key="orders",
    max_records=5000,
)
```

**JSON Response trích xuất các trường dùng cho Cohort (`GET /com/orders.json`):**
```json
{
  "orders": [
    {
      "id": 1481002911,
      "created_at": "2025-11-12T04:30:00Z",
      "cancelled_at": null,
      "financial_status": "paid",
      "total_price": 540000.0,
      "source_name": "web",
      "customer": { "id": 70122, "orders_count": 3 }
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `cohort_months` | integer | No | `6` | Số tháng phân tích cohort gần nhất (`3`–`12` tháng). |
| `exclude_channels` | array[string] | No | `[]` | Tùy chọn loại trừ kênh sàn TMĐT (vd `["shopee","tiktok"]`) nếu sàn ẩn định danh khách hàng. |
| `min_order_value_vnd` | integer | No | `0` | Loại trừ đơn 0đ (đơn tặng quà/mẫu thử) nếu đặt `> 0`. |
| `revenue_basis` | enum | No | `"net"` | `net` (đã trừ hoàn tiền/giảm giá) hoặc `gross`. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Làm sạch dữ liệu đơn hàng:**
   - Loại bỏ đơn có `cancelled_at != null`, `financial_status == "refunded"`, hoặc `customer == null` (khách lẻ POS không lưu hồ sơ — cần đếm riêng tỷ lệ đơn không định danh để cảnh báo độ phủ).
   - Chuyển đổi `created_at` sang múi giờ Việt Nam (`UTC+7`) rồi trích xuất `order_month = YYYY-MM`.
2. **Xác định Cohort & Kỳ mua lại:**
   - Với mỗi `customer_id`, tìm tháng đơn đầu tiên: $\text{cohort\_month} = \min(\text{order\_month})$.
   - Chỉ số kỳ giữ chân: $k = (\text{year}_{\text{order}} - \text{year}_{\text{cohort}}) \times 12 + (\text{month}_{\text{order}} - \text{month}_{\text{cohort}})$ (với $k \in \{0, 1, \dots, 6\}$).
3. **Công thức các chỉ số cốt lõi:**
   - Tỷ lệ giữ chân tháng $k$: $\text{Retention}(c, k) = \frac{|\text{Khách của cohort } c \text{ có đơn tại tháng } c+k|}{|\text{Tổng khách mới của cohort } c|} \times 100\%$.
   - Tỷ lệ mua lại (Repeat Purchase Rate): $\text{RPR} = \frac{\text{Số khách có } \ge 2 \text{ đơn thành công trong kỳ}}{\text{Tổng số khách có } \ge 1 \text{ đơn thành công trong kỳ}} \times 100\%$.
   - Khoảng cách mua lại (Inter-Purchase Interval): Với mọi khách có $\ge 2$ đơn, tính $\Delta t_{1\to 2} = \text{date}(\text{order}_2) - \text{date}(\text{order}_1)$ (ngày), sau đó lấy **Median** và **P75** để đề xuất lịch gửi tin nhắn nhắc mua lại.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Ma trận Giữ chân Khách hàng theo Tháng (Cohort Retention M0–M5):**
| Cohort | Khách mới (M0) | M1 (%) | M2 (%) | M3 (%) | M4 (%) | M5 (%) | LTV TB 90 ngày (VND) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2025-11` | 420 | 18.6% | 14.3% | 11.2% | 9.8% | 8.1% | 1.180.000 |
| `2025-12` | 585 | 14.2% | 10.6% | 8.9% | 7.5% | — | 960.000 |
| `2026-01` | 390 | 21.0% | 16.4% | 12.8% | — | — | 1.320.000 |
| `2026-02` | 310 | 22.3% | 15.8% | — | — | — | 1.250.000 |
| `2026-03` | 445 | 19.8% | — | — | — | — | — |

- **Repeat Purchase Rate (6 tháng):** `26.4%` | **Khoảng cách đơn 1 → đơn 2:** Median `28 ngày` (P75: `49 ngày`).
- **Nhận xét điểm rơi Churn:** Cohort `2025-12` (mùa sale 12.12) có M1 tụt mạnh (`14.2%` so với trung bình `20.5%`), cho thấy khách săn khuyến mãi sâu ít quay lại. Thời điểm vàng gửi ZNS/voucher kích hoạt đơn 2 là **ngày thứ 22–25 sau đơn đầu**.

```json
{
  "skill": "customer-cohort-retention",
  "cohort_months": 6,
  "unidentified_orders_excluded_pct": 4.2,
  "repeat_purchase_rate_pct": 26.4,
  "inter_purchase_days": { "median": 28, "p75": 49, "mean": 34.6 },
  "cohorts": [
    {
      "cohort_month": "2025-11",
      "size": 420,
      "retention_pct": { "M0": 100.0, "M1": 18.6, "M2": 14.3, "M3": 11.2, "M4": 9.8, "M5": 8.1 },
      "avg_ltv_90d_vnd": 1180000
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Chỉ đọc lịch sử đơn hàng và tổng hợp số liệu thống kê.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Không liệt kê tên, SĐT hay danh sách khách hàng cá nhân; toàn bộ đầu ra là dữ liệu ẩn danh ở cấp độ nhóm Cohort.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, báo thiếu quyền đọc đơn hàng. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `https://apis.haravan.com/com`. |
| `422 Unprocessable` | `created_at_min` sai định dạng | Chuyển đổi sang ISO-8601 (`+07:00`). |
| `429 Too Many Requests` | Quét 5.000 đơn trên nhiều trang | Phân trang tự động kèm backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Hồ sơ khách hàng trùng lặp theo SĐT (`090...` vs `+8490...`):** Nếu cùng 1 người mua bằng 2 hồ sơ khác nhau giữa Web và Harasocial, thuật toán theo `customer_id` sẽ tính sai thành 2 khách mới và kéo giảm giả tạo Repeat Purchase Rate. Nên nhóm bổ sung theo SĐT chuẩn hóa hoặc chạy `customer-duplicate-phone-finder` trước.
2. **Đơn vãng lai POS (`customer: null`) & Đơn sàn TMĐT bị ẩn định danh:** Nếu tỷ lệ đơn thiếu `customer_id` vượt quá 15%, báo cáo **phải hiển thị cảnh báo độ phủ** ở đầu bảng để tránh hiểu sai tỷ lệ giữ chân toàn shop.
3. **Hiệu ứng cắt cụt cửa sổ (Left-Truncation Bias):** Nếu chỉ lấy đơn 6 tháng gần nhất, một khách cũ mua từ năm ngoái quay lại tháng 11 sẽ bị gắn nhầm vào Cohort `2025-11` nếu không đối chiếu với `customer.orders_count` hoặc `customer.created_at`. Cần lọc chỉ tính vào Cohort mới những khách có đơn đầu tiên thực sự nằm trong tháng đó.

## 8. Liên kết Workflow & Skill kế tiếp
- **Làm sạch trùng lặp trước khi tính Cohort chính xác:** Chạy `customer-duplicate-phone-finder`.
- **Phân khúc sâu để hành động theo từng nhóm:** Chạy `customer-rfm-segmentation` và `customer-vip-churn-watchlist`.
