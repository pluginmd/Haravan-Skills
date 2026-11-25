---
name: catalog-image-alt-audit
description: "Kiểm tra ảnh sản phẩm bị thiếu, ảnh thiếu thuộc tính alt text SEO và đề xuất bộ alt text chuẩn tiếng Việt."
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
    - "GET https://apis.haravan.com/com/products/{product_id}/images.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 1000
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
# Catalog Image & Alt Text Audit — Kiểm Toán Ảnh Sản Phẩm & Chuẩn Hóa Alt SEO Tiếng Việt

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` kiểm toán hệ thống hình ảnh sản phẩm trên Haravan (`/com/products.json` và `/com/products/{product_id}/images.json`) để phát hiện sản phẩm thiếu ảnh, sản phẩm chỉ có 1 ảnh đơn điệu, ảnh thiếu thuộc tính `alt` (hoặc `alt` rỗng / lặp tên file vô nghĩa như `IMG_4821.jpg`, `z512345.jpg`), và tạo sẵn bộ đề xuất `alt` chuẩn SEO tiếng Việt tự nhiên. Tại Việt Nam, ảnh sản phẩm có `alt` tốt giúp tăng traffic tự nhiên từ Google Images (rất quan trọng với ngành Thời trang, Nội thất, Mỹ phẩm, Gia dụng) và cải thiện điểm Accessibility.

- **Khi nào sử dụng:** Trước khi chạy chiến dịch SEO ngành hàng, sau khi upload bộ sưu tập sản phẩm mới, hoặc khi audit SEO tổng thể cho cửa hàng.
- **Khi nào KHÔNG sử dụng:** Khi muốn tự động ghi đè `alt` lên hàng trăm ảnh ngay lập tức (skill này là `L1 / read`, xuất bảng đề xuất; muốn ghi hàng loạt cần duyệt proposal `PUT /com/products/{id}/images/{image_id}.json`).
- **Definition of Done (DoD):**
  1. Quét danh mục sản phẩm (tối đa `max_records=1000`) và thống kê đầy đủ: số SP `0 ảnh`, số SP `< 3 ảnh`, tổng số ảnh, tỷ lệ ảnh thiếu hoặc kém chất lượng `alt`.
  2. Tự động sinh chuỗi `alt` tiếng Việt gợi ý (dưới 125 ký tự, không nhồi nhét từ khóa) cho từng ảnh thiếu `alt` dựa trên `title`, `vendor`, `product_type`, và vị trí ảnh (`position`).
  3. Xuất báo cáo Markdown kèm bảng gợi ý `image_id → proposed_alt` sẵn sàng duyệt.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Danh sách sản phẩm kèm mảng `images` | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,vendor,product_type,images,variants` |
| Chi tiết ảnh của 1 sản phẩm cụ thể | `com.read_products` | `GET https://apis.haravan.com/com/products/{product_id}/images.json` |

**Gọi tối ưu (tránh N+1 API calls) bằng `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True)
# Endpoint /products.json đã trả sẵn mảng images[], chỉ gọi /{product_id}/images.json khi cần kiểm tra sâu 1 SP
products = c.paginate("com", "/products.json", key="products", params={"limit": 50, "fields": "id,title,vendor,product_type,images"}, max_records=1000)
```

**Sample Response (`GET /com/products/1051120045/images.json`):**
```json
{
  "images": [
    { "id": 300112201, "product_id": 1051120045, "position": 1, "src": "https://product.hstatic.net/200000123456/product/img_4821_master.jpg", "alt": null, "variant_ids": [112001] },
    { "id": 300112202, "product_id": 1051120045, "position": 2, "src": "https://product.hstatic.net/200000123456/product/z512345_master.jpg", "alt": "IMG_4822.jpg", "variant_ids": [] }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `max_alt_length` | integer | Không | `125` | Độ dài tối đa chuẩn SEO & Screen Reader cho thuộc tính `alt`. |
| `min_images_per_product` | integer | Không | `3` | Ngưỡng cảnh báo sản phẩm ít ảnh. |
| `brand_suffix` | string | Không | `""` (lấy từ `vendor`) | Tên thương hiệu nối cuối `alt` nếu còn đủ độ dài. |
| `max_records` | integer | Không | `1000` | Số sản phẩm tối đa quét trong 1 lần. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Phân loại Chất lượng `alt` (4 mức)
1. **`MISSING_ALT` (Nghiêm trọng):** `alt` là `null` hoặc chuỗi rỗng `""` sau khi `strip()`.
2. **`JUNK_ALT` (Cần thay thế):** `alt` khớp regex tên file thô (`^(IMG_|DSC_|z\d+|Screenshot|image|hinh).*|\.(jpg|jpeg|png|webp)$`), hoặc độ dài `< 8` ký tự, hoặc lặp y hệt nhau trên tất cả ảnh của cùng 1 sản phẩm.
3. **`TOO_LONG_ALT` (Cảnh báo):** `len(alt) > 125` ký tự (nguy cơ spam từ khóa Google).
4. **`GOOD_ALT` (Đạt):** `8 <= len(alt) <= 125`, mô tả rõ ràng, không trùng tên file.

### Quy tắc sinh `alt` tiếng Việt tự nhiên (không nhồi từ khóa)
- Ảnh vị trí `position == 1` (ảnh đại diện): `f"{title} - {vendor}"` (nếu có tên màu/biến thể gắn `variant_ids` thì ưu tiên ghép tên màu: `f"{title} màu {color_option} - {vendor}"`).
- Ảnh vị trí `position >= 2`: `f"{title} - góc chi tiết {position} ({vendor})"` hoặc ghép theo biến thể gắn với ảnh đó; cắt gọn thông minh theo ranh giới từ để `<= 125` ký tự.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Kiểm toán Ảnh & Alt Text SEO (Markdown)
- **Phạm vi quét:** `185` sản phẩm | **Tổng số ảnh:** `742` ảnh
- **Tình trạng:** `3` SP thiếu ảnh hoàn toàn (`0 ảnh`) | `28` SP ít ảnh (`< 3`) | `412` ảnh thiếu `alt` (`55.5%`) | `64` ảnh dùng `alt` tên file rác (`8.6%`)

| Product ID | Image ID | Vị trí | `alt` hiện tại | `alt` đề xuất (SEO tiếng Việt) | Phân loại |
| --- | --- | --- | --- | --- | --- |
| `1051120045` | `300112201` | 1 | `(trống)` | `Áo Khoác Dù 2 Lớp Chống Nước - Saigon Streetwear` | `MISSING_ALT` |
| `1051120045` | `300112202` | 2 | `IMG_4822.jpg` | `Áo Khoác Dù 2 Lớp Chống Nước - ảnh chi tiết 2` | `JUNK_ALT` |

### JSON Output Schema
```json
{
  "skill": "catalog-image-alt-audit",
  "scanned_products": 185,
  "total_images": 742,
  "summary": { "zero_image_products": 3, "low_image_products": 28, "missing_alt": 412, "junk_alt": 64, "too_long_alt": 5, "good_alt": 261 },
  "alt_coverage_pct": 35.2,
  "proposals_sample": [
    { "product_id": 1051120045, "image_id": 300112201, "current_alt": null, "proposed_alt": "Áo Khoác Dù 2 Lớp Chống Nước - Saigon Streetwear", "issue": "MISSING_ALT" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ Read-Only (`L1`):** Chỉ đọc và đề xuất bảng `proposed_alt`, không tự gọi `PUT /com/products/{id}/images/{image_id}.json`.
- **Tránh N+1 API Calls:** Luôn đọc mảng `images` trực tiếp từ `GET /com/products.json` thay vì gọi 1.000 lần `GET /com/products/{id}/images.json` (gây cạn leaky bucket).
- **Cảnh báo Partial Sample:** Nếu cửa hàng có `> 1000` sản phẩm, báo rõ `partial_sample: true` và khuyến nghị chạy theo từng `collection_id` hoặc `product_type`.
- **Bảo vệ tương thích Theme:** Mọi đề xuất ghi đè `alt` sau này phải giữ nguyên các tag kỹ thuật màu sắc của theme (xem mục Edge Cases) và lưu bản `.backup.json` trước khi gọi `PUT`.
- **PII:** Không chứa thông tin cá nhân (`pii_level: none`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu `com.read_products` | Yêu cầu cấp quyền đọc sản phẩm. |
| `429 Too Many Requests` | Gọi riêng lẻ từng `/images.json` cho nhiều sản phẩm | Chuyển sang lấy gộp qua `/products.json?fields=id,title,vendor,images`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Haravan tự dùng `alt` làm khóa lọc ảnh theo màu sắc trên một số Theme VN:** Nhiều theme Haravan (F1Gen, EGANY, Haravan default) dùng quy ước `alt` chứa chuỗi như `color_den` hoặc `mau-trang` để đổi gallery ảnh khi khách chọn màu. **Cảnh báo bắt buộc:** Nếu phát hiện `alt` hiện tại khớp pattern `color_|mau_|#` hoặc chứa tên màu kỹ thuật, **KHÔNG đề xuất ghi đè** để tránh làm hỏng chức năng đổi ảnh theo màu trên storefront!
2. **Ảnh trong `body_html` (mô tả bài viết) cũng thiếu `alt`:** Endpoint `images.json` chỉ chứa ảnh gallery sản phẩm; cần ghi chú nếu `body_html` có nhiều `<img src="...">` thiếu `alt=""`.
3. **Tên file ảnh tải từ Zalo (`z5123456789_...jpg`):** Cực kỳ phổ biến ở shop VN; regex `^z\d{10,}` giúp bắt chính xác loại `alt` rác này.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-data-completeness-audit`.
- **Chạy tiếp theo:** `seo-technical-audit` (kiểm toán toàn diện SEO on-page & schema sản phẩm).
