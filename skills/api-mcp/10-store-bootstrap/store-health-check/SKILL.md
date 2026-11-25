---
name: store-health-check
description: "Khám sức khỏe tổng quát cửa hàng Haravan trên 5 trụ cột: Catalog, Tồn kho, Đơn hàng/Giao vận, Khuyến mãi và Storefront."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 10-store-bootstrap
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_shop
    - com.read_products
    - com.read_orders
    - com.read_inventories
    - com.read_discounts
    - web.read_themes
  endpoints:
    - "GET https://apis.haravan.com/com/shop.json"
    - "GET https://apis.haravan.com/com/products.json"
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/promotions.json"
    - "GET https://apis.haravan.com/web/themes.json"
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
# Store Health Check — Khám Sức Khỏe Tổng Quát Cửa Hàng Haravan (5 Trụ Cột)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` cung cấp bức tranh điều hành toàn diện (Executive Scorecard) cho chủ cửa hàng / Quản lý vận hành Haravan trên **5 trụ cột**: (1) Catalog, (2) Tồn kho, (3) Đơn hàng & Giao vận, (4) Khuyến mãi, và (5) Storefront/Theme. Đây là skill chẩn đoán nhanh (triage) chạy định kỳ hàng tuần hoặc đầu mỗi buổi họp giao ban để phát hiện ngay điểm nghẽn trước khi đi sâu vào từng domain.

- **Khi nào sử dụng:** Khám sức khỏe định kỳ hàng tuần/tháng, nhận bàn giao vận hành một cửa hàng Haravan mới, hoặc khi doanh thu đột ngột giảm bất thường mà chưa rõ nguyên nhân.
- **Khi nào KHÔNG sử dụng:** Khi cửa hàng chưa khai trương chưa có đơn hàng (dùng `store-bootstrap-checklist`), hoặc khi cần chỉnh sửa dữ liệu (phải chuyển sang skill L2/L3 tương ứng).
- **Definition of Done (DoD):**
  1. Quét dữ liệu read-only từ 6 nguồn API (`shop`, `products`, `orders`, `inventory_locations`, `promotions`, `themes`) trong giới hạn `max_records`.
  2. Tính điểm sức khỏe từng trụ cột (mỗi trụ cột 20đ → tổng **100 điểm**) và xếp hạng `A / B / C / D`.
  3. Liệt kê Top 5 rủi ro cấp bách nhất kèm đúng tên skill chuyên sâu cần chạy tiếp theo để xử lý.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Trụ cột | Scope | Endpoint Haravan |
| --- | --- | --- |
| Nền tảng | `com.read_shop` | `GET https://apis.haravan.com/com/shop.json` |
| 1. Catalog | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50` |
| 2. Tồn kho | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?limit=50` |
| 3. Đơn hàng & Giao vận | `com.read_orders` | `GET https://apis.haravan.com/com/orders.json?limit=50&created_at_min=<7d_ago>` |
| 4. Khuyến mãi | `com.read_discounts` | `GET https://apis.haravan.com/com/promotions.json?limit=50` |
| 5. Storefront | `web.read_themes` | `GET https://apis.haravan.com/web/themes.json` |

**Chạy trực tiếp qua CLI chuẩn của repo (`scripts/hrv_ops.py`):**
```bash
# Chạy trên store thật (cần HARAVAN_ACCESS_TOKEN)
python3 scripts/hrv_ops.py health-check

# Chạy thử offline với dữ liệu mẫu Việt Nam
python3 scripts/hrv_ops.py --demo health-check
```

**Sample Response tổng hợp từ `scripts/hrv_ops.py health-check`:**
```json
{
  "skill": "store-health-check",
  "shop": { "name": "Demo VN Store", "domain": "demo-vn.myharavan.com", "currency": "VND" },
  "health_score": 76,
  "pillars": {
    "catalog": { "score": 16, "max": 20, "issues": ["3 variants thiếu SKU", "2 sản phẩm thiếu ảnh"] },
    "inventory": { "score": 12, "max": 20, "issues": ["2 SKU tồn âm", "5 SKU dưới ngưỡng tồn tối thiểu"] },
    "orders": { "score": 15, "max": 20, "issues": ["4 đơn chưa xử lý > 48h", "tỷ lệ hủy 11.2%"] },
    "promotions": { "score": 15, "max": 20, "issues": ["2 chương trình hết hạn chưa tắt"] },
    "storefront": { "score": 18, "max": 20, "issues": ["chưa có staging theme backup mới"] }
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `order_window_days` | integer | Không | `30` | Cửa sổ ngày quét đơn hàng (`7..90`). |
| `low_stock_threshold` | integer | Không | `5` | Ngưỡng tồn kho khả dụng (`qty_available`) cảnh báo thấp. |
| `unfulfilled_sla_hours` | integer | Không | `48` | Ngưỡng giờ cảnh báo đơn hàng chưa xuất kho (SLA). |
| `max_records` | integer | Không | `5000` | Trần số bản ghi quét tối đa cho mỗi tài nguyên. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức tính điểm 5 Trụ cột (Tổng = 100 điểm)
- **Trụ cột 1 — Catalog (20đ):** Khởi đầu 20đ; trừ theo tỷ lệ sản phẩm thiếu ảnh (`-5đ` nếu > 5%), thiếu SKU/trùng SKU (`-5đ`), `compare_at_price <= price` (`-5đ`), mô tả rỗng (`-5đ`).
- **Trụ cột 2 — Tồn kho (20đ):** Khởi đầu 20đ; trừ `-8đ` nếu có bất kỳ SKU nào tồn âm (`qty_onhand < 0` hoặc `qty_available < 0`), trừ `-6đ` nếu tỷ lệ hết hàng > 15% catalog đang bán, trừ `-6đ` nếu > 10% SKU dưới `low_stock_threshold`.
- **Trụ cột 3 — Đơn hàng & Giao vận (20đ):** Khởi đầu 20đ; trừ `-7đ` nếu có đơn `notfulfilled` quá `48h`, trừ `-7đ` nếu tỷ lệ hủy (`cancelled_status == "cancelled"`) > 10%, trừ `-6đ` nếu đơn COD chưa thu tiền quá 7 ngày > 5%.
- **Trụ cột 4 — Khuyến mãi (20đ):** Khởi đầu 20đ; trừ `-10đ` nếu có 2+ chương trình khuyến mãi đang chồng chéo không chủ đích, trừ `-10đ` nếu có khuyến mãi quá hạn nhưng vẫn ở trạng thái `active`.
- **Trụ cột 5 — Storefront (20đ):** Khởi đầu 20đ; trừ `-10đ` nếu không xác định được `role == "main"`, trừ `-10đ` nếu không có theme backup `unpublished`.

**Xếp hạng tổng:** `A (>= 85)`, `B (70–84)`, `C (50–69)`, `D (< 50 — Cần can thiệp khẩn cấp)`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Sức Khỏe Cửa Hàng Haravan — Điểm tổng: 76/100 (Hạng B)
| Trụ cột | Điểm | Mức độ | Chỉ số chính | Skill xử lý tiếp theo |
| --- | --- | --- | --- | --- |
| 1. Catalog | 16/20 | Tốt | 148 SP, 3 variant thiếu SKU, 2 SP thiếu ảnh | `catalog-data-completeness-audit` |
| 2. Tồn kho | 12/20 | Cần chú ý | 2 SKU tồn âm (POS), 5 SKU sắp hết | `inventory-multi-location-audit` |
| 3. Đơn hàng (30d) | 15/20 | Cần chú ý | 412 đơn, 4 đơn trễ SLA > 48h, hủy 11.2% | `order-triage-daily` |
| 4. Khuyến mãi | 15/20 | Tốt | 6 KM active, 2 KM hết hạn cần dọn | `promo-audit-overlap` |
| 5. Storefront | 18/20 | Tốt | Live theme ổn định, nên nhân bản backup | `haravan-cli-theme-ops` |

> *Lưu ý tài chính:* Mọi ước tính doanh thu/tỷ lệ hủy trong báo cáo là **Operational Estimate**, không thay thế sổ cái kế toán chính thức.

### JSON Output Schema
```json
{
  "skill": "store-health-check",
  "window_days": 30,
  "partial_sample": false,
  "overall_score": 76,
  "grade": "B",
  "pillars": { "catalog": 16, "inventory": 12, "orders": 15, "promotions": 15, "storefront": 18 },
  "top_priority_actions": [
    { "priority": "P1", "pillar": "inventory", "issue": "2 SKU tồn âm tại Kho Q.1", "next_skill": "inventory-multi-location-audit" },
    { "priority": "P1", "pillar": "orders", "issue": "4 đơn chưa xuất kho quá 48h", "next_skill": "order-triage-daily" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** 100% lệnh gọi là `GET`. Không thực hiện sửa đổi dữ liệu.
- **Cảnh báo Partial Sample:** Nếu cửa hàng có > 5.000 đơn trong 30 ngày hoặc > 5.000 SKU, dừng ở `max_records=5000`, gắn `"partial_sample": true` và ghi rõ phạm vi dữ liệu đã quét trong báo cáo.
- **Bảo vệ PII:** Không xuất tên, số điện thoại, địa chỉ hay email khách hàng từ object `orders` vào báo cáo tổng hợp.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` trên 1 trong 6 endpoint | Token chỉ có quyền một số module (vd thiếu `com.read_discounts`) | Không làm sập toàn bộ báo cáo; đánh dấu trụ cột đó `SKIPPED` và quy đổi điểm trên các trụ cột còn lại (vd `/80`). |
| `429 Too Many Requests` | Quét đồng thời 5 tài nguyên lớn | Chạy tuần tự qua `HaravanClient(req_per_sec=2.5)`, ưu tiên dùng `fields=` để giảm kích thước JSON. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Đơn hàng từ sàn TMĐT (Shopee/TikTok/Lazada) đổ về Haravan:** Các đơn này có `source_name` là sàn và trạng thái vận chuyển đồng bộ chậm hơn đơn website; cần tách tỷ lệ hủy của đơn Website vs đơn Sàn khi giải thích trụ cột Đơn hàng.
2. **Cửa hàng mới < 7 ngày chưa có đơn hoặc khuyến mãi:** Trụ cột Đơn hàng/Khuyến mãi không bị trừ điểm oan; ghi trạng thái `N/A (No data yet)`.
3. **Biến thể không quản lý tồn kho (`inventory_management: null`):** Thường gặp ở dịch vụ, voucher điện tử hoặc hàng order; phải loại khỏi mẫu số tính tỷ lệ hết hàng để tránh sai lệch.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup`.
- **Chạy tiếp theo (theo trụ cột yếu nhất):** `catalog-data-completeness-audit`, `inventory-low-stock-watchdog`, `inventory-multi-location-audit`, `order-triage-daily`, `promo-audit-overlap`.
