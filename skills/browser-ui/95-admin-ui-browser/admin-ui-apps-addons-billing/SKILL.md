---
name: admin-ui-apps-addons-billing
description: "Quản lý & kiểm toán chỉ đọc trên Haravan Admin: danh sách Ứng dụng (/admin/apps), kiểm tra Private App/OAuth, Tiện ích đơn hàng (/admin/settings/order_addon) và rà soát Gói dịch vụ / Hóa đơn (/admin/settings/billings)."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 95-admin-ui-browser
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/apps"
    - "UI /admin/settings/order_addon"
    - "UI /admin/settings/billings"
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

# Haravan Admin UI — Kiểm Toán Ứng Dụng, Tiện Ích & Gói Dịch Vụ (`/admin/apps` & `/admin/settings/billings`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Thực hiện rà soát **chỉ đọc (`Read-Only L1`)** toàn bộ hệ sinh thái tích hợp và chi phí nền tảng trên Haravan Admin không cần API token: kiểm kê danh sách ứng dụng bên thứ 3 đã cài tại `/admin/apps`, kiểm tra trạng thái **Private App / OAuth App** (phạm vi quyền cấp phép, app không còn dùng cần rà soát bảo mật — tuyệt đối không in token/secret), kiểm tra cấu hình **Tiện ích đơn hàng** (`/admin/settings/order_addon`), và rà soát **Gói dịch vụ / Hạn mức / Hóa đơn thanh toán Haravan** (`/admin/settings/billings`).
- **Phạm vi UI:** `/admin/apps`, `/admin/settings/order_addon` và `/admin/settings/billings`. Skill tuyệt đối không cài/gỡ app, không xoay/tạo lại secret và không bấm bất kỳ nút nâng cấp/mua thêm gói dịch vụ nào.
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Xem đầy đủ `/admin/apps`, Private Apps, `/admin/settings/order_addon` và `/admin/settings/billings` (gói dịch vụ, lịch sử hóa đơn).
  - **Staff:** Thông thường Staff chỉ thấy một số app được phân quyền; mục `Billing` (`/admin/settings/billings`) và `Ứng dụng riêng (Private Apps)` thường chỉ dành riêng cho **Chủ cửa hàng (Owner)**. Nếu Staff không truy cập được hoặc thấy thông báo `Bạn không có quyền truy cập`, dừng và báo rõ cần tài khoản Owner.
- **Yêu cầu Gói dịch vụ Haravan:** Màn hình `/admin/apps` và `/admin/settings/billings` có trên mọi gói; số lượng chi nhánh, nhân viên, dung lượng file và quyền dùng tính năng nâng cao hiển thị trực tiếp trong trang `Billing`.
- **Pre-flight Check bắt buộc:**
  1. Kiểm tra phiên đăng nhập qua `admin-ui-session-navigator` và xác minh đúng cửa hàng đích.
  2. Áp dụng quy tắc **Zero Secret Exposure**: nếu màn hình Private App có hiển thị API Key / Access Token / Client Secret, **tuyệt đối không chụp ảnh lộ secret nguyên văn, không copy và không ghi vào log/JSON**.

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

| Màn hình kiểm toán | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Thông tin cần đọc / Kiểm tra |
| :--- | :--- | :--- | :--- |
| Danh sách Ứng dụng | `/admin/apps` | Danh sách thẻ/bảng `Ứng dụng đã cài đặt`, nút `Kho ứng dụng`, tab/mục `Ứng dụng riêng (Private Apps)` (nếu có) | Tên ứng dụng, trạng thái hoạt động, ngày cài đặt, nhóm quyền truy cập (scopes), dấu hiệu app dư thừa |
| Chi tiết App / OAuth | `/admin/apps` → Click tên app hoặc `Chi tiết` / `Quyền truy cập` | `Quyền truy cập ứng dụng`, `Thông tin nhà phát triển`, nút `Gỡ cài đặt` (**Hard-Blocked**) | Kiểm tra app bên thứ 3 có yêu cầu quyền quá rộng (ví dụ `write_orders`/`read_customers` không cần thiết) |
| Tiện ích đơn hàng | `/admin/settings/order_addon` | Các khối cấu hình tiện ích mở rộng cho quy trình xử lý đơn hàng (ví dụ: quy tắc tự động xử lý, mã đơn hàng, tích hợp tiện ích vận đơn/in ấn/đồng bộ) | Ghi nhận các tiện ích đang `Bật` / `Tắt` và đối chiếu với quy trình vận hành thực tế |
| Gói dịch vụ & Hạn mức | `/admin/settings/billings` | Khối `Thông tin gói dịch vụ` (Tên gói: Standard/Pro/Grow/Scale, Ngày hết hạn, Chu kỳ gia hạn), khối `Hạn mức sử dụng` | Số nhân viên đang dùng/giới hạn, số kho/chi nhánh, dung lượng lưu trữ, dịch vụ bổ trợ (Harasocial, Haraloyalty, POS...) |
| Lịch sử Hóa đơn | `/admin/settings/billings` (Khối dưới) | Bảng `Lịch sử thanh toán` / `Hóa đơn` | Mã hóa đơn, ngày lập, dịch vụ/gói, số tiền, trạng thái (`Đã thanh toán` / `Chờ thanh toán`), ngày gia hạn tiếp theo |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `full_apps_billing_audit` | `full_apps_billing_audit` \| `installed_apps_inventory` \| `private_app_oauth_review` \| `order_addon_audit` \| `billing_plan_quota_check` |
| `check_expiry_days_threshold` | `integer` | Không | `30` | Ngưỡng cảnh báo sớm (số ngày trước khi hết hạn gói dịch vụ Haravan hoặc add-on), `7 <= value <= 90` |
| `flag_unused_apps` | `boolean` | Không | `true` | Gắn cờ các ứng dụng đã cài nhưng không còn dùng trong quy trình hiện tại (dựa trên danh sách `expected_apps`) |
| `expected_apps` | `array<string>` | Không | `[]` | Danh sách tên ứng dụng cửa hàng xác nhận đang sử dụng chính thức để đối chiếu chênh lệch |
| `mask_all_secrets` | `boolean` | Không | `true` | Bắt buộc luôn `true` — không bao giờ đọc/xuất token hay secret từ màn hình Private App |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Kiểm kê toàn bộ Ứng dụng đã cài đặt (`/admin/apps`)
1. Điều hướng tới `https://{store_domain}/admin/apps`, chờ danh sách ứng dụng tải hoàn tất.
2. Cuộn qua toàn bộ danh sách `Ứng dụng đã cài đặt`, ghi nhận đầy đủ: Tên ứng dụng, Phân loại (Vận chuyển, Kế toán/Hóa đơn điện tử, Marketing/ZNS, Reviews, ERP...), Trạng thái (`Đang hoạt động` / `Chưa kích hoạt`).
3. Đối chiếu với danh sách `expected_apps` (nếu có): đánh dấu các ứng dụng lạ hoặc ứng dụng cài thử nghiệm cũ không còn sử dụng (gây chậm storefront nếu chèn script tag hoặc rủi ro lộ dữ liệu đơn hàng/khách hàng).
4. **Tuyệt đối không bấm `Gỡ cài đặt` hay `Cài đặt ứng dụng mới`**; chụp ảnh danh sách tổng quan (`preview_screenshot`) và liệt kê khuyến nghị dọn dẹp để Owner tự quyết định.

### Kịch bản 2: Rà soát Private App / OAuth Scopes (Zero Secret Exposure)
1. Tại `/admin/apps`, mở khu vực `Ứng dụng riêng` / `Private Apps` hoặc xem phần `Quyền truy cập` của các ứng dụng tích hợp (ERP, CRM, Webhook).
2. Kiểm tra danh sách ứng dụng nội bộ/đối tác đang được cấp quyền API: ghi nhận Tên app, danh sách Scopes đang mở (ví dụ `com.read_orders`, `com.write_products`, `com.read_customers`), và trạng thái kích hoạt.
3. Đối chiếu nguyên tắc **Least-Privilege**: gắn cờ cảnh báo cho bất kỳ app nào chỉ dùng để đọc báo cáo nhưng lại đang giữ quyền ghi (`write_*`) hoặc quyền đọc dữ liệu khách hàng không cần thiết.
4. **Tuyệt đối không click nút `Hiện mật khẩu / Reveal Token`**, không bấm `Tạo lại Token` và không chụp vùng chứa khóa bí mật nếu khóa đang hiển thị mở.

### Kịch bản 3: Kiểm tra cấu hình Tiện ích đơn hàng (`/admin/settings/order_addon`)
1. Điều hướng tới `https://{store_domain}/admin/settings/order_addon` (hoặc từ `/admin/settings` → bấm thẻ `Tiện ích đơn hàng`).
2. Đọc toàn bộ các mục tiện ích đơn hàng đang hiển thị trên trang: ghi nhận trạng thái công tắc (`Bật` / `Tắt`) và thông số cấu hình hiện hành của từng tiện ích.
3. Đối chiếu với nhu cầu vận hành thực tế (ví dụ: tiện ích đã bật nhưng không dùng gây thừa thao tác cho nhân viên sale/kho, hoặc tiện ích cần thiết đang tắt).
4. **Chỉ đọc, không gạt công tắc và không bấm `Lưu`**; chụp ảnh hiện trạng để làm căn cứ trước khi đề xuất thay đổi.

### Kịch bản 4: Rà soát Gói dịch vụ, Hạn mức & Lịch sử Hóa đơn (`/admin/settings/billings`)
1. Điều hướng tới `https://{store_domain}/admin/settings/billings` (từ `/admin/settings` → bấm thẻ `Billing`).
2. Đọc khối **Thông tin gói dịch vụ**: Tên gói hiện tại (Standard / Pro / Grow / Scale), ngày bắt đầu, ngày hết hạn, và danh sách gói bổ trợ đi kèm (Haravan POS, Harasocial, Haraloyalty, Omni...).
3. Kiểm tra **Hạn mức tài nguyên**: so sánh mức sử dụng thực tế so với giới hạn gói (số tài khoản nhân viên, số kho/chi nhánh, dung lượng file) và tính số ngày còn lại tới hạn gia hạn; bật cảnh báo đỏ nếu còn ≤ `check_expiry_days_threshold` ngày.
4. Đọc bảng **Lịch sử hóa đơn**: kiểm tra có hóa đơn nào đang ở trạng thái `Chờ thanh toán` hay quá hạn không; **tuyệt đối không bấm `Nâng cấp gói`, `Gia hạn`, `Mua thêm` hay `Thanh toán ngay`**.

### Kịch bản 5: Lập Lịch Cảnh Báo Gia Hạn & Kế Hoạch Tối Ưu Hạn Mức Gói (Read-Only Summary)
1. Tổng hợp kết quả từ 3 màn hình (`/admin/apps`, `/admin/settings/order_addon`, `/admin/settings/billings`) thành bảng kiểm toán duy nhất.
2. Nếu hạn mức nhân viên hoặc chi nhánh đạt `>= 85%`, đối chiếu chéo với `admin-ui-staff-roles-config` (ràng buộc nhân viên đã nghỉ việc chưa khóa tài khoản) và `admin-ui-locations-inventory-ops` (kho ngừng hoạt động) trước khi Owner cân nhắc mua thêm hạn mức.
3. Xuất danh sách hành động ưu tiên cho Owner kèm ngày hạn chót gia hạn rõ ràng; không thực hiện bất kỳ thao tác ghi nào.

### Ma Trận Đánh Giá Rủi Ro Ứng Dụng & Gói Dịch Vụ (Audit Severity Matrix)

| Mức độ cảnh báo | Dấu hiệu phát hiện trên `/admin/apps` & `/admin/settings/billings` | Hành động khuyến nghị cho Owner |
| :--- | :--- | :--- |
| 🔴 **Nghiêm trọng (Critical)** | Gói dịch vụ còn `<= 7 ngày` hết hạn, có hóa đơn quá hạn, hoặc Private App chỉ đọc nhưng có quyền `write_orders` / `write_customers` | Gia hạn gói ngay / Thu hẹp scope OAuth & kiểm tra lịch sử truy cập |
| 🟠 **Cao (High)** | Gói còn `8–30 ngày` hết hạn, hạn mức Nhân viên/Chi nhánh đạt `>= 90%`, hoặc có ứng dụng lạ không rõ chủ sở hữu | Lập kế hoạch gia hạn, khóa tài khoản NV đã nghỉ, rà soát app lạ |
| 🟡 **Trung bình (Medium)** | Có app cài thử nghiệm cũ không còn sử dụng hoặc tiện ích đơn hàng bật dư thừa | Kiểm tra Script Tag tồn dư rồi Owner chủ động gỡ app |
| 🟢 **Ổn định (Healthy)** | Đủ hạn mức (`< 80%`), hạn gói `> 30 ngày`, 100% app đúng mục đích và Least-Privilege | Duy trì kiểm toán định kỳ hàng tháng |

## 5. Quy trình An toàn 4 Pha (Read-Only Audit Protocol)

1. **Pha 1 — Session & Role Pre-Check (Xác minh quyền Owner):**
   - Xác minh phiên đăng nhập qua `admin-ui-session-navigator` và kiểm tra đúng `store_domain`.
   - Kiểm tra xem tài khoản hiện tại có thấy thẻ `Billing` tại `/admin/settings` và mục `Ứng dụng riêng` tại `/admin/apps` không (phân biệt rõ quyền Owner vs Staff), sau đó chụp `pre_screenshot`.
2. **Pha 2 — Read-Only Inspection (`mode: read`):**
   - Mở lần lượt `/admin/apps`, `/admin/settings/order_addon` và `/admin/settings/billings`.
   - Chỉ cuộn trang và đọc thông tin tổng quan (tên app, scopes, công tắc tiện ích, tên gói, hạn mức, lịch sử hóa đơn).
   - **Tuyệt đối không bấm bất kỳ nút nào làm thay đổi trạng thái (`Cài đặt`, `Gỡ cài đặt`, `Lưu`, `Tạo lại Token`, `Nâng cấp gói`, `Gia hạn`)**.
3. **Pha 3 — Secret Redaction & Evidence Capture (Bảo vệ bí mật tuyệt đối):**
   - Kiểm tra màn hình trước khi chụp ảnh: tuyệt đối không mở `Hiện mật khẩu / Reveal Token` và không chụp vùng chứa `Access Token` / `Client Secret` / số thẻ thanh toán.
   - Chụp `preview_screenshot` vùng tổng quan an toàn làm bằng chứng kiểm toán.
4. **Pha 4 — Audit Report & Owner Action Plan:**
   - Xuất bảng kiểm toán tổng hợp Apps / Private Apps / Tiện ích đơn hàng / Gói dịch vụ & Hóa đơn + JSON Output Schema.
   - Phân loại rõ mức độ ưu tiên (`Khẩn cấp — Sắp hết hạn gói`, `Bảo mật — App dư thừa/thừa quyền`, `Tối ưu — Hạn mức nhân viên/chi nhánh`) để **Owner** tự thao tác trên trình duyệt.

### Checklist Kiểm Toán Bảo Mật & Chi Phí Nền Tảng (Platform Hygiene Checklist)

- [ ] Toàn bộ ứng dụng tại `/admin/apps` đều có chủ sở hữu nghiệp vụ rõ ràng (không tồn tại app thử nghiệm bỏ quên).
- [ ] Mọi Private App / OAuth App chỉ được cấp đúng scopes tối thiểu theo nguyên tắc **Least-Privilege**.
- [ ] Không có bất kỳ `HARAVAN_ACCESS_TOKEN` / `CLIENT_SECRET` nào bị đọc, in ra chat hoặc lọt vào ảnh chụp.
- [ ] Ngày hết hạn gói dịch vụ Haravan và add-on (POS/Harasocial/Haraloyalty) còn lớn hơn ngưỡng cảnh báo (`check_expiry_days_threshold`).
- [ ] Không có hóa đơn `Chờ thanh toán` quá hạn và hạn mức nhân viên/chi nhánh/dung lượng file còn dư địa an toàn (< 85%).

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Kiểm toán Ứng dụng, Tiện ích & Gói dịch vụ (Read-Only Snapshot)

| Hạng mục kiểm toán | Hiện trạng ghi nhận (Current State) | Mức đánh giá | Khuyến nghị hành động (Owner thực hiện) |
| :--- | :--- | :--- | :--- |
| Gói dịch vụ Haravan | `Haravan Grow` — Hết hạn `15/12/2026` (còn 20 ngày) | ⚠️ Sắp đến hạn | Lập kế hoạch gia hạn trước 10/12 để tránh gián đoạn POS/Website |
| Hạn mức tài nguyên | Nhân viên: `9/10`, Chi nhánh: `3/5`, File: `62%` | ⚠️ Gần chạm trần NV | Rà soát nhân viên đã nghỉ việc tại `/admin/settings/accounts` |
| Ứng dụng đã cài (`/admin/apps`) | `11` apps (`8` đang dùng, `3` app thử nghiệm cũ không dùng) | 🟡 Cần dọn dẹp | Owner kiểm tra script tag & cân nhắc gỡ 3 app dư thừa |
| Private Apps / OAuth | `2` Private Apps (1 app đọc báo cáo nhưng có `write_orders`) | 🔴 Thừa quyền | Owner thu hẹp scope về `com.read_orders` để giảm rủi ro |
| Tiện ích đơn hàng (`/order_addon`) | Đang bật 2/4 tiện ích theo đúng quy trình kho | ✅ Ổn định | Giữ nguyên cấu hình hiện tại |
| Lịch sử Hóa đơn (`/billings`) | `0` hóa đơn quá hạn, hóa đơn gần nhất `Đã thanh toán` | ✅ Đầy đủ | Lưu chứng từ hóa đơn GTGT cho bộ phận kế toán |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-apps-addons-billing",
  "mode": "read",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/billings",
  "scenario": "full_apps_billing_audit",
  "session_authenticated": true,
  "owner_access_verified": true,
  "dry_run": true,
  "secrets_exposed": false,
  "pre_screenshot": "artifacts/apps_list_pre.png",
  "preview_screenshot": "artifacts/billing_overview_audit.png",
  "post_screenshot": null,
  "audit_findings": {
    "plan_name": "Haravan Grow",
    "days_until_expiry": 20,
    "staff_quota_used": "9/10",
    "locations_quota_used": "3/5",
    "installed_apps_count": 11,
    "flagged_unused_apps_count": 3,
    "overprivileged_private_apps_count": 1,
    "order_addons_enabled": 2,
    "unpaid_invoices_count": 0
  },
  "warnings": [
    "Subscription expires in 20 days (threshold: 30 days).",
    "1 Private App holds write_orders scope despite read-only usage."
  ],
  "saved_verified": false
}
```

### Bảng Đối Chiếu Nhanh Quyền Truy Cập 3 Màn Hình (Owner vs Staff)

| Màn hình kiểm toán | Owner (Chủ cửa hàng) | Staff (Nhân viên phân quyền) | Hành vi chuẩn khi thiếu quyền |
| :--- | :--- | :--- | :--- |
| `/admin/apps` (Ứng dụng bên thứ 3) | ✅ Xem đủ & quản lý | ⚠️ Chỉ thấy app được cấp quyền | Ghi nhận danh sách app thấy được + chú thích quyền Staff |
| `/admin/apps` (Private Apps / OAuth) | ✅ Xem danh sách & scopes | ❌ Thường bị ẩn hoàn toàn | Dừng mục Private App, báo cần tài khoản Owner |
| `/admin/settings/order_addon` | ✅ Xem & cấu hình | ⚠️ Tùy quyền `Cấu hình` | Chỉ đọc trạng thái Bật/Tắt nếu thấy, không tự sửa |
| `/admin/settings/billings` | ✅ Xem gói, hạn mức & hóa đơn | ❌ Mặc định khóa với Staff | Dừng mục Billing, báo rõ cần Owner đăng nhập để kiểm toán |

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm trên 3 màn hình này:**
  - `Nâng cấp gói`, `Nâng cấp gói scale`, `Mua thêm`, `Gia hạn ngay`, `Thanh toán` tại `/admin/settings/billings` (phát sinh giao dịch tài chính thực tế).
  - `Gỡ cài đặt` (`Uninstall`), `Xóa ứng dụng`, `Cài đặt ứng dụng` tại `/admin/apps` (có thể làm đứt đồng bộ ERP/Vận chuyển/Hóa đơn điện tử đang chạy live).
  - `Tạo Private App`, `Tạo lại Token / Rotate Secret`, `Hiện mật khẩu` (vi phạm Zero Secret Exposure và có thể làm gãy tích hợp API hiện hành).
  - Bất kỳ công tắc `Bật/Tắt` hoặc nút `Lưu` nào tại `/admin/settings/order_addon` (skill này chỉ đọc L1).
- **Credential & Billing Handoff Gate:**
  - Mọi quyết định gia hạn gói, mua thêm chi nhánh/nhân viên hoặc nhập thông tin thanh toán phải do **Owner** tự thực hiện trực tiếp trên trình duyệt.
  - Gặp `accounts.haravan.com` → dừng ngay cho người dùng tự đăng nhập.

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Tài khoản Staff không thấy thẻ `Billing` tại `/admin/settings`:** Đây là cơ chế phân quyền bảo mật mặc định của Haravan dành riêng cho Owner. Agent không cố truy cập vòng; báo rõ mục `Billing` bị giới hạn quyền Owner và hoàn tất phần kiểm toán các mục mà Staff được phép xem.
2. **Ứng dụng đã gỡ nhưng vẫn để lại Script Tag làm chậm Website:** Một số app cũ khi gỡ bỏ không tự dọn script trên storefront. Agent khuyến nghị chạy kèm `storefront-script-tag-audit` (API) sau khi Owner gỡ app.
3. **Ứng dụng mở ra trang ngoài (External App / OAuth redirect):** Khi click một ứng dụng tại `/admin/apps`, Haravan có thể chuyển hướng sang domain đối tác thứ 3 (như sàn TMĐT, hãng vận chuyển, app CRM). Agent không tự bấm `Cho phép (Authorize)` hay nhập tài khoản đối tác; dừng và báo cho người dùng.
4. **Banner nhắc gia hạn / khuyến mãi nâng gói che khuất nội dung bảng:** Đóng banner bằng nút `X` hoặc cuộn qua; tuyệt đối không click vào nút kêu gọi hành động (`Xem bảng giá` / `Nâng cấp ngay`).
5. **Gói bổ trợ (Harasocial / Haraloyalty / POS) hết hạn lệch ngày với gói chính:** Kiểm tra riêng ngày hết hạn của từng gói con trong bảng chi tiết tại `/admin/settings/billings`, không chỉ đọc ngày hết hạn của gói Website chính.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Chính sách Rollback & Bàn Giao Owner (Read-Only L1)
- **Rollback thủ công:** Không áp dụng — skill `L1 mode: read` hoàn toàn chỉ đọc, không cài/gỡ app, không thay đổi công tắc tiện ích và không thực hiện giao dịch thanh toán gói.
- **Lưu ý an toàn khi Owner tự dọn app sau kiểm toán:** Trước khi Owner tự bấm `Gỡ cài đặt` một ứng dụng bên thứ 3 (như app vận chuyển, hóa đơn điện tử, chatbox hoặc ERP), luôn kiểm tra ứng dụng đó có còn webhook/script tag đang chạy live không và sao lưu cấu hình cần thiết.
- **Lưu ý khi Owner thu hẹp OAuth / Private App Scopes:** Thực hiện thử nghiệm trên cửa hàng `staging` trước khi thu hẹp quyền trên `production` để tránh làm gián đoạn luồng đồng bộ đơn hàng tự động.

### Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan
- Kiểm toán cấu hình cửa hàng, sức khỏe hệ thống, script tag tồn dư và webhook tích hợp qua API: `skills/api-mcp/10-store-bootstrap/store-config-audit`, `store-health-check`, `skills/api-mcp/80-theme-seo-cro/storefront-script-tag-audit`, `skills/api-mcp/00-core-platform/haravan-webhook-manager`.
- Thiết lập xác thực API/OAuth chuẩn Least-Privilege: `skills/api-mcp/00-core-platform/haravan-auth-setup`.
- Rà soát nhân viên, phân quyền & danh sách kho hàng để tối ưu hạn mức gói trên UI: `skills/browser-ui/95-admin-ui-browser/admin-ui-staff-roles-config`, `admin-ui-locations-inventory-ops`.
