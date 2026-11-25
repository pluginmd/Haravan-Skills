# Policy: Haravan Admin Agentic Browsing Safety (`skills/browser-ui/`)

Tài liệu này quy định luật bắt buộc cho mọi **AI Browser Agent (Agentic Browsing)** — bao gồm **Antigravity Internal Browser**, **ChatGPT Internal Browser / Operator**, **Claude in Chrome Extension / Computer Use**, và các trình duyệt AI tự động — khi điều khiển con trỏ chuột, điền form và click nút trực tiếp trên giao diện quản trị **Haravan Admin (`*.myharavan.com/admin`)**.

---

## 1. Xác thực & Phiên đăng nhập (Zero Credential Handling)
- **Tuyệt đối không** yêu cầu người dùng gửi mật khẩu/OTP qua chat và **không** tự nhập email/mật khẩu/2FA/Passkey vào `https://accounts.haravan.com`.
- Khi gặp màn hình đăng nhập hoặc hết phiên (session expired), Agent phải **dừng lại ngay**, báo cho người dùng tự đăng nhập trực tiếp trên trình duyệt internal, sau đó tiếp tục ngay trên tab hiện tại.

## 2. Cơ chế Screenshot-Before-Save (Tương đương `dry_run: true`)
Mọi thao tác cấu hình trên Haravan Admin UI (`L2` & `L3`) bắt buộc tuân theo quy trình 4 bước:
1. **Pre-State Capture:** Mở màn hình mục tiêu, đọc và chụp lại trạng thái cấu hình hiện có trước khi sửa (để làm căn cứ rollback thủ công).
2. **Stage Without Saving:** Điền form / chọn radio / bật-tắt switch theo yêu cầu nhưng **CHƯA bấm nút `Lưu` / `Xác nhận` / `Thêm` / `Kết nối`**.
3. **Human Confirmation Gate:** Chụp ảnh màn hình trạng thái đã điền sẵn + tóm tắt bảng thay đổi (Before → After) và dừng chờ người dùng duyệt.
   - Với **L3 Critical UI** (`admin-ui-payment-methods-setup`, `admin-ui-staff-roles-config`, `admin-ui-domains-channels-website`): **bắt buộc xác nhận ở lượt hội thoại riêng (`separate_turn: true`)**.
4. **Apply & Post-Save Verification:** Sau khi người dùng xác nhận, bấm nút `Lưu`, chờ toast thông báo thành công, reload lại trang để xác minh dữ liệu đã được lưu bền vững.

## 3. Các nút bấm CẤM tự ý click (Hard-Blocked UI Actions)
- `Xóa` / `Xóa vĩnh viễn` (sản phẩm, đơn hàng, nhân viên, kho, tên miền, phương thức thanh toán).
- `Chọn làm chủ sở hữu` hoặc `Chấm dứt các phiên đăng nhập` tại `/admin/settings/accounts`.
- `Thay đổi tên miền chính` tại `/admin/settings/domains` khi chưa xác minh DNS/SSL.
- `Xuất bản (Publish)` giao diện lên Live Theme.
- `Nâng cấp gói` / `Mua thêm` / bất kỳ nút nào phát sinh thanh toán dịch vụ Haravan (`/admin/settings/billings`).

## 4. Giới hạn Cross-Origin Iframe (`https://web.haravan.app`)
- Qua kiểm chứng thực tế trên Haravan Admin, 5 màn hình con dưới **Kênh bán hàng > Website** (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) được nhúng qua **cross-origin iframe** `https://web.haravan.app`.
- Trình duyệt sandbox bảo mật sẽ ẩn nội dung bên trong cross-origin iframe. Do đó:
  - Với **Themes / Liquid / Assets**: dùng `@haravan/cli` (`haravan-cli-theme-ops`) hoặc Web API (`/web/themes.json`).
  - Với **Pages / Blogs / Articles / Redirects / Script Tags**: dùng Haravan Web API (`/web/*`).
  - Với **Menu** và **Theme Customizer** trong iframe: Agent cung cấp hướng dẫn từng bước để người dùng thao tác trực tiếp trên tab đang mở.
