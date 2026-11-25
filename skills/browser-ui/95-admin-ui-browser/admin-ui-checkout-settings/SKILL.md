---
name: admin-ui-checkout-settings
description: "Cấu hình luồng đặt hàng tại /admin/settings/checkouts: tài khoản khách hàng, Multipass, xác thực OTP Zalo, nhắc đơn chưa thanh toán, đặt cọc và nhận tại cửa hàng."
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
    - "UI /admin/settings/checkouts"
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

# Haravan Admin UI: Checkout Flow, Zalo OTP, Deposit & Pickup Setup

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Toàn bộ cấu hình trải nghiệm trang thanh toán tại `/admin/settings/checkouts` (tách biệt hoàn toàn với `/admin/settings/payments` là cấu hình cổng thanh toán) **không có REST API công khai** từ Haravan. Đây là màn hình quyết định trực tiếp **Tỷ lệ chuyển đổi Checkout (Checkout Conversion Rate)** gồm 7 khu vực: `Tài khoản khách hàng`, `Cấu hình đăng nhập` (`Standard`/`Legacy`, OTP Zalo, `Multipass`), `Yêu cầu nhập Email`, `Xử lý đơn hàng`, `Thiết lập đặt cọc`, `Nhận tại cửa hàng` và `Ngôn ngữ`.
- **Mục tiêu nghiệp vụ:**
  - Giảm tối đa ma sát đặt hàng cho khách Việt Nam (cho phép mua không cần tài khoản, không ép nhập email nếu khách dùng SĐT).
  - Bật tự động kéo lại đơn bỏ giỏ (`Gửi email nhắc nhở đơn hàng chưa thanh toán` sau 6h/24h), triển khai đăng nhập OTP Zalo, bật đặt cọc cho hàng giá trị cao/pre-order và bật nhận hàng tại cửa hàng.
- **Phân quyền Owner vs Staff:**
  - **Owner:** Toàn quyền chỉnh sửa mọi section tại `/admin/settings/checkouts`.
  - **Staff:** Cần có quyền **Cấu hình > Thanh toán** tại `/admin/settings/group_permissions`. Các tích hợp bảo mật như `Cấu hình Multipass` hoặc ủy quyền Zalo OA nên do Owner trực tiếp phê duyệt.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - `Tài khoản khách hàng`, `Yêu cầu nhập Email`, `Xử lý đơn hàng` và `Ngôn ngữ` có sẵn trên mọi gói.
  - Các tính năng nâng cao như `Cấu hình Multipass` (SSO), xác thực `OTP Zalo` (cần liên kết Zalo OA / hạn mức ZNS), `Thiết lập đặt cọc` và `Nhận tại cửa hàng` đa chi nhánh có thể phụ thuộc vào gói **Pro / Grow / Scale** hoặc cấu hình kho tại `/admin/settings/locations`.
- **Pre-flight Check phiên đăng nhập & Kiểm tra chéo:**
  1. Mở `https://{store_domain}/admin/settings/checkouts`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; tuyệt đối không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Cuộn kiểm tra đủ cả 7 section (`Tài khoản khách hàng`, `Cấu hình đăng nhập`, `Yêu cầu nhập Email`, `Xử lý đơn hàng`, `Thiết lập đặt cọc`, `Nhận tại cửa hàng`, `Ngôn ngữ`) để xác định mục nào khả dụng theo gói hiện tại.
  4. Xác nhận trước với người dùng xem store có đang tích hợp Mobile App / SSO qua `Multipass` không (nếu có, khóa tuyệt đối không chạm section `Multipass`).

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/checkouts` | 1. `Tài khoản khách hàng` | Radio buttons + nút `Lưu` (góc trên/dưới phải) | `Vô hiệu hóa`, `Bắt buộc phải có tài khoản mua hàng`, `Không ràng buộc phải có tài khoản mua hàng` (Khuyến nghị tối ưu chuyển đổi) |
| `/admin/settings/checkouts` | 2. `Cấu hình đăng nhập` | Radio, Toggle Switch, `Tùy chỉnh tài khoản`, `Cấu hình Multipass` (CẤM tự tái tạo key) | Phiên bản đăng nhập (`Standard` / `Legacy`), phương thức đăng nhập (`Email`, `Số điện thoại` xác thực OTP qua Zalo), SSO Multipass |
| `/admin/settings/checkouts` | 3. `Yêu cầu nhập Email` | Radio buttons | `Không bắt buộc` (Khuyến nghị cho thị trường VN), `Bắt buộc` |
| `/admin/settings/checkouts` | 4. `Xử lý đơn hàng` | Checkbox & Radio buttons | `Tự động xử lý giao hàng` (Cảnh báo rủi ro kho — mặc định TẮT), `Tự động lưu trữ đơn hàng`, `Gửi email nhắc nhở đơn hàng chưa thanh toán` (`Không bao giờ` / `Sau 6 tiếng` / `Sau 24 tiếng`) |
| `/admin/settings/checkouts` | 5. `Thiết lập đặt cọc` | Toggle Switch / Radio / Input % hoặc số tiền | Cho phép khách đặt cọc một phần giá trị đơn hàng, quy định tỷ lệ/ngưỡng đơn áp dụng đặt cọc |
| `/admin/settings/checkouts` | 6. `Nhận tại cửa hàng` | Toggle Switch / Link tới `/admin/settings/locations` | Cho phép khách chọn chi nhánh đến lấy hàng trực tiếp (chỉ hiện các kho đã bật `Địa điểm lấy hàng`) |
| `/admin/settings/checkouts` | 7. `Ngôn ngữ` | `Chỉnh sửa ngôn ngữ`, nút `Lưu` | Ngôn ngữ giao diện trang Checkout (`Tiếng Việt`, `English`) và tùy chỉnh nhãn nút/thông báo |

> **Phân biệt nhanh:** `/admin/settings/checkouts` quản lý **hành vi & trải nghiệm trang đặt hàng** (L2); còn `/admin/settings/payments` quản lý **tài khoản nhận tiền, Haravan QR, VNPay, COD** (L3 Critical).

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `optimize_conversion` | `optimize_conversion` \| `login_standard_zalo_otp` \| `abandoned_cart_reminder` \| `deposit_setup` \| `store_pickup_setup` |
| `customer_account_mode` | `string` | Không | `Không ràng buộc` | `Vô hiệu hóa` \| `Bắt buộc` \| `Không ràng buộc` |
| `require_email` | `string` | Không | `Không bắt buộc` | `Không bắt buộc` \| `Bắt buộc` |
| `login_version` | `string` | Khi `login_standard_zalo_otp` | `Standard` | `Standard` \| `Legacy`; kèm `enable_zalo_otp: boolean` |
| `abandoned_reminder` | `string` | Khi `abandoned_cart_reminder` | `Sau 6 tiếng` | `Không bao giờ` \| `Sau 6 tiếng` \| `Sau 24 tiếng` |
| `auto_fulfill_order` | `boolean` | Không | `false` | Luôn giữ `false` trừ khi người dùng yêu cầu tường minh (rủi ro trừ kho tự động) |
| `deposit_config` | `object` | Khi `deposit_setup` | `{}` | `{enabled: bool, deposit_percent?: number (10..90), min_order_value_vnd?: number}` |
| `enable_store_pickup` | `boolean` | Khi `store_pickup_setup` | `true` | Yêu cầu có ít nhất 1 kho đã bật `Địa điểm lấy hàng` tại `/admin/settings/locations` |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi qua cổng Screenshot-Before-Save |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Tối ưu tỷ lệ chuyển đổi Checkout (`optimize_conversion`)
1. Tại `/admin/settings/checkouts`, cuộn tới section `Tài khoản khách hàng`.
2. Chọn radio `Không ràng buộc phải có tài khoản mua hàng` (giúp khách mua nhanh trong 1 phút mà vẫn cho phép khách cũ đăng nhập tích điểm).
3. Cuộn tới section `Yêu cầu nhập Email`, chọn radio `Không bắt buộc` (khách hàng VN đặt qua di động thường chỉ nhập SĐT; ép nhập email dễ làm rớt 15–25% đơn).
4. Kiểm tra nhanh section `Ngôn ngữ`: đảm bảo đúng `Tiếng Việt` (hoặc ngôn ngữ mục tiêu của storefront).
5. **DỪNG — chưa bấm `Lưu`**, chuyển sang chụp ảnh preview.

### Scenario 2: Bật đăng nhập `Standard` & xác thực OTP qua Zalo (`login_standard_zalo_otp`)
1. Cuộn tới section `Cấu hình đăng nhập` trên `/admin/settings/checkouts`.
2. Kiểm tra trạng thái phiên bản đăng nhập hiện tại: nếu đang ở `Legacy` và người dùng muốn nâng lên `Standard`, chọn radio `Standard` (ghi chú rõ tác động: `Standard` hỗ trợ đăng nhập không cần mật khẩu / OTP hiện đại hơn).
3. Click `Tùy chỉnh tài khoản` (nếu cần xem cấu hình hiển thị) hoặc bật công tắc phương thức `Số điện thoại` (xác thực OTP qua Zalo).
4. Nếu hệ thống hiện popup yêu cầu kết nối **Zalo OA** hoặc cấp quyền gửi tin **ZNS**, **DỪNG NGAY LẬP TỨC** để Chủ shop tự đăng nhập tài khoản quản trị Zalo OA trên trình duyệt.
5. Không chạm vào nút `Cấu hình Multipass` trừ khi có yêu cầu tích hợp SSO riêng. **DỪNG — chưa bấm `Lưu`**.

### Scenario 3: Bật Email nhắc đơn bỏ quên 6h/24h & rà soát Xử lý đơn hàng (`abandoned_cart_reminder`)
1. Cuộn tới section `Xử lý đơn hàng` trên `/admin/settings/checkouts`.
2. Kiểm tra checkbox `Tự động xử lý giao hàng`: **đảm bảo đang TẮT** (`false`) để tránh hệ thống tự xuất kho cho đơn COD chưa gọi xác nhận.
3. Kiểm tra checkbox `Tự động lưu trữ đơn hàng` theo quy trình vận hành kho của shop.
4. Tại mục `Gửi email nhắc nhở đơn hàng chưa thanh toán`: chọn radio `Sau 6 tiếng` (khuyến nghị cho thời trang/mỹ phẩm/FMCG) hoặc `Sau 24 tiếng` (sản phẩm giá trị cao cần cân nhắc).
5. Nhắc người dùng đồng bộ nội dung mẫu email `Đơn hàng chưa hoàn tất` tại `/admin/settings/notifications` nếu muốn thêm mã giảm giá kéo đơn. **DỪNG — chưa bấm `Lưu`**.

### Scenario 4: Bật `Thiết lập đặt cọc` một phần giá trị đơn hàng (`deposit_setup`)
1. Cuộn tới section `Thiết lập đặt cọc` tại `/admin/settings/checkouts`.
2. Gạt Toggle Switch bật tính năng đặt cọc (nếu bị khóa theo gói, dừng ngay và báo giới hạn gói).
3. Điền tỷ lệ phần trăm đặt cọc (`deposit_config.deposit_percent`, ví dụ `30%`) hoặc điều kiện áp dụng theo ngưỡng giá trị đơn hàng.
4. Kiểm tra chéo xem cửa hàng đã kích hoạt ít nhất 1 phương thức nhận tiền trả trước (`Haravan QR`, `VNPay/MoMo` hoặc `Chuyển khoản qua ngân hàng`) tại `/admin/settings/payments` chưa.
5. **DỪNG — chưa bấm `Lưu`**.

### Scenario 5: Bật `Nhận tại cửa hàng` theo chi nhánh (`store_pickup_setup`)
1. Cuộn tới section `Nhận tại cửa hàng` trên `/admin/settings/checkouts`.
2. Gạt Toggle Switch sang trạng thái **Bật** (`enable_store_pickup = true`).
3. Kiểm tra danh sách chi nhánh hiển thị ngay bên dưới (hoặc mở chéo `/admin/settings/locations` trên tab khác để xác minh kho mục tiêu đã tick checkbox `Địa điểm lấy hàng`).
4. Nếu chưa có kho nào bật `Địa điểm lấy hàng`, ghi cảnh báo rõ trong bản preview và đề xuất chạy thêm `admin-ui-locations-inventory-ops`.
5. **DỪNG — chưa bấm `Lưu`**.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser Safety Protocol)

### Pha 1: Pre-State Capture (Chụp Ảnh Trạng Thái Gốc 7 Section)
- Mở `/admin/settings/checkouts`, xác minh không redirect sang `accounts.haravan.com`.
- Cuộn chụp ảnh toàn bộ 7 section (`artifacts/checkout_settings_pre.png` — có thể tách 2 ảnh trên/dưới nếu trang dài) làm căn cứ rollback chính xác từng radio/switch.

### Pha 2: Stage Without Saving (Chọn Radio / Bật Switch Chưa Lưu)
- Chọn đúng radio/switch theo Scenario ở Mục 4 (đảm bảo `Tự động xử lý giao hàng` giữ nguyên trạng thái tắt trừ khi được yêu cầu tường minh).
- Nếu bật OTP Zalo cần ủy quyền **Zalo OA / ZNS**, dừng ngay để Chủ cửa hàng tự đăng nhập trực tiếp trên trình duyệt.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu`**.

### Pha 3: Screenshot-Before-Save & Human Approval Gate
- Chụp ảnh màn hình các section đã thay đổi (`artifacts/checkout_settings_preview.png`).
- Gửi bảng so sánh `Before → After` (Mục 6), gắn cờ cảnh báo nếu có thay đổi ảnh hưởng lớn tới chuyển đổi (như `Bắt buộc tài khoản`) hoặc vận hành kho (`Tự động xử lý giao hàng`).
- Dừng chờ người dùng xác nhận tường minh (L2: `confirmation_required: true`).

### Pha 4: Save & Post-Save Reload Verification
- Sau khi người dùng xác nhận, bấm nút `Lưu` và chờ toast *"Cập nhật thành công"*.
- Nhấn reload trang (`F5`), kiểm tra lại tất cả các radio/switch vừa chỉnh để xác minh lưu bền vững, chụp `artifacts/checkout_settings_post.png`.
- Khuyến nghị kiểm thử nhanh 1 lượt trên trang checkout storefront (tab ẩn danh) để xác minh hiển thị đúng ngôn ngữ, trường email và tùy chọn nhận tại cửa hàng.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/checkouts`)

| Section trên Haravan Admin | Trước (Before) | Đề xuất (After) | Tác động chuyển đổi / Vận hành |
| :--- | :--- | :--- | :--- |
| `Tài khoản khách hàng` | `Bắt buộc phải có tài khoản` | `Không ràng buộc phải có tài khoản` | Giảm ma sát, tăng tỷ lệ hoàn tất đơn |
| `Cấu hình đăng nhập` | `Legacy` (chỉ Email) | `Standard` + `OTP qua Zalo` | Trải nghiệm đăng nhập nhanh qua SĐT |
| `Yêu cầu nhập Email` | `Bắt buộc` | `Không bắt buộc` | Phù hợp hành vi khách VN trên mobile |
| `Xử lý đơn hàng` | `Nhắc đơn: Không bao giờ` | `Nhắc đơn: Sau 6 tiếng` (`Tự giao: Tắt`) | Tự động thu hồi đơn bỏ giỏ an toàn |
| `Thiết lập đặt cọc` | `Tắt` | `Bật (30% cho đơn >= 2.000.000đ)` | Giảm bom hàng đơn giá trị cao |
| `Nhận tại cửa hàng` | `Tắt` | `Bật` (đã xác minh kho lấy hàng) | Khách tự chọn chi nhánh gần nhất |

> **Yêu cầu xác nhận:** Các cấu hình trên đã được chọn sẵn tại `/admin/settings/checkouts` (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng xác nhận **"Đồng ý lưu cấu hình thanh toán"** để Agent bấm nút `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-checkout-settings",
  "scenario": "optimize_conversion",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/checkouts",
  "phase_status": "awaiting_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/checkout_settings_pre.png",
    "preview_screenshot": "artifacts/checkout_settings_preview.png",
    "post_screenshot": "artifacts/checkout_settings_post.png"
  },
  "checks_passed": {
    "multipass_untouched": true,
    "auto_fulfill_disabled": true,
    "pickup_warehouse_checked": true
  },
  "changes_staged": {
    "customer_account_mode": "Không ràng buộc",
    "require_email": "Không bắt buộc",
    "abandoned_checkout_reminder": "Sau 6 tiếng",
    "auto_fulfill_order": false,
    "enable_store_pickup": true
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| Tái tạo / Xóa secret trong `Cấu hình Multipass` | **HARD-BLOCKED** | Làm đứt toàn bộ phiên đăng nhập SSO với Mobile App hoặc hệ thống tích hợp ngoài |
| Tự ý bật `Tự động xử lý giao hàng` | **HARD-BLOCKED** | Tự động trừ tồn kho & đẩy trạng thái giao cho cả đơn COD chưa gọi xác nhận |
| Tự ý bật `Bắt buộc phải có tài khoản mua hàng` | **HARD-BLOCKED** | Gây sụt giảm mạnh tỷ lệ chuyển đổi checkout nếu không phải chiến lược B2B có chủ đích |
| Popup đăng nhập Zalo OA / ZNS & `accounts.haravan.com` | **HANDOFF GATE** | Dừng ngay để Chủ cửa hàng tự đăng nhập và cấp quyền trực tiếp trên trình duyệt |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Bật `Nhận tại cửa hàng` thành công nhưng trang Checkout không hiện lựa chọn nhận tại cửa hàng:** Nguyên nhân do chưa có kho nào bật checkbox `Địa điểm lấy hàng` tại `/admin/settings/locations/{id}` hoặc tồn kho tại kho đó bằng `0` → Chuyển sang kiểm tra bằng `admin-ui-locations-inventory-ops`.
2. **Bật `Gửi email nhắc nhở đơn hàng chưa thanh toán` nhưng khách vẫn không nhận được email:** Do `Yêu cầu nhập Email` đang để `Không bắt buộc` nên khách không để lại email (chỉ nhập SĐT), hoặc mẫu email `Đơn hàng chưa hoàn tất` tại `/admin/settings/notifications` đang bị tắt → Ghi chú rõ để shop kết hợp kịch bản nhắc đơn qua Zalo/Harasocial.
3. **Chuyển từ `Legacy` sang `Standard` nhưng giao diện theme cũ bị lỗi nút đăng nhập:** Một số theme Liquid cũ gọi form `/account/login` tùy biến không tương thích hoàn toàn với luồng `Standard` mới → Kiểm tra thử đăng nhập trên tab ẩn danh ngay sau khi lưu; nếu lỗi, rollback về `Legacy`.
4. **Các radio/switch bị mờ (`disabled`) hoặc trang báo 403:** Tài khoản Staff thiếu quyền Cấu hình Thanh toán → Yêu cầu Owner đăng nhập hoặc cấp quyền tại `/admin/settings/group_permissions`.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Mở lại `artifacts/checkout_settings_pre.png` của `/admin/settings/checkouts` đã lưu ở Pha 1.
2. Chọn lại chính xác từng radio/switch (đặc biệt phiên bản `Standard` / `Legacy`, chế độ `Tài khoản khách hàng`, `Yêu cầu nhập Email` và `Thiết lập đặt cọc`) theo đúng ảnh gốc.
3. Bấm `Lưu`, chờ toast *"Cập nhật thành công"*, nhấn reload (`F5`) và test nhanh 1 lượt đặt hàng trên storefront bằng tab ẩn danh.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Thêm 1 sản phẩm vào giỏ trên tab ẩn danh và đi tới trang Checkout: kiểm tra khách không bị ép đăng nhập và không bị báo lỗi bắt buộc nhập Email.
- [ ] Nếu bật `Nhận tại cửa hàng`: xác nhận danh sách chi nhánh lấy hàng hiện đúng tên & địa chỉ kho đã cấu hình tại `/admin/settings/locations`.
- [ ] Nếu bật `Gửi email nhắc nhở đơn hàng chưa thanh toán`: kiểm tra mẫu email `Đơn hàng chưa hoàn tất` tại `/admin/settings/notifications` đang ở trạng thái **Bật**.
- [ ] Nếu bật `Thiết lập đặt cọc`: xác nhận có ít nhất 1 phương thức trả trước (`Haravan QR` / `VNPay` / `Chuyển khoản`) đang hoạt động tại `/admin/settings/payments`.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `order-abandoned-recovery` (`GET /com/checkouts.json`): Theo dõi số lượng và tỷ lệ chuyển đổi đơn bỏ giỏ qua Commerce API trước/sau khi tối ưu trang checkout và bật nhắc đơn 6h/24h.
- `skills/api-mcp/` → `order-ops`: Kiểm tra tỷ lệ đơn hàng đặt cọc thành công và trạng thái thanh toán một phần (`partially_paid`).
- `skills/browser-ui/` → `order-abandoned-checkouts-audit`, `admin-ui-payment-methods-setup`, `admin-ui-locations-inventory-ops`, `admin-ui-notifications-print-webhooks`.
