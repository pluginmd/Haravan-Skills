---
name: admin-ui-staff-roles-config
description: "Thiết lập Vai trò phân quyền (/admin/settings/group_permissions), Nhóm phân công (/admin/settings/group_accounts) và Nhân viên (/admin/settings/accounts)."
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
    - "UI /admin/settings/accounts"
    - "UI /admin/settings/group_permissions"
    - "UI /admin/settings/group_accounts"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 20
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: true
---

# Haravan Admin UI: Staff Accounts, Roles & Assignment Groups (Critical L3)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Toàn bộ hệ thống phân quyền RBAC trên Haravan Admin — gồm **Nhân viên** (`/admin/settings/accounts`), **Vai trò** (`/admin/settings/group_permissions`) và **Nhóm phân công** (`/admin/settings/group_accounts`) — **không có REST API công khai** và chỉ quản trị được trên giao diện Haravan Admin UI.
- **Mức độ rủi ro L3 Critical (`separate_turn: true`):** Cấp thừa quyền (đặc biệt quyền `Xóa`, `Xuất dữ liệu khách hàng`, `Cấu hình thanh toán`, `Billing`) hoặc bấm nhầm `Chọn làm chủ sở hữu` / `Chấm dứt các phiên đăng nhập` có thể gây mất quyền kiểm soát cửa hàng hoặc rò rỉ dữ liệu khách hàng nghiêm trọng.
- **Phân quyền Owner vs Staff:**
  - **Bắt buộc tài khoản Chủ cửa hàng (Owner):** Chỉ Owner mới có toàn quyền tạo/sửa vai trò, mời nhân viên, xem toàn bộ danh sách tài khoản và giới hạn phạm vi kho. Tài khoản Staff thường sẽ bị ẩn nút `Thêm nhân viên` và `Tạo vai trò`.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Mỗi gói Haravan giới hạn số lượng tài khoản nhân viên tối đa (`x / y nhân viên`) tại `/admin/settings/accounts`. Khi hết slot, giao diện hiển thị nút `Mua thêm` — Agent **TUYỆT ĐỐI KHÔNG bấm `Mua thêm`**.
  - Tính năng `Nhóm phân công` (`/admin/settings/group_accounts`) để tự động chia đơn/tư vấn theo nhóm nhân sự và chi nhánh thường có trên các gói **Pro / Grow / Scale**.
- **Pre-flight Check phiên đăng nhập & Quyền Owner:**
  1. Mở `https://{store_domain}/admin/settings/accounts`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để Owner tự đăng nhập; tuyệt đối không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Xác nhận tài khoản đang đăng nhập có biểu tượng/nhãn **Chủ cửa hàng (Owner)** và thấy đầy đủ nút `Thêm nhân viên` tại `/accounts`, `Tạo vai trò` tại `/group_permissions`.
  4. Kiểm tra bộ đếm giới hạn tài khoản nhân viên theo gói (`x/y nhân viên`) trước khi đề xuất mời nhân sự mới; chuẩn bị quy tắc che PII (`a***@domain.com`, `090****678`) cho mọi báo cáo.

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/accounts` | `Chủ cửa hàng` & `Danh sách nhân viên` | `Thêm nhân viên`, `Mua thêm` (HARD-BLOCKED), `Chọn làm chủ sở hữu` (HARD-BLOCKED), `Chấm dứt các phiên đăng nhập` (HARD-BLOCKED) | Thông tin Chủ sở hữu, danh sách nhân viên (Tên, Email, Vai trò, Trạng thái hoạt động, Lần đăng nhập gần nhất), bộ đếm hạn mức nhân viên theo gói |
| `/admin/settings/group_permissions` | `Danh sách Vai trò` (RBAC) | `Tạo vai trò`, `Chỉnh sửa`, `Xóa` (HARD-BLOCKED) | Tên vai trò, Số nhân viên đang được gán, danh mục vai trò mẫu và vai trò tùy chỉnh |
| `/admin/settings/group_permissions/new` | `Tạo vai trò` / `Chỉnh sửa vai trò` | Cây Checkbox phân quyền, nút `Lưu`, `Hủy` | `Tên vai trò`, `Mô tả`, cây checkbox chi tiết: Đơn hàng, Vận chuyển, Sản phẩm, Khách hàng, Sổ quỹ, Khuyến mãi, Báo cáo, Thuế & Kế toán, Cấu hình |
| `/admin/settings/group_accounts` | `Nhóm phân công` | `Thêm nhóm phân công`, `Chỉnh sửa`, `Lưu`, `Xóa` (HARD-BLOCKED) | `Tên nhóm phân công`, danh sách nhân viên thuộc nhóm phụ trách xử lý đơn hàng/kho/kênh bán |

> **Nguyên tắc Least-Privilege RBAC:** Mọi vai trò mới đều mặc định **TẮT** toàn bộ nhóm quyền hủy diệt/nhạy cảm (`Xóa`, `Hoàn tiền`, `Xuất danh sách khách hàng`, `Phương thức thanh toán`, `Billing`, `Tên miền`, `Phân quyền`).

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `audit_rbac` | `audit_rbac` \| `create_role` \| `create_assignment_group` \| `invite_staff` \| `audit_inactive_slots` |
| `role_template` | `string` | Khi `create_role` | `warehouse_ops` | `warehouse_ops` \| `cs_harasocial` \| `marketing_seo` \| `accounting_readonly` |
| `role_name` | `string` | Khi `create_role` | — | Tên vai trò duy nhất, tiếng Việt rõ ràng (ví dụ `Kho Vận - Đóng Gói (Chuẩn)`) |
| `group_name` / `member_names` | `string` / `array` | Khi `create_assignment_group` | — | Tên nhóm phân công và danh sách nhân viên đã tồn tại trên store |
| `staff_invite` | `object` | Khi `invite_staff` | `{}` | `{full_name, email, role_name, allowed_locations[]}`; bắt buộc che PII trong báo cáo (`a***@domain.com`) |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true`; mọi thao tác ghi L3 bắt buộc `separate_turn: true` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Kiểm toán RBAC toàn diện (`audit_rbac` — Read-Only)
- **Điều kiện kích hoạt:** Kiểm toán bảo mật định kỳ hàng quý hoặc sau khi thay đổi nhân sự vận hành/kế toán/agency marketing.
1. Mở lần lượt `/admin/settings/accounts`, `/admin/settings/group_permissions` và `/admin/settings/group_accounts`.
2. Kiểm tra danh sách nhân viên đang có quyền `Toàn quyền (Full Access)` hoặc được gán các quyền rủi ro cao:
   - Quyền `Xóa` đơn hàng, sản phẩm, khách hàng.
   - Quyền `Xuất danh sách khách hàng` (nguy cơ rò rỉ data PII).
   - Quyền `Cấu hình thanh toán`, `Tên miền`, `Billing` và `Phân quyền`.
3. Kiểm tra xem có nhân viên kho/bán hàng tại chi nhánh nào đang xem được toàn bộ kho thay vì chỉ kho phụ trách không.
4. Xuất báo cáo kiểm toán RBAC đã che PII (`a***@domain.com`, `090****678`) và đề xuất lộ trình thu hẹp quyền; không thực hiện thao tác ghi.

### Scenario 2: `Tạo vai trò` chuẩn Least-Privilege (`create_role`)
- **Điều kiện kích hoạt:** Chuẩn hóa bộ vai trò tối thiểu cho từng phòng ban trước khi onboard nhân sự mới hoặc agency ngoài.
1. Điều hướng tới `https://{store_domain}/admin/settings/group_permissions`, click nút `Tạo vai trò` (`/admin/settings/group_permissions/new`).
2. Nhập `Tên vai trò` từ `role_name` và mô tả rõ phạm vi công việc.
3. Tick đúng ma trận quyền tối thiểu theo `role_template`:
   - `warehouse_ops`: Xem đơn hàng, Vận chuyển / Đóng gói / Biên bản bàn giao, Xem tồn kho theo kho gán; **TẮT** sửa giá, xóa đơn, sổ quỹ, xuất danh sách khách hàng.
   - `cs_harasocial`: Xem/Tạo đơn hàng nháp, Xem khách hàng, Quản lý đánh giá; **TẮT** xóa đơn, hoàn tiền, xuất file khách hàng, cấu hình thanh toán.
   - `marketing_seo`: Khuyến mãi, Website/Blog/Trang nội dung, Kênh Marketing; **TẮT** sổ quỹ, nhân viên, thanh toán, billing.
   - `accounting_readonly`: Chỉ đọc Đơn hàng, Báo cáo, Sổ quỹ, Công nợ, Quản lý thu hộ COD, Thuế & Kế toán; **TẮT** sửa sản phẩm, xóa dữ liệu, cấu hình phân quyền.
4. Rà soát lại toàn bộ cây checkbox đảm bảo 100% nhóm quyền nguy hiểm đã bỏ tick. **DỪNG — chưa bấm `Lưu`**.

### Scenario 3: `Thêm nhóm phân công` xử lý đơn theo chi nhánh (`create_assignment_group`)
- **Điều kiện kích hoạt:** Cửa hàng có nhiều ca trực sale/CSKH hoặc nhiều chi nhánh cần chia đơn hàng tự động theo nhóm.
1. Điều hướng tới `https://{store_domain}/admin/settings/group_accounts`.
2. Click nút `Thêm nhóm phân công`.
3. Nhập tên nhóm (`group_name`, ví dụ `Nhóm Xử Lý Đơn HCM - Ca Sáng`) và chọn đúng danh sách nhân viên (`member_names`) phụ trách ca/chi nhánh tương ứng.
4. **DỪNG — chưa bấm `Lưu`**, chuyển sang cổng duyệt L3 `separate_turn: true`.

### Scenario 4: `Thêm nhân viên` & gán đúng Vai trò + Phạm vi kho (`invite_staff`)
- **Điều kiện kích hoạt:** Tuyển mới nhân sự hoặc cấp tài khoản tạm cho kế toán/agency.
1. Điều hướng tới `https://{store_domain}/admin/settings/accounts`, xác nhận còn slot nhân viên trống trong gói (không vượt giới hạn).
2. Click nút `Thêm nhân viên`.
3. Điền họ tên, email công việc từ `staff_invite`, chọn đúng **Vai trò** tối thiểu đã kiểm chuẩn (tuyệt đối không chọn `Toàn quyền`) và giới hạn **Địa điểm / Kho hàng** được phép truy cập (`allowed_locations`).
4. **DỪNG — chưa bấm `Lưu` / `Gửi lời mời`**, che email trong bảng preview gửi Owner xác nhận ở lượt riêng.

### Scenario 5: Rà soát tài khoản không hoạt động & giới hạn slot gói (`audit_inactive_slots` — Read-Only)
- **Điều kiện kích hoạt:** Cửa hàng chạm trần số lượng tài khoản nhân viên theo gói (hiển thị nút `Mua thêm`) hoặc rà soát thu hồi quyền nhân sự nghỉ việc cuối tháng.
1. Tại `/admin/settings/accounts`, đọc hạn mức nhân viên hiện dùng trên tổng hạn mức gói (ví dụ `10/10 nhân viên`).
2. Rà soát cột `Lần đăng nhập gần nhất` và trạng thái hoạt động của từng nhân viên, lọc ra các tài khoản không hoạt động `> 60 ngày` hoặc tài khoản agency/cộng tác viên đã hết hợp đồng.
3. Đối chiếu danh sách vai trò đang gán cho các tài khoản không hoạt động đó để ưu tiên cảnh báo nếu có tài khoản cũ giữ quyền `Toàn quyền`.
4. Lập danh sách đề xuất (đã che PII: `a***@domain.com`, `090****678`) gửi Chủ cửa hàng tự xem xét khóa/thu hồi để giải phóng slot mà **tuyệt đối không tự bấm `Xóa`, `Khóa tài khoản` hay `Mua thêm`**.

> **Lưu ý kiểm chuẩn:** Sau khi Owner thu hồi tài khoản cũ, nhắc Owner kiểm tra lại các `Nhóm phân công` (`/admin/settings/group_accounts`) để đảm bảo không còn nhân viên đã nghỉ việc trong nhóm chia đơn tự động.

## 5. Quy trình An toàn 4 Pha (L3 Critical — `separate_turn: true`)

### Pha 1: Pre-State Capture (Chụp Ảnh Hiện Trạng RBAC)
- Mở lần lượt `/admin/settings/accounts`, `/admin/settings/group_permissions` và `/admin/settings/group_accounts`.
- Chụp ảnh hiện trạng (`artifacts/roles_pre.png`), ghi nhận danh sách vai trò và nhân sự đang hoạt động (bắt buộc che email `a***@domain.com` và SĐT `090****678` trong báo cáo).

### Pha 2: Stage Without Saving (Điền Form & Tick Ma Trận Quyền)
- Điền form `Tạo vai trò` (`/admin/settings/group_permissions/new`), `Thêm nhóm phân công` (`/admin/settings/group_accounts`) hoặc `Thêm nhân viên` (`/admin/settings/accounts`).
- Kiểm tra lại 100% các nhóm quyền nguy hiểm (`Xóa`, `Billing`, `Thanh toán`, `Xuất khách hàng`) đã bỏ tick hoàn toàn.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu` / `Gửi lời mời`**.

### Pha 3: Screenshot-Before-Save & Separate-Turn Gate (`separate_turn: true`)
- Chụp ảnh toàn bộ cây checkbox quyền đã chọn (`artifacts/roles_preview.png`).
- Trình bày bảng ma trận phân quyền `Before → After` (Mục 6) và **dừng hoàn toàn chờ Chủ cửa hàng xác nhận tường minh ở LƯỢT HỘI THOẠI TIẾP THEO**.

### Pha 4: Save & Post-Save Reload Verification
- Chỉ khi nhận được xác nhận ở lượt riêng, click `Lưu` và chờ toast thông báo thành công.
- Nhấn `F5` reload trang, mở kiểm tra lại vai trò/nhóm/nhân viên vừa tạo để xác minh các checkbox và phạm vi kho đã lưu chính xác, chụp `artifacts/roles_post.png`.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Ma trận Phân quyền RBAC (`/admin/settings/group_permissions` — L3 Critical)

| Nhóm quyền trên Haravan | `warehouse_ops` (Kho vận) | `cs_harasocial` (CSKH) | `accounting_readonly` (Kế toán) | Quyền CẤM cấp mặc định |
| :--- | :--- | :--- | :--- | :--- |
| Đơn hàng & Vận chuyển | Xem đơn, Đóng gói, Bàn giao | Xem/Tạo đơn nháp | Chỉ xem đơn & Quản lý COD | ❌ Xóa đơn, ❌ Hủy/Hoàn tiền |
| Sản phẩm & Tồn kho | Xem tồn kho (theo kho gán) | Chỉ xem sản phẩm | Chỉ xem | ❌ Sửa giá, ❌ Xóa sản phẩm |
| Khách hàng & CRM | Không cấp | Xem KH & Đánh giá | Không cấp | ❌ Xuất danh sách khách hàng |
| Sổ quỹ, Báo cáo & Thuế | Không cấp | Không cấp | Chỉ xem Sổ quỹ, Công nợ, Thuế | ❌ Thanh toán / Billing / Tên miền |

> **⚠️ L3 Critical (`separate_turn: true`) — Yêu cầu xác nhận ở lượt hội thoại riêng:** Ma trận phân quyền cho vai trò `Kho Vận - Đóng Gói (Chuẩn)` đã được chọn sẵn tại `/admin/settings/group_permissions/new` (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng trả lời **"Xác nhận lưu vai trò Kho Vận"** ở lượt tiếp theo để Agent bấm `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-staff-roles-config",
  "scenario": "create_role",
  "risk": "critical",
  "separate_turn_required": true,
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/group_permissions/new",
  "phase_status": "awaiting_separate_turn_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/roles_pre.png",
    "preview_screenshot": "artifacts/roles_preview.png",
    "post_screenshot": "artifacts/roles_post.png"
  },
  "checks_passed": {
    "owner_session_verified": true,
    "dangerous_permissions_unchecked": true,
    "pii_redacted_in_output": true,
    "separate_turn_enforced": true
  },
  "changes_staged": {
    "role_name": "Kho Vận - Đóng Gói (Chuẩn)",
    "role_template": "warehouse_ops",
    "dangerous_permissions_excluded": ["delete", "billing", "payments_config", "export_customers"]
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Chọn làm chủ sở hữu` (`/accounts`) | **HARD-BLOCKED** | Chuyển giao toàn bộ quyền sở hữu tối cao cửa hàng — không thể tự hoàn tác |
| `Chấm dứt các phiên đăng nhập` (`/accounts`) | **HARD-BLOCKED** | Đăng xuất đồng loạt toàn bộ nhân sự đang xử lý đơn/POS live |
| `Mua thêm` (`/accounts`) | **HARD-BLOCKED** | Phát sinh chi phí mua thêm slot nhân viên trên gói Haravan |
| `Xóa` / `Khóa tài khoản` nhân viên hoặc vai trò đang dùng | **HARD-BLOCKED** | Gây gián đoạn vận hành; chỉ liệt kê tài khoản không hoạt động để Owner tự quyết |
| Trang đăng nhập `accounts.haravan.com` | **HANDOFF GATE** | Dừng ngay để Owner tự đăng nhập; che toàn bộ email/SĐT trong báo cáo |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Nút `Thêm nhân viên` hoặc `Tạo vai trò` bị ẩn:** Tài khoản đang đăng nhập là Staff chứ không phải Chủ cửa hàng (Owner) → Dừng ngay, yêu cầu Owner đăng nhập trực tiếp.
2. **Chạm giới hạn số lượng nhân viên của gói Haravan:** Click `Thêm nhân viên` hiện popup nhắc `Mua thêm` → Dừng, chạy Scenario 5 để liệt kê tài khoản không hoạt động cho Owner tự xử lý.
3. **Toast báo lỗi trùng tên vai trò khi lưu:** Đề xuất đặt hậu tố phân biệt rõ phiên bản (ví dụ `Kho Vận - Chuẩn v2`), cập nhật tên và chụp lại `preview_screenshot`.
4. **Nhân viên mới báo không nhận được email lời mời kích hoạt:** Kiểm tra lại chính tả email (đã che trong log), nhắc nhân viên kiểm tra thư mục Spam/Quảng cáo hoặc đề nghị Owner bấm gửi lại lời mời tại `/admin/settings/accounts`.
5. **Nhân viên sau khi đổi vai trò vẫn thấy menu cũ:** Do phiên trình duyệt của nhân viên còn cache quyền cũ → Nhắc nhân viên đăng xuất và đăng nhập lại Haravan Admin để áp dụng ma trận quyền mới.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Đối chiếu `artifacts/roles_pre.png` của `/admin/settings/group_permissions` và `/admin/settings/accounts`.
2. Nếu vừa chỉnh sửa vai trò cũ: mở lại vai trò đó, tick lại đúng các quyền gốc theo ảnh chụp và bấm `Lưu`.
3. Nếu vừa tạo vai trò hoặc nhóm phân công mới chưa gán nhân sự: Owner tự bấm `Xóa` bản ghi đó trên trình duyệt.
4. Nếu gán nhầm vai trò cho nhân viên: mở chi tiết nhân viên tại `/admin/settings/accounts`, đổi về vai trò cũ và bấm `Lưu`.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Mở lại vai trò vừa tạo tại `/admin/settings/group_permissions`: xác nhận các quyền `Xóa`, `Billing`, `Thanh toán`, `Xuất khách hàng` đều ở trạng thái **Tắt**.
- [ ] Kiểm tra phạm vi kho gán cho nhân viên kho/chi nhánh tại `/admin/settings/accounts`.
- [ ] Xác nhận báo cáo/JSON đã che toàn bộ email (`a***@domain.com`) và SĐT (`090****678`).

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `config/permissions.yaml`: Tham chiếu chuẩn Least-Privilege giữa Haravan API Scopes (`com.read_*`) và Admin UI RBAC.
- `skills/browser-ui/` → `admin-ui-locations-inventory-ops` (xác định danh sách kho để giới hạn phạm vi kho của Staff), `admin-ui-session-navigator`.
