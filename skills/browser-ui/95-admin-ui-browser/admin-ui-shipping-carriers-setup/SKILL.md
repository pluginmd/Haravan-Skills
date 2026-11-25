---
name: admin-ui-shipping-carriers-setup
description: "Cấu hình biểu phí vận chuyển theo khu vực/Tỉnh-Thành, kết nối NVC VN (GHN, GHTK, Viettel Post, J&T, Ahamove) và kích thước kiện hàng tại /admin/settings/shipments."
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
    - "UI /admin/settings/shipments"
    - "UI /admin/settings/locations"
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

# Haravan Admin UI: Shipping Rates, VN Carriers & Packaging Setup

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Toàn bộ cấu hình vận chuyển trên Haravan tại `/admin/settings/shipments` — bao gồm **Phí vận chuyển** theo khu vực/Tỉnh-Thành/ngưỡng freeship, kết nối **Nhà vận chuyển bên thứ 3** (GHN, GHTK, Viettel Post, J&T, Ahamove, Ninja Van, BEST Express...), tạo **Nhà vận chuyển tùy chỉnh** và thiết lập **Kích thước kiện hàng đóng gói** (tối đa 50 phân loại hộp) — **không có REST API công khai** và chỉ thao tác được trực tiếp trên Haravan Admin UI.
- **Mục tiêu nghiệp vụ:**
  - Thiết lập ma trận biểu phí giao hàng nội thành/ngoại tỉnh/freeship phủ kín 100% địa bàn Việt Nam, không trùng lặp tỉnh/thành và không hở khoảng giá trị đơn hàng.
  - Hỗ trợ kết nối an toàn tài khoản hợp đồng NVC Việt Nam, chuẩn hóa hộp đóng gói tiêu chuẩn để NVC tính cước quy đổi chính xác, và xác minh kho lấy hàng tại `/admin/settings/locations`.
- **Phân quyền Owner vs Staff:**
  - **Owner:** Toàn quyền tạo/sửa/xóa biểu phí, kết nối hoặc ngắt NVC, cấu hình kích thước kiện hàng và kho lấy hàng.
  - **Staff:** Cần được cấp đồng thời quyền **Cấu hình > Vận chuyển** (`/admin/settings/shipments`) và **Cấu hình > Địa chỉ và kho hàng** (`/admin/settings/locations`) tại `/admin/settings/group_permissions`.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Mọi gói đều hỗ trợ biểu phí vận chuyển cơ bản, kết nối NVC đối tác và tối đa **50 kích thước kiện hàng đóng gói**.
  - Các gói **Grow / Scale** hỗ trợ nhiều kho lấy hàng (`Địa điểm lấy hàng`) và quy tắc chia đơn đa chi nhánh; gói **Standard** bị giới hạn số lượng kho — không bấm `Mua thêm` kho nếu chạm giới hạn.
- **Pre-flight Check phiên đăng nhập & Môi trường:**
  1. Mở `https://{store_domain}/admin/settings/shipments`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; tuyệt đối không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Xác nhận cửa hàng đang ở đúng môi trường (`staging` vs `production`) và đếm sẵn số khu vực phí ship + số loại kích thước kiện hàng đang tồn tại (`x/50`).
  4. Xác minh đơn vị khối lượng (`g` hay `kg`) tại `/admin/settings/general` nếu sắp tạo biểu phí `Dựa trên khối lượng sản phẩm`.

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/shipments` | 1. `Phí vận chuyển` | `Thêm`, `Thêm khu vực vận chuyển`, `Thêm giá vận chuyển`, `Lưu`, `Xóa` (CẤM tự bấm) | Quốc gia (`Việt Nam`), chọn Tỉnh/Thành phố (TP.HCM, Hà Nội, Các tỉnh thành khác), `Tên phương thức vận chuyển`, Tiêu chuẩn (`Dựa trên giá sản phẩm` / `Dựa trên khối lượng sản phẩm`), Khoảng (`Từ ... Đến ...`), `Giá vận chuyển` (VND — `0` = Freeship) |
| `/admin/settings/shipments` | 2. `Nhà vận chuyển` → `Nhà vận chuyển bên thứ 3` | `Thêm nhà vận chuyển`, `Kết nối`, `Chỉnh sửa`, `Ngừng kết nối` (CẤM tự bấm) | Kết nối GHN, GHTK, Viettel Post, J&T Express, Ahamove, Ninja Van (**Chủ shop tự đăng nhập tài khoản/token hợp đồng NVC**); cài đặt hiển thị cước tự động |
| `/admin/settings/shipments` | 2. `Nhà vận chuyển` → `Nhà vận chuyển tùy chỉnh` | `Thêm nhà vận chuyển tùy chỉnh`, `Chỉnh sửa`, `Lưu`, `Xóa` (CẤM tự bấm) | Tạo NVC nội bộ (Shipper cửa hàng, Chành xe, Giao hỏa tốc tự túc), nhập tên NVC và URL tra cứu hành trình (nếu có) |
| `/admin/settings/shipments` | 3. `Kích thước kiện hàng đóng gói` | `Thêm`, `Chỉnh sửa`, `Lưu`, `Xóa` (CẤM tự bấm) | Tên phân loại hộp (giới hạn tối đa **50 loại**), `Dài × Rộng × Cao (cm)`, checkbox đặt làm kiện hàng mặc định |
| `/admin/settings/locations/{id}` | Kiểm tra chéo Kho lấy hàng | Checkbox `Địa điểm lấy hàng`, `Lưu` | Xác nhận địa chỉ kho (chuẩn 2 cấp/3 cấp VN tùy phiên bản địa giới hành chính Haravan đang áp dụng) và bật cờ `Địa điểm lấy hàng` |

> **Đặc thù đối soát COD theo NVC Việt Nam:** `GHN` và `GHTK` hỗ trợ tự động đồng bộ trạng thái vận đơn & đối soát COD về Haravan; trong khi `Viettel Post` thường cần đối soát COD thủ công hoặc upload bảng kê tại `/admin/shipments/managecod`.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `shipping_rates_zones` | `shipping_rates_zones` \| `connect_3pl_carrier` \| `custom_carrier_setup` \| `package_sizes_setup` \| `verify_pickup_location` |
| `shipping_zones` | `array<object>` | Khi `shipping_rates_zones` | `[]` | `[{zone_name, provinces[], rate_name, condition_type: "price"\|"weight", min_val, max_val, fee_vnd}]`; không trùng tỉnh, khoảng giá liên tục |
| `carrier_name` | `string` | Khi `connect_3pl_carrier` | — | `GHN` \| `GHTK` \| `Viettel Post` \| `J&T Express` \| `Ahamove` \| `Ninja Van` |
| `custom_carrier` | `object` | Khi `custom_carrier_setup` | `{}` | `{name, tracking_url_template?, note?}` |
| `package_sizes` | `array<object>` | Khi `package_sizes_setup` | `[]` | `[{name, length_cm, width_cm, height_cm, is_default}]`; tổng số hộp toàn shop `<= 50`, kích thước `> 0` |
| `location_id_or_name` | `string` | Khi `verify_pickup_location` | — | Tên hoặc ID kho trung tâm cần kiểm tra/bật `Địa điểm lấy hàng` |
| `dry_run` | `boolean` | Có | `true` | Bắt buộc `true` trước khi qua bước Screenshot-Before-Save |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Tạo Biểu phí vận chuyển Tỉnh/Thành & Freeship theo ngưỡng đơn (`Phí vận chuyển`)
1. Tại `/admin/settings/shipments`, rà soát toàn bộ khu vực hiện có trong section `Phí vận chuyển` để lập danh sách các Tỉnh/Thành phố đã gán (tránh lỗi trùng lặp tỉnh/thành).
2. Click `Thêm khu vực vận chuyển` (hoặc mở khu vực hiện có), chọn Quốc gia `Việt Nam` và tick đúng các Tỉnh/Thành phố mục tiêu (ví dụ nhóm `Nội thành TP.HCM & Hà Nội`, nhóm `Các tỉnh thành còn lại`).
3. Trong từng khu vực, click `Thêm giá vận chuyển`:
   - Nhập `Tên phương thức vận chuyển` dễ hiểu cho khách (ví dụ `Giao hàng tiêu chuẩn`, `Miễn phí vận chuyển (Đơn từ 500.000đ)`).
   - Chọn tiêu chuẩn `Dựa trên giá sản phẩm` (hoặc `Dựa trên khối lượng sản phẩm` — phải khớp đơn vị `g`/`kg` ở `/admin/settings/general`).
   - Nhập khoảng giá trị liên tục tuyệt đối (ví dụ Mức 1: `Từ 0đ` → `Đến 499.999đ` = `25.000đ`; Mức 2: `Từ 500.000đ` → `Trở lên` = `0đ`).
4. **DỪNG — chưa bấm `Lưu`**, kiểm tra lại toàn bộ 63 tỉnh/thành (hoặc danh mục tỉnh/thành mới của VN) đã được phủ kín.

### Scenario 2: Kết nối Nhà vận chuyển bên thứ 3 (GHN, GHTK, Viettel Post, J&T, Ahamove)
1. Tại section `Nhà vận chuyển` → tab/khối `Nhà vận chuyển bên thứ 3`, kiểm tra trạng thái kết nối hiện có của `carrier_name`.
2. Click `Thêm nhà vận chuyển` → chọn đúng logo/tên nhà vận chuyển (`GHN`, `GHTK`, `Viettel Post`, `J&T Express`, `Ahamove`).
3. Click `Kết nối` để mở modal/trang đăng nhập tài khoản hợp đồng NVC.
4. **DỪNG NGAY LẬP TỨC (Credential Handoff Gate):** Nhắc Chủ shop tự nhập SĐT/Email, Mật khẩu, OTP hoặc API Token của NVC trực tiếp trên trình duyệt.
5. Ghi chú rõ đặc thù vận hành COD cho Chủ shop trước khi vận hành live:
   - **GHN & GHTK:** Tự động đồng bộ trạng thái vận đơn và đối soát thu hộ COD về Haravan.
   - **Viettel Post:** Cần đối soát COD thủ công hoặc upload bảng kê đối soát tại `/admin/shipments/managecod`.

### Scenario 3: Tạo Nhà vận chuyển tùy chỉnh (Shipper nội bộ / Chành xe)
1. Cuộn tới khối `Nhà vận chuyển tùy chỉnh` trong section `Nhà vận chuyển` tại `/admin/settings/shipments`.
2. Click nút `Thêm nhà vận chuyển tùy chỉnh`.
3. Điền tên nhà vận chuyển từ `custom_carrier.name` (ví dụ `Shipper Nội Bộ Cửa Hàng` hoặc `Chành Xe Phương Trang`) và URL tra cứu hành trình (nếu có).
4. **DỪNG — chưa bấm `Lưu`**, chụp ảnh preview form để người dùng duyệt trước khi kích hoạt hiển thị trên màn hình tạo vận đơn.

### Scenario 4: Thiết lập Kích thước kiện hàng đóng gói (Tối đa 50 loại) & Lưu ý Địa chỉ 2 cấp VN
1. Cuộn xuống section `Kích thước kiện hàng đóng gói` tại `/admin/settings/shipments`.
2. Đếm số lượng phân loại kiện hàng hiện có (đảm bảo sau khi thêm tổng số `<= 50` phân loại theo giới hạn hệ thống Haravan).
3. Click `Thêm`, điền `Tên kiện hàng` (ví dụ `Hộp S - Mỹ phẩm`, `Hộp M - Thời trang`), nhập kích thước chuẩn `Dài × Rộng × Cao (cm)` và tick chọn hộp mặc định nếu `is_default = true`.
4. Kiểm tra cảnh báo địa giới hành chính Việt Nam (2 cấp Tỉnh/Xã mới vs 3 cấp Tỉnh/Quận/Phường cũ trên giao diện Haravan): đảm bảo địa chỉ kho và khu vực ship khớp đúng danh mục địa phương đang kích hoạt trên store để NVC không báo lỗi *Invalid Ward/District*.
5. **DỪNG — chưa bấm `Lưu`**.

### Scenario 5: Kiểm tra & Bật `Địa điểm lấy hàng` tại `/admin/settings/locations/{id}`
1. Điều hướng sang `https://{store_domain}/admin/settings/locations`.
2. Mở chi tiết kho lấy hàng mục tiêu (`/admin/settings/locations/{id}`) theo `location_id_or_name`.
3. Xác minh đầy đủ `Số điện thoại` người bàn giao hàng, `Địa chỉ` chi tiết và danh mục địa phương chuẩn (không bỏ trống cấp hành chính).
4. Kiểm tra checkbox `Địa điểm lấy hàng`: nếu đang tắt, tick bật lên để NVC (GHN/GHTK/VTP/Ahamove) có thể chọn kho này làm điểm lấy hàng khi đẩy vận đơn.
5. **DỪNG — chưa bấm `Lưu`**, chụp ảnh preview trạng thái kho.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser Safety Protocol)

### Pha 1: Pre-State Capture (Chụp Ảnh Trạng Thái Gốc)
- Mở `/admin/settings/shipments` (và `/admin/settings/locations/{id}` nếu chạy Scenario 5), xác minh không redirect sang `accounts.haravan.com`.
- Chụp ảnh toàn bộ biểu phí vận chuyển, danh sách NVC đã kết nối và danh sách hộp đóng gói hiện có (`artifacts/shipments_setup_pre.png`).
- Lập danh sách đối chiếu Tỉnh/Thành phố đang gán trong từng khu vực để ngăn trùng lặp trước khi sửa.

### Pha 2: Stage Without Saving (Điền Biểu Phí / Hộp / Mở Form NVC)
- Điền biểu phí vận chuyển mới, tên NVC tùy chỉnh hoặc kích thước hộp (`<= 50` loại) theo Scenario ở Mục 4.
- Nếu kết nối NVC bên thứ 3 (GHN/GHTK/VTP/J&T/Ahamove), mở đúng tới modal đăng nhập rồi **dừng bàn giao cho Chủ shop tự nhập tài khoản/OTP/token**.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu`**.

### Pha 3: Screenshot-Before-Save & Human Approval Gate
- Chụp ảnh màn hình đã điền (`artifacts/shipments_setup_preview.png`).
- Trình bày bảng `Before → After` (Mục 6), xác nhận 3 tiêu chí kiểm chuẩn: (1) Không trùng tỉnh/thành, (2) Không hở khoảng giá/khối lượng, (3) Đã bật `Địa điểm lấy hàng` cho kho trung tâm.
- Dừng chờ người dùng xác nhận tường minh (L2: `confirmation_required: true`).

### Pha 4: Save & Post-Save Reload Verification
- Chỉ sau khi người dùng xác nhận, click nút `Lưu` và chờ toast *"Cập nhật thành công"*.
- Reload trang `/admin/settings/shipments` (`F5`), xác minh các khu vực phí ship, NVC và hộp đóng gói lưu bền vững, chụp `artifacts/shipments_setup_post.png`.
- Khuyến nghị kiểm chứng nhanh 1 giỏ hàng thử trên storefront (tab ẩn danh) với 2 địa chỉ mẫu: nội thành và ngoại tỉnh.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/shipments`)

| Section | Hạng mục | Trước (Before) | Đề xuất (After) | Kiểm chuẩn an toàn |
| :--- | :--- | :--- | :--- | :--- |
| `Phí vận chuyển` | Nội thành TP.HCM & Hà Nội | Đồng giá `30.000đ` | `0–499.999đ`: `25.000đ` \| `>= 500.000đ`: `0đ` | Khoảng giá liên tục, không trùng tỉnh |
| `Phí vận chuyển` | Các tỉnh thành khác | Chưa có Freeship | `0–699.999đ`: `35.000đ` \| `>= 700.000đ`: `0đ` | Phủ kín toàn quốc |
| `Nhà vận chuyển` | `GHN` / `Viettel Post` | Chưa kết nối | Đã mở form `Kết nối` chờ Chủ shop đăng nhập | Lưu ý: VTP đối soát COD thủ công |
| `Nhà vận chuyển tùy chỉnh` | `Shipper Nội Bộ` | *(Chưa có)* | Đã điền tên & URL tra cứu nội bộ | Không ảnh hưởng NVC 3PL |
| `Kích thước kiện hàng` | `Hộp S - Tiêu chuẩn` | *(Chưa có)* | `20 × 15 × 10 cm` (Mặc định) | Đang dùng `1/50` loại hộp |
| `/locations/{id}` | `Địa điểm lấy hàng` | `Tắt` | `Bật` (đủ địa chỉ & SĐT kho) | Sẵn sàng đẩy vận đơn NVC |

> **Yêu cầu xác nhận:** Cấu hình vận chuyển tại `/admin/settings/shipments` đã được điền sẵn (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng xác nhận **"Đồng ý lưu cấu hình vận chuyển"** để Agent bấm nút `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-shipping-carriers-setup",
  "scenario": "shipping_rates_zones",
  "store_domain": "myshop.myharavan.com",
  "routes_visited": ["/admin/settings/shipments", "/admin/settings/locations/102456"],
  "phase_status": "awaiting_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/shipments_setup_pre.png",
    "preview_screenshot": "artifacts/shipments_setup_preview.png",
    "post_screenshot": "artifacts/shipments_setup_post.png"
  },
  "checks_passed": {
    "no_duplicate_provinces": true,
    "continuous_price_weight_ranges": true,
    "package_count_within_50": true,
    "pickup_location_verified": true
  },
  "changes_staged": {
    "shipping_zones_updated": 2,
    "package_sizes_total_after": 1,
    "pickup_location_enabled": true,
    "carrier_login_handed_off": true
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Ngừng kết nối` / `Xóa` NVC bên thứ 3 | **HARD-BLOCKED** | Làm đứt luồng đẩy vận đơn & đồng bộ trạng thái COD cho các đơn đang giao |
| `Xóa` khu vực vận chuyển `Việt Nam` | **HARD-BLOCKED** | Khiến toàn bộ khách hàng không chọn được phương thức giao hàng khi checkout |
| `Xóa` hộp đóng gói đang đặt làm mặc định | **HARD-BLOCKED** | Gây lỗi tính cước quy đổi; chỉ xóa sau khi đã gán hộp mặc định mới |
| Modal đăng nhập GHN/GHTK/VTP/J&T/Ahamove | **HANDOFF GATE** | Tuyệt đối không hỏi/tự nhập mật khẩu, OTP hay API Token NVC; bàn giao Owner tự nhập |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Khách hàng báo *"Không có phương thức vận chuyển phù hợp"* trên trang Checkout:** Nguyên nhân phổ biến nhất là hở khoảng giá/khối lượng (ví dụ cài `0–499.000đ` và `500.000đ+` làm đơn `499.500đ` lọt khe) hoặc bỏ sót 1 Tỉnh/Thành phố khi tách khu vực → Rà soát lại toàn bộ biên dưới/biên trên và danh sách tỉnh.
2. **Đẩy vận đơn sang GHN/GHTK/VTP báo lỗi *"Địa chỉ lấy hàng không hợp lệ"*:** Do kho tại `/admin/settings/locations/{id}` chưa bật checkbox `Địa điểm lấy hàng` hoặc địa chỉ hành chính cũ/mới chưa khớp bảng mã NVC → Chạy Scenario 5 để chuẩn hóa kho.
3. **Chạm giới hạn 50 loại `Kích thước kiện hàng đóng gói`:** Nút `Thêm` bị khóa hoặc báo vượt hạn mức → Dừng lại, đề xuất gộp các cỡ hộp chênh lệch `< 2cm` và chỉ xóa hộp cũ khi người dùng phê duyệt.
4. **Cước vận chuyển tự động của NVC tính cao bất thường:** Do sản phẩm chưa nhập khối lượng thực tế (`grams`) hoặc hộp mặc định đang khai báo kích thước quá lớn làm NVC tính theo khối lượng quy đổi `(D×R×C)/5000` → Kiểm tra lại kích thước hộp mặc định và khối lượng SKU.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Đối chiếu `artifacts/shipments_setup_pre.png` của `/admin/settings/shipments` và ảnh gốc `/admin/settings/locations/{id}`.
2. Chỉnh sửa lại các mức phí vận chuyển trong từng khu vực về đúng bảng giá cũ, đặt lại `Kích thước kiện hàng đóng gói` mặc định ban đầu và bấm `Lưu`.
3. Nếu vừa bật nhầm `Địa điểm lấy hàng` trên một kho không dùng để giao vận, mở lại `/admin/settings/locations/{id}` bỏ tick và bấm `Lưu`.
4. Mở tab ẩn danh trên storefront, thêm 1 sản phẩm mẫu vào giỏ hàng và kiểm tra lại bước tính phí giao hàng ở trang Checkout.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Thử địa chỉ nội thành (TP.HCM/Hà Nội) với đơn dưới ngưỡng và trên ngưỡng Freeship: phí ship nhảy đúng `25.000đ` → `0đ`.
- [ ] Thử địa chỉ ngoại tỉnh (ví dụ Đà Nẵng / Cần Thơ / Lào Cai): không xuất hiện lỗi *"Không có phương thức vận chuyển phù hợp"*.
- [ ] Xác nhận kho lấy hàng trung tâm tại `/admin/settings/locations/{id}` đã bật `Địa điểm lấy hàng` và đủ địa chỉ chuẩn.
- [ ] Nếu kết nối Viettel Post: đã nhắc vận hành lịch đối soát COD thủ công tại `/admin/shipments/managecod`.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `fulfillment-ops` & `finance-cod-reconciliation`: Đọc vận đơn, kiểm tra cước phí thực tế và đối soát tiền thu hộ COD qua Commerce API (`/com/orders.json`, `/com/fulfillments.json`) sau khi kết nối NVC.
- `skills/api-mcp/` → `catalog-audit`: Quét hàng loạt SKU đang có khối lượng `grams = 0` trước khi áp dụng biểu phí theo khối lượng.
- `skills/browser-ui/` → `admin-ui-locations-inventory-ops`, `admin-ui-shipments-cod-mass-fulfill`, `order-abandoned-checkouts-audit`.
