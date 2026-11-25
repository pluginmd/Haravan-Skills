---
name: admin-ui-session-navigator
description: "Quy chuẩn điều hướng Haravan Admin (*.myharavan.com/admin), xử lý đăng nhập/2FA, bản đồ 17 mục Cấu hình và luật Screenshot-Before-Save."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 95-admin-ui-browser
layer: L0
wave: 1
mode: reference
risk: low
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI https://accounts.haravan.com"
    - "UI /admin/dashboard/generals"
    - "UI /admin/settings"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 50
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

# Haravan Admin UI Session, Sitemap & Safe Browser Navigator

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Vai trò nền tảng (L0 Reference Skill):** Đây là skill điều hướng chuẩn, quy ước nhận diện trạng thái giao diện và giao thức an toàn gốc cho **toàn bộ 26 Browser UI Skills** vận hành trên **Haravan Admin (`https://{store_domain}/admin`)**. Mọi Browser Agent trước khi thao tác chuột/phím trên bất kỳ màn hình nào đều phải tuân thủ sitemap đã kiểm chứng trong `api/admin-ui-sitemap.yaml` và quy tắc an toàn trong `policies/browser-ui-safety.md`.
- **Mục tiêu nghiệp vụ:**
  1. Xác minh trạng thái phiên đăng nhập Haravan Admin mà **tuyệt đối không chạm tới mật khẩu/2FA/Passkey**.
  2. Điều hướng nhanh, chính xác tới đúng URL đích (12 nhóm Sidebar Navigation, 17 mục `/admin/settings`, phím tắt `Ctrl+K`, quản lý đa tab) và nhận diện chính xác toast/spinner/modal của Haravan Admin UI.
  3. Phân biệt rành mạch khi nào dùng **Browser UI (`skills/browser-ui/`)** vs **API/MCP (`skills/api-mcp/`)**, và xử lý ranh giới **cross-origin iframe `https://web.haravan.app`** cũng như ứng dụng ngoài (`Haravan POS`, `Harasocial`).
- **Quyền tài khoản (Owner vs Staff) & Gói dịch vụ:**
  - **Owner:** Thấy đủ 17/17 mục trong `/admin/settings` (bao gồm `Nhân viên`, `Vai trò`, `Billing`, `Phương thức thanh toán`, `Tên miền`).
  - **Staff:** Sidebar và `/admin/settings` chỉ hiển thị các mục được cấp trong `/admin/settings/group_permissions`. Nếu URL đích trả về trang trống hoặc thông báo `Không có quyền truy cập`, dừng và báo rõ hạng mục quyền bị thiếu.
  - **Gói dịch vụ (Standard / Pro / Grow / Scale):** Một số màn hình (Kho nâng cao, Dùng chung khuyến mãi, Báo cáo RFM, CRM Flow) có thể hiện banner yêu cầu nâng gói — chỉ ghi nhận, **tuyệt đối không bấm nút nâng cấp**.
- **Pre-flight Check bắt buộc:** Mở hoặc tái sử dụng tab `https://{store_domain}/admin/dashboard/generals`; kiểm tra subdomain trên thanh địa chỉ (`staging` vs `production`). Nếu URL chuyển hướng về `https://accounts.haravan.com` → **Dừng ngay lập tức** để người dùng tự đăng nhập trực tiếp trên trình duyệt.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, 12 Sidebar Groups & Ma trận 17 Mục Settings)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Live-Verified Architecture:** Haravan Admin (`*.myharavan.com/admin`) gồm 17 mục `/admin/settings` chạy Native DOM + 3 phân hệ chạy Cross-Origin Iframe (`web.haravan.app`, `customers.haravan.app`, `reports.haravan.app`). Xem chi tiết đầy đủ tại `api/admin-ui-sitemap.yaml`.


### A. Thanh điều hướng chính (Sidebar Navigation — 12 Nhóm Đã Kiểm Chứng)

| Route / URL | Nhóm Menu (Exact UI Label) | Các mục con đã kiểm chứng (Verified Children) | Ghi chú kỹ thuật & Skill liên kết |
| :--- | :--- | :--- | :--- |
| `/admin/dashboard/generals` | `Tổng quan` | Trang chủ Admin, thanh tìm nhanh `Ctrl+K` (`Tìm kiếm`) | Điểm kiểm tra phiên đăng nhập chuẩn |
| `/admin/orders` | `Đơn hàng` | `Tất cả đơn hàng` (`/admin/orders`), `Đơn hàng nháp` (`/admin/draft_orders`), `Chưa hoàn tất` (`/admin/orders/checkouts`), `Giao hàng hàng loạt` (`/admin/orders/mass_fulfill`) | Dùng `admin-ui-orders-daily-ops`, `draft-orders-quote-proposal` |
| `/admin/shipments/dashboard` | `Vận chuyển` | `Tổng quan`, `Vận chuyển` (`/shipments`), `Quản lý thu hộ` (`/managecod`), `Đóng gói` (`/packed`), `Biên bản bàn giao`, `Biên bản hoàn hàng` | Dùng `admin-ui-shipments-cod-mass-fulfill` |
| `/admin/products` | `Sản phẩm` | `Tất cả sản phẩm`, `Nhóm sản phẩm` (`/collections`), `Bảng giá` (`/pricing_list`), `Tồn kho` (`/inventories`) | Dùng `admin-ui-products-catalog-ops`, `admin-ui-inventory-advanced-ops` |
| `/admin/customers` | `Khách hàng` | `Tất cả khách hàng`, `Nhóm khách hàng` (`/segments`), `Broadcast` (`/broadcast_campaigns`), `Kịch bản tự động` (`/flows`), `Đánh giá` (`/rating`), `Thành viên` (`/settings`) | Dùng `admin-ui-customers-profile-ops`, `admin-ui-crm-flows-broadcast` |
| `/admin/accounting/transactions` | `Sổ quỹ` | `Sổ quỹ` (`/transactions`), `Công nợ` (`/debts`) | Read-Only (`finance-cashbook-debt-audit`) |
| `/admin/discounts` | `Khuyến mãi` | Mã giảm giá, Chương trình khuyến mãi, Mua X tặng Y | Dùng `admin-ui-discounts-promotions-ops` |
| `/admin/reports/dashboard` | `Báo cáo` | `Bảng phân tích` (`/dashboard`), `Danh sách báo cáo` (`/listing`) | Read-Only (`admin-ui-reports-analytics-export`) |
| `/admin/etax/declarations` | `Thuế & kế toán` | `Tờ khai thuế` (`/declarations`), `Sổ kế toán` (`/revenue_ledgers`) | Pháp lý thuế — CẤM tự nộp (`admin-ui-tax-einvoice-accounting`) |
| `/admin/settings/marketing_channels` | `Marketing` | `TikTok Ads` (`/admin/marketings/tiktok_ads/products`), `Google Ads` (`/admin/googleshop`) | Cần người dùng tự OAuth |
| `/admin/settings/sale_channels` | `Kênh bán hàng` | 5 mục `Website` (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) + External: `Haravan POS` (`pos.haravan.app`), `Harasocial` (`app.harasocial.com`) | ⚠️ 5 mục Website chạy trong **cross-origin iframe `https://web.haravan.app`** → dùng `admin-ui-website-theme-menu-assist` |
| `/admin/apps` | `Ứng dụng` | Danh sách ứng dụng đã cài đặt & Private Apps | Read-Only (`admin-ui-apps-addons-billing`) |

### B. Ma trận Đầy đủ 17 Mục Cấu Hình (`/admin/settings`)

| # | Route (`/admin/settings/...`) | Nhãn hiển thị (Exact UI Label) | Skill chuyên trách tương ứng | Tầng / Rủi ro |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `/admin/settings/general` | `Cấu hình chung` | `admin-ui-general-policies-setup` | L2 Medium |
| 2 | `/admin/settings/accounts` | `Nhân viên` | `admin-ui-staff-roles-config` | **L3 Critical** |
| 3 | `/admin/settings/group_permissions` | `Vai trò` | `admin-ui-staff-roles-config` | **L3 Critical** |
| 4 | `/admin/settings/group_accounts` | `Nhóm phân công` | `admin-ui-staff-roles-config` | **L3 Critical** |
| 5 | `/admin/settings/locations` | `Địa chỉ và kho hàng` | `admin-ui-locations-inventory-ops` | L2 Medium |
| 6 | `/admin/settings/shipments` | `Vận chuyển` | `admin-ui-shipping-carriers-setup` | L2 Medium |
| 7 | `/admin/settings/payments` | `Phương thức thanh toán` | `admin-ui-payment-methods-setup` | **L3 Critical** |
| 8 | `/admin/settings/checkouts` | `Thanh toán` | `admin-ui-checkout-settings` | L2 Medium |
| 9 | `/admin/settings/sale_channels` | `Kênh bán hàng` | `admin-ui-domains-channels-website` | **L3 Critical** |
| 10 | `/admin/settings/marketing_channels` | `Kênh marketing` | `admin-ui-domains-channels-website` | **L3 Critical** |
| 11 | `/admin/settings/files` | `Quản lý file` | `storefront-file-storage-audit` | L1 Low |
| 12 | `/admin/settings/notifications` | `Thông báo` | `admin-ui-notifications-print-webhooks` | L2 Medium |
| 13 | `/admin/settings/billings` | `Billing` | `admin-ui-apps-addons-billing` (Read-Only) | L1 Low (Hard-Blocked) |
| 14 | `/admin/settings/vat_setting` | `Thuế & hóa đơn điện tử` | `admin-ui-tax-einvoice-accounting` | L2 High |
| 15 | `/admin/settings/domains` | `Tên miền` | `admin-ui-domains-channels-website` | **L3 Critical** |
| 16 | `/admin/settings/order_addon` | `Tiện ích đơn hàng` | `admin-ui-apps-addons-billing` (Read-Only) | L1 Low |
| 17 | `/admin/settings/policies` | `Điều khoản & Chính sách` | `admin-ui-general-policies-setup` | L2 Medium |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`^[a-z0-9-]+\.myharavan\.com$`) |
| `target_path` | `string` | Không | `/admin/dashboard/generals` | Đường dẫn tương đối hợp lệ trong `api/admin-ui-sitemap.yaml` |
| `navigation_method` | `enum` | Không | `direct_url` | `direct_url` \| `ctrl_k_search` \| `sidebar_click` |
| `verify_settings_hub` | `boolean` | Không | `false` | Nếu `true`, mở `/admin/settings` để kiểm đếm số mục Cấu hình tài khoản hiện tại thấy được (Owner = 17/17) |
| `reuse_existing_tab` | `boolean` | Không | `true` | Tái sử dụng tab Haravan Admin đang mở để giữ phiên và tránh mở tràn tab |
| `route_decision_check` | `boolean` | Không | `true` | Kiểm tra xem tác vụ nên chạy `browser_ui` hay chuyển sang `api_mcp` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click & Ma trận Định tuyến)

### Kịch bản 1: Điều hướng trực tiếp & Kiểm tra Phiên Đăng nhập (`accounts.haravan.com` Gate)
1. Kiểm tra danh sách tab đang mở; nếu đã có tab `https://{store_domain}/admin/...` và `reuse_existing_tab: true`, chuyển tiêu điểm sang tab đó, ngược lại mở URL `https://{store_domain}{target_path}`.
2. Chờ tải hoàn tất (hết vòng xoay spinner/skeleton) và kiểm tra URL thực tế trên thanh địa chỉ:
   - Nếu URL chuyển hướng về `https://accounts.haravan.com` → **DỪNG NGAY**, không điền bất kỳ trường nào, báo người dùng tự đăng nhập (Email/Mật khẩu/Passkey/2FA/Google/Apple) trực tiếp trên cửa sổ trình duyệt.
   - Nếu URL giữ nguyên trong `https://{store_domain}/admin/...` → xác nhận phiên hợp lệ và kiểm tra đúng subdomain cửa hàng (`staging` vs `production`).
3. Chụp `pre_screenshot` xác nhận vị trí và quyền hiển thị.

### Kịch bản 2: Kỹ thuật Điều hướng Nhanh bằng Phím tắt `Ctrl+K` (Quick Search)
1. Từ bất kỳ màn hình nào trong Haravan Admin, nhấn tổ hợp phím `Ctrl+K` (hoặc click ô `Tìm kiếm` trên thanh topbar).
2. Khi modal tìm kiếm nhanh mở ra, gõ từ khóa ngắn gọn: mã đơn hàng (`#10482`), SKU sản phẩm, SĐT khách hàng (9 số cuối), hoặc tên màn hình cấu hình (`Phương thức thanh toán`, `Kho hàng`).
3. Chờ danh sách gợi ý phân nhóm (`Đơn hàng`, `Sản phẩm`, `Khách hàng`, `Cài đặt`) hiển thị đầy đủ; xác minh đúng dòng kết quả (tránh click nhầm mục đầu tiên khi kết quả còn đang tải) rồi nhấn `Enter` hoặc click mở.

### Kịch bản 3: Quản lý Đa Tab (Multi-Tab Discipline) khi Xử lý Hàng đợi
1. Khi làm việc với danh sách có bộ lọc phức tạp (`/admin/orders`, `/admin/products`, `/admin/customers`), giữ **Tab 1** làm tab danh sách chính (không điều hướng rời khỏi trang để tránh mất bộ lọc và vị trí phân trang).
2. Mở từng bản ghi chi tiết sang **Tab 2** (click giữa / `Ctrl+Click` / mở URL chi tiết ở tab phụ), thao tác và xác minh xong thì đóng Tab 2 hoặc tái sử dụng Tab 2 cho bản ghi kế tiếp.
3. Không mở quá 3–4 tab Admin đồng thời để tránh xung đột session/cache hoặc bấm nhầm giữa hai bản ghi tương tự.

### Kịch bản 4: Nhận diện Toast, Spinner & Modal chuẩn của Haravan Admin UI
1. **Spinner / Skeleton Loading:** Sau mỗi lần lọc bảng, chuyển trang hoặc bấm nút `Lưu`, phải chờ toàn bộ thanh progress/spinner biến mất và nút bấm hết trạng thái `disabled` trước khi đọc DOM hoặc chụp ảnh.
2. **Toast Notification (Góc trên/dưới màn hình):**
   - *Toast xanh lá* (`Cập nhật thành công`, `Lưu thành công`): xác nhận lệnh đã được server tiếp nhận, tiếp tục bước reload `F5` kiểm chứng.
   - *Toast đỏ / vàng* (`Lỗi hệ thống`, `SKU đã tồn tại`, `Không có quyền`): dừng ngay, chụp ảnh toàn bộ thông báo lỗi để báo người dùng.
3. **Modal xác nhận & Unsaved Changes Warning:** Nếu chuyển trang khi form chưa lưu, Haravan bật modal `Bạn có thay đổi chưa lưu` (`Rời khỏi` / `Ở lại`). Luôn đọc kỹ tiêu đề modal trước khi bấm — tuyệt đối không bấm xác nhận trên modal màu đỏ (`Xóa`, `Hủy đơn`, `Gỡ cài đặt`).

### Kịch bản 5: Ma trận Quyết định — Khi nào dùng Browser UI (`browser_ui`) vs API/MCP (`api_mcp`)

| Tiêu chí tác vụ | Dùng `skills/browser-ui/` (Không cần Token) | Dùng `skills/api-mcp/` (Cần `HARAVAN_ACCESS_TOKEN`) |
| :--- | :--- | :--- |
| Màn hình độc quyền chỉ có trên UI | 17 mục `/admin/settings`, Bảng giá B2B, Sổ quỹ/Công nợ, CRM Flows/Broadcast, Đánh giá, Menu Website, Kho nâng cao (PO/Điều chuyển/Kiểm kho) | Không có REST API đầy đủ — ưu tiên `browser_ui` |
| Xử lý hàng loạt lớn (> 50–100 bản ghi) | ❌ Chậm, dễ timeout UI | ✅ Dùng `api_mcp` qua `scripts/hrv_client.py` (tôn trọng rate limit 80/4 req/s) |
| Đọc báo cáo tổng hợp / đối soát nhanh | ✅ Khi người dùng không có API token (`admin-ui-reports-analytics-export`) | ✅ Khi cần tổng hợp đa nguồn tự động, xuất JSON/CSV sạch, chạy định kỳ |
| Sửa Theme Liquid / Pages / Blogs / Redirects | ⚠️ Bị chặn bởi cross-origin iframe `web.haravan.app` (chỉ Assisted-UI) | ✅ Dùng `@haravan/cli` (`haravan-cli-theme-ops`) và Web API (`/web/*`) |
| Hủy đơn / Hoàn tiền / Xuất kho hàng loạt | ❌ Hard-Blocked trên UI hàng ngày | ✅ Dùng L3 Critical API skills có dry-run & separate-turn confirmation |

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Protocol)

1. **Pha 1 — Pre-State Capture (Xác minh phiên & Môi trường):**
   - Mở màn hình đích (hoặc tái sử dụng tab Haravan Admin đang mở), đối chiếu chính xác `store_domain` (`staging` vs `production`).
   - Xác minh phiên đăng nhập không bị redirect sang `accounts.haravan.com`, kiểm tra quyền hiển thị và chụp `pre_screenshot`.
2. **Pha 2 — Stage Without Saving (`dry_run: true`):**
   - Ở skill L0 này chỉ điều hướng, xác nhận trạng thái iframe/quyền và định tuyến kênh thực thi (`browser_ui` vs `api_mcp`).
   - Khi bàn giao sang skill L2/L3 kế tiếp, điền form/cấu hình nhưng **dừng tuyệt đối trước nút `Lưu` / `Xác nhận` / `Áp dụng`**.
3. **Pha 3 — Screenshot-Before-Save Gate (Cổng xác nhận bắt buộc):**
   - Chụp `preview_screenshot` màn hình đích đã sẵn sàng (hoặc form đã điền sẵn), lập bảng đối chiếu `Before → After` và dừng chờ người dùng xác nhận.
   - Bắt buộc **xác nhận ở lượt hội thoại riêng (`separate_turn: true`)** với toàn bộ skill L3 (`payments`, `accounts`, `domains`) và L2 High-Risk (`inventory-advanced-ops`, `tax-einvoice-accounting`).
4. **Pha 4 — Save & Post-Save Reload Verification (Xác minh lưu bền vững):**
   - Sau khi người dùng duyệt (ở skill L2/L3), bấm `Lưu` 1 lần, chờ toast xanh và hết spinner, nhấn `F5` reload trang xác minh dữ liệu bền vững và chụp `post_screenshot`.
   - Với riêng L0 navigator, giữ nguyên tab đang mở để skill kế tiếp tái sử dụng (`saved_verified: false`).

### Quy Ước Nhận Diện Tín Hiệu UI Haravan Admin (UI Signal Matrix)

| Tín hiệu giao diện | Ý nghĩa kỹ thuật trên Haravan Admin | Hành động bắt buộc của Agent |
| :--- | :--- | :--- |
| URL bắt đầu bằng `accounts.haravan.com` | Chưa đăng nhập hoặc hết phiên (Session Expired) | **Dừng ngay**, mời người dùng tự đăng nhập, giữ nguyên tab |
| Vòng xoay Spinner / Skeleton / Nút `disabled` | Trang hoặc lệnh API nền đang tải | Chờ tải xong hoàn toàn trước khi đọc DOM hoặc click tiếp |
| Toast xanh lá (`Thành công`) | Server đã ghi nhận dữ liệu | Thực hiện `F5` reload trang để xác minh dữ liệu bền vững |
| Toast đỏ / vàng (`Lỗi`, `Không có quyền`) | Lỗi validation, thiếu quyền Staff hoặc trùng khóa | Dừng ngay, chụp ảnh toàn bộ thông báo lỗi và báo người dùng |
| Khung nhúng `https://web.haravan.app` | Cross-origin iframe bảo mật của 5 mục Website | Không click mù; chuyển sang `admin-ui-website-theme-menu-assist` hoặc Web API/CLI |

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Trạng thái Điều hướng & Định tuyến Haravan Admin

| Thông số kiểm tra | Trạng thái trước (Before) | Kết quả xác minh (After Navigation) | Đánh giá |
| :--- | :--- | :--- | :--- |
| Tên miền & Môi trường | Chưa mở tab | `myshop.myharavan.com` (Production) | ✅ Đúng cửa hàng |
| Phiên đăng nhập | Chưa xác minh | Đã đăng nhập hợp lệ (không redirect `accounts.haravan.com`) | ✅ Sẵn sàng |
| Đường dẫn & Quyền | `/admin/dashboard/generals` | `/admin/settings` (hiển thị đủ `17/17` mục) | ✅ Quyền Owner |
| Kênh thực thi & Iframe | Chưa định tuyến | Không nằm trong iframe `web.haravan.app` → Dùng `browser_ui` | ✅ Hợp lệ |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-session-navigator",
  "mode": "reference",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings",
  "navigation_method": "direct_url",
  "session_authenticated": true,
  "settings_items_visible": 17,
  "is_cross_origin_iframe": false,
  "recommended_channel": "browser_ui",
  "active_tabs_count": 1,
  "pre_screenshot": "artifacts/navigator_session_check.png",
  "preview_screenshot": "artifacts/navigator_target_ready.png",
  "post_screenshot": null,
  "changes_staged": null,
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Zero Credential Handling:** Tuyệt đối không hỏi mật khẩu/OTP qua chat và tuyệt đối không tự nhập email/mật khẩu/2FA/Passkey tại `https://accounts.haravan.com`.
- **Các nút TUYỆT ĐỐI CẤM tự bấm trên toàn Haravan Admin:**
  - `Xóa` / `Xóa vĩnh viễn` (sản phẩm, đơn hàng, khách hàng, nhân viên, kho, tên miền, khuyến mãi, phương thức thanh toán).
  - `Chọn làm chủ sở hữu`, `Chấm dứt các phiên đăng nhập` (`/admin/settings/accounts`).
  - `Thay đổi tên miền chính` (`/admin/settings/domains`) khi chưa xác minh DNS/SSL.
  - `Xuất bản (Publish)` giao diện lên Live Theme (`/admin/sale_channels/online_store/themes`).
  - `Nâng cấp gói`, `Nâng cấp gói scale`, `Mua thêm`, `Thanh toán` (`/admin/settings/billings` và mọi banner nâng gói).
  - `Nộp tờ khai` tại `/admin/etax/declarations`.

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Phiên hết hạn giữa chừng (Mid-Session Expiry):** Bất kỳ click/chuyển trang nào bị đẩy về `https://accounts.haravan.com/Account/Login` → dừng lập tức, bảo toàn ngữ cảnh đang dở và yêu cầu người dùng tự đăng nhập lại trên chính tab đó.
2. **Tài khoản quản lý nhiều cửa hàng (`*.myharavan.com`):** Luôn đối chiếu chính xác subdomain trên thanh URL trước khi thao tác để tránh chỉnh nhầm từ cửa hàng `dev/staging` sang `production` (hoặc ngược lại).
3. **Popup bảo trì / Banner giới thiệu tính năng mới / Nút chat hỗ trợ che nút `Lưu`:** Đóng popup bằng nút `X`/`Đóng` hoặc cuộn trang để lộ rõ nút thao tác; không bấm vào các nút quảng cáo nâng cấp gói.
4. **Cross-origin iframe `https://web.haravan.app` & External Apps (`pos.haravan.app`, `app.harasocial.com`):** Không cố click mù bên trong khung iframe bị ẩn DOM; định tuyến ngay sang `admin-ui-website-theme-menu-assist` hoặc `skills/api-mcp/` tương ứng.
5. **Toast lỗi `429` hoặc bảng tải treo vô hạn:** Chờ 3–5 giây rồi tải lại nhẹ 1 lần; không spam click liên tục nút `Lưu` (tránh tạo trùng đơn hàng/phiếu kho).

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Rollback thủ công:** Không áp dụng (skill `L0 mode: reference`, chỉ kiểm tra phiên, quyền và điều hướng — không ghi dữ liệu).
- **Liên kết chéo với `skills/api-mcp/` & Tài liệu nền tảng:**
  - Tài liệu chuẩn hóa cốt lõi: `api/admin-ui-sitemap.yaml` và `policies/browser-ui-safety.md`.
  - Khi chuyển kênh sang REST API / MCP (có `HARAVAN_ACCESS_TOKEN`): `skills/api-mcp/00-core-platform/haravan-api-core`, `haravan-auth-setup`, `haravan-cli-theme-ops`.
  - Kế thừa trực tiếp bởi toàn bộ 25 Browser UI Skills chuyên trách còn lại trong `skills/browser-ui/`.
