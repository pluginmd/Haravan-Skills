---
name: seo-blog-content-optimizer
description: "Đánh giá bài viết tin tức (/web/blogs/{id}/articles.json) và đề xuất tạo mới hoặc tối ưu cấu trúc SEO, internal link về sản phẩm."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 80-theme-seo-cro
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: web
  scopes:
    - com.read_contents
    - com.write_contents
  endpoints:
    - "GET https://apis.haravan.com/web/blogs.json"
    - "GET https://apis.haravan.com/web/blogs/{blog_id}/articles.json"
    - "POST https://apis.haravan.com/web/blogs/{blog_id}/articles.json"
    - "PUT https://apis.haravan.com/web/blogs/{blog_id}/articles/{article_id}.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Blog & Article SEO Optimizer Proposal

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Biến chuyên mục Tin tức / Blog trên Haraweb thành kênh thu hút Organic Traffic có khả năng chuyển đổi đơn hàng, thông qua việc kiểm toán bài viết hiện có (`audit`), tối ưu cấu trúc Heading/Internal Link (`update_article`) hoặc tạo bản nháp bài viết mới (`create_draft` ở trạng thái ẩn `published: false`).
- **Ngữ cảnh Haravan:** Haraweb quản lý bài viết theo cấp bậc `Blog` (`/web/blogs.json`) → `Article` (`/web/blogs/{blog_id}/articles.json`). Đa số shop Haravan đăng bài kiểu tin ngắn dưới 300 từ, thiếu phân cấp `<h2>`/`<h3>`, thiếu ảnh có thẻ `alt` và đặc biệt **không gắn liên kết nội bộ (internal link)** trỏ về `/products/{handle}` hoặc `/collections/{handle}` khiến traffic đọc xong thoát ngay.
- **Definition of Done (DoD):**
  1. Đọc danh sách bài viết của `blog_id` mục tiêu và chấm điểm Content SEO Score (0–100) cho từng bài.
  2. Soạn đề xuất sửa đổi hoặc bản thảo bài viết mới chuẩn SEO tiếng Việt (H2/H3 rõ ràng, mật độ từ khóa tự nhiên, ≥ 2 internal link về sản phẩm/bộ sưu tập thật đang tồn tại).
  3. Sinh bản Preview Diff + file Backup JSON qua `scripts/dry_run_report.py` (lưu nguyên `body_html` gốc trước khi `PUT`); mặc định `published: false` khi tạo mới và chỉ gọi API ghi sau khi người dùng duyệt.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `web` (`https://apis.haravan.com/web`) |
| **Scopes tối thiểu** | `com.read_contents`, `com.write_contents` |
| **Endpoints** | `GET /web/blogs.json`, `GET/POST /web/blogs/{blog_id}/articles.json`, `PUT /web/blogs/{blog_id}/articles/{article_id}.json` |

**Ví dụ gọi qua `scripts/hrv_client.py` (tạo bản nháp an toàn ở chế độ `dry_run=True`):**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
blogs = client.request("GET", "web", "/blogs.json")
articles = client.paginate("web", "/blogs/1000234567/articles.json", "articles", limit=50, max_pages=5)

draft_payload = {
    "article": {
        "title": "Cách chọn áo Polo nam cotton Pique thoáng mát cho mùa hè 2026",
        "author": "Đội ngũ Nội dung",
        "tags": "ao-polo, huong-dan-chon-size, thoi-trang-nam",
        "summary_html": "<p>Hướng dẫn chi tiết cách phân biệt vải cotton Pique, chọn form dáng và phối đồ chuẩn chỉnh.</p>",
        "body_html": "<h2>1. Vải cotton Pique là gì?</h2><p>...</p><p>Xem ngay <a href='/collections/ao-polo-nam'>bộ sưu tập Áo Polo Nam</a>.</p>",
        "published": False
    }
}
preview = client.request("POST", "web", "/blogs/1000234567/articles.json", payload=draft_payload)
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `blog_id` | `integer` | Bắt buộc | — | ID chuyên mục blog lấy từ `GET /web/blogs.json`. |
| `action` | `string` | Bắt buộc | `audit` | Enum: `audit`, `create_draft`, `update_article`. |
| `article_id` | `integer` | Khi `update_article` | `null` | ID bài viết cần tối ưu. |
| `target_keyword` | `string` | Khi tạo/tối ưu | `""` | Từ khóa SEO chính tiếng Việt (tối đa 80 ký tự). |
| `product_links` | `array[string]` | Không | `[]` | Danh sách đường dẫn tương đối `/products/...` hoặc `/collections/...` để chèn internal link. |
| `dry_run` | `boolean` | Bắt buộc | `true` | Luôn `true` ở bước đề xuất; chỉ đổi `false` sau khi người dùng xác nhận. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Chấm điểm Content SEO cho từng bài viết (`audit`):**
   - **Độ dài nội dung (25 điểm):** `word_count >= 800` đạt tối đa; `300–799` đạt 15đ; `< 300` (Thin Content) đạt 0đ.
   - **Cấu trúc Heading (20 điểm):** Không chứa `<h1>` trùng lặp trong `body_html` (vì Haraweb đã dùng `<h1>` cho `article.title`), có ít nhất `2` thẻ `<h2>` và phân cấp `<h3>` hợp lý.
   - **Internal Linking (25 điểm):** Có ≥ 2 liên kết trỏ tới `/products/` hoặc `/collections/` với anchor text mô tả tự nhiên (không dùng anchor "tại đây", "click ngay").
   - **Hình ảnh & Alt Text (15 điểm):** Có ảnh đại diện (`article.image`) và 100% thẻ `<img>` trong `body_html` có thuộc tính `alt` mô tả chứa từ khóa liên quan.
   - **Tóm tắt & Tags (15 điểm):** Có `summary_html` dài 120–160 ký tự và tối thiểu `2` tags phân loại.
   $$\text{Content SEO Score} = S_{\text{length}} + S_{\text{heading}} + S_{\text{internal\_link}} + S_{\text{media}} + S_{\text{meta}}$$
2. **Sinh bản thảo hoặc tối ưu hóa (`create_draft` / `update_article`):**
   - Kiểm tra HTML hợp lệ: không chèn `<script>`, không chèn inline CSS phá vỡ giao diện mobile, dùng đường dẫn tương đối `/products/{handle}` thay vì hardcode domain.
   - Với `update_article`: **giữ nguyên `handle` (URL cũ)** để không làm gãy link Google đã index; chỉ nâng cấp `body_html`, `summary_html`, `tags`.
3. **Backup & Preview:** Lưu nguyên bản `body_html` cũ vào `hrv-seo-blog-content-optimizer-<ts>.backup.json` qua `write_dry_run_artifact()`.
4. **Thực thi & Xác minh:** Sau khi người dùng duyệt, gọi `POST`/`PUT` với `published: false` (khi tạo mới), sau đó gọi `GET /web/blogs/{blog_id}/articles/{id}.json` xác nhận bài đã lưu sạch sẽ.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Đề xuất Tối ưu SEO Blog Haraweb (`blog_id: 1000234567`)
- **Chế độ:** `update_article` (`dry_run: true`) | **Bài viết:** `#1000891234` — *"Bí quyết bảo quản áo sơ mi không nhăn"*
- **Điểm SEO trước → sau dự kiến:** `42 / 100` → `92 / 100`
- **Backup gốc:** `artifacts/hrv-seo-blog-content-optimizer-20261125T071000Z.backup.json`

| Tiêu chí | Hiện tại (Before) | Đề xuất (After) |
| --- | --- | --- |
| Độ dài | 240 từ (Thin Content) | 960 từ (hướng dẫn 5 bước chi tiết) |
| Cấu trúc Heading | 0 thẻ `<h2>`, dùng `<p><b>` | 4 thẻ `<h2>`, 6 thẻ `<h3>` chuẩn ngữ nghĩa |
| Internal Links | 0 link sản phẩm | 3 link về `/collections/ao-so-mi-nam`, `/products/ao-so-mi-bamboo` |
| URL Handle | `bi-quyet-bao-quan-ao-so-mi` | Giữ nguyên (không gây lỗi 404) |

> Vui lòng xác nhận **"Duyệt cập nhật bài #1000891234"** để tiến hành ghi lên Haravan.
```

```json
{
  "skill": "seo-blog-content-optimizer",
  "action": "update_article",
  "dry_run": true,
  "blog_id": 1000234567,
  "article_id": 1000891234,
  "seo_score_before": 42,
  "seo_score_est_after": 92,
  "published": false,
  "backup_json": "artifacts/hrv-seo-blog-content-optimizer-20261125T071000Z.backup.json"
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run & Draft-First (L2):** Bắt buộc `dry_run: true`, `confirmation_required: true`, `max_records <= 50`. Mọi bài tạo mới **bắt buộc đặt `published: false`** để biên tập viên xem trước giao diện thực tế trên Haravan Admin rồi mới tự bấm xuất bản.
- **Bảo vệ URL đã index:** Tuyệt đối không tự ý đổi `handle` của bài viết đang có traffic organic; nếu bắt buộc đổi, phải tạo 301 Redirect qua `/web/redirects.json`.
- **Rollback:** Khi cần khôi phục bài viết đã `PUT`, đọc trường `before` (`body_html`, `summary_html`, `tags`) trong file `*.backup.json` và gọi `PUT` khôi phục hoặc dùng `governance-rollback-executor`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng ngay, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_contents` / `com.write_contents` | Thông báo rõ scope thiếu; không thử ghi khi thiếu quyền. |
| `404 Not Found` | `blog_id` hoặc `article_id` không tồn tại | Gọi `GET /web/blogs.json` liệt kê danh sách `blog_id` hợp lệ. |
| `422 Unprocessable` | `title` rỗng, HTML vượt kích thước hoặc ký tự không hợp lệ | Rút gọn/làm sạch HTML, kiểm tra `title` rồi chạy lại dry-run. |
| `429 Too Many Requests` | Cập nhật hàng loạt nhiều bài vượt rate limit | `HaravanClient` tự backoff `1s -> 2s -> 4s`; dừng batch nếu lỗi lặp. |

- **Edge Case 1 — Copy-paste từ Word/Google Docs chứa rác `<span style="font-size:...">`:** Khi `audit` phát hiện inline style rác làm vỡ font trên mobile, cần làm sạch giữ lại thẻ chuẩn (`p`, `h2`, `h3`, `ul`, `li`, `a`, `img`, `table`) trước khi đề xuất `PUT`.
- **Edge Case 2 — Bài viết đang nhúng shortcode/iframe YouTube hoặc form đăng ký:** Không được vô tình xóa thẻ `<iframe>` video hoặc mã nhúng CTA của shop khi tối ưu `body_html`; phải bảo toàn nguyên khối nhúng đó.
- **Edge Case 3 — Tạo trùng bài khi retry sau timeout:** Trước khi retry `POST`, gọi `GET /web/blogs/{blog_id}/articles.json` kiểm tra `title` đã tồn tại chưa (`idempotency_required: true`).

## 8. Liên kết Workflow & Skill kế tiếp

- **Kiểm toán SEO tổng thể toàn site (sản phẩm, trang tĩnh, redirect):** Chạy trước bằng `seo-metadata-serp-audit` (L1).
- **Tạo 301 Redirect nếu hợp nhất/đổi URL bài viết cũ:** Chuyển sang `storefront-redirect-proposal` (L2) hoặc `python3 scripts/hrv_ops.py redirect-audit`.
- **Kiểm tra bài viết hiển thị đẹp trên mobile & tốc độ ảnh:** Kết hợp `theme-performance-cro-audit` (L1).
