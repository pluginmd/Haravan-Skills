---
name: customer-vip-churn-watchlist
description: "Nhận diện khách hàng VIP có dấu hiệu rời bỏ (quá chu kỳ mua lặp lại bình thường) để kích hoạt kịch bản chăm sóc cá nhân hóa."
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

# Haravan VIP Customer & Churn-Risk Watchlist

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Theo quy luật Pareto trong bán lẻ Việt Nam, **top 10–15% khách hàng VIP đóng góp 35–50% tổng doanh thu**, nhưng họ thường rời bỏ trong im lặng (không khiếu nại) sau một lần hết hàng hoặc trải nghiệm giao vận kém. Skill này theo dõi tập khách VIP trên Haravan, so sánh số ngày chưa quay lại với **chu kỳ mua lặp lại cá nhân hóa của chính khách hàng đó** để lập danh sách cảnh báo sớm (`At-Risk VIP Watchlist`) sắp xếp theo giá trị trọn đời (LTV) đang có nguy cơ mất đi.

**Tiêu chí hoàn thành (Definition of Done):**
- Lọc chính xác tập khách VIP đạt ngưỡng `vip_min_spend_vnd` hoặc `vip_min_orders` (chỉ tính đơn thành công).
- Tính `avg_purchase_cycle_days` (chu kỳ mua trung bình cá nhân) và `churn_ratio = days_since_last_order / avg_purchase_cycle_days` cho từng VIP.
- Xếp hạng 3 mức cảnh báo (`CRITICAL ≥ 2.0x`, `WARNING 1.5x–1.99x`, `WATCH 1.2x–1.49x`), đề xuất kịch bản win-back theo nhóm hàng hay mua, và ẩn toàn bộ PII.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_customers`, `com.read_orders` |
| **Endpoints** | `GET /com/customers.json`, `GET /com/orders.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate(
    "/com/orders.json",
    params={"status": "any", "created_at_min": "2025-04-10T00:00:00+07:00", "limit": 50},
    data_key="orders",
    max_records=5000,
)
```

**JSON Response trích xuất để tính chu kỳ mua VIP (`GET /com/orders.json`):**
```json
{
  "orders": [
    { "id": 1480112001, "created_at": "2025-10-05T03:00:00Z", "cancelled_at": null, "total_price": 2100000.0, "customer": { "id": 70419 } },
    { "id": 1480551902, "created_at": "2025-11-10T06:20:00Z", "cancelled_at": null, "total_price": 1950000.0, "customer": { "id": 70419 } },
    { "id": 1481023410, "created_at": "2025-12-18T08:10:00Z", "cancelled_at": null, "total_price": 2400000.0, "customer": { "id": 70419 } }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `vip_min_spend_vnd` | integer | No | `5000000` | Ngưỡng tổng chi tiêu thuần để định danh VIP (VND). |
| `vip_min_orders` | integer | No | `3` | Số đơn thành công tối thiểu (dùng kèm `OR`/`AND` theo cấu hình shop). |
| `churn_inactive_days` | integer | No | `60` | Ngưỡng ngày im lặng tối thiểu để vào danh sách cảnh báo (`30`–`180` ngày). |
| `cycle_multiplier_warning` | number | No | `1.5` | Hệ số vượt chu kỳ cá nhân bắt đầu gắn cờ `WARNING`. |
| `cycle_multiplier_critical` | number | No | `2.0` | Hệ số vượt chu kỳ cá nhân gắn cờ `CRITICAL`. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Xác định Tập Khách VIP:** Từ danh sách đơn thành công (`cancelled_at == null`, không `refunded`), tính cho mỗi `customer_id`: `ltv_vnd`, `orders_count`, danh sách mốc thời gian đơn $t_1 < t_2 < \dots < t_n$. Giữ lại khách đạt `ltv_vnd >= vip_min_spend_vnd` HOẶC `orders_count >= vip_min_orders`.
2. **Tính Chu kỳ Mua Cá nhân & Tỷ số Rời bỏ (Personal Churn Ratio):**
   - Số ngày từ đơn gần nhất: $D_{\text{inactive}} = \text{Now} - t_n$ (ngày).
   - Chu kỳ mua trung bình cá nhân (khi $n \ge 2$): $C_i = \frac{t_n - t_1}{n - 1}$ (áp sàn tối thiểu `14 ngày` để tránh nhiễu khi khách mua 2 đơn liên tiếp trong 1 tuần).
   - Nếu $n = 1$ (VIP mua 1 đơn rất lớn): dùng chu kỳ trung vị toàn shop $C_{\text{shop}}$ (hoặc `churn_inactive_days`).
   - Tỷ số rời bỏ: $\text{ChurnRatio}_i = \frac{D_{\text{inactive}}}{C_i}$.
3. **Phân tầng Watchlist & Ưu tiên theo LTV rủi ro:**
   - `CRITICAL`: $\text{ChurnRatio}_i \ge 2.0$ VÀ $D_{\text{inactive}} \ge \text{churn\_inactive\_days}$.
   - `WARNING`: $1.5 \le \text{ChurnRatio}_i < 2.0$ VÀ $D_{\text{inactive}} \ge 0.75 \times \text{churn\_inactive\_days}$.
   - Kiểm tra thêm **tín hiệu bất mãn ở đơn cuối** (đơn $t_n$ có bị hoàn tiền một phần, giao trễ > 5 ngày, hay khách mới hủy 1 đơn gần đây) để gắn cờ `LAST_ORDER_FRICTION` cho CSKH chuẩn bị kịch bản xin lỗi trước khi tặng ưu đãi.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**VIP Churn-Risk Watchlist (Tổng LTV đang có nguy cơ rời bỏ: 248.500.000 VND / 27 VIP):**
| Mức độ | Customer ID | LTV (VND) | Số đơn | Chu kỳ TB (ngày) | Im lặng (ngày) | Tỷ số Churn | Tín hiệu đơn cuối | Gợi ý Win-back |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CRITICAL` | `70419` | 18.450.000 | 7 | 37 | 112 | **3.0x** | Bình thường | CSKH gọi hỏi thăm + Voucher VIP 200k |
| `CRITICAL` | `70108` | 14.200.000 | 5 | 42 | 95 | **2.3x** | `LAST_ORDER_FRICTION` (giao trễ 6 ngày) | Gọi xin lỗi trải nghiệm giao hàng + Freeship VIP |
| `WARNING` | `70882` | 9.600.000 | 4 | 30 | 52 | **1.7x** | Bình thường | Gửi ZNS giới thiệu bộ sưu tập mới |

```json
{
  "skill": "customer-vip-churn-watchlist",
  "vip_criteria": { "min_spend_vnd": 5000000, "min_orders": 3, "churn_inactive_days": 60 },
  "total_vip_count": 185,
  "at_risk_vip_count": 27,
  "at_risk_total_ltv_vnd": 248500000,
  "watchlist": [
    {
      "severity": "CRITICAL",
      "customer_id": 70419,
      "ltv_vnd": 18450000,
      "orders_count": 7,
      "avg_cycle_days": 37,
      "inactive_days": 112,
      "churn_ratio": 3.03,
      "last_order_friction": false,
      "top_purchased_category": "Trà Thảo Mộc"
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Chỉ đọc và lập danh sách theo dõi; không tự động nhắn tin cho khách hay tự tạo mã giảm giá.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Tuyệt đối chỉ dùng `customer_id` trong Watchlist; nhân viên CSKH tự tra cứu SĐT trong Haravan Admin khi thực hiện cuộc gọi chăm sóc.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_customers` hoặc `com.read_orders` | Dừng, báo chính xác quyền thiếu. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `/com/`. |
| `422 Unprocessable` | Tham số ngày không hợp lệ | Chuẩn hóa về ISO-8601 (`+07:00`). |
| `429 Too Many Requests` | Quét lịch sử đơn hàng 12–24 tháng | Throttle & backoff tự động qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **VIP mua quà tặng theo mùa vụ (Tết Nguyên Đán, Trung Thu, 8/3, 20/10):** Khách chỉ mua 1–2 lần/năm vào đúng dịp lễ với giá trị cao (10–20 triệu). Nếu đánh đồng với chu kỳ 60 ngày sẽ báo động giả hàng loạt; cần gắn cờ `SEASONAL_BUYER` nếu $\ge 80\%$ đơn của khách rơi vào cùng 1–2 tháng lễ.
2. **VIP đã đổi sang mua ở hồ sơ trùng khác (POS/Harasocial):** Khách tưởng như "im lặng 90 ngày" trên hồ sơ Website nhưng thực tế tuần trước vừa mua tại cửa hàng POS bằng hồ sơ khác. Khuyến nghị chạy `customer-duplicate-phone-finder` trước khi kích hoạt chiến dịch win-back.
3. **Khách mua sản phẩm bền (điện gia dụng, nội thất) có chu kỳ mua lại tự nhiên 1–2 năm:** Cần điều chỉnh tham số `churn_inactive_days` phù hợp đặc thù ngành hàng (FMCG/mỹ phẩm: 45–60 ngày; thời trang: 60–90 ngày; gia dụng: 180+ ngày).

## 8. Liên kết Workflow & Skill kế tiếp
- **Gắn tag theo dõi VIP nguy cơ cao:** Chuyển `customer_id` nhóm `CRITICAL` sang `customer-tag-note-proposal` (tag `vip-churn-risk`).
- **Kiểm tra chéo phân khúc tổng thể:** Kết hợp `customer-rfm-segmentation` và `customer-cohort-retention`.
