---
name: haravan-auth-setup
description: "Hướng dẫn thiết lập xác thực Private App hoặc OAuth2 (offline_access), kiểm tra kết nối và đối chiếu least-privilege scopes."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 00-core-platform
layer: L0
wave: 1
mode: reference
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_shop
    - offline_access
  endpoints:
    - "GET https://apis.haravan.com/com/shop.json"
    - "GET https://apis.haravan.com/com/locations.json"
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
# Haravan Auth Setup — Thiết lập Xác thực, OAuth2 & Least-Privilege Scopes

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L0 / reference` hướng dẫn thiết lập xác thực an toàn cho AI Agent kết nối Haravan theo nguyên tắc **Least-Privilege Scopes** (chỉ cấp đúng quyền cần thiết). Trong thực tế vận hành tại Việt Nam, chủ shop thường tạo Private App hoặc kết nối OAuth2 App nhưng hay tick chọn toàn bộ quyền (`write_*` cho mọi module), tạo rủi ro cực lớn nếu token bị lộ hoặc Agent chạy nhầm.

- **Khi nào sử dụng:** Khi onboard cửa hàng Haravan mới, xoay vòng (rotate) token định kỳ, gặp lỗi `401 Unauthorized` / `403 Forbidden`, hoặc cần đối chiếu phạm vi quyền tối thiểu trước khi bật skill Wave 2/3.
- **Khi nào KHÔNG sử dụng:** Khi vận hành hoàn toàn qua trình duyệt không cần API token (sử dụng nhóm `skills/browser-ui/`).
- **Definition of Done (DoD):**
  1. Xác định rõ mô hình xác thực phù hợp (Private App Token vs OAuth2 `offline_access`).
  2. Biến môi trường `HARAVAN_ACCESS_TOKEN` được nạp từ `.env` (đã nằm trong `.gitignore`) và vượt qua bài kiểm tra `GET /com/shop.json` + `GET /com/locations.json`.
  3. Có ma trận đối chiếu scopes thực tế so với `config/permissions.yaml` và xác nhận không thừa quyền `write_*` khi chỉ chạy audit L1.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Mô hình Auth | Phù hợp cho | Scope tối thiểu để verify | Endpoint kiểm tra |
| --- | --- | --- | --- |
| **Private App Token** | Nội bộ 1 cửa hàng Haravan (Khuyến nghị cho Ops Agent) | `com.read_shop` | `GET https://apis.haravan.com/com/shop.json` |
| **OAuth2 App (`offline_access`)** | Agency / Multi-store / App tích hợp đa cửa hàng | `com.read_shop`, `offline_access` | `GET https://apis.haravan.com/com/locations.json` |

**Bước 1 — Luồng OAuth2 Authorization Code (chỉ dùng cho App đa cửa hàng):**
```http
GET https://accounts.haravan.com/connect/authorize
  ?response_mode=form_post
  &response_type=code id_token
  &scope=openid profile email org userinfo offline_access com.read_shop com.read_products
  &client_id=<HARAVAN_CLIENT_ID>
  &redirect_uri=https://your-app.vn/auth/haravan/callback
  &nonce=<random_nonce>
```

**Bước 2 — Đổi `code` lấy `access_token` và `refresh_token`:**
```json
// POST https://accounts.haravan.com/connect/token
// Content-Type: application/x-www-form-urlencoded
{
  "grant_type": "authorization_code",
  "code": "<auth_code_from_callback>",
  "client_id": "<HARAVAN_CLIENT_ID>",
  "client_secret": "<HARAVAN_CLIENT_SECRET>",
  "redirect_uri": "https://your-app.vn/auth/haravan/callback"
}
```

**Sample Response khi đổi token & kiểm tra `GET /com/locations.json`:**
```json
// Response từ /connect/token (KHÔNG lưu hoặc in ra log chat)
{
  "access_token": "<REDACTED_JWT_OR_OPAQUE_TOKEN>",
  "expires_in": 3600,
  "token_type": "Bearer",
  "refresh_token": "<REDACTED_REFRESH_TOKEN>"
}
```
```json
// Response từ GET https://apis.haravan.com/com/locations.json
{
  "locations": [
    { "id": 1001234, "name": "Kho Tổng Thủ Đức", "status": "active", "is_primary": true, "province": "Hồ Chí Minh" },
    { "id": 1001235, "name": "Cửa hàng Quận 1 (POS)", "status": "active", "is_primary": false, "province": "Hồ Chí Minh" }
  ]
}
```

**Kiểm tra nhanh bằng CLI của repo:**
```bash
# Đọc token từ ENV, không truyền trực tiếp trên dòng lệnh có thể lưu vào shell history
source .env && python3 scripts/hrv_ops.py probe
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `auth_mode` | enum (`private_app`, `oauth2`) | Có | `private_app` | Chọn luồng Private App hay OAuth2. |
| `target_layer` | enum (`L1_read`, `L2_proposal`, `L3_write`) | Có | `L1_read` | Xác định bộ scope tối thiểu cần cấp theo tầng rủi ro. |
| `store_env` | enum (`staging`, `production`) | Có | `staging` | Luôn kiểm thử kết nối trên dev/staging store trước. |
| `probe_endpoints` | array[string] | Không | `["/shop.json", "/locations.json"]` | Danh sách endpoint GET để kiểm tra quyền thực tế. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Ma trận phân tầng Scopes (Least-Privilege Profile)
- **Profile 1 — Read-Only Audit (`L1`):** Chỉ cấp `com.read_shop`, `com.read_products`, `com.read_inventories`, `com.read_orders`, `com.read_customers`, `com.read_discounts`, `com.read_contents`, `web.read_themes`, `web.read_script_tags`. **0 quyền `write_*`**.
- **Profile 2 — Catalog & Inventory Proposal (`L2`):** Bổ sung từng quyền cụ thể theo nhu cầu (`com.write_products` cho giá/catalog hoặc `com.write_inventories` cho phiếu điều chỉnh/chuyển kho).
- **Profile 3 — Webhook & Theme CLI:** Tách token riêng cho `wh_api` và `web.write_themes` để tránh lộ chéo quyền.

### Quy trình kiểm tra xác thực 5 bước
1. **Kiểm tra vệ sinh biến môi trường:** Xác nhận `.env` có trong `.gitignore`; kiểm tra `HARAVAN_ACCESS_TOKEN` có độ dài > 20 ký tự và không chứa khoảng trắng/xuống dòng.
2. **Probe danh tính cửa hàng:** Gọi `GET /com/shop.json` → ghi nhận `shop.id`, `myharavan_domain`, đối chiếu đúng môi trường `staging` hay `production`.
3. **Probe chi nhánh:** Gọi `GET /com/locations.json` → xác nhận danh sách `location_id` hoạt động (`status == "active"`).
4. **Kiểm tra Scope thực tế (Scope Capability Matrix):** Thử gọi `GET` nhẹ (`limit=1` hoặc `/count.json`) tới từng nhóm tài nguyên người dùng muốn chạy; phân loại `GRANTED (200)` vs `MISSING_SCOPE (403)`.
5. **Khuyến nghị tối giản hóa quyền:** Nếu phát hiện token có quyền vượt quá mục đích (ví dụ chỉ chạy báo cáo nhưng cấp `com.write_orders`), cảnh báo người dùng tạo Private App riêng chỉ có quyền đọc.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo kiểm tra Xác thực & Scope (Markdown)
| Tài nguyên | Endpoint Probe | HTTP Status | Trạng thái Scope | Hành động khuyến nghị |
| --- | --- | --- | --- | --- |
| Cửa hàng | `GET /com/shop.json` | `200` | `com.read_shop` (OK) | Đạt |
| Chi nhánh/Kho | `GET /com/locations.json` | `200` | `com.read_shop` (OK) | Tìm thấy 3 kho đang hoạt động |
| Sản phẩm | `GET /com/products/count.json` | `200` | `com.read_products` (OK) | Đạt |
| Đơn hàng | `GET /com/orders/count.json` | `403` | Thiếu `com.read_orders` | Cấp thêm nếu cần chạy báo cáo đơn/tốc độ bán |
| Giao diện | `GET /web/themes.json` | `200` | `web.read_themes` (OK) | Đạt |

### JSON Output Schema
```json
{
  "skill": "haravan-auth-setup",
  "auth_mode": "private_app",
  "environment": "staging",
  "token_present": true,
  "shop_domain": "demo-vn.myharavan.com",
  "active_locations_count": 3,
  "scope_matrix": {
    "com.read_shop": "granted",
    "com.read_products": "granted",
    "com.read_orders": "missing",
    "web.read_themes": "granted"
  },
  "ready_for_skills": ["store-config-audit", "catalog-data-completeness-audit"]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Zero Secret Exposure:** Tuyệt đối không yêu cầu người dùng dán `HARAVAN_ACCESS_TOKEN`, `CLIENT_SECRET`, mật khẩu hoặc OTP vào khung chat. Nếu người dùng lỡ dán token vào chat, cảnh báo ngay lập tức yêu cầu **thu hồi (Revoke) và tạo lại token mới** trong Haravan Admin → Cấu hình → Ứng dụng riêng.
- **Tách biệt Staging / Production:** Khuyến nghị đặt tên biến rõ ràng hoặc kiểm tra `shop.myharavan_domain` trước mọi phiên làm việc để tránh nhầm token production khi đang thử nghiệm.
- **Xoay vòng token (Rotation):** Thiết lập lịch rotate Private App Token mỗi 90 ngày hoặc ngay khi có nhân sự kỹ thuật nghỉ việc.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách khắc phục |
| --- | --- | --- |
| `401 Unauthorized` | Access token OAuth2 hết hạn (thường 1 giờ) chưa refresh, hoặc Private App bị xóa | Dùng `refresh_token` (`grant_type=refresh_token`) để lấy token mới, hoặc tạo lại Private App. |
| `403 Forbidden` | Đã sửa scope trên Haravan Admin nhưng chưa lấy lại token mới (với OAuth2) | Thực hiện lại luồng OAuth2 authorize để cấp token mang scope mới. |
| `400 Bad Request` (tại `/connect/token`) | Sai `redirect_uri` (khác dấu `/` cuối hoặc http vs https) hoặc `code` đã dùng 1 lần | So khớp từng ký tự `redirect_uri` trong Partner Portal; mỗi `code` chỉ đổi được 1 lần. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Nhầm lẫn quyền `com.read_contents` vs `web.read_contents`:** Trên Haravan, một số endpoint `/web/` (như `/web/redirects.json`, `/web/pages.json`) lại yêu cầu scope `com.read_contents` tùy phiên bản app. Luôn đối chiếu `config/permissions.yaml` và test thực tế bằng `GET`.
2. **Token Private App không cần `offline_access` nhưng không gọi được `wh_api`:** Connect Webhook (`webhook.haravan.com/api/subscribe`) yêu cầu OAuth2 App có scope `wh_api`, trong khi Private App quản lý webhook trực tiếp trong Admin UI.
3. **Copy token dính ký tự ẩn (`\r\n` hoặc dấu cách đầu/cuối):** Khi dán vào `.env` trên Windows/macOS, ký tự `\r` làm header `Authorization: Bearer ...` bị lỗi `401`. Luôn `.strip()` biến môi trường khi nạp.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy tiếp theo:** `haravan-api-core` (cấu hình client & rate-limit), `store-bootstrap-checklist` (kiểm tra độ sẵn sàng khai trương), `store-staff-permission-audit` (kiểm toán phân quyền nhân sự).
