---
name: inventory-aging-dead-stock
description: "Phát hiện hàng tồn kho chậm luân chuyển (30/60/90+ ngày không phát sinh đơn) và ước tính giá trị vốn bị chôn."
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
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/products.json"
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
# Inventory Aging & Dead Stock — Phân Tích Hàng Tồn Lâu Ngày & Ước Tính Vốn Chôn

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` phân tích tuổi tồn kho (Inventory Aging) của toàn bộ SKU đang còn hàng trên Haravan bằng cách đối chiếu tồn kho hiện tại (`/com/inventory_locations.json`), ngày tạo sản phẩm (`/com/products.json`) và lịch sử bán hàng (`/com/orders.json` trong 90 ngày gần nhất). Tại Việt Nam, hàng tồn đọng (Dead Stock / Slow-moving) chiếm 20–40% dòng tiền của các shop thời trang và bán lẻ; phát hiện sớm giúp chủ shop ra quyết định xả kho (clearance), ghép combo hoặc điều chuyển sang chi nhánh bán tốt hơn trước khi hàng lỗi mốt hoặc hết hạn sử dụng.

- **Khi nào sử dụng:** Cuối mỗi tháng / cuối mùa vụ, trước khi lập kế hoạch nhập hàng mới (PO), hoặc khi chuẩn bị chương trình xả kho thanh lý (Clearance Sale).
- **Khi nào KHÔNG sử dụng:** Khi cửa hàng mới mở < 30 ngày chưa có đủ lịch sử đơn hàng, hoặc khi cần xem SKU sắp hết hàng (dùng `inventory-low-stock-watchdog`).
- **Definition of Done (DoD):**
  1. Kết nối 3 tập dữ liệu: tồn kho hiện tại (`qty_onhand > 0`), sản phẩm (giá bán, ngày tạo), và đơn hàng không bị hủy trong `lookback_days` (mặc định 90 ngày).
  2. Phân nhóm toàn bộ SKU còn tồn vào 4 rổ tuổi không bán được (`0–30d Active`, `31–60d Slow`, `61–90d Stagnant`, `> 90d Dead Stock`) và tính **ước tính giá trị tồn kho (Retail Value / Cost Estimate)**.
  3. Xuất bảng Top 20 SKU chôn vốn lớn nhất kèm đề xuất hành động xả kho cụ thể.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Tồn kho chi tiết theo kho | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?limit=50` |
| Danh mục sản phẩm & giá bán | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,created_at,tags,variants` |
| Đơn hàng trong 90 ngày gần nhất | `com.read_orders` | `GET https://apis.haravan.com/com/orders.json?limit=50&created_at_min=<90d_ago>&fields=id,created_at,cancelled_status,line_items` |

**Truy vấn tối ưu bằng `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True, req_per_sec=2.5)
inv = c.paginate("com", "/inventory_locations.json", key="inventory_locations", max_records=5000)
orders = c.paginate("com", "/orders.json", key="orders", params={"created_at_min": "2026-08-27T00:00:00Z", "fields": "id,created_at,cancelled_status,line_items"}, max_records=5000)
```

**Sample Response (`GET /com/inventory_locations.json?limit=2`):**
```json
{
  "inventory_locations": [
    { "id": 5001, "location_id": 1001234, "product_id": 1041120088, "variant_id": 1100231, "qty_onhand": 64, "qty_commited": 0, "qty_available": 64, "updated_at": "2026-07-10T04:12:00Z" }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | Không | `90` | Cửa sổ ngày quét đơn hàng (`30..180`). |
| `min_age_days_to_evaluate` | integer | Không | `30` | Bỏ qua sản phẩm mới tạo dưới `30` ngày để tránh báo nhầm hàng mới về là Dead Stock. |
| `default_cogs_ratio` | float | Không | `0.55` | Tỷ lệ ước tính giá vốn / giá bán lẻ khi API không có giá vốn (ghi rõ là ước tính). |
| `location_ids` | array[integer] | Không | `[]` (toàn hệ thống) | Lọc theo kho cụ thể nếu cần phân tích riêng kho tổng hoặc cửa hàng POS. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức phân loại Tuổi Tồn Kho & Giá trị Vốn Chôn
Với mỗi `variant_id` có `total_onhand > 0` và `product_age_days >= min_age_days_to_evaluate`:
1. Từ `orders` hợp lệ (`cancelled_status != "cancelled"`), tính:
   - `sold_units_window = sum(item.quantity)` trong `lookback_days`.
   - `last_sold_at = max(order.created_at)` cho `variant_id` đó.
   - `days_since_last_sale = (now - last_sold_at).days` (nếu `sold_units_window == 0`, gán `> lookback_days`).
2. **Phân rổ Aging Buckets:**
   - `0–30 ngày`: **Healthy / Active**
   - `31–60 ngày`: **Slow-Moving** (cân nhắc đẩy quảng cáo / gói combo)
   - `61–90 ngày`: **Stagnant** (cân nhắc giảm giá 20–30%)
   - `> 90 ngày` (0 đơn trong 90 ngày): **Dead Stock** (xả kho / thanh lý / đóng gói quà tặng)
3. **Ước tính giá trị tồn kho:**
   - `retail_value_vnd = total_onhand * variant.price`
   - `estimated_capital_vnd = retail_value_vnd * default_cogs_ratio` (trừ khi có bảng giá vốn thực tế).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Phân tích Tồn Kho Chậm Luân Chuyển (90 ngày gần nhất)
| Phân nhóm Aging | Số SKU | Tổng tồn (cái) | Giá trị bán lẻ (VND) | Ước tính vốn chôn (55%) | Tỷ trọng vốn |
| --- | --- | --- | --- | --- | --- |
| `0–30 ngày` (Active) | 184 | 4.120 | 1.480.000.000 | 814.000.000 | 64.2% |
| `31–60 ngày` (Slow) | 42 | 780 | 285.000.000 | 156.750.000 | 12.4% |
| `61–90 ngày` (Stagnant) | 25 | 510 | 198.000.000 | 108.900.000 | 8.6% |
| `> 90 ngày` (Dead Stock) | 31 | 890 | 342.000.000 | 188.100.000 | 14.8% |

**Top SKU Dead Stock cần ưu tiên giải phóng:**
1. `AKP-2024-XL` (Áo Khoác Phao 2024 - XL): Tồn `64`, `0` đơn / 90 ngày, Giá trị lẻ `41.600.000₫` → Gắn tag `clearance` & giảm giá xả kho.

> *Tuyên bố tài chính:* Giá trị vốn bị chôn là **Operational Estimate** dựa trên tỷ lệ ước tính `default_cogs_ratio`, không thay thế báo cáo giá trị hàng tồn kho kế toán (FIFO/Bình quân gia quyền).

### JSON Output Schema
```json
{
  "skill": "inventory-aging-dead-stock",
  "lookback_days": 90,
  "partial_sample": false,
  "buckets": {
    "active_0_30d": { "skus": 184, "units": 4120, "retail_value_vnd": 1480000000 },
    "slow_31_60d": { "skus": 42, "units": 780, "retail_value_vnd": 285000000 },
    "stagnant_61_90d": { "skus": 25, "units": 510, "retail_value_vnd": 198000000 },
    "dead_gt_90d": { "skus": 31, "units": 890, "retail_value_vnd": 342000000, "estimated_capital_vnd": 188100000 }
  },
  "top_dead_stock": [{ "variant_id": 1100231, "sku": "AKP-2024-XL", "qty_onhand": 64, "days_since_last_sale": ">90", "retail_value_vnd": 41600000 }]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ đọc và tính toán, không tự ý giảm giá hay ẩn sản phẩm.
- **Cảnh báo Partial Sample:** Nếu số đơn trong 90 ngày vượt `max_records=5000`, báo rõ `partial_sample: true` vì một SKU có thể đã bán ở phần đơn chưa quét hết.
- **PII:** Chỉ đọc `line_items` và `created_at` từ `/com/orders.json`, không đọc hay lưu thông tin cá nhân khách hàng.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu `com.read_orders` hoặc `com.read_inventories` | Báo rõ scope còn thiếu để chạy đủ phân tích. |
| `429 Too Many Requests` | Quét 90 ngày đơn hàng của shop lớn | Dùng `fields=id,created_at,cancelled_status,line_items` và `since_id` với `2.0 req/s`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Hàng mới nhập về hôm qua nhưng sản phẩm đã tạo từ năm ngoái:** `product.created_at` cũ hơn 90 ngày nhưng thực chất mới restock tuần trước → cần kết hợp kiểm tra `inventory_location.updated_at` hoặc đối chiếu phiếu nhập `purchase_receives` trước khi kết luận Dead Stock.
2. **Hàng lẻ size (Broken Size Run — chỉ còn size XS hoặc XXL):** Rất phổ biến trong ngành thời trang VN; gom nhóm ở cấp `product_id` để thấy sản phẩm bán chạy nhưng riêng 1–2 size bị chết tồn.
3. **Sản phẩm đã bị ẩn (`published_at == null`) nhưng vẫn còn tồn trong kho:** Nhiều shop ẩn sản phẩm trên web rồi quên luôn hàng trong kho vật lý → tách riêng cột `hidden_with_stock` để nhắc mở bán thanh lý.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `inventory-multi-location-audit`.
- **Chạy tiếp theo:** `catalog-product-lifecycle-proposal` (gắn tag `clearance`), `pricing-bulk-adjustment-proposal` (lập đề xuất giảm giá xả kho có kiểm soát).
