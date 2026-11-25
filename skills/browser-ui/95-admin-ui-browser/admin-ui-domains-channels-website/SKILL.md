---
name: admin-ui-domains-channels-website
description: "Quản lý Tên miền (/admin/settings/domains), Kênh bán hàng (/admin/settings/sale_channels), Kênh marketing (/admin/settings/marketing_channels) và hướng dẫn xử lý iframe Website."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 95-admin-ui-browser
layer: L3
wave: 3
mode: write
risk: critical
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/settings/domains"
    - "UI /admin/settings/sale_channels"
    - "UI /admin/settings/marketing_channels"
    - "UI /admin/sale_channels/online_store/themes"
    - "UI /admin/sale_channels/online_store/menus"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 10
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: true
---

# Haravan Admin UI: Domains/SSL, Sales Channels & Website Iframe Guide (Critical L3)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Cấu hình **Tên miền & chứng chỉ SSL** (`/admin/settings/domains`), kết nối **Kênh bán hàng** (`/admin/settings/sale_channels` — Website, Haravan POS, Harasocial, Shopee, Lazada, TikTok Shop, Tiki) và **Kênh marketing** (`/admin/settings/marketing_channels` — TikTok Ads, Google Ads/Shopping) hoàn toàn nằm trên Haravan Admin UI, không có REST API để thay đổi.
- **Mức độ rủi ro L3 Critical (`separate_turn: true`):** Đổi nhầm `Tên miền chính` khi DNS/SSL chưa sẵn sàng hoặc gỡ nhầm kênh sàn đang chạy live sẽ gây **sập storefront** (lỗi chứng chỉ HTTPS) hoặc **đứt luồng đồng bộ đơn hàng & tồn kho đa kênh** ngay lập tức.
- **Lưu ý kỹ thuật Cross-Origin Iframe (`https://web.haravan.app`):** Theo `api/admin-ui-sitemap.yaml` và `policies/browser-ui-safety.md`, 5 màn hình con dưới **Kênh bán hàng > Website** (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) chạy trong cross-origin iframe `https://web.haravan.app` bị trình duyệt sandbox ẩn DOM. Agent phải **chủ động định tuyến** sang `@haravan/cli` / Web API (`/web/*`) thay vì cố click mù trong iframe.
- **Phân quyền Owner vs Staff & Giới hạn gói (Standard / Pro / Grow / Scale):**
  - **Bắt buộc tài khoản Chủ cửa hàng (Owner)** đối với `/admin/settings/domains` và ủy quyền OAuth kết nối sàn TMĐT/quảng cáo.
  - Số lượng gian hàng sàn TMĐT (Shopee/Lazada/TikTok Shop) và quyền dùng Haravan POS / Harasocial phụ thuộc vào gói dịch vụ (**Omnichannel / Pro / Grow / Scale**) — không tự bấm nâng cấp gói.
- **Pre-flight Check phiên đăng nhập & DNS:**
  1. Mở `https://{store_domain}/admin/settings/domains` (hoặc `/sale_channels`, `/marketing_channels`).
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để Owner tự đăng nhập; không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Ghi nhớ tên miền dự phòng gốc `https://{store_domain}` (`*.myharavan.com`) để luôn có đường vào khôi phục khẩn cấp nếu tên miền tùy chỉnh gặp sự cố SSL.
  4. Xác nhận trước với Owner đã trỏ bản ghi DNS `A` / `CNAME` và tạm tắt Proxy đám mây cam trên Cloudflare (nếu dùng) để Haravan có thể xác thực và cấp phát chứng chỉ SSL tự động.

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/domains` | `Tên miền chính` & Danh sách tên miền | `Kết nối tên miền hiện có`, `Thay đổi tên miền chính` (HARD-BLOCKED nếu chưa SSL), `Xóa` (HARD-BLOCKED) | Cột: Tên miền (`*.myharavan.com`, custom domain), `Trạng thái` (`Đã kết nối` / `Đang chờ DNS` / `SSL đang hoạt động`), tùy chọn chuyển hướng toàn bộ traffic về tên miền chính |
| `/admin/settings/sale_channels` | `Kênh bán hàng` | `Thêm kênh bán hàng`, `Cấu hình`, `Xóa kênh` (HARD-BLOCKED) | Website, Haravan POS (`https://pos.haravan.app`), Harasocial (`https://app.harasocial.com`), Shopee, Lazada, TikTok Shop, Tiki |
| `/admin/settings/marketing_channels` | `Kênh marketing` | `Kết nối`, `Cấu hình` | TikTok Ads (`/admin/marketings/tiktok_ads/products`), Google Ads / Google Shopping (`/admin/googleshop`), Meta Pixel / CAPI |
| `/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}` | Website (5 màn hình con) | **Cross-origin iframe `https://web.haravan.app`** (Sandbox ẩn DOM) | `Giao diện` → `@haravan/cli` (`haravan pull`/`deploy` staging); `Blogs` & `Trang nội dung` → Web API `/web/*`; `Menu` & `Cấu hình Website` → hướng dẫn người dùng tự thao tác trực tiếp |

> **Quy tắc định tuyến Iframe:** Bất kỳ yêu cầu nào liên quan đến chỉnh code Liquid, sửa Trang nội dung/Blog trên Website đều ưu tiên thực thi qua `skills/api-mcp/` thay vì cố tương tác trong iframe `https://web.haravan.app`.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền gốc Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `audit_domains_ssl` | `audit_domains_ssl` \| `connect_custom_domain` \| `sales_channels_ops` \| `marketing_channels_ops` \| `website_iframe_routing` |
| `custom_domain` | `string` | Khi `connect_custom_domain` | — | Tên miền hợp lệ không kèm `https://` (ví dụ `shop.thuonghieu.vn`); cần đã trỏ DNS `A`/`CNAME` |
| `change_primary_domain` | `boolean` | Khi `connect_custom_domain` | `false` | **Chỉ cho phép `true` khi `dns_verified = true` VÀ SSL đã xanh** |
| `channel_name` | `string` | Khi `sales_channels_ops` / `marketing_channels_ops` | — | `Shopee` \| `Lazada` \| `TikTok Shop` \| `Haravan POS` \| `Harasocial` \| `TikTok Ads` \| `Google Ads` |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true`; mọi thao tác ghi L3 bắt buộc `separate_turn: true` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Kiểm toán Tên miền, trạng thái SSL & DNS (`audit_domains_ssl` — Read-Only)
- **Điều kiện kích hoạt:** Trước khi ra mắt website mới, trước khi đổi tên miền chính hoặc khi khách hàng báo lỗi cảnh báo bảo mật HTTPS.
1. Điều hướng tới `https://{store_domain}/admin/settings/domains`.
2. Ghi nhận **Tên miền chính hiện tại**, trạng thái chứng chỉ **SSL** của từng tên miền và cờ chuyển hướng traffic về tên miền chính.
3. Rà soát 3 cảnh báo phổ biến:
   - Tên miền ở trạng thái `Đang chờ DNS` (sai bản ghi `A` / `CNAME` hoặc đang bật Cloudflare Proxy đám mây cam).
   - Chứng chỉ SSL chưa kích hoạt / bị kẹt do bản ghi `CAA` hoặc `AAAA` xung đột.
   - Trùng lặp `www.domain.vn` và `domain.vn` chưa bật chuyển hướng 301 về 1 tên miền chính duy nhất.
4. Báo cáo hiện trạng kèm hướng dẫn bản ghi DNS cần kiểm tra tại nhà cung cấp tên miền; không thực hiện thao tác ghi.

### Scenario 2: `Kết nối tên miền hiện có` & kiểm chuẩn `Thay đổi tên miền chính` (`connect_custom_domain`)
- **Điều kiện kích hoạt:** Gắn tên miền thương hiệu riêng (`thuonghieu.vn` / `shop.thuonghieu.vn`) vào cửa hàng Haravan.
1. Tại `/admin/settings/domains`, chụp ảnh hiện trạng (`pre_screenshot`) để lưu tên miền chính đang hoạt động.
2. Click nút `Kết nối tên miền hiện có`, nhập `custom_domain` (không kèm `https://`) vào ô nhập liệu nhưng **CHƯA bấm nút xác nhận kết nối**.
3. Nếu người dùng yêu cầu bấm `Thay đổi tên miền chính`:
   - Kiểm tra tên miền đích đã nằm trong danh sách ở trạng thái `Đã kết nối` **VÀ** có chứng chỉ `SSL` xanh chưa.
   - Nếu **chưa có SSL xanh** → **CHẶN NGAY LẬP TỨC**, giải thích rủi ro lỗi bảo mật trình duyệt (`NET::ERR_CERT_COMMON_NAME_INVALID`) làm sập website bán hàng.
4. **DỪNG — chưa bấm `Kết nối` / `Lưu`**, chuyển sang cổng duyệt L3 `separate_turn: true`.

### Scenario 3: Kiểm toán & hỗ trợ kết nối `Kênh bán hàng` (`sales_channels_ops`)
- **Điều kiện kích hoạt:** Kiểm tra đứt gãy đồng bộ đơn hàng/tồn kho sàn TMĐT hoặc mở rộng thêm gian hàng Shopee/Lazada/TikTok Shop.
1. Điều hướng tới `https://{store_domain}/admin/settings/sale_channels`.
2. Kiểm tra trạng thái từng kênh đang chạy: Website, Haravan POS (`pos.haravan.app`), Harasocial (`app.harasocial.com`), Shopee, Lazada, TikTok Shop, Tiki (cảnh báo ngay nếu thấy token ủy quyền sàn sắp/đã hết hạn làm dừng đồng bộ đơn).
3. Nếu cần thêm kênh mới hoặc gia hạn ủy quyền: click `Thêm kênh bán hàng` / `Cấu hình`, chọn đúng `channel_name` tới bước chuyển hướng OAuth sang Shopee Seller Center / TikTok Shop / Lazada.
4. **DỪNG NGAY LẬP TỨC (OAuth Handoff Gate):** Yêu cầu Chủ cửa hàng tự đăng nhập tài khoản sàn và bấm ủy quyền trực tiếp trên trình duyệt.

### Scenario 4: Kiểm toán & hỗ trợ kết nối `Kênh marketing` (`marketing_channels_ops`)
- **Điều kiện kích hoạt:** Kiểm tra đồng bộ sản phẩm lên Google Shopping / TikTok Ads hoặc kết nối mới tài khoản quảng cáo.
1. Điều hướng tới `https://{store_domain}/admin/settings/marketing_channels`.
2. Kiểm tra trạng thái đồng bộ Catalog Feed trên **TikTok Ads** (`/admin/marketings/tiktok_ads/products`) và **Google Ads / Google Shopping** (`/admin/googleshop`):
   - Ghi nhận số lượng sản phẩm `Đã duyệt` vs `Bị từ chối (Disapproved)` và lý do từ chối phổ biến (thiếu GTIN/MPN, thiếu chính sách đổi trả, sai giá).
   - Kiểm tra trạng thái kết nối Meta Pixel / Conversions API (CAPI) nếu có.
3. Nếu cần kết nối tài khoản quảng cáo mới, mở tới nút `Kết nối` rồi **DỪNG NGAY** để Owner tự đăng nhập Google Ads / TikTok Business Center qua OAuth trực tiếp trên trình duyệt.

### Scenario 5: Định tuyến xử lý Cross-Origin Iframe `https://web.haravan.app` (`website_iframe_routing`)
- **Điều kiện kích hoạt:** Người dùng yêu cầu sửa giao diện Liquid, chỉnh trang nội dung, đăng bài blog hoặc cập nhật thanh điều hướng Menu trên Website.
1. Khi gặp bất kỳ route nào trong 5 màn hình con của Website (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`), xác nhận đây là **cross-origin iframe `https://web.haravan.app`** bị trình duyệt sandbox ẩn DOM.
2. Tuyệt đối **không cố click mù** bên trong iframe; lập tức định tuyến sang công cụ chuẩn xác:
   - **Giao diện (`themes`):** Chuyển sang `haravan-cli-theme-ops` dùng `@haravan/cli` (`haravan pull` / `haravan deploy` trên **Staging Theme** — tuyệt đối cấm sửa hoặc `Publish` trực tiếp lên Live Theme).
   - **Trang nội dung (`pages`) & Blogs (`articles`):** Chuyển sang `web-pages-blogs-ops` gọi Haravan Web API (`/web/pages.json`, `/web/blogs.json`, `/web/redirects.json`).
   - **Menu (`menus`) & Cấu hình Website (`settings` / Theme Customizer):** Mở đúng tab trên trình duyệt và gửi hướng dẫn click từng bước rõ ràng để người dùng tự thao tác trực tiếp.
3. Ghi rõ kênh thực thi thay thế trong báo cáo để tránh lặp lại thao tác bị chặn iframe.

### Bảng đối chiếu nhanh Kênh thay thế cho 5 màn hình Iframe Website (`https://web.haravan.app`)
| Màn hình con trên Admin | Route | Trạng thái Iframe | Kênh thực thi được khuyến nghị |
| :--- | :--- | :--- | :--- |
| `Giao diện` | `/admin/sale_channels/online_store/themes` | Cross-origin (Ẩn DOM) | `@haravan/cli` (`haravan-cli-theme-ops`) trên Staging Theme |
| `Blogs` & `Trang nội dung` | `/admin/sale_channels/online_store/{articles,pages}` | Cross-origin (Ẩn DOM) | Haravan Web API (`/web/blogs.json`, `/web/pages.json`) |
| `Menu` & `Cấu hình Website` | `/admin/sale_channels/online_store/{menus,settings}` | Cross-origin (Ẩn DOM) | Hướng dẫn từng bước để người dùng tự thao tác trên tab mở |

## 5. Quy trình An toàn 4 Pha (L3 Critical — `separate_turn: true`)

### Pha 1: Pre-State Capture (Lưu Trạng Thái Tên Miền & Kênh Gốc)
- Mở `/admin/settings/domains` (hoặc `/sale_channels`, `/marketing_channels`), xác minh quyền Owner.
- Chụp ảnh toàn trang (`artifacts/domains_pre.png`), ghi rõ **Tên miền chính hiện tại**, trạng thái SSL và danh sách sàn/kênh đang kết nối.

### Pha 2: Stage Without Saving / OAuth Handoff
- Điền `custom_domain` vào form `Kết nối tên miền hiện có` (hoặc dừng ngay tại luồng đăng nhập OAuth Shopee/Lazada/TikTok/Google để Owner tự đăng nhập).
- Nếu yêu cầu `Thay đổi tên miền chính`, bắt buộc xác minh tên miền đích đã `Đã kết nối` + `SSL xanh`; nếu chưa → chặn ngay.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Kết nối` / `Thay đổi tên miền chính`**.

### Pha 3: Screenshot-Before-Save & Separate-Turn Gate (`separate_turn: true`)
- Chụp ảnh màn hình đã điền (`artifacts/domains_preview.png`).
- Gửi bảng `Before → After` (Mục 6) kèm đánh giá rủi ro downtime storefront và **dừng hoàn toàn chờ Owner xác nhận tường minh ở LƯỢT HỘI THOẠI TIẾP THEO**.

### Pha 4: Save & Post-Save Reload Verification
- Chỉ khi nhận được xác nhận ở lượt riêng, bấm xác nhận kết nối, chờ toast thành công và nhấn `F5` reload kiểm tra trạng thái `Đã kết nối` / cấp phát SSL.
- Mở kiểm tra nhanh HTTPS trên storefront (tab ẩn danh) để đảm bảo không lỗi chứng chỉ, chụp `artifacts/domains_post.png`.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/domains` — L3 Critical)

| Hạng mục | Trước (Before) | Đề xuất (After) | Kiểm chuẩn DNS / SSL & Rủi ro |
| :--- | :--- | :--- | :--- |
| Tên miền chính hiện tại | `myshop.myharavan.com` | Giữ nguyên (chưa đổi chính) | 0% rủi ro downtime storefront |
| Tên miền kết nối mới | *(Chưa có)* | `shop.thuonghieu.vn` | DNS `CNAME` đã trỏ; chờ cấp SSL xanh |
| Kênh bán hàng đang chạy | Website, POS, Shopee | Giữ nguyên, không gỡ kênh | Bảo toàn đồng bộ đơn hàng live |
| Website (`web.haravan.app`) | Yêu cầu sửa Theme/Page | Định tuyến sang `@haravan/cli` & Web API | Không click mù trong cross-origin iframe |

> **⚠️ L3 Critical (`separate_turn: true`) — Yêu cầu xác nhận ở lượt hội thoại riêng:** Đã điền sẵn tên miền `shop.thuonghieu.vn` tại `/admin/settings/domains` (chưa bấm kết nối, xem `preview_screenshot`). Vui lòng trả lời **"Xác nhận kết nối tên miền shop.thuonghieu.vn"** ở lượt tiếp theo để Agent thực thi.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-domains-channels-website",
  "scenario": "connect_custom_domain",
  "risk": "critical",
  "separate_turn_required": true,
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/domains",
  "phase_status": "awaiting_separate_turn_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/domains_pre.png",
    "preview_screenshot": "artifacts/domains_preview.png",
    "post_screenshot": "artifacts/domains_post.png"
  },
  "checks_passed": {
    "owner_session_verified": true,
    "dns_records_checked": true,
    "ssl_verified_before_primary_switch": false,
    "separate_turn_enforced": true
  },
  "changes_staged": {
    "custom_domain": "shop.thuonghieu.vn",
    "change_primary_domain": false
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Thay đổi tên miền chính` khi chưa có SSL xanh | **HARD-BLOCKED** | Gây lỗi bảo mật HTTPS và sập toàn bộ website bán hàng ngay lập tức |
| `Xóa` tên miền live hoặc `Xóa kênh` sàn TMĐT | **HARD-BLOCKED** | Mất mapping sản phẩm & đứt luồng đồng bộ đơn Shopee/Lazada/TikTok Shop |
| `Xuất bản (Publish)` lên Live Theme | **HARD-BLOCKED** | Cấm ghi đè trực tiếp Live Theme; luôn thao tác trên Staging Theme qua `@haravan/cli` |
| Luồng đăng nhập OAuth sàn TMĐT / Ads / `accounts.haravan.com` | **HANDOFF GATE** | Dừng ngay để Chủ cửa hàng tự đăng nhập và bấm ủy quyền trực tiếp trên trình duyệt |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Bị chặn tương tác DOM trong 5 màn hình Website (`https://web.haravan.app`):** Do chính sách bảo mật cross-origin iframe → Không cố click mù, chuyển ngay sang Scenario 5 (`@haravan/cli` / Web API `/web/*` / hướng dẫn tay).
2. **Lỗi *"DNS chưa được cấu hình đúng"* khi kết nối tên miền:** Chụp lại chính xác bản ghi `A` / `CNAME` Haravan hiển thị, nhắc tắt chế độ Proxy đám mây cam trên Cloudflare (chuyển sang *DNS Only* tạm thời) để Haravan cấp SSL, chờ 15–60 phút rồi thử lại.
3. **Kênh Shopee/TikTok Shop báo hết hạn ủy quyền:** Không bấm `Xóa kênh` (sẽ mất mapping sản phẩm); mở vào `Cấu hình` để Owner thực hiện gia hạn ủy quyền (Re-authorize) lại token OAuth.
4. **Staff không thấy mục `/admin/settings/domains`:** Quyền tên miền chỉ dành cho Chủ cửa hàng → Yêu cầu Owner đăng nhập thực hiện.
5. **Chứng chỉ SSL kẹt trạng thái *"Đang xử lý"* quá 24 giờ:** Kiểm tra xem tên miền có bản ghi `CAA` hoặc `AAAA` (IPv6) xung đột tại nhà cung cấp DNS không; đề xuất Owner rà soát DNS và liên hệ hỗ trợ kỹ thuật Haravan.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công (Khẩn cấp nếu đổi tên miền chính gặp lỗi SSL)
1. Truy cập ngay bằng tên miền gốc `https://{store_domain}/admin/settings/domains` (domain `*.myharavan.com` luôn truy cập được kể cả khi custom domain lỗi).
2. Đối chiếu `artifacts/domains_pre.png`, chọn lại tên miền chính cũ đang có SSL xanh và bấm xác nhận khôi phục.
3. Kiểm tra lại trang chủ storefront bằng cửa sổ ẩn danh để chắc chắn chứng chỉ HTTPS xanh trở lại.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Truy cập `https://{custom_domain}` trên tab ẩn danh: khóa SSL xanh, không cảnh báo bảo mật trình duyệt.
- [ ] Kiểm tra chuyển hướng `http://` → `https://` và `www` ↔ root domain hoạt động đúng 1 chiều (tránh trùng lặp SEO).
- [ ] Kiểm tra trạng thái đồng bộ đơn hàng/tồn kho trên các sàn TMĐT tại `/admin/settings/sale_channels` vẫn xanh.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `haravan-cli-theme-ops` (quản lý Theme Liquid trên Staging Theme bằng `@haravan/cli`) và `web-pages-blogs-ops` (quản lý Pages/Blogs/Redirects qua Web API `/web/*`).
- `skills/browser-ui/` → `admin-ui-session-navigator`, `admin-ui-general-policies-setup`.
