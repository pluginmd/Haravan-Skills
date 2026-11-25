---
name: seo-metadata-serp-audit
description: "Kiểm toán tiêu đề SEO, meta description, cấu trúc URL handle, trang nội dung (/web/pages.json) và dữ liệu có cấu trúc Product JSON-LD trên Haraweb."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 80-theme-seo-cro
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: web
  scopes:
    - com.read_products
    - com.read_contents
  endpoints:
    - "GET https://apis.haravan.com/com/products.json"
    - "GET https://apis.haravan.com/web/pages.json"
    - "GET https://apis.haravan.com/web/blogs.json"
    - "GET https://apis.haravan.com/web/redirects.json"
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

# Haravan Technical SEO & Metadata SERP Audit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Kiểm toán toàn diện sức khỏe Technical SEO và khả năng hiển thị SERP (Search Engine Results Page) cho storefront Haraweb — bao gồm sản phẩm (`/com/products.json`), trang tĩnh (`/web/pages.json`), chuyên mục blog (`/web/blogs.json`) và bảng chuyển hướng 301 (`/web/redirects.json`).
- **Ngữ cảnh Haravan:** Các cửa hàng Haravan thường mất hàng chục phần trăm Organic CTR do 5 lỗi phổ biến: (1) Trùng `title` giữa các sản phẩm gần giống nhau (gây keyword cannibalization), (2) `handle` URL có ký tự thừa/số đuôi `-1`, `-copy` do nhân bản sản phẩm, (3) Mô tả sản phẩm quá mỏng (< 100 từ) hoặc toàn ảnh không có chữ, (4) Chuỗi redirect vòng lặp/dài tầng tại `/web/redirects.json`, và (5) Thiếu hoặc sai dữ liệu có cấu trúc `Product` / `BreadcrumbList` JSON-LD khiến Google không hiển thị giá (VND) và trạng thái `InStock` trên kết quả tìm kiếm.
- **Definition of Done (DoD):**
  1. Quét đầy đủ sản phẩm (≤ `max_products`), trang tĩnh, blog và bảng redirects qua Web & Commerce API.
  2. Tính điểm Technical SEO Score (0–100) và phân loại lỗi `P0`/`P1`/`P2`.
  3. Đề xuất bộ Title (≤ 60 ký tự) & Meta Description (130–155 ký tự) chuẩn tiếng Việt tự nhiên cho Top 20 trang/sản phẩm ưu tiên cao nhất.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `web` & `com` (`https://apis.haravan.com/web`, `/com`) |
| **Scopes tối thiểu** | `com.read_products`, `com.read_contents` |
| **Endpoints** | `GET /com/products.json`, `GET /web/pages.json`, `GET /web/blogs.json`, `GET /web/redirects.json` |

**Ví dụ gọi qua `scripts/hrv_client.py` (kết hợp kiểm tra redirect qua `hrv_ops.py`):**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
products = client.paginate("com", "/products.json", "products", params={"published_status": "published"}, limit=50, max_pages=10)
pages = client.paginate("web", "/pages.json", "pages", limit=50, max_pages=5)
blogs = client.request("GET", "web", "/blogs.json").get("blogs", [])
redirects = client.paginate("web", "/redirects.json", "redirects", limit=50, max_pages=10)
```

**Ví dụ JSON Response thực tế từ `GET /web/pages.json?limit=1` và `/web/redirects.json?limit=1`:**
```json
{
  "pages": [
    { "id": 10004512, "title": "Chính sách đổi trả", "handle": "chinh-sach-doi-tra", "body_html": "<p>Đổi trả trong 7 ngày.</p>" }
  ],
  "redirects": [
    { "id": 50219, "path": "/products/ao-cu", "target": "/products/ao-moi" }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `max_products` | `integer` | Không | `500` | Phạm vi `1..1000` (khớp `max_records: 1000`). |
| `title_max_chars` | `integer` | Không | `60` | Ngưỡng độ dài tối đa của SEO Title hiển thị đẹp trên Google desktop/mobile. |
| `min_word_count` | `integer` | Không | `100` | Ngưỡng số từ tối thiểu trong `body_html` để không bị gắn cờ Thin Content. |
| `check_redirects` | `boolean` | Không | `true` | Kiểm tra chuỗi redirect dây chuyền (`A -> B -> C`) hoặc tự trỏ chính mình (`A -> A`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Kiểm toán Sản phẩm & Trang tĩnh (`products`, `pages`):**
   - **Trùng lặp Title (`P0: DUPLICATE_TITLE`):** Chuẩn hóa lowercase/trim `title`; mọi nhóm có `count >= 2` đều bị đánh dấu gây cạnh tranh từ khóa nội bộ.
   - **URL Handle bẩn (`P1: DIRTY_HANDLE`):** Phát hiện `handle` kết thúc bằng `-copy`, `-1`, `-2` hoặc dài > `75` ký tự hoặc chứa ký tự mã hóa URL lỗi.
   - **Title quá dài hoặc quá ngắn (`P1: TITLE_LENGTH`):** `len(title) > title_max_chars` (bị Google cắt `...`) hoặc `len(title) < 20`.
   - **Thin Content (`P1: THIN_CONTENT`):** Lọc bỏ thẻ HTML trong `body_html`, đếm số từ tiếng Việt; đánh dấu nếu `< min_word_count` (đặc biệt trên trang sản phẩm chủ lực và trang chính sách).
   - **Thiếu Alt ảnh (`P2: MISSING_IMAGE_ALT`):** Kiểm tra `images[].alt` hoặc thẻ `<img>` trong `body_html` bị rỗng.
2. **Kiểm toán Redirects (`/web/redirects.json`):**
   - Phát hiện **Redirect Loop** (`path == target` hoặc `A -> B -> A` — lỗi `P0`).
   - Phát hiện **Redirect Chain** (`A -> B` và `B -> C` — lỗi `P1`, gây lãng phí crawl budget).
3. **Checklist Schema Product JSON-LD (cho Theme Haraweb):**
   - Xác minh khuyến nghị cấu trúc `@type: "Product"` phải có đủ: `name`, `image`, `sku`, `offers.price`, `offers.priceCurrency: "VND"`, `offers.availability` (`InStock`/`OutOfStock`), `brand`.
4. **Tính Technical SEO Score (0–100):**
   $$\text{SEO Score} = 100 - \min\left(100,\; \frac{6 \cdot N_{P0} + 2 \cdot N_{P1} + 0.5 \cdot N_{P2}}{N_{\text{pages}} + N_{\text{products}}} \times 100\right)$$

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Kiểm toán Technical SEO & SERP Haraweb
- **Phạm vi quét:** 350 sản phẩm | 12 trang tĩnh | 3 chuyên mục blog | 48 redirects
- **Technical SEO Score:** `71.4 / 100` | **Lỗi P0:** 5 | **Lỗi P1:** 68 | **Lỗi P2:** 112

| Mức độ | Mã lỗi | Số lượng | Ví dụ URL / ID | Khuyến nghị khắc phục |
| --- | --- | ---: | --- | --- |
| P0 | `DUPLICATE_TITLE` | 4 | `/products/ao-thun-nam-1`, `/products/ao-thun-nam-2` | Gộp biến thể hoặc viết lại Title phân biệt chất liệu/form |
| P0 | `REDIRECT_LOOP` | 1 | `/collections/sale` → `/collections/sale` | Xóa ngay redirect vòng lặp trên `/web/redirects.json` |
| P1 | `DIRTY_HANDLE` | 19 | `/products/quan-jean-nam-copy` | Đổi handle sạch + **bắt buộc tạo 301 Redirect từ URL cũ** |
| P1 | `THIN_CONTENT` | 49 | `/products/giay-the-thao-x` (38 từ) | Bổ sung bảng size, chất liệu, hướng dẫn bảo quản ≥ 150 từ |
```

```json
{
  "skill": "seo-metadata-serp-audit",
  "summary": { "products_scanned": 350, "pages_scanned": 12, "redirects_scanned": 48, "seo_score": 71.4, "p0_count": 5, "p1_count": 68 },
  "serp_rewrite_proposals": [
    { "resource_type": "product", "id": 1054218901, "current_title": "Áo Polo Nam Cotton Pique Cao Cấp Chính Hãng Siêu Thoáng Mát 2026", "suggested_title": "Áo Polo Nam Cotton Pique Form Slim | LocalBrandVN", "suggested_meta_desc": "Áo Polo nam vải cotton Pique thoáng mát, giữ form sau nhiều lần giặt. Đủ size M-XXL, kiểm hàng trước khi thanh toán, đổi trả 7 ngày." }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ gọi `GET`. **Tuyệt đối không tự ý chỉnh sửa `robots.txt.liquid` trên Live Theme** (rủi ro `Disallow: /` làm mất toàn bộ index Google trong 24–48h).
- **Quy tắc đổi URL Handle:** Mỗi khi báo cáo đề xuất sửa `handle` của một sản phẩm/trang đã tồn tại, bắt buộc ghi kèm cảnh báo tạo **301 Redirect** qua `/web/redirects.json` trước hoặc ngay khi đổi handle.
- **Rollback:** Không cần vì là skill đọc (`rollback.supported: false`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng audit, thông báo làm mới `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_products` hoặc `com.read_contents` | Chạy phần có quyền hoặc dừng và liệt kê rõ scope cần cấp. |
| `404 Not Found` | Gọi `/com/pages.json` thay vì `/web/pages.json` | Đảm bảo `pages`, `blogs`, `redirects` đi qua surface `web`. |
| `422 Unprocessable` | Tham số `limit > 250` | Luôn kẹp `limit <= 250` trong `client.paginate()`. |
| `429 Too Many Requests` | Quét 4 endpoint liên tiếp vượt 4 req/s | Dùng `HaravanClient` (leaky bucket 2.5 req/s + exponential backoff). |

- **Edge Case 1 — Sản phẩm hết hàng theo mùa (Seasonal OOS):** Không đề xuất xóa sản phẩm hết hàng tạm thời có backlink tốt; thay vào đó đề xuất giữ nguyên URL và hiển thị sản phẩm tương tự để bảo toàn sức mạnh SEO.
- **Edge Case 2 — Mô tả sản phẩm chỉ chứa ảnh thiết kế dài (Infographic):** Phổ biến ở các shop thời trang/mỹ phẩm VN. Thuật toán đếm từ sẽ báo `THIN_CONTENT` (0 từ) — Agent cần gợi ý bổ sung ít nhất 150–200 từ text mô tả + thẻ `alt` cho ảnh để Googlebot đọc được.
- **Edge Case 3 — Redirect từ đường dẫn có dấu tiếng Việt hoặc query string:** `/web/redirects.json` của Haravan so khớp theo path chuẩn hóa; cần kiểm tra URL encode để tránh tạo trùng redirect.

## 8. Liên kết Workflow & Skill kế tiếp

- **Tối ưu bài viết Blog để kéo traffic về sản phẩm:** Chuyển sang `seo-blog-content-optimizer` (L2).
- **Kiểm toán tốc độ và mã Liquid render Schema JSON-LD:** Chạy tiếp `theme-liquid-code-review` (L1).
- **Kiểm tra nhanh lỗi Redirect bằng CLI:** Chạy `python3 scripts/hrv_ops.py redirect-audit`.
