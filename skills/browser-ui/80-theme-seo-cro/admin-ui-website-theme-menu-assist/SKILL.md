---
name: admin-ui-website-theme-menu-assist
description: "Vận hành Website Haravan (/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}): xử lý thông minh giới hạn cross-origin iframe web.haravan.app, định tuyến Hybrid sang Web API/@haravan/cli và hướng dẫn Assisted-UI cho Menu đa cấp & Theme Customizer."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 80-theme-seo-cro
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/sale_channels/online_store/themes"
    - "UI /admin/sale_channels/online_store/articles"
    - "UI /admin/sale_channels/online_store/pages"
    - "UI /admin/sale_channels/online_store/menus"
    - "UI /admin/sale_channels/online_store/settings"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 25
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

# Haravan Admin UI — Vận Hành Website, Giao Diện & Menu (Hybrid Cross-Origin Assist)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Xử lý thông minh và an toàn toàn bộ 5 màn hình con dưới **Kênh bán hàng > Website** (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) vốn có đặc thù kỹ thuật chạy trong **cross-origin iframe `https://web.haravan.app`**. Thay vì cố click mù gây lỗi hoặc làm hỏng giao diện Live, skill thực hiện 2 cơ chế:
  1. **Định tuyến Hybrid sang Web API / `@haravan/cli`:** Chuyển giao các tác vụ sửa Theme Liquid/Assets, Pages, Blogs/Articles, URL Redirects sang bộ skill `api-mcp` tương ứng (khi cửa hàng có token/CLI).
  2. **Assisted-UI Runbook từng bước:** Mở đúng màn hình đích trên Haravan Admin, chuẩn bị sẵn cấu trúc JSON/cây Menu đa cấp, nội dung chuẩn SEO, checklist thiết lập Theme Customizer/Cấu hình Website và đồng hành từng bước để người dùng thao tác trực tiếp bên trong iframe `web.haravan.app` an toàn.
- **Phạm vi UI:** 5 tuyến đường Website (`/themes`, `/articles`, `/pages`, `/menus`, `/settings`). Không bao gồm trỏ DNS/tên miền chính (dùng `admin-ui-domains-channels-website`).
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Toàn quyền truy cập cả 5 mục Website, nhân bản theme, chỉnh Menu, đăng bài Blog/Trang nội dung và sửa cấu hình SEO/Google Analytics/Facebook Pixel.
  - **Staff:** Yêu cầu quyền `Kênh bán hàng Website` (`Giao diện`, `Blog & Trang nội dung`, `Menu`, `Cấu hình Website`). Nếu Staff bị ẩn mục `Giao diện` hoặc `Cấu hình Website`, dừng và báo thiếu quyền.
- **Yêu cầu Gói dịch vụ Haravan:** Kênh Website khả dụng trên các gói có tích hợp Haravan Web (Omnichannel / Web / Pro / Grow / Scale). Một số theme bản quyền trả phí có giới hạn quyền chỉnh sửa mã Liquid nâng cao.
- **Pre-flight Check bắt buộc:**
  1. Kiểm tra phiên đăng nhập qua `admin-ui-session-navigator` và xác minh đang mở đúng `store_domain`.
  2. Xác nhận trước khi chạm vào **Giao diện**: tuyệt đối **không sửa trực tiếp Live Theme (`role: "main"` / Giao diện đang hiển thị)**; bắt buộc nhân bản (`Sao chép`) ra một Staging Theme trước.

## 2. Bản đồ Giao diện Thực tế (Exact Route, Cross-Origin Iframe & Chiến lược Định tuyến)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Cross-Origin Iframe (Live-Verified):** Toàn bộ 5 màn hình Website (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) nhúng `https://web.haravan.app`. Ưu tiên Web API (`/web/*`) và `@haravan/cli` cho Theme/Pages/Blogs/Redirects; dùng Assisted-UI cho Menu & Theme Customizer.


| Mục con Website | Route chính xác trên Admin | Origin thực tế (Verified) | Chiến lược thực thi chuẩn | Hạng mục thao tác chính |
| :--- | :--- | :--- | :--- | :--- |
| `Giao diện` | `/admin/sale_channels/online_store/themes` | Cross-origin iframe `https://web.haravan.app` | **Hybrid:** `@haravan/cli` / Web API cho code Liquid; **Assisted-UI** cho `Thiết lập giao diện` (Customizer) | `Sao chép` theme làm Staging, `Thiết lập giao diện`, `Chỉnh sửa code`, `Xem trước`, (**CẤM** tự bấm `Xuất bản`) |
| `Blogs` | `/admin/sale_channels/online_store/articles` | Cross-origin iframe `https://web.haravan.app` | **Hybrid:** Web API (`/web/blogs/*`) cho tạo/tối ưu hàng loạt; **Assisted-UI** khi đăng bài trực tiếp | Danh mục Blog, Bài viết (`Tiêu đề`, `Nội dung`, `Ảnh đại diện`, `Tối ưu SEO`, `Trạng thái hiển thị`, `Tag`) |
| `Trang nội dung` | `/admin/sale_channels/online_store/pages` | Cross-origin iframe `https://web.haravan.app` | **Hybrid:** Web API (`/web/pages.json`); **Assisted-UI** cho landing page/trang chính sách | Trang `Giới thiệu`, `Liên hệ`, `Hướng dẫn chọn size`, `Chính sách đổi trả`, chọn `Khung giao diện (Template)` |
| `Menu` | `/admin/sale_channels/online_store/menus` | Cross-origin iframe `https://web.haravan.app` | **Assisted-UI bắt buộc** (Haravan không có public API sửa cấu trúc cây Menu đa cấp) | `Menu chính (Main menu)`, `Footer menu`, kéo thả phân cấp cấp 1–2–3, gắn link tới `Nhóm sản phẩm`/`Trang`/`Blog`/`URL ngoài` |
| `Cấu hình Website` | `/admin/sale_channels/online_store/settings` | Cross-origin iframe `https://web.haravan.app` | **Assisted-UI** (kèm kiểm toán SEO/Redirect qua Web API) | `Tiêu đề trang chủ`, `Mô tả trang chủ`, `Ảnh chia sẻ MXH`, `Google Analytics / GA4`, `Facebook Pixel`, `Mật khẩu bảo vệ Website`, `Chuyển hướng URL` |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `menu_hierarchy_assist` | `menu_hierarchy_assist` \| `theme_staging_customizer_assist` \| `blog_page_hybrid_publish` \| `website_seo_tracking_settings` \| `iframe_hybrid_router` |
| `has_api_token_or_cli` | `boolean` | Không | `false` | Nếu `true`, tự động đề xuất chuyển các tác vụ Liquid/Pages/Blogs sang `skills/api-mcp/` |
| `target_theme_mode` | `enum` | Khi sửa Theme | `staging_duplicate` | Bắt buộc `staging_duplicate` (tuyệt đối không chấp nhận `live_direct`) |
| `menu_tree_spec` | `array<object>` | Khi sửa Menu | `[]` | Cấu trúc cây tối đa 3 cấp (`label`, `link_type`, `target_url`, `children`), tổng ≤ `25` mục/đợt |
| `content_draft` | `object` | Khi đăng Blog/Page | `null` | Gồm `title`, `body_html`, `meta_title` (≤ 70 ký tự), `meta_description` (≤ 320 ký tự), `handle`, `published` (`false` mặc định) |
| `tracking_ids` | `object` | Khi cấu hình Web | `{}` | `ga4_id` (`^G-[A-Z0-9]+$`), `fb_pixel_id` (`^[0-9]{10,20}$`), `homepage_title`, `homepage_description` |
| `dry_run` | `boolean` | Không | `true` | Bắt buộc `true` — dựng bản thiết kế/checklist hoàn chỉnh trước khi thao tác |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click & Hybrid)

### Kịch bản 1: Định tuyến Hybrid thông minh khi gặp Cross-Origin Iframe (`web.haravan.app`)
1. Điều hướng tới tuyến đường Website mục tiêu (ví dụ `/admin/sale_channels/online_store/themes`), xác nhận khung chính của trang được nhúng từ `https://web.haravan.app` (DOM nội bộ bị sandbox ẩn).
2. **Dừng ngay mọi nỗ lực click mù trong iframe**; kiểm tra tham số `has_api_token_or_cli` và loại yêu cầu của người dùng:
   - Nếu cần sửa code Liquid/CSS/JS hàng loạt → chuyển sang `skills/api-mcp/00-core-platform/haravan-cli-theme-ops` (`haravan pull` / `haravan deploy` vào Staging Theme).
   - Nếu cần kiểm toán/cập nhật hàng loạt SEO Pages, Blogs hoặc Redirects → chuyển sang `seo-metadata-serp-audit`, `seo-blog-content-optimizer`, `store-redirect-audit`.
   - Nếu cần chỉnh **Menu đa cấp**, **Theme Customizer kéo thả**, hoặc người dùng không dùng API token → kích hoạt ngay chế độ **Assisted-UI** (Kịch bản 2–5).

### Kịch bản 2: Assisted-UI thiết lập Cây Menu Đa Cấp (`/admin/sale_channels/online_store/menus`)
1. Mở sẵn tab `https://{store_domain}/admin/sale_channels/online_store/menus` cho người dùng và chụp ảnh trạng thái khung trang (`pre_screenshot`).
2. Chuẩn bị sẵn bản thiết kế cây Menu dạng bảng phân cấp rõ ràng (`Cấp 1` → `Cấp 2` → `Cấp 3`), kèm chính xác loại liên kết Haravan (`Nhóm sản phẩm`, `Trang nội dung`, `Blog`, `Tìm kiếm`, `Địa chỉ web`) để người dùng không bị gắn link gãy 404.
3. Hướng dẫn người dùng thao tác từng bước trong iframe `web.haravan.app`:
   - Bước A: Chọn `Menu chính` (hoặc bấm `Thêm menu` nếu tạo menu footer mới).
   - Bước B: Bấm `Thêm liên kết` → nhập `Tên` và chọn đúng `Liên kết` từ danh sách nhóm SP/trang.
   - Bước C: Kéo thả biểu tượng 6 chấm sang phải dưới mục cha để tạo Menu cấp 2/cấp 3 theo sơ đồ.
4. Nhắc người dùng kiểm tra đủ mục rồi mới bấm `Lưu menu`, sau đó mở storefront ở tab ẩn danh để kiểm tra hiển thị trên cả Desktop & Mobile.

### Kịch bản 3: Assisted-UI nhân bản Staging Theme & Chỉnh sửa Theme Customizer (`/themes`)
1. Mở sẵn `https://{store_domain}/admin/sale_channels/online_store/themes`.
2. Hướng dẫn người dùng tại khối `Giao diện hiện tại`: bấm menu `Thao tác` → chọn `Sao chép` để tạo bản Staging Theme (đổi tên có ngày tháng, ví dụ `[STAGING 25/11] Doi Banner Black Friday`).
3. Trên bản Staging Theme vừa tạo, hướng dẫn người dùng bấm `Thiết lập giao diện` (Theme Customizer) để thay đổi Banner trang chủ, màu chủ đạo, chọn Nhóm sản phẩm nổi bật, bật/tắt section khuyến mãi theo checklist đã soạn sẵn.
4. Hướng dẫn bấm `Lưu` trên Staging Theme → bấm `Thao tác` → `Xem trước` để kiểm tra giao diện trên Mobile & Desktop. **Dừng tại đây** — tuyệt đối không tự bấm `Xuất bản` lên Live khi người dùng chưa kiểm thử xong toàn bộ luồng giỏ hàng/thanh toán.

### Kịch bản 4: Hybrid / Assisted-UI đăng Bài viết Blog & Trang nội dung chuẩn SEO (`/articles`, `/pages`)
1. Nếu có API token: đề xuất chạy Web API (`/web/pages.json` hoặc `/web/blogs/{id}/articles.json`) với `published: false` (bản nháp).
2. Nếu thao tác trên UI: mở sẵn `/admin/sale_channels/online_store/articles` hoặc `/pages`, cung cấp sẵn khối nội dung HTML sạch (đã tối ưu heading `H2/H3`, ảnh có thẻ `Alt`, `Meta Title <= 70 ký tự`, `Meta Description <= 320 ký tự`, `URL Handle` không dấu).
3. Hướng dẫn người dùng bấm `Tạo bài viết` / `Thêm trang`, dán nội dung vào trình soạn thảo, chọn `Ẩn` (bản nháp) hoặc hẹn giờ đăng, kiểm tra bản xem trước rồi mới bấm `Lưu`.

### Kịch bản 5: Assisted-UI kiểm tra Cấu hình SEO Trang chủ, GA4/Pixel & Mật khẩu Website (`/settings`)
1. Mở sẵn `https://{store_domain}/admin/sale_channels/online_store/settings`.
2. Đối chiếu bộ giá trị mới (`homepage_title`, `homepage_description`, `ga4_id`, `fb_pixel_id`) với chuẩn định dạng để tránh dán nhầm cả đoạn `<script>` vào ô chỉ nhận ID.
3. Nhắc người dùng kiểm tra kỹ mục **Bảo vệ bằng mật khẩu** (đảm bảo đang **Tắt** với cửa hàng Live đang bán hàng, tránh vô tình khóa toàn bộ khách vào Website) và **tuyệt đối không sửa `robots.txt` live** nếu không có kiểm tra SEO chuyên sâu.
4. Người dùng tự bấm `Lưu` trong iframe, sau đó Agent xác minh lại trên storefront (kiểm tra thẻ `<title>`, meta description hoặc trạng thái truy cập trang chủ).

### Bảng Quyết Định Kênh Thực Thi Cho 5 Phân Hệ Website (`web.haravan.app`)

| Yêu cầu nghiệp vụ của người dùng | Có API Token / `@haravan/cli`? | Kênh tối ưu nên chọn | Lý do kỹ thuật |
| :--- | :--- | :--- | :--- |
| Chỉnh sửa code Liquid / CSS / JS Theme | Có | `@haravan/cli` (`haravan-cli-theme-ops`) | Có version control Git, deploy vào Staging Theme an toàn |
| Sửa Banner, màu sắc, thứ tự Section Theme | Không / Có | Assisted-UI trên Staging Theme (`/themes`) | Theme Customizer trực quan chỉ có trong iframe `web.haravan.app` |
| Dựng hoặc sắp xếp cây Menu đa cấp (1–2–3) | Không / Có | Assisted-UI bắt buộc (`/menus`) | Haravan không mở REST API chỉnh sửa cây Menu đa cấp |
| Tối ưu SEO / đăng hàng loạt Pages, Blogs, Redirects | Có | Web API (`/web/*`) trong `skills/api-mcp/` | Nhanh, chuẩn hóa hàng loạt, không bị giới hạn iframe |
| Sửa nhanh 1 bài Blog / Trang hoặc cấu hình GA4/Pixel | Không | Assisted-UI (`/articles`, `/pages`, `/settings`) | Agent soạn sẵn nội dung/ID chuẩn, người dùng dán & bấm `Lưu` |

## 5. Quy trình An toàn 4 Pha (Hybrid & Assisted-UI Safety Protocol)

1. **Pha 1 — Pre-State & Live Storefront Capture (Sao lưu hiện trạng Live):**
   - Mở đúng route `/admin/sale_channels/online_store/*` trên Haravan Admin, xác nhận khung cross-origin iframe `https://web.haravan.app`.
   - Mở đồng thời storefront công khai (`https://{store_domain}`) ở tab riêng để chụp ảnh giao diện/menu/SEO gốc (`pre_screenshot`) làm căn cứ đối chiếu.
2. **Pha 2 — Stage Proposal / Staging Theme (`dry_run: true`):**
   - Chuẩn bị trọn gói tài liệu thực thi trước khi chỉnh sửa: sơ đồ cây Menu 3 cấp, checklist chỉnh Theme Customizer trên bản **Staging Theme (`Sao chép`)**, bản nháp HTML/Meta SEO (`published: false`), hoặc mã GA4/Pixel đã kiểm định regex.
   - **Tuyệt đối không chỉnh trực tiếp Live Theme và chưa bấm `Lưu` / `Xuất bản`**.
3. **Pha 3 — Human Confirmation & Guided Execution Gate:**
   - Trình bày bảng `Before → After` kèm hướng dẫn click từng bước rõ ràng (hoặc đề xuất chạy lệnh `@haravan/cli` / Web API nếu có token).
   - Chờ người dùng xác nhận và trực tiếp thực hiện cú click `Lưu` bên trong iframe `web.haravan.app` (đảm bảo tuân thủ tuyệt đối ranh giới sandbox trình duyệt).
4. **Pha 4 — Post-Save Storefront Verification (Xác minh trên giao diện khách hàng):**
   - Sau khi người dùng báo đã bấm `Lưu`, tải lại URL storefront (hoặc link `Xem trước` của Staging Theme) ở chế độ không cache (`Ctrl+Shift+R`).
   - Kiểm tra trực quan Menu mới không gãy link 404, Banner/Section hiển thị đúng cả Desktop & Mobile, thẻ `<title>` / `<meta description>` đã cập nhật và chụp `post_screenshot`.

### Checklist Kiểm Thử Trước Khi Xuất Bản Giao Diện / Menu (Storefront QA Gate)

- [ ] Đã nhân bản (`Sao chép`) Live Theme ra bản Staging có tên gắn ngày (`[STAGING DD/MM]`) trước khi sửa bất kỳ thiết lập hay mã Liquid nào.
- [ ] Toàn bộ liên kết trong Menu đa cấp mới đều được chọn từ danh sách `Nhóm sản phẩm` / `Trang nội dung` / `Blog` chuẩn (không gắn URL gãy 404).
- [ ] Đã kiểm tra luồng mua hàng mẫu trên link `Xem trước` (Trang chủ → Chi tiết SP → Thêm vào giỏ → Trang thanh toán) trên cả Desktop và Mobile.
- [ ] Mục `Bảo vệ Website bằng mật khẩu` tại `/settings` vẫn đang **Tắt** đối với cửa hàng Live và không chỉnh sửa `robots.txt`.
- [ ] Không cố vượt rào cross-origin iframe `web.haravan.app`; mọi thao tác code Liquid hàng loạt đều định tuyến qua `@haravan/cli`.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Đề xuất Cập nhật Website

| Khu vực Website | Hạng mục thay đổi | Trước (Before) | Sau (After — Proposed / Assisted) | Kênh thực thi |
| :--- | :--- | :--- | :--- | :--- |
| `Menu chính` (`/menus`) | Mục `Khuyến mãi` | Chưa có cấp 2 | Thêm cấp 2: `Sale Hè`, `Đồng giá 199K`, `Combo Tiết Kiệm` | Assisted-UI (iframe) |
| `Giao diện` (`/themes`) | Banner trang chủ | Banner Thu 2026 | Cập nhật trên **Staging Theme `[STAGING 25/11]`** (chưa Publish) | Assisted-UI / `@haravan/cli` |
| `Trang nội dung` (`/pages`) | Trang `Chọn Size` | *(Chưa có)* | Bản nháp `published: false`, Meta Title 58 ký tự, Handle `huong-dan-chon-size` | Web API / Assisted-UI |
| `Cấu hình` (`/settings`) | Mã theo dõi GA4 | *(Trống)* | `G-ABC123XYZ9` (đúng định dạng ID, không dán thẻ `<script>`) | Assisted-UI (iframe) |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-website-theme-menu-assist",
  "mode": "proposal",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/sale_channels/online_store/menus",
  "scenario": "menu_hierarchy_assist",
  "session_authenticated": true,
  "is_cross_origin_iframe": true,
  "iframe_origin": "https://web.haravan.app",
  "execution_strategy": "assisted_ui",
  "hybrid_fallback_skill": "skills/api-mcp/00-core-platform/haravan-cli-theme-ops",
  "dry_run": true,
  "live_theme_untouched": true,
  "pre_screenshot": "artifacts/website_storefront_pre.png",
  "preview_screenshot": "artifacts/website_menus_iframe_ready.png",
  "post_screenshot": null,
  "changes_staged": [
    {
      "section": "main_menu",
      "action": "add_submenu_items",
      "items_count": 3,
      "staging_only": true
    }
  ],
  "warnings": [
    "Cross-origin iframe web.haravan.app detected; user must click Save inside iframe."
  ],
  "saved_verified": false
}
```

### Mẫu Cấu Trúc Cây Menu 3 Cấp Chuẩn (Assisted-UI Blueprint)

```text
Menu chính (Main menu)
├── Sản phẩm mới (Liên kết: Nhóm sản phẩm -> /collections/san-pham-moi)
├── Thời trang Nam (Liên kết: Nhóm sản phẩm -> /collections/thoi-trang-nam)
│   ├── Áo Polo (Cấp 2 -> /collections/ao-polo-nam)
│   └── Quần Jeans (Cấp 2 -> /collections/quan-jeans-nam)
├── Khuyến mãi (Liên kết: Nhóm sản phẩm -> /collections/khuyen-mai)
│   ├── Sale Hè 2026 (Cấp 2)
│   ├── Đồng giá 199K (Cấp 2)
│   └── Combo Tiết Kiệm (Cấp 2)
└── Hướng dẫn chọn size (Liên kết: Trang nội dung -> /pages/huong-dan-chon-size)
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các thao tác TUYỆT ĐỐI CẤM tự thực hiện hoặc tự bấm:**
  - `Xuất bản (Publish)` giao diện đè lên Live Theme (`role: "main"`) khi chưa kiểm thử trên Staging Theme và chưa có xác nhận trực tiếp của người dùng.
  - `Xóa giao diện`, `Xóa Menu chính`, `Xóa trang nội dung` đang có traffic SEO.
  - Bật `Bảo vệ Website bằng mật khẩu` trên cửa hàng đang bán hàng live.
  - Chỉnh sửa trực tiếp `robots.txt` live (có thể làm mất toàn bộ index Google Search).
- **Iframe & Credential Gate:** Không bao giờ cố vượt rào bảo mật cross-origin iframe `https://web.haravan.app`; gặp `accounts.haravan.com` → dừng ngay cho người dùng tự đăng nhập.

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Khung nội dung bên trong `/admin/sale_channels/online_store/*` hiển thị trắng hoặc trình duyệt không đọc được DOM:** Đây là hành vi chuẩn của chính sách bảo mật trình duyệt (Same-Origin Policy) với iframe `https://web.haravan.app`, không phải lỗi mạng. Chuyển ngay sang chế độ Hybrid (Web API/`@haravan/cli`) hoặc Assisted-UI hướng dẫn người dùng thao tác trực tiếp trên tab đang mở.
2. **Sửa nhầm code Liquid làm vỡ layout trang chủ hoặc mất nút `Thêm vào giỏ`:** Vì luôn thao tác trên Staging Theme (`Sao chép` trước), giao diện Live hoàn toàn không bị ảnh hưởng; nếu lỡ sửa trên Live, dùng ngay tính năng `Phiên bản cũ` (Older versions) trong trình sửa file Liquid để khôi phục.
3. **Trình duyệt chặn cookie bên thứ 3 khiến iframe `web.haravan.app` báo lỗi đăng nhập lặp lại:** Hướng dẫn người dùng bật cho phép cookie cho `*.haravan.app` / `*.myharavan.com` hoặc mở bằng trình duyệt chính không bật chế độ chặn cookie cực đoan.
4. **Menu mới gắn liên kết sai URL tạo lỗi 404 trên storefront:** Luôn chọn mục liên kết từ danh sách gợi ý (`Nhóm sản phẩm`, `Trang nội dung`) thay vì gõ tay URL; sau khi lưu, kiểm tra thử từng mục cấp 1–2 trên storefront.
5. **Dán nhầm cả đoạn `<script>` Google Analytics vào ô chỉ nhận Measurement ID:** Làm lỗi hiển thị thẻ script ở phần đầu trang; luôn kiểm tra định dạng `G-XXXXXXXXXX` trước khi lưu tại `/settings`.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback Thủ công theo Từng Phân hệ Website
- **Giao diện (Themes):** Nếu lỡ xuất bản giao diện mới phát sinh lỗi hiển thị giỏ hàng/thanh toán, mở ngay `/admin/sale_channels/online_store/themes` → tìm bản Theme backup cũ → bấm `Thao tác` → `Xuất bản` lại để khôi phục giao diện ổn định trong vòng 10 giây.
- **Mã nguồn Liquid sửa nhầm trong trình soạn thảo:** Mở đúng file `.liquid` bị lỗi → chọn dropdown `Phiên bản cũ` (Older versions) ở đầu trình soạn thảo → chọn mốc thời gian trước khi sửa → bấm `Lưu`.
- **Menu đa cấp (`/menus`):** Mở lại `Menu chính` / `Footer menu`, khôi phục chính xác tên mục, cấu trúc phân cấp và liên kết gốc dựa trên ảnh chụp storefront `pre_screenshot`.
- **Trang nội dung / Blog / Cấu hình SEO (`/pages`, `/articles`, `/settings`):** Chuyển bài viết/trang đăng nhầm về trạng thái `Ẩn` (không xóa nếu đã chia sẻ link), hoặc khôi phục lại `Tiêu đề trang chủ` / `GA4 ID` / `FB Pixel ID` từ `pre_screenshot`.

### Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan
- Quản lý Theme qua CLI & kiểm toán code Liquid / hiệu năng CRO / Script Tag / SEO / Redirect: `skills/api-mcp/00-core-platform/haravan-cli-theme-ops`, `skills/api-mcp/80-theme-seo-cro/theme-liquid-code-review`, `theme-performance-cro-audit`, `storefront-script-tag-audit`, `seo-metadata-serp-audit`, `seo-blog-content-optimizer`, `skills/api-mcp/10-store-bootstrap/store-redirect-audit`.
- Quản lý tên miền, kênh bán hàng & kho tệp tin trên UI: `skills/browser-ui/95-admin-ui-browser/admin-ui-domains-channels-website`, `skills/browser-ui/80-theme-seo-cro/storefront-file-storage-audit`.
