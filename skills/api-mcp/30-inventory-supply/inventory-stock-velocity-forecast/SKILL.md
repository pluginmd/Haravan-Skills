---
name: inventory-stock-velocity-forecast
description: "Phân tích tốc độ luân chuyển hàng hóa (ABC/XYZ) và tính điểm đặt hàng lại (Reorder Point) dựa trên lead time nhà cung cấp."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 30-inventory-supply
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_inventories
    - com.read_orders
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---
# Inventory Stock Velocity & Forecast — Phân Tích ABC/XYZ & Tính Điểm Đặt Hàng Lại (ROP)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` phân tích tốc độ luân chuyển hàng hóa theo mô hình **ABC (đóng góp doanh thu)** kết hợp **XYZ (độ ổn định nhu cầu)** và tính toán khoa học **Điểm đặt hàng lại (Reorder Point — ROP)**, **Tồn kho an toàn (Safety Stock)** và **Số lượng đề xuất nhập (Suggested Order Qty)** dựa trên thời gian giao hàng thực tế của nhà cung cấp (`lead_time_days`). Đây là công cụ giúp các doanh nghiệp bán lẻ Việt Nam chuyển từ "nhập hàng theo cảm tính" sang nhập hàng theo dữ liệu, giảm đồng thời tình trạng đứt hàng nhóm A và tồn đọng nhóm C.

- **Khi nào sử dụng:** Lập kế hoạch nhập hàng (Open-to-Buy / PO) hàng tuần/tháng, chuẩn bị tồn kho trước mùa cao điểm (11.11, 12.12, Tết Nguyên Đán), hoặc tối ưu định mức tồn kho an toàn.
- **Khi nào KHÔNG sử dụng:** Khi chỉ cần cảnh báo cháy hàng khẩn cấp trong ngày (dùng `inventory-low-stock-watchdog`), hoặc khi cửa hàng có lịch sử bán `< 30` ngày.
- **Definition of Done (DoD):**
  1. Thu thập lịch sử đơn hàng 60–90 ngày (`/com/orders.json`, loại đơn hủy) và tồn kho khả dụng (`/com/inventory_locations.json`).
  2. Phân loại toàn bộ SKU vào ma trận 9 ô **ABC × XYZ** và tính chính xác `ADS`, độ lệch chuẩn ngày `σ_d`, `Safety_Stock`, `ROP`, và `Suggested_PO_Qty`.
  3. Xuất bảng đề xuất đặt hàng ưu tiên nhóm `AX / AY / BX` kèm giả định `lead_time_days` và mức độ phục vụ (`service_level`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Lịch sử đơn hàng 60–90 ngày | `com.read_orders` | `GET https://apis.haravan.com/com/orders.json?limit=50&created_at_min=<60d_ago>&fields=id,created_at,cancelled_status,line_items` |
| Tồn kho khả dụng toàn hệ thống | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?limit=50` |
| Danh mục sản phẩm & biến thể | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,vendor,variants` |

**Truy vấn chuỗi thời gian theo ngày bằng `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True, req_per_sec=2.5)
orders = c.paginate("com", "/orders.json", key="orders", params={"created_at_min": "2026-09-26T00:00:00Z", "fields": "id,created_at,cancelled_status,line_items"}, max_records=5000)
inv = c.paginate("com", "/inventory_locations.json", key="inventory_locations", max_records=5000)
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `analysis_days` | integer | Không | `60` | Chuỗi ngày lịch sử để tính `ADS` và độ lệch chuẩn `σ_d` (`30..180`). |
| `lead_time_days` | integer | Không | `10` | Thời gian từ lúc đặt PO đến khi hàng về kho (VD: xưởng nội địa `7–14` ngày, hàng nhập TQ `15–25` ngày). |
| `target_cover_days` | integer | Không | `30` | Chu kỳ phủ hàng mong muốn sau khi nhập về kho. |
| `service_level_z` | float | Không | `1.65` | Hệ số Z theo mức phục vụ: `1.28` (90%), `1.65` (95% — chuẩn nhóm A), `2.05` (98%). |
| `seasonality_multiplier` | float | Không | `1.0` | Hệ số mùa vụ (vd `1.3` cho tháng sát Tết/Mega Sale). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### 1. Phân loại ABC (Theo đóng góp Doanh thu tích lũy)
- Sắp xếp SKU giảm dần theo doanh thu trong `analysis_days`:
  - **Nhóm A:** Chiếm `0% – 80%` doanh thu tích lũy (Hero SKUs — kiểm soát chặt nhất).
  - **Nhóm B:** Chiếm `80% – 95%` doanh thu tích lũy.
  - **Nhóm C:** Chiếm `95% – 100%` doanh thu tích lũy.

### 2. Phân loại XYZ (Theo Hệ số biến thiên nhu cầu `CV = σ_d / ADS`)
- **Nhóm X (`CV <= 0.5`):** Nhu cầu rất ổn định, dễ dự báo chính xác.
- **Nhóm Y (`0.5 < CV <= 1.0`):** Biến động theo mùa/chiến dịch khuyến mãi.
- **Nhóm Z (`CV > 1.0`):** Nhu cầu thất thường (đột biến theo livestream hoặc hàng bán rất chậm).

### 3. Công thức Điểm Đặt Hàng Lại (ROP) & Lượng Đặt Hàng Đề Xuất
```text
ADS_adj = ADS * seasonality_multiplier
Safety_Stock = ceil( service_level_z * sigma_d * sqrt(lead_time_days) )
ROP = ceil( ADS_adj * lead_time_days + Safety_Stock )
Suggested_PO_Qty = max(0, ceil( ADS_adj * (lead_time_days + target_cover_days) + Safety_Stock - qty_available - qty_incoming ))
```
- Khi `qty_available <= ROP` → phát tín hiệu **REORDER NOW**.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bảng Dự Báo Tốc Độ Bán & Điểm Đặt Hàng Lại (Lead Time = 10 ngày, Service Level = 95%)
| SKU | Nhóm | ADS | Độ lệch `σ_d` | Tồn hiện tại | Safety Stock | ROP | Trạng thái | Đề xuất đặt PO (30d cover) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ATN-250-DEN-L` | `AX` | `3.2` | `1.1` | `11` | `6` | `38` | **REORDER NOW** | `123` cái |
| `AKD-DEN-M` | `AY` | `2.4` | `1.9` | `32` | `10` | `34` | **REORDER NOW** | `74` cái |
| `QCG-REU-L` | `BX` | `1.5` | `0.6` | `55` | `4` | `19` | Đủ hàng | `0` cái |

> *Lưu ý dự báo:* Kết quả là **Operational Forecast Aid**, chưa tự động trừ các đợt đứt hàng trong quá khứ nếu không điều chỉnh thủ công.

### JSON Output Schema
```json
{
  "skill": "inventory-stock-velocity-forecast",
  "params": { "analysis_days": 60, "lead_time_days": 10, "service_level_z": 1.65, "seasonality_multiplier": 1.0 },
  "abc_xyz_matrix": { "AX": 14, "AY": 9, "AZ": 3, "BX": 28, "BY": 21, "BZ": 11, "CX": 18, "CY": 34, "CZ": 72 },
  "reorder_recommendations": [
    { "sku": "ATN-250-DEN-L", "class": "AX", "ads": 3.2, "sigma_d": 1.1, "qty_available": 11, "safety_stock": 6, "rop": 38, "suggested_po_qty": 123 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ xuất bảng tính dự báo để bộ phận thu mua duyệt, không tự động tạo PO.
- **Partial Sample:** Nếu cửa hàng có `> 5.000` đơn trong 60 ngày, phải thu hẹp `analysis_days` xuống `30` ngày hoặc báo rõ `partial_sample: true` vì thiếu đơn sẽ làm `ADS` bị tính thấp hơn thực tế.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu `com.read_orders` hoặc `com.read_inventories` | Báo rõ scope cần bổ sung. |
| `429 Too Many Requests` | Quét 60–90 ngày đơn hàng lớn | Phân trang bằng `since_id` với `fields=id,created_at,cancelled_status,line_items` ở `2.0 req/s`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Sai lệch do đứt hàng trong quá khứ (Stockout Censored Demand):** Nếu một SKU bán chạy bị hết hàng suốt 20/60 ngày vừa qua, chia tổng bán cho 60 ngày sẽ kéo tụt `ADS` đi 33% và gây đặt thiếu hàng lặp lại. Cần cảnh báo những SKU có chuỗi ngày liên tiếp bán = 0 kèm tồn cuối kỳ = 0.
2. **Đặt hàng theo thùng / MOQ của nhà cung cấp:** `Suggested_PO_Qty` ra số lẻ (vd `123` cái) nhưng xưởng may chỉ nhận cắt tối thiểu `100` cái hoặc bội số `50` cái → ghi chú nhắc làm tròn theo MOQ của từng NCC.
3. **Sản phẩm mới ra mắt `< 14` ngày:** Không đủ mẫu tính `σ_d` chính xác → xếp vào nhóm `NEW_LAUNCH` riêng thay vì ép vào `AZ/CZ`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `inventory-purchase-order-audit` (lấy `lead_time_days` thực tế và `qty_incoming`).
- **Chạy tiếp theo:** `inventory-aging-dead-stock` (xử lý nhóm `CZ`), `inventory-transfer-proposal` (cân bằng kho nội bộ trước khi đặt mới).
