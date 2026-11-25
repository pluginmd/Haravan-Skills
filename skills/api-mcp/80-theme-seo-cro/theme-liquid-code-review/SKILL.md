---
name: theme-liquid-code-review
description: "Kiểm toán mã nguồn Haravan Liquid (layout, templates, snippets, assets) phát hiện vòng lặp N+1, ảnh chưa lazy-load, script chặn render và lỗi cú pháp."
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
    - web.read_themes
  endpoints:
    - "GET https://apis.haravan.com/web/themes.json"
    - "GET https://apis.haravan.com/web/themes/{theme_id}/assets.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
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

# Haravan Liquid Theme Code & Standards Review

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Kiểm toán chuyên sâu mã nguồn giao diện Haravan Liquid (`layout/`, `templates/`, `snippets/`, `assets/`) nhằm phát hiện các nút thắt hiệu năng (vòng lặp N+1, ảnh gốc không resize, thiếu `loading="lazy"`, JS/CSS chặn render trong `<head>`) và các lỗi bảo mật/SEO (nhúng `http://`, thiếu `page_title`/`canonical_url`, lỗi cú pháp Liquid chưa đóng thẻ).
- **Ngữ cảnh Haravan:** Haraweb biên dịch Liquid phía máy chủ (server-side) trước khi trả HTML. Khi theme chứa vòng lặp lồng nhau quét qua toàn bộ `collections['all'].products` bên trong trang danh mục hoặc trang sản phẩm, TTFB (Time to First Byte) có thể vọt lên > 2.5 giây. Skill này hỗ trợ cả chế độ đọc qua Web API (`/web/themes/{id}/assets.json`) lẫn review trực tiếp thư mục đã tải về bằng `@haravan/cli` (`haravan pull`).
- **Definition of Done (DoD):**
  1. Xác định rõ `theme_id` mục tiêu (phân biệt `role: "main"` Live Theme vs `role: "unpublished"` Staging Theme).
  2. Quét các tệp trọng yếu (`layout/theme.liquid`, `templates/index.liquid`, `templates/collection.liquid`, `templates/product.liquid`, `snippets/*.liquid`).
  3. Xuất báo cáo Code Review phân mức `P0`/`P1`/`P2` kèm chính xác tên file, dòng lỗi và đoạn code **Before / After** sẵn sàng áp dụng lên Staging Theme.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `web` (`https://apis.haravan.com/web`) hoặc local `@haravan/cli` |
| **Scopes tối thiểu** | `web.read_themes` |
| **Endpoints** | `GET /web/themes.json`, `GET /web/themes/{theme_id}/assets.json` |

**Ví dụ gọi qua `scripts/hrv_client.py` và kéo mã nguồn bằng `@haravan/cli`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
themes = client.request("GET", "web", "/themes.json").get("themes", [])
theme_id = next(t["id"] for t in themes if t.get("role") == "main")
assets = client.request("GET", "web", f"/themes/{theme_id}/assets.json").get("assets", [])
# Đọc nội dung 1 file cụ thể:
theme_liquid = client.request(
    "GET", "web", f"/themes/{theme_id}/assets.json",
    params={"asset[key]": "layout/theme.liquid"}
)
```
```bash
# Kéo theme về máy để review offline toàn diện (an toàn, chỉ đọc):
npx @haravan/cli pull --theme-id <STAGING_THEME_ID> --dir ./theme-staging
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `theme_id` | `integer` | Không | `main` theme | ID theme cần kiểm toán (bỏ trống sẽ tự tìm theme `role: "main"` để đọc). |
| `local_theme_dir` | `string` | Không | `null` | Đường dẫn thư mục theme đã kéo bằng `@haravan/cli` (nếu truyền sẽ đọc trực tiếp, tiết kiệm API call). |
| `focus_areas` | `array[string]` | Không | `["performance", "seo", "security"]` | Các nhóm quy tắc cần rà soát. |
| `max_files` | `integer` | Không | `100` | Số lượng file `.liquid`/`.js`/`.css` tối đa đọc qua API (`<= 500`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Checklist phát hiện Anti-Pattern Liquid (kèm ví dụ Before / After):**
   - **P0 — Vòng lặp N+1 lồng nhau trên `collections` / `products`:** Quét lồng 2–3 vòng `{% for %}` không có `limit:` làm tăng thời gian render TTFB.
     ```liquid
     <!-- BEFORE (P0: Quét toàn bộ sản phẩm bên trong mỗi thẻ sản phẩm -> O(N*M)) -->
     {% for p in collection.products %}
       {% for all_p in collections['all'].products %}
         {% if all_p.vendor == p.vendor %}...{% endif %}
       {% endfor %}
     {% endfor %}

     <!-- AFTER (Giới hạn tập duyệt hoặc gán biến ngoài vòng lặp) -->
     {% assign featured = collections['noi-bat'].products %}
     {% for p in collection.products limit: 24 %}
       {% render 'product-card', product: p %}
     {% endfor %}
     ```
   - **P1 — Ảnh gốc chưa resize & thiếu `loading="lazy"` (LCP vs Below-the-fold):**
     ```liquid
     <!-- BEFORE (Tải ảnh gốc 3MB + thiếu width/height gây CLS + thiếu lazy-load) -->
     <img src="{{ product.featured_image.src }}" alt="{{ product.title }}">

     <!-- AFTER (Dùng filter img_url: 'grande'/'medium' + kích thước tường minh + lazy) -->
     <img src="{{ product.featured_image.src | img_url: 'grande' }}"
          alt="{{ product.title | escape }}"
          width="600" height="600" loading="lazy" decoding="async">
     ```
     *Lưu ý:* Ảnh Hero/Banner đầu trang (LCP) **KHÔNG** dùng `loading="lazy"` mà dùng `fetchpriority="high"`.
   - **P1 — Render-Blocking `<script>` trong `<head>` của `layout/theme.liquid`:** Thẻ `<script src="...">` thiếu `defer` hoặc `async` chặn trình duyệt dựng DOM.
   - **P1 — Thiếu thẻ SEO nền tảng trong `<head>`:** Kiểm tra có đủ `<title>{{ page_title }}</title>`, `<meta name="description">`, `<link rel="canonical" href="{{ canonical_url }}">`.
   - **P0 — Lỗi cú pháp Liquid / Bảo mật:** Cặp thẻ `{% if %}`/`{% for %}` không khớp `{% endif %}`/`{% endfor %}`, hoặc nhúng script `http://`, hoặc xuất biến chưa `| escape` trong thuộc tính HTML.
2. **Tính Theme Code Health Score (0–100):**
   $$\text{Code Health Score} = 100 - \min(100,\; 20 \cdot N_{P0} + 7 \cdot N_{P1} + 2 \cdot N_{P2})$$

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Kiểm toán Mã nguồn Haravan Liquid
- **Theme:** `Dawn-VN-Live` (`id: 10012948`, `role: main`) | **Số file rà soát:** 34 | **Code Health Score:** `64 / 100`

| Mức độ | File | Dòng | Mã lỗi | Chi tiết & Đề xuất sửa |
| --- | --- | ---: | --- | --- |
| P0 | `snippets/product-loop.liquid` | 42 | `LIQUID_N_PLUS_1` | Lồng `for` qua `collections.all.products` không có `limit`. Thêm `limit: 20` hoặc tách biến. |
| P1 | `layout/theme.liquid` | 18 | `RENDER_BLOCKING_JS` | 3 thẻ `<script src="...">` thiếu `defer`. Thêm thuộc tính `defer`. |
| P1 | `snippets/product-card.liquid` | 12 | `UNOPTIMIZED_IMAGE` | Dùng ảnh gốc chưa qua `img_url: 'grande'` và thiếu `loading="lazy"`. |
| P2 | `templates/product.liquid` | 88 | `MISSING_ALT_ESCAPE` | Thêm `| escape` vào thuộc tính `alt="{{ product.title | escape }}"`. |
```

```json
{
  "skill": "theme-liquid-code-review",
  "theme_id": 10012948,
  "theme_role": "main",
  "files_reviewed": 34,
  "code_health_score": 64,
  "findings": [
    { "severity": "P0", "file": "snippets/product-loop.liquid", "line": 42, "rule": "LIQUID_N_PLUS_1", "recommendation": "Loại bỏ vòng lặp lồng trên collections.all và thêm limit" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Cấm tuyệt đối sửa Live Theme (`role: "main"`):** Skill này là Read-Only (L1). Không bao giờ gọi `PUT /web/themes/{id}/assets.json` hay `DELETE` lên theme đang chạy.
- **Quy trình áp dụng thay đổi an toàn:** Nhân bản Live Theme sang Staging Theme (`role: "unpublished"`), kéo về bằng `npx @haravan/cli pull`, áp dụng bản vá, kiểm thử trên preview URL rồi mới được đội kỹ thuật publish.
- **Cấm đụng `templates/robots.txt.liquid` live:** Nếu phát hiện file `robots.txt.liquid` có cấu hình chặn bot bất thường, chỉ báo cáo P0 để quản trị viên tự duyệt, không tự sửa.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng review, yêu cầu làm mới `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `web.read_themes` | Báo rõ cần scope `web.read_themes` (hoặc dùng `local_theme_dir`). |
| `404 Not Found` | `theme_id` không tồn tại hoặc `asset[key]` sai đường dẫn | Gọi `GET /web/themes.json` để xác nhận ID hợp lệ. |
| `422 Unprocessable` | Tham số `asset[key]` không đúng định dạng | URL-encode giá trị `asset[key]`. |
| `429 Too Many Requests` | Đọc từng file asset qua API quá nhanh | Dùng `HaravanClient` (2.5 req/s) hoặc khuyến nghị dùng `npx @haravan/cli pull` để đọc local 0 API call. |

- **Edge Case 1 — File asset nhị phân hoặc file JS/CSS đã minify 1 dòng dài:** Bỏ qua các file ảnh (`.png`, `.jpg`, `.woff2`) và `.min.js`/`.min.css` khi phân tích cú pháp Liquid để tiết kiệm quota API và tránh báo lỗi giả.
- **Edge Case 2 — Dùng `loading="lazy"` sai chỗ trên ảnh Hero/Banner đầu trang:** Nếu phát hiện ảnh banner đầu tiên trong `index.liquid` hoặc ảnh chính PDP đang có `loading="lazy"`, cần cảnh báo ngược lại (`P1: LAZY_ON_LCP_IMAGE`) vì điều này làm chậm chỉ số LCP.
- **Edge Case 3 — Snippet đệ quy (include/render chính nó):** Một số menu đa cấp dùng `{% include 'menu-item' %}` gọi đệ quy không kiểm soát độ sâu; cần nhắc giới hạn độ sâu tối đa 3 cấp.

## 8. Liên kết Workflow & Skill kế tiếp

- **Triển khai bản vá Liquid an toàn trên Staging Theme:** Chuyển sang `haravan-cli-theme-ops` (L2) với `@haravan/cli`.
- **Kiểm toán các script nhúng từ App bên ngoài theme:** Chạy song song `storefront-script-tag-audit` (L1).
- **Đánh giá tác động giao diện lên tỷ lệ chuyển đổi mua hàng:** Chuyển sang `theme-performance-cro-audit` (L1).
