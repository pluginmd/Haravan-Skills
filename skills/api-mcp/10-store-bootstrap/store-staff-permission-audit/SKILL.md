---
name: store-staff-permission-audit
description: "Kiểm toán danh sách tài khoản nhân viên (/com/users.json), phát hiện tài khoản dư quyền, không hoạt động lâu ngày hoặc email cá nhân."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 10-store-bootstrap
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/users.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---
# Store Staff Permission Audit — Kiểm Toán Tài Khoản Nhân Viên & Phân Quyền Haravan

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` kiểm toán danh sách tài khoản nhân sự đang có quyền truy cập Haravan Admin (`/com/users.json`) nhằm phát hiện sớm 4 rủi ro bảo mật phổ biến nhất tại các doanh nghiệp bán lẻ Việt Nam: (1) Nhân viên cũ đã nghỉ việc nhưng chưa bị khóa tài khoản, (2) Quá nhiều tài khoản mang quyền quản trị toàn phần (`account_owner` / full admin), (3) Tài khoản dùng email cá nhân (`@gmail.com`, `@yahoo.com`) thay vì email công ty dễ rò rỉ dữ liệu khách hàng, và (4) Tài khoản không hoạt động lâu ngày (dormant accounts).

- **Khi nào sử dụng:** Định kỳ hàng quý (Quarterly Security Review), ngay khi có nhân sự vận hành/kế toán/agency nghỉ việc hoặc kết thúc hợp đồng, hoặc trước khi tích hợp thêm đối tác bên ngoài.
- **Khi nào KHÔNG sử dụng:** Khi muốn tự động khóa hoặc hạ quyền tài khoản nhân viên (API không hỗ trợ và thao tác phân quyền trên `/admin/settings/accounts` thuộc nhóm `L3 critical` phải thực hiện thủ công có xác nhận).
- **Definition of Done (DoD):**
  1. Tải đầy đủ danh sách tài khoản từ `GET /com/users.json` (xử lý graceful fallback nếu gói Haravan chưa mở endpoint này).
  2. Phân loại toàn bộ tài khoản theo 4 nhóm rủi ro (`HIGH / MEDIUM / LOW`) và **che toàn bộ PII** (email, số điện thoại) trong báo cáo theo `policies/pii-handling.md`.
  3. Xuất bảng đề xuất thu hồi/hạ quyền rõ ràng để chủ cửa hàng thực hiện tại `/admin/settings/accounts`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Danh sách tài khoản nhân viên | `com.read_shop` | `GET https://apis.haravan.com/com/users.json` |

**Chạy thu thập dữ liệu qua `scripts/hrv_client.py` (tích hợp sẵn redaction):**
```python
from scripts.hrv_client import HaravanClient, redact_email, redact_phone
c = HaravanClient(dry_run=True)
users = c.get("com", "/users.json").get("users") or []
```

**Sample Response từ Haravan (`GET https://apis.haravan.com/com/users.json`):**
```json
{
  "users": [
    {
      "id": 400101,
      "first_name": "Minh",
      "last_name": "Nguyễn",
      "email": "minh.nguyen@saigonstreetwear.vn",
      "phone": "0901234567",
      "account_owner": true,
      "user_type": "regular",
      "permissions": ["full"],
      "receive_announcements": 1
    },
    {
      "id": 400108,
      "first_name": "Agency",
      "last_name": "Ads 2024",
      "email": "agency.ads.old@gmail.com",
      "phone": "0912345678",
      "account_owner": false,
      "user_type": "regular",
      "permissions": ["full"]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `company_email_domains` | array[string] | Không | `[]` (suy ra từ `shop.domain`) | Danh sách domain email công ty hợp lệ (vd `["saigonstreetwear.vn"]`). |
| `max_full_admin_count` | integer | Không | `3` | Ngưỡng tối đa số tài khoản có quyền `full` trước khi cảnh báo. |
| `sensitive_permissions` | array[string] | Không | `["full", "settings", "orders", "customers", "reports"]` | Nhóm quyền nhạy cảm cần rà soát kỹ (xuất danh sách khách, sửa cổng thanh toán). |
| `redact_pii` | boolean | Không | `true` | Bắt buộc `true` — che email (`a***@gmail.com`) và SĐT (`090****567`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Ma trận chấm điểm Rủi ro Nhân sự (Staff Risk Rules)
1. **Rule S1 — Dư thừa quyền Full Admin (`HIGH`):** `account_owner == false` nhưng `permissions` chứa `"full"` (hoặc `> 80%` tổng quyền hệ thống). Đặc biệt nghiêm trọng nếu kết hợp với email cá nhân (`@gmail.com`, `@yahoo.com`, `@outlook.com`).
2. **Rule S2 — Tài khoản đối tác/agency bên ngoài (`HIGH`):** Tên hoặc email chứa từ khóa `agency`, `freelance`, `partner`, `test`, `dev`, `old`, `2023`, `2024` nhưng vẫn còn tồn tại trong danh sách active.
3. **Rule S3 — Email cá nhân (`MEDIUM`):** Domain email không nằm trong `company_email_domains` → khó thu hồi quyền truy cập khi nhân viên nghỉ việc, nguy cơ bị chiếm đoạt nếu không bật 2FA.
4. **Rule S4 — Tổng số Full Admin vượt ngưỡng (`MEDIUM`):** `count(full_admins) > max_full_admin_count`.
5. **Rule S5 — Quyền xuất dữ liệu khách hàng & cài đặt thanh toán (`MEDIUM`):** Đếm số nhân viên có đồng thời quyền `customers` + `settings` để chủ shop rà soát theo nguyên tắc Least-Privilege.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Kiểm toán Phân quyền Nhân viên (PII đã được che)
- **Tổng số tài khoản:** `12` (`1` Account Owner, `4` Full Admin, `7` Phân quyền giới hạn)
- **Cảnh báo:** `2 HIGH` | `3 MEDIUM`

| User ID | Tên hiển thị | Email (Masked) | Quyền chính | Mức rủi ro | Khuyến nghị hành động |
| --- | --- | --- | --- | --- | --- |
| `400108` | Agency Ads 2024 | `a***@gmail.com` | `full` | HIGH | Thu hồi ngay nếu đã kết thúc hợp đồng tại `/admin/settings/accounts` |
| `400112` | Tuấn (Sale cũ) | `t***@gmail.com` | `orders, customers, settings` | HIGH | Xác nhận còn làm việc không; hạ quyền `settings` & `export` |
| `400105` | Lan (Kế toán) | `l***@saigonstreetwear.vn` | `orders, reports` | LOW | Phù hợp vai trò |

### JSON Output Schema
```json
{
  "skill": "store-staff-permission-audit",
  "pii_redacted": true,
  "summary": {
    "total_users": 12,
    "account_owners": 1,
    "full_admin_non_owner": 3,
    "personal_email_accounts": 4,
    "high_risk_count": 2
  },
  "findings": [
    {
      "user_id": 400108,
      "email_masked": "a***@gmail.com",
      "risk": "HIGH",
      "reasons": ["non_owner_full_admin", "personal_email_domain", "agency_keyword_detected"],
      "action": "Review and revoke at /admin/settings/accounts"
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Bảo vệ PII nghiêm ngặt (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Tuyệt đối không in email đầy đủ hay số điện thoại gốc của nhân viên ra báo cáo/JSON/CSV.
- **Không tự ý sửa/xóa tài khoản:** Mọi thay đổi phân quyền nhân sự là thao tác `L3 critical`; Agent chỉ báo cáo và hướng dẫn chủ cửa hàng tự thực hiện trên `/admin/settings/accounts`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Gói dịch vụ Haravan hiện tại chưa mở API `/com/users.json` (chỉ có trên gói cao cấp/Omni) hoặc Private App thiếu quyền | Không retry vô ích; chuyển sang phương án kiểm toán qua giao diện `skills/browser-ui/` tại `/admin/settings/accounts`. |
| `401 Unauthorized` | Token hết hạn | Kiểm tra lại qua `haravan-auth-setup`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Gói cơ bản không hỗ trợ `/com/users.json`:** Haravan giới hạn endpoint này ở một số gói dịch vụ. Khi gặp `403`, Agent phải thông báo rõ giới hạn gói cước và đề xuất kiểm tra trực tiếp trên màn hình `/admin/settings/accounts` (chỉ đọc).
2. **Tài khoản `permissions` trả về rỗng hoặc `null`:** Trên một số phiên bản API, `account_owner: true` có thể trả `permissions: []` thay vì `["full"]`; luôn kiểm tra `account_owner` trước khi kết luận thiếu quyền.
3. **API không trả về `last_login_at`:** Nếu response của Haravan không có trường thời điểm đăng nhập cuối, không được tự suy đoán tài khoản "không hoạt động 90 ngày" — phải ghi chú rõ `last_login_at: unavailable_via_api` và đề nghị đối chiếu Nhật ký hoạt động (Activity Log) trên Admin UI.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup`.
- **Chạy tiếp theo:** `store-config-audit` (kiểm toán chi nhánh & cấu hình), hoặc skill kiểm tra giao diện phân quyền trong `skills/browser-ui/` nếu cần rà soát Activity Log.
