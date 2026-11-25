---
name: ops-daily-morning-briefing
description: "Bản tin vận hành đầu ngày (8:00 AM UTC+7): doanh thu hôm qua theo kênh, đơn chờ xử lý, cảnh báo COD rủi ro, SKU sắp hết hàng."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 90-control-tower-governance
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_inventories
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 3000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: financial
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---

# Haravan Daily Morning Store Briefing (Control Tower)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Tổng hợp bản tin điều hành đầu ngày (khung giờ chuẩn `08:00 AM UTC+7`) đọc nhanh trong 60 giây dành cho chủ shop và quản lý vận hành — hợp nhất 4 tín hiệu sống còn: Kết quả bán hàng hôm qua theo kênh, Backlog kho/vận chuyển sáng nay, Cảnh báo đơn COD rủi ro cao và Top SKU bán chạy / sắp hết hàng.
- **Ngữ cảnh Haravan:** Chủ shop đa kênh tại Việt Nam thường phải mở 4–5 màn hình khác nhau trên Haravan Admin (Báo cáo doanh thu, Đơn chưa giao, Tồn kho từng chi nhánh, Sàn TMĐT) mỗi sáng. Skill này gom toàn bộ thành một bản tin gọn nhẹ sẵn sàng gửi qua Zalo/Slack/Telegram và kèm 3 đầu việc ưu tiên nhất cho ca sáng.
- **Definition of Done (DoD):**
  1. Thu thập đơn hàng của `report_date` (UTC+7: `00:00:00` → `23:59:59`) và backlog đơn chưa xử lý qua `GET /com/orders.json` (hoặc `scripts/hrv_ops.py morning-briefing`).
  2. Tính chính xác doanh thu thuần ước tính, số đơn, AOV, tỷ lệ hủy, tỷ trọng theo kênh (`web`, `pos`, `harasocial`, `shopee`, `tiktokshop`, `lazada`).
  3. Liệt kê Top 5 SKU bán chạy, Top 5 SKU sắp đứt hàng, số đơn kẹt > 48h, đơn COD rủi ro cao và đúng 3 hành động ưu tiên cho ca sáng (đã ẩn toàn bộ PII).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_inventories`, `com.read_products` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/inventory_locations.json` |

**Ví dụ chạy nhanh bằng CLI có sẵn trong repo (`scripts/hrv_ops.py`):**
```bash
# Chạy bản tin sáng thực tế (đọc HARAVAN_ACCESS_TOKEN từ ENV)
python3 scripts/hrv_ops.py morning-briefing

# Chạy bản demo offline với dữ liệu mẫu Việt Nam
python3 scripts/hrv_ops.py --demo morning-briefing
```

**Ví dụ truy vấn đơn hàng đúng khung ngày UTC+7 qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
orders = client.paginate(
    surface="com",
    path="/orders.json",
    resource_key="orders",
    params={
        "created_at_min": "2026-11-24T00:00:00+07:00",
        "created_at_max": "2026-11-24T23:59:59+07:00",
        "status": "any",
    },
    limit=50,
    max_pages=60,
)
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `report_date` | `string` | Không | Hôm qua (`UTC+7`) | Định dạng `YYYY-MM-DD`. |
| `low_stock_threshold` | `integer` | Không | `5` | Ngưỡng tồn kho khả dụng (`qty_available <= 5`) để đưa vào mục cảnh báo sắp hết hàng. |
| `stuck_hours` | `integer` | Không | `48` | Ngưỡng số giờ đơn chưa xuất kho hoặc kẹt vận chuyển cần xử lý gấp. |
| `cod_high_value_vnd` | `integer` | Không | `1500000` | Ngưỡng giá trị đơn COD (VND) cần gắn cờ gọi điện xác nhận trước khi đóng gói. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Tổng hợp Kinh doanh ngày `report_date` (Operational Estimate):**
   - Lọc đơn hợp lệ (`cancelled_status == "uncancelled"`):
     $$\text{Est. Net Revenue} = \sum (\text{total\_price} - \text{total\_refunds}), \quad \text{AOV} = \frac{\text{Est. Net Revenue}}{N_{\text{valid\_orders}}}$$
     $$\text{Cancel Rate} = \frac{N_{\text{cancelled}}}{N_{\text{total\_orders}}} \times 100\%$$
   - Phân rã tỷ trọng doanh thu và số đơn theo `source_name` (cảnh báo nếu một kênh thường có đơn bất ngờ về `0`).
2. **Đo lường Backlog Ca Sáng:**
   - **Chưa đóng gói:** `fulfillment_status in (null, "notfulfilled", "partial")` và `cancelled_status == "uncancelled"`.
   - **Đơn kẹt > `stuck_hours`:** Chưa xuất kho hoặc đã giao ĐVVC quá 48h chưa cập nhật trạng thái giao.
   - **Đơn COD rủi ro cao:** `gateway` là COD, chưa xác nhận và `total_price >= cod_high_value_vnd` (hoặc khách từng có lịch sử hoàn đơn).
3. **Sức khỏe Tồn kho & Sản phẩm:**
   - Top 5 SKU bán chạy nhất ngày `report_date` (theo tổng `quantity` và doanh thu).
   - Top 5 SKU có `qty_available <= low_stock_threshold` đang có phát sinh đơn trong 7 ngày qua.
4. **Sinh 3 Hành động Ưu tiên Ca Sáng:** Sắp xếp theo mức độ khẩn cấp: (1) Xác nhận đơn COD lớn & giải phóng đơn sắp quá hạn SLA sàn, (2) Bổ sung tồn kho/tắt ads cho SKU sắp hết, (3) Xử lý đơn kẹt giao vận.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### BẢN TIN VẬN HÀNH SÁNG — 25/11/2026 (Dữ liệu ngày 24/11, UTC+7)

**1. Kết quả kinh doanh hôm qua (Operational Estimate)**
- **Doanh thu thuần ước tính:** `48,650,000 VND` | **Đơn hợp lệ:** `62` | **AOV:** `784,677 VND` | **Tỷ lệ hủy:** `4.6%` (3 đơn)
- **Theo kênh:** Shopee `44%` (27 đơn) • Web `29%` (18 đơn) • POS `16%` (10 đơn) • Harasocial `11%` (7 đơn)

**2. Backlog cần xử lý sáng nay**
- Chờ đóng gói: **19 đơn** (có 4 đơn Shopee sắp chạm hạn bàn giao 12:00 trưa)
- Kẹt vận chuyển > 48h: **5 đơn** (3 GHTK, 2 GHN)
- COD giá trị cao cần gọi xác nhận: **3 đơn** (`#10481`, `#10485`, `#10490` — tổng `6,420,000 VND`)

**3. Top SKU bán chạy & Cảnh báo tồn kho**
- Bán chạy: `POLO-BLK-L` (14 cái), `JEAN-BLU-31` (11 cái), `TEE-WHT-M` (9 cái)
- Sắp hết hàng: `POLO-BLK-L` (còn **2**), `KHOAC-GRY-XL` (còn **0** — đang bán trên Web)

**4. Top 3 việc ưu tiên ca sáng**
1. Gọi xác nhận 3 đơn COD > 1.5tr trước 09:30 và ưu tiên đóng gói 4 đơn Shopee trước 11:30.
2. Kiểm tra điều chuyển kho cho `POLO-BLK-L` (còn 2 cái) và tạm ẩn `KHOAC-GRY-XL`.
3. Tạo ticket giục giao 5 đơn kẹt > 48h với GHTK/GHN.

> *Financial Disclaimer:* Số liệu doanh thu là ước tính vận hành từ Haravan API, không thay thế sổ cái kế toán.
```

```json
{
  "skill": "ops-daily-morning-briefing",
  "report_date": "2026-11-24",
  "timezone": "Asia/Ho_Chi_Minh",
  "kpi": { "net_revenue_est_vnd": 48650000, "valid_orders": 62, "cancelled_orders": 3, "aov_vnd": 784677, "cancel_rate_pct": 4.6 },
  "backlog": { "unfulfilled_orders": 19, "stuck_over_48h": 5, "high_value_cod_count": 3 },
  "low_stock_alerts": [{ "sku": "POLO-BLK-L", "qty_available": 2 }],
  "top_3_actions": ["Xác nhận 3 đơn COD > 1.5tr và đóng gói 4 đơn Shopee trước 11:30", "Điều chuyển tồn kho POLO-BLK-L", "Giục giao 5 đơn kẹt > 48h"]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ gọi `GET`. Không tự hủy đơn COD rủi ro hay tự ẩn SKU hết hàng.
- **Bảo vệ PII (`pii_level: financial`):** Ẩn toàn bộ tên/SĐT/địa chỉ khách hàng khi chia sẻ bản tin lên nhóm chat chung (chỉ nêu `order_number` và giá trị đơn).
- **Financial Disclaimer:** Bắt buộc đính kèm ghi chú số liệu là ước tính vận hành (*Operational Estimate*).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn qua đêm | Gửi cảnh báo lỗi xác thực thay vì xuất bản tin 0đ gây hiểu nhầm. |
| `403 Forbidden` | Thiếu 1 trong 3 scope đọc | Vẫn xuất các mục có quyền và ghi rõ mục bị thiếu scope. |
| `404 Not Found` | Endpoint sai | Kiểm tra surface `com`. |
| `422 Unprocessable` | Định dạng `report_date` không hợp lệ | Xác thực `YYYY-MM-DD` trước khi gọi API. |
| `429 Too Many Requests` | Bão đơn Mega Sale > 2.000 đơn/ngày | `HaravanClient` tự backoff `1s -> 2s -> 4s`; nếu chạm `max_records: 3000`, ghi chú rõ số liệu bị cắt trần. |

- **Edge Case 1 — Ngày không có đơn hàng (shop mới hoặc nghỉ Tết):** Tránh lỗi chia cho 0 khi tính `AOV` và `Cancel Rate`; hiển thị `0 VND` và thông báo rõ không phát sinh đơn.
- **Edge Case 2 — Đơn tạo từ hôm kia nhưng mới thanh toán hôm qua:** Bản tin tính theo `created_at` (ngày đặt hàng) để khớp nhịp vận hành; ghi chú rõ tiêu chí lọc `created_at` để không nhầm với báo cáo dòng tiền kế toán.
- **Edge Case 3 — Lệch múi giờ UTC (00:00 UTC = 07:00 sáng VN):** Luôn truyền offset `+07:00` trong `created_at_min`/`created_at_max` để không bị mất 7 tiếng doanh thu buổi sáng.

## 8. Liên kết Workflow & Skill kế tiếp

- **Xử lý sâu các đơn COD rủi ro cao phát hiện sáng nay:** Chuyển sang `order-cod-risk-scorer` (L1) hoặc `python3 scripts/hrv_ops.py cod-risk`.
- **Kiểm tra chi tiết đơn kẹt giao vận:** Chạy `fulfillment-wismo-delay-audit` (L1) hoặc `python3 scripts/hrv_ops.py wismo`.
- **Tổng hợp cuối tuần / cuối tháng:** Kết nối lên `ops-weekly-business-review` (L1) và `ops-monthly-financial-close` (L1).
