---
name: catalog-duplicate-sku-barcode
description: "Phát hiện toàn bộ SKU hoặc Barcode bị trùng lặp giữa các variant trên Haravan — nguyên nhân hàng đầu gây lệch tồn kho đa kênh."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 20-catalog-merchandising
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_products
  endpoints:
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
# Catalog Duplicate SKU & Barcode — Phát Hiện Trùng Lặp Mã Hàng Đa Kênh

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` quét toàn bộ biến thể sản phẩm trên Haravan để phát hiện 100% các trường hợp **trùng lặp SKU** (kể cả trùng không phân biệt hoa/thường hoặc dư khoảng trắng như `"ATN-01"` và `"atn-01 "`), **trùng lặp Barcode/EAN**, và **SKU trống/không hợp lệ**. Trên hệ thống Haravan Omni kết nối HaraRetail POS + Shopee/TikTok/Lazada, trùng SKU là nguyên nhân số 1 gây trừ nhầm tồn kho giữa hai sản phẩm khác nhau, xuất nhầm hàng tại kho và lệch báo cáo giá vốn.

- **Khi nào sử dụng:** Trước khi bật đồng bộ sàn TMĐT (Shopee/Lazada/TikTok), trước đợt kiểm kho định kỳ (`inventory-stocktake-cycle-count`), sau mỗi đợt import sản phẩm mới, hoặc khi kho báo tồn nhảy bất thường.
- **Khi nào KHÔNG sử dụng:** Khi muốn tự động đổi SKU hàng loạt (đổi SKU đang liên kết sàn TMĐT có thể làm đứt mapping sàn — phải rà soát thủ công hoặc lập proposal riêng có duyệt).
- **Definition of Done (DoD):**
  1. Tải toàn bộ danh sách sản phẩm và variants trong phạm vi `max_records=5000`.
  2. Chuẩn hóa chuỗi (`trim`, `upper`) để phát hiện cả trùng tuyệt đối (`EXACT`) lẫn trùng ẩn do khoảng trắng/chữ hoa-thường (`NORMALIZED_COLLISION`).
  3. Xuất danh sách cụm trùng kèm `product_id`, `variant_id`, `title`, trạng thái `published`, và giá bán để team vận hành chọn 1 bản chuẩn giữ lại và đổi mã các bản còn lại.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Danh sách sản phẩm & toàn bộ biến thể | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,published_at,variants` |

**Chạy quét tối ưu băng thông bằng `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True, req_per_sec=2.5)
products = c.paginate(
    "com", "/products.json", key="products",
    params={"limit": 50, "fields": "id,title,published_at,variants"},
    max_records=5000,
)
```

**Sample Response (`GET /com/products.json?fields=id,title,published_at,variants`):**
```json
{
  "products": [
    {
      "id": 105001122,
      "title": "Áo Polo Pique Basic - Trắng",
      "published_at": "2026-06-15T03:00:00Z",
      "variants": [
        { "id": 111001, "title": "M", "sku": "POLO-TRG-M", "barcode": "8938501100012", "price": 349000.0 }
      ]
    },
    {
      "id": 105009988,
      "title": "[SALE] Áo Polo Pique Basic - Trắng",
      "published_at": "2026-11-01T03:00:00Z",
      "variants": [
        { "id": 119901, "title": "M", "sku": "polo-trg-m ", "barcode": "8938501100012", "price": 249000.0 }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `case_insensitive` | boolean | Không | `true` | Coi `"SKU-A"` và `"sku-a"` là trùng (do đa số ERP/POS không phân biệt hoa thường). |
| `include_unpublished` | boolean | Không | `true` | Quét cả sản phẩm đang ẩn vì sản phẩm ẩn vẫn giữ liên kết kho/POS. |
| `check_barcode` | boolean | Không | `true` | Kiểm tra trùng lặp trường `barcode` song song với `sku`. |
| `sku_regex` | string | Không | `""` | Biểu thức chính quy kiểm tra chuẩn đặt mã SKU nội bộ (vd `^[A-Z0-9-]{4,24}$`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Thuật toán Gom cụm Trùng lặp (Collision Detection)
1. **Duyệt phẳng toàn bộ Variants:** Từ mỗi `product`, duyệt mảng `variants`, tạo bản ghi `(product_id, variant_id, product_title, variant_title, published, raw_sku, raw_barcode, price)`.
2. **Chuẩn hóa khóa:**
   - `norm_sku = raw_sku.strip().upper()` (nếu `case_insensitive=true`).
   - `norm_barcode = re.sub(r"\s+", "", raw_barcode or "")`.
3. **Phân loại 4 nhóm lỗi:**
   - **P0 — Trùng SKU giữa 2 sản phẩm đang bán (`ACTIVE_CROSS_PRODUCT_DUP`):** Mức độ nghiêm trọng nhất — chắc chắn gây lệch kho đa kênh.
   - **P1 — Trùng SKU giữa 1 sản phẩm đang bán và 1 sản phẩm ẩn (`ACTIVE_VS_HIDDEN_DUP`):** Nguy cơ khi bật lại hoặc quét POS.
   - **P1 — Trùng Barcode khác SKU (`BARCODE_COLLISION`):** Thu ngân quét mã vạch tại quầy POS sẽ bắn nhầm sản phẩm.
   - **P2 — SKU trống (`EMPTY_SKU`) hoặc chứa ký tự lạ/khoảng trắng (`MALFORMED_SKU`):** Không map được sang Shopee/TikTok/ERP.
4. **Xếp hạng ưu tiên xử lý:** Sắp xếp các cụm trùng theo `severity (P0 → P1 → P2)` và số lượng biến thể bị trùng giảm dần.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Trùng Lặp SKU & Barcode (Markdown)
- **Tổng số sản phẩm / variants đã quét:** `312` SP / `1.084` variants
- **Phát hiện:** `4` cụm trùng SKU **P0** (đang cùng bán) | `6` cụm trùng **P1** (có SP ẩn) | `3` cụm trùng Barcode | `15` variants thiếu SKU

| Mức độ | Mã chuẩn hóa | Kiểu trùng | Các Variant bị ảnh hưởng (`product_id / variant_id`) | Trạng thái | Hành động đề xuất |
| --- | --- | --- | --- | --- | --- |
| `P0` | `POLO-TRG-M` | Normalized SKU (`"POLO-TRG-M"` vs `"polo-trg-m "`) | `105001122/111001` (349k) & `105009988/119901` (249k) | Cả 2 đang bán | Gộp SP Sale vào khuyến mãi thay vì nhân bản SP, hoặc đổi SKU bản `119901` |
| `P1` | `8938501100012` | Barcode trùng | `105001122/111001` & `105009988/119901` | Cả 2 đang bán | Xóa/đổi barcode bản phụ để tránh quét nhầm tại POS |

### JSON Output Schema
```json
{
  "skill": "catalog-duplicate-sku-barcode",
  "scanned_variants": 1084,
  "partial_sample": false,
  "summary": { "duplicate_sku_groups": 10, "p0_active_sku_groups": 4, "duplicate_barcode_groups": 3, "empty_sku_variants": 15 },
  "duplicate_skus": [
    {
      "severity": "P0",
      "normalized_sku": "POLO-TRG-M",
      "variants": [
        { "product_id": 105001122, "variant_id": 111001, "raw_sku": "POLO-TRG-M", "published": true, "price": 349000 },
        { "product_id": 105009988, "variant_id": 119901, "raw_sku": "polo-trg-m ", "published": true, "price": 249000 }
      ]
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ Read-Only (`L1`):** Tuyệt đối không tự ý sửa đổi SKU hay Barcode trên Haravan vì SKU là khóa ngoại (foreign key) liên kết trực tiếp với Shopee/Lazada/TikTok/MISA.
- **Lưu ý vận hành trước khi sửa:** Nhắc người dùng kiểm tra tab "Liên kết sản phẩm" trên Haravan Omnichannel trước khi đổi mã của bất kỳ variant nào trong danh sách `P0`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu scope `com.read_products` | Cấp quyền đọc sản phẩm. |
| `429 Too Many Requests` | Quét > 100 trang sản phẩm liên tục | Dùng `fields=id,title,published_at,variants` để giảm payload 80% và chạy `2.5 req/s`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Nhân bản sản phẩm (Duplicate Product) để chạy Flash Sale:** Rất nhiều shop VN hay bấm "Nhân bản sản phẩm" trên Haravan Admin để tạo bản giảm giá riêng mà quên sửa SKU → sinh ra hàng loạt cặp trùng P0.
2. **Sản phẩm Combo/Bộ sản phẩm có chung SKU với sản phẩm lẻ:** Cần phân biệt bằng `product_type`/`title` (chứa chữ "Combo", "Set") để đề xuất đặt tiền tố `CB-` cho mã combo.
3. **Barcode chứa số `0` ở đầu bị mất khi từng nhập qua Excel:** Ví dụ `"0893..."` thành `"893..."` hoặc dạng khoa học `"8.9385E+12"` → cần gắn cờ `MALFORMED_BARCODE` để sửa lại.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-bulk-import-proposal`, `inventory-stocktake-cycle-count`.
- **Chạy tiếp theo:** `inventory-multi-location-audit` (kiểm tra lệch tồn kho do trùng SKU gây ra), `catalog-data-completeness-audit`.
