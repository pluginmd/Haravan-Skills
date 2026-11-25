---
name: finance-sales-by-channel-omni
description: "Báo cáo doanh thu, số đơn, AOV và tỷ lệ hoàn theo từng kênh trong hệ sinh thái Haravan Omni (Haraweb, Harasocial, HaraRetail POS, Shopee, Lazada, TikTok Shop)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 60-finance-analytics
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/locations.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
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

# Haravan Omnichannel Sales Performance Report

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Thế mạnh cốt lõi của Haravan tại Việt Nam là **bán hàng đa kênh hợp nhất (Omnichannel)**: Website (`Haraweb`), Chat/Livestream (`Harasocial`), Cửa hàng vật lý (`HaraRetail POS` theo từng chi nhánh), và Sàn TMĐT (`Shopee`, `TikTok Shop`, `Lazada`). Skill này tổng hợp **Omnichannel Scorecard** so sánh trực diện Gross Sales, Discounts, Returns/Cancels, Net Sales, Số đơn, AOV và tăng trưởng kỳ trước (WoW/MoM) cho từng kênh và từng chi nhánh POS.

**Tiêu chí hoàn thành (Definition of Done):**
- Chuẩn hóa toàn bộ `source_name` / `channel` của Haravan về 6 kênh chuẩn Omni và ánh xạ `location_id` sang tên chi nhánh POS từ `GET /com/locations.json`.
- Tính chính xác công thức thác doanh thu (`Gross Sales - Discounts - Returns/Cancels = Net Sales`) trên cùng quy ước múi giờ `Asia/Ho_Chi_Minh (UTC+7)`.
- Khi `compare_previous_period: true`, tính đầy đủ `% tăng trưởng` so với kỳ liền trước có cùng độ dài ngày, kèm **Financial Disclaimer**.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_shop` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/locations.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
locations = client.get("/com/locations.json")["locations"]
orders = client.paginate(
    "/com/orders.json",
    params={"status": "any", "created_at_min": "2026-03-01T00:00:00+07:00", "created_at_max": "2026-03-31T23:59:59+07:00", "limit": 50},
    data_key="orders",
    max_records=5000,
)
```

**JSON Response trích xuất từ `GET /com/locations.json` & `GET /com/orders.json`:**
```json
{
  "locations": [
    { "id": 101, "name": "Kho Trung Tâm HCM", "active": true },
    { "id": 102, "name": "Cửa Hàng POS Quận 1", "active": true },
    { "id": 103, "name": "Cửa Hàng POS Cầu Giấy HN", "active": true }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `date_from` | string | Yes | — | Ngày bắt đầu (`YYYY-MM-DD`, tính từ `00:00:00+07:00`). |
| `date_to` | string | Yes | — | Ngày kết thúc (`YYYY-MM-DD`, tính đến `23:59:59+07:00`). |
| `compare_previous_period` | boolean | No | `true` | Tự động truy vấn kỳ liền trước có cùng số ngày để tính `%Δ Net Sales` và `%Δ Orders`. |
| `include_shipping_in_net` | boolean | No | `false` | Mặc định tách riêng phí vận chuyển khỏi Net Product Sales theo chuẩn phân tích bán lẻ. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Ánh xạ Kênh Haravan Omni (`source_name` Normalization):**
   - `web` / `haraweb` → **Haraweb (Website)**
   - `harasocial` / `facebook` / `zalo` / `instagram` → **Harasocial (Social/Chat)**
   - `pos` / `hararetail` → **HaraRetail POS** (tách thêm theo `location_id` → tên chi nhánh)
   - `shopee`, `tiktok`, `lazada` → giữ nguyên từng sàn TMĐT; các nguồn khác gom vào `Other / Admin Draft`.
2. **Công thức Thác Doanh thu (Revenue Waterfall):**
   - $\text{GrossSales} = \sum (\text{line\_item.price} \times \text{quantity})$ (trên tất cả đơn đặt trong kỳ).
   - $\text{Discounts} = \sum \text{order.total\_discounts}$.
   - $\text{ReturnsCancels} = \sum \text{Giá trị đơn hủy} + \sum \text{Tổng tiền hoàn}$.
   - $\text{NetSales} = \text{GrossSales} - \text{Discounts} - \text{ReturnsCancels}$.
   - $\text{AOV} = \frac{\text{NetSales}}{\text{Số đơn thành công}}$; $\text{Growth\%} = \frac{\text{NetSales}_{\text{hiện tại}} - \text{NetSales}_{\text{kỳ trước}}}{\text{NetSales}_{\text{kỳ trước}}} \times 100\%$.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Omnichannel Scorecard (01/03/2026 – 31/03/2026 vs Kỳ trước 28 ngày — Múi giờ `UTC+7`):**
| Kênh Haravan Omni | Số đơn thành công | Gross Sales (VND) | Chiết khấu | Hủy / Hoàn | Net Sales (VND) | Tỷ trọng | AOV (VND) | vs Kỳ trước |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **HaraRetail POS** | 485 | 332.000.000 | 18.500.000 | 3.500.000 | **310.000.000** | 31.0% | 639.000 | `+8.4%` |
| **Haraweb (Web)** | 410 | 328.000.000 | 22.000.000 | 21.000.000 | **285.000.000** | 28.5% | 695.000 | `+12.1%` |
| **Shopee** | 512 | 295.000.000 | 29.000.000 | 26.000.000 | **240.000.000** | 24.0% | 468.000 | `-3.2%` |
| **Harasocial** | 238 | 210.000.000 | 15.000.000 | 30.000.000 | **165.000.000** | 16.5% | 693.000 | `+15.6%` |
| **Tổng Toàn Shop** | **1.645** | **1.165.000.000** | **84.500.000** | **80.500.000** | **1.000.000.000** | **100%** | **608.000** | **`+7.5%`** |

**Đóng góp theo Chi nhánh HaraRetail POS:**
- `Cửa Hàng POS Quận 1 (ID 102)`: `192.000.000đ` (61.9% POS, 290 đơn, AOV 662k)
- `Cửa Hàng POS Cầu Giấy HN (ID 103)`: `118.000.000đ` (38.1% POS, 195 đơn, AOV 605k)

```json
{
  "skill": "finance-sales-by-channel-omni",
  "disclaimer": "Operational Estimate / Reconciliation Aid — tính theo created_at múi giờ Asia/Ho_Chi_Minh, không thay thế sổ cái kế toán.",
  "period": { "from": "2026-03-01", "to": "2026-03-31", "timezone": "Asia/Ho_Chi_Minh" },
  "total_net_sales_vnd": 1000000000,
  "mom_growth_pct": 7.5,
  "channels": [
    { "channel": "pos", "orders": 485, "gross_sales_vnd": 332000000, "discounts_vnd": 18500000, "returns_vnd": 3500000, "net_sales_vnd": 310000000, "share_pct": 31.0, "aov_vnd": 639000, "growth_pct": 8.4 }
  ],
  "pos_locations": [
    { "location_id": 102, "name": "Cửa Hàng POS Quận 1", "net_sales_vnd": 192000000, "orders": 290 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Financial Disclaimer Bắt buộc:**
  > *Tuyên bố trách nhiệm tài chính: Báo cáo là **Operational Estimate / Reconciliation Aid** tổng hợp theo ngày tạo đơn (`created_at`, UTC+7) trên Haravan — không thay thế doanh thu ghi nhận theo ngày xuất hóa đơn trên sổ cái kế toán.*
- **Chế độ Read-Only (L1):** Chỉ đọc và tổng hợp dữ liệu bán hàng.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_shop` | Vẫn chạy báo cáo theo `location_id`, ghi chú không ánh xạ được tên chi nhánh POS. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `/com/`. |
| `422 Unprocessable` | `date_from > date_to` | Báo lỗi tham số và dừng trước khi gọi API. |
| `429 Too Many Requests` | Kỳ báo cáo dài + kỳ so sánh vượt 5.000 đơn | Tự động chia nhỏ cửa sổ ngày (chunking theo tuần) và backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Lệch múi giờ UTC vs `Asia/Ho_Chi_Minh (UTC+7)`:** Đơn đặt từ `00:00–06:59` sáng giờ VN sẽ mang ngày hôm trước theo chuẩn UTC trên Haravan API; bắt buộc truyền rõ `+07:00` trong `created_at_min`/`created_at_max` để không lệch doanh thu đầu/cuối tháng.
2. **Đơn POS nhưng `location_id` bị `null` (nhân viên tạo đơn nháp trên Web Admin rồi thu tiền mặt):** Gom vào nhóm `Admin / Unassigned POS` để kế toán biết cần nhắc nhân viên chọn đúng chi nhánh khi tạo đơn.
3. **Chênh lệch ghi nhận doanh thu sàn TMĐT (Shopee/TikTok):** Haravan ghi nhận theo giá trị đơn hàng đồng bộ về, chưa trừ trợ giá sàn hoặc phí hoa hồng sàn; cần đối chiếu thêm với `finance-profit-margin-analyzer` để thấy lãi thực từng kênh.

## 8. Liên kết Workflow & Skill kế tiếp
- **Đánh giá biên lợi nhuận thực của từng kênh:** Chuyển sang `finance-profit-margin-analyzer`.
- **Phân tích nguyên nhân tỷ lệ hủy cao ở kênh Harasocial:** Chuyển sang `finance-refund-rate-analysis`.
- **Tổng hợp thuế GTGT & hóa đơn điện tử cuối tháng:** Chuyển sang `finance-tax-vat-summary`.
