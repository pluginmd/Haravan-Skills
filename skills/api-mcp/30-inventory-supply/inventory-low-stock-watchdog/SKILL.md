---
name: inventory-low-stock-watchdog
description: "Cảnh báo sớm các SKU bán chạy sắp hết hàng theo ngưỡng tồn kho tối thiểu và tốc độ bán thực tế (days of cover)."
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
    - com.read_products
    - com.read_orders
  endpoints:
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/products.json"
    - "GET https://apis.haravan.com/com/orders.json"
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
# Inventory Low Stock Watchdog — Cảnh Báo Sớm Hết Hàng Theo Tốc Độ Bán (Days of Cover)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` giám sát hàng ngày toàn bộ SKU đang bán trên Haravan để phát hiện sớm các mặt hàng sắp hết tồn kho dựa trên cả **ngưỡng tồn tối thiểu tĩnh (`min_stock`)** lẫn **số ngày đủ bán thực tế (`Days of Cover — DoC`)** tính từ tốc độ bán 14–30 ngày gần nhất. Trong thương mại điện tử Việt Nam, để SKU bán chạy (Hero SKU) rơi về `0` giữa lúc đang chạy quảng cáo Facebook/TikTok không chỉ mất doanh thu trực tiếp mà còn làm hỏng máy học (learning phase) của chiến dịch ads và giảm thứ hạng hiển thị sàn TMĐT.

- **Khi nào sử dụng:** Chạy mỗi sáng (trong quy trình Morning Briefing), trước ngày chạy Mega Sale / Livestream lớn, hoặc khi chuẩn bị duyệt đơn đặt hàng nhà cung cấp (PO).
- **Khi nào KHÔNG sử dụng:** Khi cần dự báo dài hạn kết hợp phân loại ABC/XYZ & Safety Stock (dùng `inventory-stock-velocity-forecast`), hoặc khi muốn tự động điều chuyển kho (dùng `inventory-transfer-proposal`).
- **Definition of Done (DoD):**
  1. Thu thập `inventory_locations`, `products`, và `orders` (14 hoặc 30 ngày gần nhất, loại đơn hủy).
  2. Tính `ADS` (Average Daily Sales) và `DoC = qty_available / ADS` cho từng SKU; phân tầng cảnh báo `P0 Out-of-Stock (0 ngày)`, `P1 Critical (< 7 ngày)`, `P2 Warning (7–14 ngày)`.
  3. Ước tính **Doanh thu có nguy cơ mất (At-Risk Revenue trong 14 ngày tới)** và gợi ý ngay hướng xử lý (điều chuyển nội bộ từ kho khác hay đặt hàng NCC).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Tồn kho khả dụng theo kho | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?limit=50` |
| Thông tin SKU, giá & trạng thái bán | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,published_at,variants` |
| Tốc độ bán hàng 30 ngày | `com.read_orders` | `GET https://apis.haravan.com/com/orders.json?limit=50&created_at_min=<30d_ago>&fields=id,created_at,cancelled_status,line_items` |

**Chạy nhanh qua CLI của repo (`scripts/hrv_ops.py`):**
```bash
python3 scripts/hrv_ops.py low-stock
# Chạy offline với dữ liệu mẫu Việt Nam:
python3 scripts/hrv_ops.py --demo low-stock
```

**Sample Response tổng hợp từ `scripts/hrv_ops.py --demo low-stock`:**
```json
{
  "skill": "inventory-low-stock-watchdog",
  "window_days": 30,
  "alerts": [
    {
      "severity": "P1_CRITICAL",
      "sku": "ATN-250-DEN-L",
      "qty_available": 11,
      "avg_daily_sales": 3.2,
      "days_of_cover": 3.4,
      "at_risk_revenue_14d_vnd": 11186000
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `velocity_window_days` | integer | Không | `30` | Số ngày tính tốc độ bán trung bình (`7..60`; dùng `14` khi sát mùa cao điểm). |
| `critical_doc_days` | integer | Không | `7` | Dưới `7` ngày đủ bán → cảnh báo `P1_CRITICAL`. |
| `warning_doc_days` | integer | Không | `14` | Từ `7..14` ngày đủ bán → cảnh báo `P2_WARNING`. |
| `static_min_threshold` | integer | Không | `5` | Ngưỡng tồn tối thiểu cho SKU bán chậm nhưng vẫn cần giữ sẵn. |
| `exclude_continue_policy` | boolean | Không | `true` | Loại bỏ hàng Pre-order (`inventory_policy == "continue"`) khỏi báo động đỏ. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức tính Tốc độ bán & Số ngày đủ bán (Days of Cover)
```text
ADS = total_sold_units_in_window / velocity_window_days
Days_of_Cover (DoC) = qty_available / ADS   (khi ADS > 0)
At_Risk_Units_14d = max(0, round(ADS * 14 - qty_available))
At_Risk_Revenue_14d = At_Risk_Units_14d * variant.price
```
Phân loại mức độ ưu tiên (sắp xếp giảm dần theo `At_Risk_Revenue_14d`):
1. **`P0_OOS_HERO`:** `qty_available <= 0` nhưng `ADS >= 0.5` (đang bán tốt nhưng vừa đứt hàng).
2. **`P1_CRITICAL`:** `0 < DoC < critical_doc_days` (hoặc `qty_available <= static_min_threshold` với `ADS > 0.2`).
3. **`P2_WARNING`:** `critical_doc_days <= DoC <= warning_doc_days`.
4. **Kiểm tra chéo đa kho:** Nếu kho online (`primary`) sắp hết nhưng kho chi nhánh POS còn dư `> 20` cái → gắn gợi ý `TRANSFER_AVAILABLE` (chạy `inventory-transfer-proposal`) thay vì chờ nhập NCC.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Cảnh Báo Hết Hàng Sớm — Watchdog (Cửa sổ 30 ngày)
- **Tóm tắt:** `3` SKU **P0 (Đứt hàng)** | `7` SKU **P1 (< 7 ngày)** | `12` SKU **P2 (7–14 ngày)**
- **Tổng doanh thu có nguy cơ mất trong 14 ngày tới (ước tính):** `148.500.000₫`

| Mức độ | SKU | Tên sản phẩm | Tồn khả dụng | Bán/ngày (ADS) | Days of Cover | Doanh thu rủi ro (14d) | Gợi ý hành động |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P0` | `AKD-DEN-M` | Áo Khoác Dù 2 Lớp - M | `0` | `2.4` | `0.0 ngày` | `18.446.000₫` | Đặt PO gấp / Tạm tắt ads mẫu này |
| `P1` | `ATN-250-DEN-L` | Áo Thun 250GSM - Đen L | `11` | `3.2` | `3.4 ngày` | `11.186.000₫` | Điều chuyển 30 cái từ Kho Q.1 |
| `P2` | `QCG-REU-L` | Quần Cargo Túi Hộp - L | `22` | `2.0` | `11.0 ngày` | `2.940.000₫` | Lập PO bổ sung tuần này |

### JSON Output Schema
```json
{
  "skill": "inventory-low-stock-watchdog",
  "window_days": 30,
  "summary": { "p0_oos_hero": 3, "p1_critical": 7, "p2_warning": 12, "total_at_risk_revenue_14d_vnd": 148500000 },
  "items": [
    { "severity": "P1", "variant_id": 1129045513, "sku": "ATN-250-DEN-L", "qty_available": 11, "ads": 3.2, "doc_days": 3.4, "transfer_candidate_location_id": 1001235 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ đọc và cảnh báo, không tự tạo PO hay phiếu chuyển kho.
- **Tuyên bố tài chính:** `At_Risk_Revenue` là **Operational Estimate** giả định tốc độ bán ổn định, chưa tính yếu tố mùa vụ đột biến.
- **PII:** Không trích xuất thông tin khách hàng từ `/com/orders.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu 1 trong 3 scope (`inventories`, `products`, `orders`) | Nếu thiếu `orders`, tự động hạ cấp sang cảnh báo theo ngưỡng tĩnh `static_min_threshold` và ghi chú rõ. |
| `429 Too Many Requests` | Quét đơn hàng 30 ngày số lượng lớn | Dùng `fields=id,created_at,cancelled_status,line_items` và `since_id`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Biến động đột biến từ 1 phiên Livestream / đơn sỉ (Outlier Spike):** Một khách sỉ mua 200 cái trong 1 ngày sẽ làm `ADS` vọt lên giả tạo gấp 5 lần bình thường. Cần ghi chú nếu 1 đơn duy nhất chiếm `> 40%` tổng lượng bán trong kỳ.
2. **Hàng đang trên đường về (`qty_incoming` từ PO đã duyệt):** Tồn khả dụng hiện tại thấp nhưng đã có PO sắp về ngày mai → nhắc đối chiếu thêm `inventory-purchase-order-audit` trước khi đặt trùng PO.
3. **Sản phẩm bị tắt bán (`published_at == null`) nhưng từng bán chạy 2 tuần trước:** Nếu shop chủ động ngừng kinh doanh mẫu đó thì không nên báo `P0` mỗi sáng; lọc theo `published_at != null`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `store-health-check`.
- **Chạy tiếp theo:** `inventory-transfer-proposal` (nếu kho khác còn dư), `inventory-stock-velocity-forecast` (tính ROP đặt hàng NCC), `inventory-purchase-order-audit` (kiểm tra hàng đang về).
