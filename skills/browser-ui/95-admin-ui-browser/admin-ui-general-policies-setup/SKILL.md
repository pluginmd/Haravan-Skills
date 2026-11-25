---
name: admin-ui-general-policies-setup
description: "Cấu hình thông tin cửa hàng, logo, tiêu chuẩn định dạng (/admin/settings/general) và Điều khoản & Chính sách (/admin/settings/policies) trên trình duyệt."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 95-admin-ui-browser
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/settings/general"
    - "UI /admin/settings/policies"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 20
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

# Haravan Admin UI: General Settings & Store Policies Setup

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Toàn bộ cấu hình nhận diện thương hiệu, thông tin liên hệ, địa chỉ trụ sở kinh doanh, tiêu chuẩn định dạng tiền tệ/múi giờ/mã đơn hàng (`/admin/settings/general`) và bộ văn bản pháp lý **Điều khoản & Chính sách** (`/admin/settings/policies`) chỉ thao tác được trên Haravan Admin UI — Haravan REST API (`/com/shop.json`) chỉ hỗ trợ đọc (Read-Only), không cho phép ghi đè.
- **Mục tiêu nghiệp vụ:**
  - Chuẩn hóa bộ nhận diện thương hiệu và thông tin liên hệ đồng bộ trên Website, trang Checkout, 13 mẫu Email giao dịch và các mẫu in phiếu đơn hàng/vận đơn.
  - Hoàn thiện bộ văn bản pháp lý TMĐT chuẩn Việt Nam (Nghị định 52/2013/NĐ-CP & Nghị định 85/2021/NĐ-CP) phục vụ đăng ký **Bộ Công Thương** và duyệt **Google Merchant Center (GMC)**.
- **Phân quyền Owner vs Staff:**
  - **Owner (Chủ cửa hàng):** Toàn quyền chỉnh sửa mọi section tại `/admin/settings/general` và `/admin/settings/policies`.
  - **Staff (Nhân viên):** Cần được cấp quyền **Cấu hình > Cấu hình chung** và **Điều khoản & Chính sách** tại `/admin/settings/group_permissions`. Một số thiết lập cấp hệ thống (đổi đơn vị tiền tệ gốc, nâng cấp gói) bị khóa hoàn toàn với Staff.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Các gói **Standard / Pro** có thể hiển thị nhãn khóa hoặc banner `Nâng cấp gói scale` tại một số tính năng nâng cao trong section `Bán hàng`, `Quản lý sản phẩm` hoặc `Xử lý đơn hàng` (ví dụ quản lý đa bảng giá, tự động hóa luồng đơn nâng cao). Agent tuyệt đối không bấm vào các banner/nút nâng cấp gói.
- **Pre-flight Check phiên đăng nhập & Môi trường:**
  1. Mở `https://{store_domain}/admin/settings/general`.
  2. Nếu bị chuyển hướng sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Xác nhận cửa hàng đúng môi trường (`staging` vs `production`) và kiểm tra góc trên bên phải xem tên cửa hàng, tài khoản đang đăng nhập có đúng quyền Owner/Staff được cấp phép hay không.
  4. Kiểm tra xem cửa hàng đã phát sinh đơn hàng live chưa (nếu đã có đơn, khóa cứng trường `Đơn vị tiền tệ` không được chỉnh sửa).
  5. Chuẩn bị sẵn thư mục lưu trữ `artifacts/` (ảnh chụp Pre/Preview/Post) và `scratch/` (file backup văn bản chính sách cũ).

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/settings/general` (Sections: `Thông tin cửa hàng`, `Nhận dạng thương hiệu` [`Chọn logo`], `Địa chỉ cửa hàng`, `Tiêu chuẩn & Định dạng`, `Bán hàng`, `Quản lý sản phẩm`, `Xử lý đơn hàng`, nút `Lưu`); `/admin/settings/policies` (Switch `Yêu cầu xác nhận Điều khoản và Chính sách`; 3 link: `Điều khoản và quy định dịch vụ`, `Chính sách bảo mật và quyền riêng tư`, `Chính sách đổi trả`).


| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/general` | `Thông tin cửa hàng` | Input text, nút `Lưu` (góc trên & dưới phải) | `Tên cửa hàng`, `Email liên hệ` (nhận thông báo từ Haravan), `Email chăm sóc khách hàng` (hiển thị cho khách), `Số điện thoại` |
| `/admin/settings/general` | `Nhận dạng thương hiệu` | `Chọn logo`, `Xóa` (CẤM tự bấm) | Ảnh logo thương hiệu (PNG/JPG nền trong suốt) dùng cho Admin, trang Checkout và tiêu đề mẫu Email |
| `/admin/settings/general` | `Địa chỉ cửa hàng` | Dropdown Quốc gia / Tỉnh-Thành / Quận-Huyện | `Tên công ty / Hộ kinh doanh`, `Địa chỉ`, `Quốc gia` (`Việt Nam`), `Tỉnh/Thành phố`, `Quận/Huyện`, `Mã bưu điện` |
| `/admin/settings/general` | `Tiêu chuẩn & Định dạng` | Dropdown, Input `Tiền tố` / `Hậu tố` | `Múi giờ` (`(GMT+07:00) Bangkok, Hanoi, Jakarta`), `Đơn vị khối lượng` (`g`/`kg`), `Đơn vị tiền tệ` (`VND` — KHÔNG đổi sau khi có đơn), `Tiền tố` & `Hậu tố` mã đơn hàng |
| `/admin/settings/general` | `Bán hàng`, `Quản lý sản phẩm`, `Xử lý đơn hàng` | Toggle Switch / Checkbox, banner `Nâng cấp gói scale` (HARD-BLOCKED) | Tùy chọn tự động lưu trữ đơn, quy tắc trừ tồn kho, cài đặt hiển thị SKU/Barcode và luồng bán hàng chung |
| `/admin/settings/policies` | `Điều khoản & Chính sách` | Rich-Text Editor, `Tạo từ mẫu` (nếu có), `Lưu` | 3 khung soạn thảo độc lập: `Chính sách đổi trả`, `Chính sách bảo mật`, `Điều khoản dịch vụ` (tự động gắn link ở chân trang Checkout) |

> **Lưu ý hành vi UI:** Nút `Lưu` tại `/admin/settings/general` chỉ kích hoạt (sáng xanh) sau khi có ít nhất một trường dữ liệu thay đổi. Khi rời trang mà chưa bấm `Lưu`, trình duyệt có thể hiện hộp thoại cảnh báo mất dữ liệu chưa lưu.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Đúng định dạng `*.myharavan.com` (không kèm `https://` hoặc dấu `/` cuối) |
| `scenario` | `string` | Có | `store_profile_update` | `store_profile_update` \| `brand_logo_update` \| `standards_order_id` \| `ops_toggles_review` \| `legal_policies_setup` |
| `store_profile` | `object` | Khi `store_profile_update` | `{}` | `{store_name, contact_email, cs_email, phone, company_name, address, province, district, postal_code}`; email chuẩn RFC, SĐT 10–11 số VN |
| `logo_file_path` | `string` | Khi `brand_logo_update` | — | Đường dẫn file ảnh `.png`/`.jpg` đã tối ưu `< 500KB`, tỷ lệ ngang gọn |
| `order_id_format` | `object` | Khi `standards_order_id` | `{}` | `{prefix: string (<= 6 ký tự), suffix: string (<= 6 ký tự), weight_unit: "g"\|"kg"}`; không chứa ký tự đặc biệt `/ \ ? #` |
| `ops_toggles` | `object` | Khi `ops_toggles_review` | `{}` | Map `{toggle_label: boolean}`; chỉ áp dụng các tùy chọn thuộc gói hiện tại |
| `policies_content` | `object` | Khi `legal_policies_setup` | `{}` | `{return_policy_html, privacy_policy_html, terms_of_service_html}`; bắt buộc khớp hotline/email tại `/admin/settings/general` |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi qua cổng xác nhận Screenshot-Before-Save |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Chuẩn hóa Thông tin cửa hàng & Địa chỉ trụ sở (`/admin/settings/general`)
1. Điều hướng tới `https://{store_domain}/admin/settings/general`, cuộn tới section `Thông tin cửa hàng`.
2. Đọc và ghi lại toàn bộ giá trị cũ của `Tên cửa hàng`, `Email liên hệ`, `Email chăm sóc khách hàng`, `Số điện thoại`.
3. Xóa trắng và nhập giá trị mới từ `store_profile` (lưu ý: phân biệt rõ `Email liên hệ` nội bộ và `Email chăm sóc khách hàng` công khai để tránh lộ email quản trị).
4. Cuộn xuống section `Địa chỉ cửa hàng`: nhập `Tên công ty / Hộ kinh doanh` (khớp giấy phép ĐKKD/MST), chọn `Quốc gia = Việt Nam`, chọn đúng `Tỉnh/Thành phố` và `Quận/Huyện`, nhập `Địa chỉ` chi tiết và `Mã bưu điện`.
5. **DỪNG — chưa bấm `Lưu`**, chuyển sang chụp ảnh preview.

### Scenario 2: Cập nhật Nhận dạng thương hiệu / Logo cửa hàng
1. Tại `/admin/settings/general`, cuộn tới section `Nhận dạng thương hiệu`.
2. Kiểm tra xem cửa hàng đã có logo hiện hành chưa; chụp lại ảnh logo cũ để dự phòng rollback.
3. Click nút `Chọn logo` (tuyệt đối **không bấm `Xóa`** logo cũ trước khi file mới sẵn sàng).
4. Tải lên file logo mới từ `logo_file_path` (ưu tiên PNG nền trong suốt, chiều rộng 300–600px, dung lượng `< 500KB`), kiểm tra khung xem trước không bị cắt mép hoặc vỡ nét.
5. **DỪNG — chưa bấm `Lưu`**, chụp ảnh preview khung logo gửi người dùng duyệt.

### Scenario 3: Thiết lập Tiêu chuẩn & Định dạng (Múi giờ, Khối lượng, Tiền tố mã đơn)
1. Cuộn tới section `Tiêu chuẩn & Định dạng` trên `/admin/settings/general`.
2. Kiểm tra dropdown `Múi giờ`: đảm bảo đúng `(GMT+07:00) Bangkok, Hanoi, Jakarta` để báo cáo doanh thu theo ngày và giờ hẹn khuyến mãi không bị lệch múi giờ.
3. Kiểm tra `Đơn vị khối lượng`: chọn `g` (khuyến nghị cho thời trang/mỹ phẩm/phụ kiện VN) hoặc `kg` (điện máy/nội thất) — phải đồng nhất với biểu phí vận chuyển theo khối lượng tại `/admin/settings/shipments`.
4. Kiểm tra `Đơn vị tiền tệ`: giữ nguyên `VND` (**TUYỆT ĐỐI KHÔNG ĐỔI** nếu store đã phát sinh đơn hàng).
5. Tại ô `Tiền tố` và `Hậu tố` mã đơn hàng: nhập theo `order_id_format` (ví dụ `Tiền tố = "ABC-"` → mã đơn mới sẽ có dạng `ABC-1001`), kiểm tra dòng ví dụ hiển thị ngay dưới ô nhập.
6. **DỪNG — chưa bấm `Lưu`**.

### Scenario 4: Rà soát cấu hình Bán hàng, Quản lý sản phẩm & Xử lý đơn hàng
1. Cuộn xuống phần cuối trang `/admin/settings/general` gồm 3 block: `Bán hàng`, `Quản lý sản phẩm`, `Xử lý đơn hàng`.
2. Đọc trạng thái từng Toggle Switch / Checkbox hiện có; ghi chú rõ mục nào đang bị khóa theo gói dịch vụ (có biểu tượng khóa hoặc banner `Nâng cấp gói scale`).
3. Chỉ bật/tắt đúng các switch được yêu cầu trong `ops_toggles` (ví dụ quy tắc giữ tồn kho, cài đặt quản lý đơn hàng chung), bỏ qua mọi lời mời nâng cấp gói.
4. **DỪNG — chưa bấm `Lưu`**, chụp ảnh đầy đủ các switch đã thay đổi.

### Scenario 5: Soạn thảo & Đồng bộ Bộ Điều khoản & Chính sách (`/admin/settings/policies`)
1. Điều hướng tới `https://{store_domain}/admin/settings/policies`.
2. Sao lưu toàn bộ nội dung hiện có của cả 3 khung (`Chính sách đổi trả`, `Chính sách bảo mật`, `Điều khoản dịch vụ`) vào artifact backup trước khi sửa.
3. Nếu cửa hàng mới trắng hoàn toàn và người dùng muốn dùng khung chuẩn nhanh, có thể tham khảo nút `Tạo từ mẫu` rồi tùy biến lại toàn bộ biến giữ chỗ (`[Tên công ty]`, `[Số điện thoại]`, `[Email]`).
4. Dán nội dung HTML/text chuẩn hóa từ `policies_content` vào từng Rich-Text Editor tương ứng; rà soát đảm bảo:
   - `Chính sách đổi trả` ghi rõ thời hạn đổi trả (ví dụ 7 ngày), điều kiện nguyên tem mác, thời gian hoàn tiền (3–7 ngày làm việc) — bắt buộc để không bị Google Merchant Center gắn lỗi *Misrepresentation*.
   - `Chính sách bảo mật` nêu rõ phạm vi thu thập, lưu trữ, bảo mật dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP.
   - `Điều khoản dịch vụ` khớp 100% tên doanh nghiệp, địa chỉ, hotline và email CSKH tại `/admin/settings/general`.
5. **DỪNG — chưa bấm `Lưu`**, chuyển sang cổng duyệt Screenshot-Before-Save.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser Safety Protocol)

### Pha 1: Pre-State Capture (Chụp & Sao lưu Trạng thái Gốc)
- Mở `/admin/settings/general` và/hoặc `/admin/settings/policies`, xác minh phiên đăng nhập hợp lệ (không redirect sang `accounts.haravan.com`).
- Chụp ảnh toàn trang trạng thái gốc (`artifacts/general_policies_pre.png`).
- Nếu chỉnh `/admin/settings/policies`, copy toàn bộ nội dung HTML/text gốc của 3 khung chính sách lưu vào `scratch/backup_policies.md` trước khi sửa bất kỳ ký tự nào.

### Pha 2: Stage Without Saving (Điền Form Chưa Bấm Lưu)
- Thực hiện điền form, chọn dropdown, tải ảnh logo xem trước, gạt switch hoặc dán văn bản chính sách theo đúng Scenario ở Mục 4.
- Kiểm tra chéo hotline, email CSKH, tên doanh nghiệp giữa `/general` và `/policies` đảm bảo khớp 100%.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu`**.

### Pha 3: Screenshot-Before-Save & Human Approval Gate
- Chụp ảnh toàn bộ vùng đã chỉnh sửa (`artifacts/general_policies_preview.png`) khi nút `Lưu` đang sáng xanh.
- Trình bày bảng so sánh `Before → After` (Mục 6) nêu rõ từng trường thay đổi và các mục giữ nguyên (như `Đơn vị tiền tệ = VND`).
- Dừng hoàn toàn và chờ người dùng xác nhận tường minh (L2: `confirmation_required: true`).

### Pha 4: Save & Post-Save Reload Verification
- Chỉ sau khi nhận được xác nhận từ người dùng, click nút `Lưu` trên từng trang tương ứng.
- Chờ toast thông báo *"Cập nhật thành công"* xuất hiện (không đóng tab khi spinner đang xoay).
- Nhấn reload trang (`F5`), kiểm tra lại toàn bộ trường thông tin và nội dung chính sách đã được lưu bền vững, chụp ảnh xác minh (`artifacts/general_policies_post.png`).

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/general` & `/policies`)

| Route / Section | Trường cấu hình | Trước (Before) | Đề xuất (After) | Kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `/general` → `Thông tin cửa hàng` | `Tên cửa hàng` | `Test Store 01` | `Thương Hiệu ABC Official` | Đồng bộ Email & Checkout |
| `/general` → `Thông tin cửa hàng` | `Email CSKH` / `Hotline` | *(Trống)* | `cskh@abc.vn` / `1900 1234` | Khớp Footer & Chính sách |
| `/general` → `Địa chỉ cửa hàng` | Công ty & Địa chỉ | `Chưa điền` | `Công ty TNHH ABC — Q.7, TP.HCM` | Khớp giấy phép ĐKKD |
| `/general` → `Tiêu chuẩn & Định dạng` | `Tiền tố mã đơn` / `Múi giờ` | *(Trống)* / `GMT+07` | `ABC-` / Giữ nguyên `GMT+07` | Không đổi `VND` |
| `/policies` → `Chính sách đổi trả` | Nội dung pháp lý | *(Trống)* | Đầy đủ 5 mục (Đổi trả 7 ngày, hoàn tiền) | Đạt chuẩn BCT & GMC |

> **Yêu cầu xác nhận:** Các thay đổi tại `/admin/settings/general` và `/admin/settings/policies` đã được điền sẵn trên trình duyệt (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng xác nhận **"Đồng ý lưu cấu hình chung & chính sách"** để Agent bấm nút `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-general-policies-setup",
  "scenario": "store_profile_update",
  "store_domain": "myshop.myharavan.com",
  "routes_visited": ["/admin/settings/general", "/admin/settings/policies"],
  "phase_status": "awaiting_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/general_policies_pre.png",
    "preview_screenshot": "artifacts/general_policies_preview.png",
    "post_screenshot": "artifacts/general_policies_post.png",
    "policies_backup_path": "scratch/backup_policies.md"
  },
  "checks_passed": {
    "currency_untouched": true,
    "timezone_gmt07_verified": true,
    "hotline_email_consistent": true,
    "bct_gmc_sections_complete": true
  },
  "changes_staged": {
    "general_fields": ["store_name", "cs_email", "phone", "address", "order_prefix"],
    "policies_updated": ["return_policy", "privacy_policy", "terms_of_service"]
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Nâng cấp gói scale` / `Nâng cấp gói` / `Mua thêm` | **HARD-BLOCKED** | Phát sinh thanh toán dịch vụ tại `/admin/settings/billings`; chỉ ghi nhận giới hạn gói cho Owner tự quyết định |
| Đổi `Đơn vị tiền tệ` (`VND` → khác) | **HARD-BLOCKED** | Làm lệch toàn bộ báo cáo tài chính, lịch sử đơn hàng và đối soát thuế sau khi đã có đơn |
| Nút `Xóa` tại `Nhận dạng thương hiệu` | **HARD-BLOCKED** | Gây mất logo trên Checkout & Email; chỉ thay thế bằng `Chọn logo` khi file mới đã sẵn sàng |
| Trang đăng nhập `accounts.haravan.com` | **HANDOFF GATE** | Tuyệt đối không hỏi hay tự nhập mật khẩu/OTP/Passkey; dừng chờ người dùng tự đăng nhập |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Toast lỗi validation khi bấm `Lưu` tại `/admin/settings/general`:** Thường do `Số điện thoại` chứa ký tự lạ (`+84`, dấu ngoặc), `Email chăm sóc khách hàng` sai cú pháp hoặc bỏ trống dropdown `Quận/Huyện` sau khi đổi `Tỉnh/Thành phố` → Giữ nguyên tab, sửa đúng định dạng rồi chụp lại `preview_screenshot`.
2. **Đổi `Tiền tố mã đơn hàng` nhưng đơn cũ không đổi:** Đây là hành vi chuẩn của Haravan — tiền tố/hậu tố chỉ áp dụng cho các đơn hàng phát sinh **sau thời điểm lưu**, không sửa ngược mã đơn cũ để bảo toàn tính kế toán.
3. **Lưu `/admin/settings/policies` thành công nhưng không hiển thị ở Footer Website:** Văn bản tại `/admin/settings/policies` tự động hiển thị dưới chân trang **Checkout**. Để hiện ở Footer trang chủ, cần tạo Trang nội dung (`web-pages-blogs-ops`) và gắn vào Menu Footer (xem lưu ý cross-origin iframe tại `admin-ui-domains-channels-website`).
4. **Staff bị khóa mờ ô nhập hoặc báo lỗi 403:** Tài khoản Staff chưa được cấp quyền `Cấu hình chung` tại `/admin/settings/group_permissions` → Dừng và yêu cầu Owner đăng nhập hoặc cấp quyền tạm thời.
5. **Rich-Text Editor tại `/admin/settings/policies` bị lỗi font khi copy từ Word/Google Docs:** Dán dưới dạng *Plain Text* (`Ctrl+Shift+V`) rồi định dạng lại bằng thanh công cụ tiêu đề/danh sách của Haravan để tránh rác thẻ HTML inline làm vỡ layout mobile.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Đối chiếu `artifacts/general_policies_pre.png` và mở file `scratch/backup_policies.md` đã sao lưu ở Pha 1.
2. Truy cập lại `/admin/settings/general`: khôi phục chính xác `Tên cửa hàng`, `Email liên hệ`, `Email chăm sóc khách hàng`, `Số điện thoại`, `Địa chỉ cửa hàng`, `Tiền tố / Hậu tố mã đơn hàng` và tải lại logo gốc nếu đã thay đổi.
3. Truy cập `/admin/settings/policies`: dán nguyên vẹn văn bản gốc của 3 mục `Chính sách đổi trả`, `Chính sách bảo mật`, `Điều khoản dịch vụ`.
4. Bấm `Lưu`, chờ toast *"Cập nhật thành công"* và nhấn reload (`F5`) để xác minh dữ liệu đã trở về trạng thái ban đầu.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Mở trang Checkout trên tab ẩn danh: xác nhận logo mới và 3 link chính sách ở chân trang hiển thị đúng, không lỗi 404.
- [ ] Gửi 1 email thử nghiệm tại `/admin/settings/notifications`: xác nhận `Tên cửa hàng`, `Email chăm sóc khách hàng` và hotline ở chân email đã cập nhật.
- [ ] Xác nhận `Đơn vị tiền tệ` vẫn là `VND` và `Múi giờ` là `(GMT+07:00) Bangkok, Hanoi, Jakarta`.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `web-pages-blogs-ops`: Tạo các trang nội dung chính sách công khai (`/pages/chinh-sach-doi-tra`, `/pages/chinh-sach-bao-mat`, `/pages/dieu-khoan-dich-vu`) qua Haravan Web API `/web/pages.json` để gắn lên Footer Website.
- `skills/api-mcp/` → `store-health-check` / `scripts/hrv_client.py` (`GET /com/shop.json`): Đọc kiểm chứng nhanh tên shop, domain, múi giờ và đơn vị tiền tệ qua REST API sau khi lưu.
- `skills/browser-ui/` → `storefront-file-storage-audit` (kiểm tra dung lượng ảnh logo), `admin-ui-notifications-print-webhooks` (đồng bộ thông tin trong mẫu email/mẫu in), `admin-ui-domains-channels-website` (gắn link chính sách vào Menu).
