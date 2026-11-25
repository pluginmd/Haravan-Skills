---
name: catalog-data-completeness-audit
description: "Chấm điểm độ hoàn thiện dữ liệu sản phẩm (tiêu đề, mô tả HTML, ảnh, SKU, barcode, giá so sánh, trọng lượng, tags, vendor)."
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
    - "GET https://apis.haravan.com/com/products/count.json"
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
# Catalog Data Completeness Audit — Chấm Điểm Độ Hoàn Thiện Dữ Liệu Sản Phẩm (100đ)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` quét toàn bộ danh mục sản phẩm trên Haravan (`/com/products.json`) và chấm điểm độ hoàn thiện dữ liệu trên thang **100 điểm** cho từng sản phẩm lẫn toàn bộ catalog. Tại Việt Nam, dữ liệu catalog thiếu hụt (thiếu SKU/Barcode, thiếu trọng lượng `grams`, thiếu ảnh, mô tả ngắn dưới 50 ký tự, thiếu `vendor`/`product_type`) gây ra 3 hậu quả trực tiếp: (1) Đồng bộ sang Shopee/TikTok Shop/Google Merchant Center bị từ chối duyệt, (2) Phí ship tự động GHN/GHTK tính sai do trọng lượng = 0g, và (3) Tỷ lệ chuyển đổi trang sản phẩm thấp.

- **Khi nào sử dụng:** Định kỳ hàng tháng, trước khi đẩy feed lên Google Shopping / Facebook Catalog / sàn TMĐT, hoặc ngay sau khi bàn giao kho dữ liệu từ team nhập liệu.
- **Khi nào KHÔNG sử dụng:** Khi chỉ cần kiểm tra trùng lặp SKU (dùng `catalog-duplicate-sku-barcode`) hoặc cần sửa dữ liệu trực tiếp (chuyển sang skill L2 tương ứng).
- **Definition of Done (DoD):**
  1. Lấy tổng số sản phẩm qua `GET /com/products/count.json` và tải danh sách (tối đa `max_records=5000`).
  2. Chấm điểm từng sản phẩm theo bộ trọng số 100 điểm chuẩn hóa (8 tiêu chí rõ ràng) và phân nhóm `A (>=85) / B (70-84) / C (50-69) / D (<50)`.
  3. Xuất bảng tổng hợp lỗi phổ biến nhất toàn shop + danh sách Top 20 sản phẩm điểm thấp nhất cần ưu tiên khắc phục.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Tổng số sản phẩm | `com.read_products` | `GET https://apis.haravan.com/com/products/count.json` |
| Chi tiết sản phẩm, biến thể & ảnh | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&page=1` |

**Chạy trực tiếp qua CLI của repo (`scripts/hrv_ops.py`):**
```bash
python3 scripts/hrv_ops.py catalog-audit
# Chạy offline với dữ liệu mẫu Việt Nam:
python3 scripts/hrv_ops.py --demo catalog-audit
```

**Sample Response (`GET https://apis.haravan.com/com/products.json?limit=1`):**
```json
{
  "products": [
    {
      "id": 1051120045,
      "title": "Áo Khoác Dù 2 Lớp Chống Nước",
      "body_html": "<p>Áo khoác dù 2 lớp...</p>",
      "vendor": "Saigon Streetwear",
      "product_type": "Áo khoác",
      "tags": "ao-khoac, chong-nuoc",
      "published_at": "2026-10-01T02:00:00Z",
      "images": [{ "id": 201, "src": "https://product.hstatic.net/..." }],
      "variants": [
        { "id": 112001, "sku": "AKD-DEN-L", "barcode": "8938501234991", "price": 549000.0, "compare_at_price": 650000.0, "grams": 450 }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `published_status` | enum (`published`, `unpublished`, `any`) | Không | `published` | Mặc định tập trung chấm điểm sản phẩm đang bán. |
| `min_description_chars` | integer | Không | `120` | Độ dài tối thiểu (sau khi bỏ thẻ HTML) để đạt điểm mô tả. |
| `min_images_count` | integer | Không | `3` | Số ảnh tối thiểu để đạt điểm tối đa phần hình ảnh. |
| `require_barcode` | boolean | Không | `false` | Bật `true` nếu cửa hàng dùng máy quét mã vạch POS / Google Shopping (GTIN). |
| `max_records` | integer | Không | `5000` | Giới hạn quét tối đa; bật `partial_sample: true` nếu vượt. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức chấm điểm Độ hoàn thiện Sản phẩm (Thang 100 điểm)
Mỗi sản phẩm `p` được tính tổng điểm `Score(p) = sum(8 tiêu chí)`:
1. **Tiêu đề chuẩn (`10đ`):** `10 <= len(title) <= 120`, không viết HOA toàn bộ (`ALL CAPS`) và không chứa ký tự nháp (`test`, `copy`).
2. **Mô tả sản phẩm (`15đ`):** `len(strip_html(body_html)) >= min_description_chars` (+15đ); nếu `30..119` ký tự (+7đ); `< 30` (+0đ).
3. **Hình ảnh (`20đ`):** `len(images) >= min_images_count` (+20đ); có `1..2` ảnh (+10đ); `0` ảnh (+0đ — gắn cờ **CRITICAL**).
4. **SKU đầy đủ (`15đ`):** `100%` variants có `sku` không rỗng (+15đ); tỷ lệ thiếu → tính tỷ lệ thuận `round(15 * valid_sku_ratio)`.
5. **Giá & Giá so sánh hợp lệ (`15đ`):** `100%` variants có `price > 0` và (`compare_at_price == 0` hoặc `compare_at_price > price`) (+15đ).
6. **Trọng lượng vận chuyển (`10đ`):** `100%` variants có `grams > 0` (với hàng vật lý `requires_shipping: true`) (+10đ).
7. **Phân loại `product_type` & `vendor` (`10đ`):** Có `product_type` (+5đ) và có `vendor` (+5đ).
8. **Tags & Barcode (`5đ`):** Có ít nhất 1 tag (+3đ) và có barcode hợp lệ (+2đ; nếu `require_barcode: true`, barcode là tiêu chí cảnh báo riêng).

**Điểm toàn cửa hàng:** `Catalog_Score = average(Score(p) for p in products)`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Chất lượng Dữ liệu Catalog — Điểm trung bình: 74.6 / 100 (Hạng B)
- **Phạm vi quét:** `240 / 240` sản phẩm đang hiển thị (`712` variants)
- **Phân bố điểm:** Hạng A (`>=85`): `92` SP | Hạng B (`70-84`): `88` SP | Hạng C (`50-69`): `44` SP | Hạng D (`<50`): `16` SP

| Hạng mục thiếu hụt | Số SP/Variant ảnh hưởng | Tỷ lệ | Tác động vận hành | Skill xử lý |
| --- | --- | --- | --- | --- |
| Thiếu trọng lượng (`grams = 0`) | 68 variants | 9.5% | Sai cước vận chuyển GHN/GHTK | Cập nhật trọng lượng theo nhóm |
| Thiếu mô tả (< 120 ký tự) | 41 SP | 17.1% | Kém SEO & tỷ lệ chuyển đổi | Bổ sung nội dung mô tả |
| `compare_at_price <= price` | 19 variants | 2.7% | Hiển thị giảm giá sai/lỗi UI | `pricing-compare-at-cleanup` |
| Thiếu ảnh sản phẩm (`0 ảnh`) | 4 SP | 1.7% | Mất uy tín & rớt feed Ads | `catalog-image-alt-audit` |
| Thiếu SKU | 12 variants | 1.7% | Không đồng bộ được POS/Sàn | Bổ sung SKU chuẩn |

### JSON Output Schema
```json
{
  "skill": "catalog-data-completeness-audit",
  "scanned_products": 240,
  "scanned_variants": 712,
  "partial_sample": false,
  "average_score": 74.6,
  "grade_distribution": { "A": 92, "B": 88, "C": 44, "D": 16 },
  "top_defects": { "zero_grams_variants": 68, "short_description_products": 41, "invalid_compare_at_variants": 19, "missing_image_products": 4, "missing_sku_variants": 12 },
  "lowest_scoring_products": [{ "product_id": 1051120999, "title": "Phụ kiện test", "score": 25, "missing": ["images", "body_html", "sku", "grams"] }]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ gọi `GET`, không sửa sản phẩm.
- **Partial Sample:** Nếu `products/count > 5000`, báo rõ `partial_sample: true` và khuyến nghị lọc theo `collection_id` hoặc `product_type` để audit từng ngành hàng.
- **PII:** Không chứa PII (`pii_level: none`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu scope `com.read_products` | Yêu cầu bổ sung quyền đọc sản phẩm. |
| `429 Too Many Requests` | Catalog lớn > 2.000 SP quét nhanh | Dùng `HaravanClient(req_per_sec=2.0)` và chỉ chọn trường cần thiết bằng `fields=`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Mô tả sản phẩm chỉ chứa thẻ `<img>` (ảnh chụp bảng size/poster) mà không có chữ:** `strip_html(body_html)` trả về rỗng nhưng thực tế trang vẫn có thông tin bằng ảnh. Cần đếm thêm số thẻ `<img>` trong `body_html` và gắn nhãn `image_only_description` (cảnh báo SEO nhưng không trừ trắng điểm trải nghiệm).
2. **Sản phẩm quà tặng 0đ (`price == 0`) dùng cho khuyến mãi mua kèm:** Rất phổ biến trên Haravan; nếu `tags` chứa `gift`/`qua-tang` hoặc `product_type == "Quà tặng"`, không trừ điểm ở tiêu chí giá `price > 0`.
3. **Biến thể mặc định `"Default Title"`:** Với sản phẩm đơn (không có size/màu), Haravan tự tạo 1 variant tên `"Default Title"`; vẫn phải kiểm tra SKU và `grams` trên variant duy nhất này.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `store-health-check`.
- **Chạy tiếp theo:** `catalog-duplicate-sku-barcode`, `catalog-image-alt-audit`, `pricing-compare-at-cleanup`, `catalog-collection-reorg-proposal`.
