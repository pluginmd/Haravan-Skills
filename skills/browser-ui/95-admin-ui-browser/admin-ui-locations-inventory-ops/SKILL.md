---
name: admin-ui-locations-inventory-ops
description: "Cấu hình Địa chỉ & Kho hàng (/admin/settings/locations), bật Địa điểm lấy hàng / xuất hóa đơn, và quản lý Bảng giá đa kênh (/admin/products/pricing_list)."
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
    - "UI /admin/settings/locations"
    - "UI /admin/products/pricing_list"
    - "UI /admin/products/inventories"
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

# Haravan Admin UI: Locations, Pickup Warehouses & Pricing Lists

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Haravan REST API (`/com/locations.json`) chỉ hỗ trợ đọc danh sách kho (Read-Only), **không cho phép tạo/sửa địa chỉ chi tiết kho**, bật/tắt cờ `Địa điểm lấy hàng` (điều kiện bắt buộc để NVC lấy hàng và bật `Nhận tại cửa hàng`) hay cờ `Cập nhật thông tin xuất hoá đơn` trên từng kho. Tương tự, màn hình `Bảng giá` đa kênh (`/admin/products/pricing_list`) và thao tác lọc/xuất file kiểm kê tồn kho trực quan tại `/admin/products/inventories` chỉ thực hiện được trên Haravan Admin UI.
- **Mục tiêu nghiệp vụ:**
  - Chuẩn hóa hệ thống kho đa chi nhánh (địa chỉ chuẩn để NVC tính phí chính xác, bật cờ kho lấy hàng và thông tin xuất hóa đơn).
  - Kiểm soát tồn kho trực quan theo từng kho (`Tồn kho`, `Đang giao dịch`, `Có thể bán`, `Hàng đang về`) và điều phối thiết lập bảng giá đa kênh/B2B.
- **Phân quyền Owner vs Staff:**
  - **Owner:** Toàn quyền tạo/sửa kho, xem tồn kho tất cả chi nhánh và quản lý toàn bộ bảng giá.
  - **Staff:** Chỉ thấy và thao tác được các kho được gán phạm vi truy cập tại `/admin/settings/accounts`; cần quyền **Cấu hình > Địa chỉ và kho hàng** và **Sản phẩm > Tồn kho / Bảng giá**.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Số lượng kho hoạt động (`Địa điểm hoạt động`) bị giới hạn cứng theo gói dịch vụ (ví dụ Standard ít kho hơn Grow/Scale). Khi chạm trần, giao diện sẽ hiển thị nút `Mua thêm` — Agent **TUYỆT ĐỐI KHÔNG bấm `Mua thêm`**.
  - Tính năng `Bảng giá` đa kênh/B2B (`/admin/products/pricing_list`) có thể yêu cầu gói **Grow / Scale** hoặc add-on tương ứng.
- **Pre-flight Check phiên đăng nhập & Hạn mức Kho:**
  1. Mở `https://{store_domain}/admin/settings/locations`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Kiểm tra hạn mức số lượng kho trên gói hiện tại (ví dụ `2/5 địa điểm`) và xác định rõ kho nào đang mang nhãn `Mặc định` (không được khóa/xóa kho mặc định).
  4. Xác nhận tài khoản đang đăng nhập có thấy đầy đủ chi nhánh mục tiêu hay không (nếu Staff bị giới hạn phạm vi kho, dừng và yêu cầu Owner thao tác).

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/locations` | Tab `Địa điểm hoạt động` / `Địa điểm đã khoá` | `Thêm địa điểm`, `Mua thêm` (HARD-BLOCKED) | Danh sách kho: Tên kho, Địa chỉ, Nhãn `Mặc định`, Bộ đếm hạn mức số lượng kho đang dùng / tối đa theo gói |
| `/admin/settings/locations/{id}` | Chi tiết Địa điểm & Kho hàng | `Lưu`, `Khoá địa điểm` (HARD-BLOCKED), `Xóa` (HARD-BLOCKED) | `Tên kho`, `Số điện thoại`, `Địa chỉ`, `Tỉnh/Thành phố`, `Quận/Huyện`, `Phường/Xã`, checkbox `Địa điểm lấy hàng`, checkbox `Cập nhật thông tin xuất hoá đơn` |
| `/admin/products/inventories` | Quản lý Tồn kho trực quan | Dropdown chọn `Kho hàng`, `Lọc`, `Tìm kiếm`, `Xuất file`, `Nhập file` (HARD-BLOCKED ghi đè) | Bảng tồn kho theo SKU: `Tồn kho`, `Đang giao dịch` (đơn chưa xuất), `Có thể bán`, `Hàng đang về` |
| `/admin/products/pricing_list` | Danh sách Bảng giá đa kênh | `Tạo bảng giá`, `Lọc`, `Tìm kiếm` | Quản lý giá bán riêng theo Kênh bán, Chi nhánh hoặc Nhóm khách hàng B2B (chi tiết xem `catalog-pricing-list-b2b-proposal`) |

> **Liên hệ kỹ thuật:** Kho có tick `Địa điểm lấy hàng` là điều kiện bắt buộc để xuất hiện trong luồng đẩy đơn của NVC (`/admin/settings/shipments`) và tùy chọn `Nhận tại cửa hàng` (`/admin/settings/checkouts`).

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `audit_locations_quota` | `audit_locations_quota` \| `update_location_address` \| `toggle_pickup_invoice_flags` \| `inventories_ui_audit` \| `pricing_list_ops` |
| `location_id_or_name` | `string` | Khi sửa kho | — | ID hoặc Tên kho cần mở tại `/admin/settings/locations/{id}` |
| `location_updates` | `object` | Khi `update_location_address` / `toggle_pickup_invoice_flags` | `{}` | `{name, phone, address, province, district, ward, is_pickup_location: bool, update_invoice_info: bool}` |
| `inventory_filter` | `object` | Khi `inventories_ui_audit` | `{}` | `{warehouse_name, low_stock_threshold?: number, export_csv?: bool}` |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi qua cổng Screenshot-Before-Save |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Rà soát danh sách kho & Hạn mức gói dịch vụ (`audit_locations_quota` — Read-Only)
- **Điều kiện kích hoạt:** Trước khi mở thêm chi nhánh bán lẻ mới hoặc khi gặp lỗi không thể đẩy đơn về kho phụ.
1. Điều hướng tới `https://{store_domain}/admin/settings/locations`.
2. Kiểm tra bộ đếm hạn mức số lượng kho (ví dụ `3/5 địa điểm`) ở đầu trang để xác định số slot trống còn lại.
3. Đọc toàn bộ danh sách ở tab `Địa điểm hoạt động` (xác định kho nào đang gắn nhãn `Mặc định`, kho nào có địa chỉ còn thiếu cấp hành chính), sau đó chuyển sang tab `Địa điểm đã khoá` để rà soát các kho cũ.
4. Lập báo cáo tổng hợp tình trạng kho và số slot còn trống; nếu đã đầy slot, ghi chú rõ không tự bấm `Mua thêm`.

### Scenario 2: Cập nhật chi tiết kho & Chuẩn hóa địa chỉ 3 cấp (`update_location_address`)
- **Điều kiện kích hoạt:** Khi đổi địa chỉ kho vật lý, đổi SĐT thủ kho hoặc NVC báo lỗi *Địa chỉ lấy hàng không hợp lệ*.
1. Tại `/admin/settings/locations`, click vào tên kho mục tiêu theo `location_id_or_name` để mở `/admin/settings/locations/{id}`.
2. Ghi lại giá trị gốc của `Tên kho`, `Số điện thoại`, `Địa chỉ`, `Tỉnh/Thành phố`, `Quận/Huyện`, `Phường/Xã`.
3. Cập nhật thông tin mới từ `location_updates`, đặc biệt chọn đầy đủ cả 3 cấp hành chính (hoặc 2 cấp theo danh mục mới nhất của Haravan) và số điện thoại người phụ trách kho để bưu tá liên hệ lấy hàng.
4. Kiểm tra lại không để ký tự đặc biệt gây lỗi mã vận đơn trong `Tên kho` và `Địa chỉ`.
5. **DỪNG — chưa bấm `Lưu`**, chuyển sang bước chụp ảnh preview.

### Scenario 3: Bật/Tắt cờ `Địa điểm lấy hàng` & `Cập nhật thông tin xuất hoá đơn` (`toggle_pickup_invoice_flags`)
- **Điều kiện kích hoạt:** Khi kích hoạt luồng NVC đến lấy hàng tại kho, bật `Nhận tại cửa hàng` trên Checkout hoặc đồng bộ thông tin chi nhánh xuất HĐĐT.
1. Mở `/admin/settings/locations/{id}` của kho mục tiêu.
2. Kiểm tra checkbox `Địa điểm lấy hàng`:
   - Tick **Bật** nếu muốn NVC (GHN/GHTK/VTP/Ahamove) đến lấy hàng tại kho này và muốn kho hiển thị trong tùy chọn `Nhận tại cửa hàng` trên trang Checkout.
   - Cảnh báo trước nếu yêu cầu **Tắt** khi kho đang là điểm lấy hàng duy nhất của cửa hàng.
3. Kiểm tra checkbox `Cập nhật thông tin xuất hoá đơn`: tick **Bật** (và nhập thông tin pháp nhân/MST chi nhánh nếu giao diện yêu cầu) để đồng bộ thông tin kho với phân hệ Hóa đơn điện tử (`/admin/settings/vat_setting`).
4. **DỪNG — chưa bấm `Lưu`**.

### Scenario 4: Kiểm tra Tồn kho trực quan & Xuất file kiểm kê theo kho (`inventories_ui_audit`)
- **Điều kiện kích hoạt:** Cần kiểm tra nhanh chênh lệch tồn kho từng chi nhánh hoặc xuất file CSV đối chiếu kiểm kê định kỳ.
1. Điều hướng tới `https://{store_domain}/admin/products/inventories`.
2. Chọn đúng `Kho hàng` cần kiểm tra trên dropdown lọc kho (tránh để mặc định *Tất cả kho* khi cần kiểm kê riêng 1 chi nhánh).
3. Rà soát các cột trạng thái quan trọng cho từng SKU:
   - `Tồn kho`: Tổng số lượng thực tế đang nằm trong kho.
   - `Đang giao dịch`: Số lượng đang bị giữ bởi các đơn hàng chưa hoàn tất giao.
   - `Có thể bán`: Số lượng còn lại khách được phép đặt (`Tồn kho - Đang giao dịch`).
   - `Hàng đang về`: Số lượng từ phiếu nhập hàng đang chờ nhận.
4. Gắn cờ cảnh báo các SKU có `Có thể bán <= 0` nhưng `Đang giao dịch > 0` (nguy cơ oversell / kẹt đơn) hoặc dưới ngưỡng `low_stock_threshold`.
5. Nếu người dùng yêu cầu tải bảng kiểm kê (`export_csv = true`), click `Xuất file` (chế độ chỉ đọc); **TUYỆT ĐỐI KHÔNG bấm `Nhập file`** ghi đè số tồn kho.

### Scenario 5: Quản trị Bảng giá đa kênh / B2B (`pricing_list_ops`)
- **Điều kiện kích hoạt:** Cửa hàng chạy gói Grow/Scale cần quản lý bảng giá riêng cho đại lý B2B, kênh POS hoặc từng chi nhánh.
1. Điều hướng tới `https://{store_domain}/admin/products/pricing_list`.
2. Rà soát danh sách bảng giá hiện có: tên bảng giá, trạng thái (`Đang áp dụng` / `Chưa áp dụng` / `Hết hạn`), phạm vi áp dụng (Kênh bán, Chi nhánh, Nhóm khách hàng) và mức ưu tiên khi trùng sản phẩm.
3. Ghi chú kiểm chuẩn không để 2 bảng giá trùng phạm vi và trùng khoảng thời gian gây xung đột giá bán.
4. Nếu cần tạo mới hoặc chỉnh sửa bảng giá chi tiết theo nhóm khách B2B/chi nhánh, thực hiện theo đúng runbook chuyên sâu của skill `catalog-pricing-list-b2b-proposal` (điền form đầy đủ nhưng **DỪNG trước nút `Lưu`**).

## 5. Quy trình An toàn 4 Pha (4-Phase Browser Safety Protocol)

### Pha 1: Pre-State Capture (Chụp Ảnh Trạng Thái Gốc)
- Mở `/admin/settings/locations/{id}` (hoặc `/admin/products/inventories`, `/admin/products/pricing_list`), xác minh phiên đăng nhập hợp lệ.
- Chụp ảnh trạng thái gốc (`artifacts/locations_pre.png`) ghi nhận rõ tên kho, địa chỉ hành chính cũ, SĐT và trạng thái 2 checkbox `Địa điểm lấy hàng` / `Cập nhật thông tin xuất hoá đơn`.

### Pha 2: Stage Without Saving (Điền Thông Tin Kho Chưa Lưu)
- Cập nhật tên kho, SĐT bàn giao, địa chỉ 3 cấp (hoặc 2 cấp chuẩn mới) và tick/bỏ tick 2 checkbox theo Scenario ở Mục 4.
- Với `/admin/products/inventories`, chỉ thực hiện lọc/đọc hoặc `Xuất file` kiểm kê; tuyệt đối không dùng `Nhập file`.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu`**.

### Pha 3: Screenshot-Before-Save & Human Approval Gate
- Chụp ảnh chi tiết kho đã chỉnh sửa (`artifacts/locations_preview.png`), nhìn rõ đủ địa chỉ hành chính và 2 checkbox.
- Gửi bảng so sánh `Before → After` (Mục 6) nêu rõ ảnh hưởng lên NVC lấy hàng, Nhận tại cửa hàng và xuất HĐĐT, sau đó dừng chờ người dùng xác nhận (`confirmation_required: true`).

### Pha 4: Save & Post-Save Reload Verification
- Sau khi người dùng xác nhận, bấm nút `Lưu` và chờ toast *"Cập nhật thành công"*.
- Nhấn `F5` reload trang `/admin/settings/locations/{id}`, xác minh địa chỉ và 2 checkbox đã lưu bền vững, chụp `artifacts/locations_post.png`.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/locations/{id}`)

| Trường cấu hình Kho | Trước (Before) | Đề xuất (After) | Ảnh hưởng vận hành |
| :--- | :--- | :--- | :--- |
| `Tên kho` | `Kho mặc định` | `Kho Trung Tâm HCM - Q7` | Rõ ràng trên phiếu in & vận đơn |
| `Số điện thoại` | *(Trống)* | `028 7300 1234` | Bưu tá NVC liên hệ lấy hàng |
| `Địa chỉ hành chính` | Thiếu `Phường/Xã` | `P. Tân Phong, Q. 7, TP.HCM` | Sửa lỗi tính cước NVC tự động |
| `Địa điểm lấy hàng` | `Tắt (false)` | `Bật (true)` | Cho phép NVC lấy hàng & Nhận tại cửa hàng |
| `Cập nhật thông tin xuất hoá đơn` | `Tắt (false)` | `Bật (true)` | Đồng bộ thông tin xuất HĐĐT chi nhánh |

> **Yêu cầu xác nhận:** Thông tin kho `Kho Trung Tâm HCM - Q7` đã được cập nhật sẵn tại `/admin/settings/locations/{id}` (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng xác nhận **"Đồng ý lưu cấu hình kho hàng"** để Agent bấm nút `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-locations-inventory-ops",
  "scenario": "toggle_pickup_invoice_flags",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/locations/102456",
  "phase_status": "awaiting_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/locations_pre.png",
    "preview_screenshot": "artifacts/locations_preview.png",
    "post_screenshot": "artifacts/locations_post.png"
  },
  "checks_passed": {
    "location_quota_within_plan": true,
    "address_levels_complete": true,
    "default_warehouse_protected": true
  },
  "changes_staged": {
    "location_name": "Kho Trung Tâm HCM - Q7",
    "address_3_levels_complete": true,
    "is_pickup_location": true,
    "update_invoice_info": true
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Mua thêm` tại `/admin/settings/locations` | **HARD-BLOCKED** | Phát sinh chi phí mua thêm kho trên gói Haravan (`/admin/settings/billings`) |
| `Khoá địa điểm` / `Xóa` kho đang có tồn hoặc đơn mở | **HARD-BLOCKED** | Gây kẹt xử lý đơn hàng đang giao dịch và lệch sổ kiểm kê kho |
| `Nhập file` ghi đè tồn kho tại `/admin/products/inventories` | **HARD-BLOCKED** | Nguy cơ ghi đè sai hàng loạt tồn kho; phải qua quy trình kiểm kê & dry-run riêng |
| Trang đăng nhập `accounts.haravan.com` | **HANDOFF GATE** | Dừng ngay để người dùng tự đăng nhập; không hỏi/tự nhập mật khẩu hay OTP |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Chạm giới hạn số kho của gói dịch vụ:** Nút `Thêm địa điểm` chuyển thành thông báo hết hạn mức và gợi ý `Mua thêm` → Dừng ngay, báo số kho đang dùng trên giới hạn gói, không tự bấm `Mua thêm`.
2. **Dropdown `Phường/Xã` không khớp địa danh sau sáp nhập hành chính:** Chọn đúng đơn vị hành chính tương ứng gần nhất trong danh mục chuẩn của Haravan và ghi chú rõ trong bảng Preview để Chủ kho xác nhận với bưu tá NVC.
3. **Không thể khóa/tắt kho do hệ thống báo còn tồn kho hoặc đơn chưa xử lý:** Kiểm tra cột `Tồn kho` và `Đang giao dịch` của kho đó tại `/admin/products/inventories`, hoàn tất hoặc chuyển kho trước khi thao tác.
4. **Staff chỉ thấy 1 kho thay vì toàn bộ hệ thống kho:** Do tài khoản Staff bị giới hạn phạm vi chi nhánh tại `/admin/settings/accounts` → Yêu cầu Owner đăng nhập hoặc mở rộng phạm vi kho cho Staff.
5. **Tắt nhầm `Địa điểm lấy hàng` làm mất lựa chọn Nhận tại cửa hàng trên Checkout:** Kiểm tra lại xem còn kho nào khác bật cờ này không; nếu là kho duy nhất, bật lại ngay và reload kiểm chứng.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Đối chiếu `artifacts/locations_pre.png` của `/admin/settings/locations/{id}`.
2. Mở lại chi tiết kho vừa sửa, điền lại chính xác `Tên kho`, `Số điện thoại`, địa chỉ hành chính 3 cấp và trạng thái 2 checkbox `Địa điểm lấy hàng` / `Cập nhật thông tin xuất hoá đơn` như ban đầu.
3. Bấm `Lưu`, chờ toast *"Cập nhật thành công"* và nhấn `F5` reload trang xác minh.
4. Nếu có chỉnh sửa bảng giá tại `/admin/products/pricing_list`, thực hiện rollback theo runbook của `catalog-pricing-list-b2b-proposal`.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Xác nhận kho trung tâm hiển thị trong tab `Địa điểm hoạt động` với địa chỉ chuẩn, không bị mất nhãn `Mặc định`.
- [ ] Nếu bật `Địa điểm lấy hàng`: kiểm tra lại trên `/admin/settings/shipments` (tạo vận đơn thử) và `/admin/settings/checkouts` (`Nhận tại cửa hàng`) xem kho đã xuất hiện đầy đủ.
- [ ] Nếu bật `Cập nhật thông tin xuất hoá đơn`: kiểm tra chéo với kế toán tại `/admin/settings/vat_setting`.
- [ ] Kiểm tra `/admin/products/inventories` cho kho vừa cập nhật: đảm bảo số liệu `Tồn kho` và `Có thể bán` không bị thay đổi ngoài ý muốn.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `inventory-stock-audit` & `inventory-adjust-proposal` (`GET /com/locations.json`, `GET /com/inventory_locations.json`): Đọc đối chiếu danh sách ID kho và kiểm tra tồn kho đa kho qua Commerce API.
- `skills/api-mcp/` → `catalog-audit`: Kiểm tra sản phẩm/biến thể có đang bật theo dõi tồn kho (`inventory_management = haravan`) trên đúng kho hay không.
- `skills/browser-ui/` → `admin-ui-shipping-carriers-setup`, `admin-ui-checkout-settings`, `catalog-pricing-list-b2b-proposal`, `admin-ui-tax-einvoice-accounting`.
