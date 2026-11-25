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

## 4. Kiến trúc Cross-Origin Micro-Frontend Iframes trên Haravan Admin (`*.haravan.app`)
Qua kiểm chứng trực tiếp trên Haravan Admin sống, có **3 phân hệ lớn** được nhúng qua **cross-origin `<iframe>`**:
1. **Website** (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) → `https://web.haravan.app`
2. **Khách hàng / CRM** (`/admin/customers`, `/segments`, `/broadcast_campaigns`, `/flows`, `/rating`, `/settings`) → `https://customers.haravan.app`
3. **Báo cáo** (`/admin/reports/dashboard`, `/admin/reports/listing`) → `https://reports.haravan.app`

**Quy tắc xử lý thông minh cho từng loại AI Browser:**
- **Trên Sandbox AI Browser (như Antigravity `/browser`):** Trình duyệt bảo mật sẽ tự ẩn (`redacted`) nội dung bên trong cross-origin iframe. Khi gặp iframe bị ẩn, Agent **không cố click mù**, mà tự động chuyển sang **`skills/api-mcp/`** (`/web/*`, `@haravan/cli`, `/com/customers.json`, `/com/orders.json`) hoặc hướng dẫn người dùng thao tác trực tiếp trên tab đang mở.
- **Trên Extension / Desktop Browser (như Claude in Chrome Extension, ChatGPT Operator khi được cấp quyền origin `*.haravan.app`):** Agent có thể tương tác trực tiếp trong iframe nhưng vẫn bắt buộc tuân thủ **Screenshot-Before-Save** và không xuất PII thô.

## 5. Quy tắc Semantic Matching & Empty-State Detection
- **Empty State Onboarding View:** Các màn hình chưa phát sinh dữ liệu (`mass_fulfill`, `draft_orders`, `managecod`, `shipment_handovers`, `shipment_returns`, `pricing_list`, `discounts`, `etax/declarations`, `settings/files`) sẽ hiển thị màn hình khởi tạo với 1–2 nút CTA (ví dụ `Bắt đầu thiết lập`, `Tạo đơn`, `Tạo biên bản`, `Tạo bảng giá`, `Tạo khuyến mãi`, `Kích hoạt`) thay vì thanh bộ lọc/bảng. Agent phải kiểm tra có đang ở Empty State hay không trước khi tìm bảng dữ liệu.
- **Semantic Fallback khi Haravan cập nhật giao diện:** Luôn ưu tiên khớp chính xác nhãn tiếng Việt trong `api/admin-ui-sitemap.yaml` (`live_dom_verified_controls`). Nếu Haravan đổi câu chữ 1–2 từ, Agent đọc Accessibility Tree + Screenshot tại đúng Route URL để khớp theo ngữ nghĩa, ghi chú sự khác biệt trong báo cáo preview và **chưa bấm Lưu** cho tới khi người dùng xác nhận.
