---
name: store-bootstrap-checklist
description: "Đánh giá toàn diện độ sẵn sàng khai trương cửa hàng Haravan (tên miền, thanh toán VN, vận chuyển, chính sách, tracking, giao diện)."
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
    - com.read_products
    - com.read_contents
    - web.read_themes
    - web.read_script_tags
  endpoints:
    - "GET https://apis.haravan.com/com/shop.json"
    - "GET https://apis.haravan.com/com/locations.json"
    - "GET https://apis.haravan.com/com/products/count.json"
    - "GET https://apis.haravan.com/web/pages.json"
    - "GET https://apis.haravan.com/web/themes.json"
    - "GET https://apis.haravan.com/web/script_tags.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
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
# Store Bootstrap Checklist — Đánh giá Độ Sẵn Sàng Khai Trương Cửa Hàng Haravan

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` thực hiện kiểm toán toàn diện 6 hạng mục sống còn trước khi một cửa hàng Haravan tại Việt Nam chính thức chạy quảng cáo (Facebook/TikTok/Google) hoặc mở bán (Go-Live). Thực tế nhiều shop mới khai trương bị khóa tài khoản quảng cáo, rớt đơn thanh toán hoặc bị khách phản ánh vì thiếu trang chính sách bắt buộc theo Nghị định 52/2013/NĐ-CP (Bộ Công Thương), quên trỏ tên miền SSL, chưa có kho mặc định hoạt động, hoặc thiếu mã tracking.

- **Khi nào sử dụng:** Trước ngày khai trương cửa hàng mới, sau khi chuyển dữ liệu từ nền tảng TMĐT khác sang Haravan, hoặc trước khi mở rộng thêm kênh bán mới.
- **Khi nào KHÔNG sử dụng:** Khi cửa hàng đã vận hành ổn định lâu ngày và cần theo dõi sức khỏe đơn hàng/tồn kho hàng tuần (dùng `store-health-check`).
- **Definition of Done (DoD):**
  1. Thu thập đầy đủ dữ liệu từ 6 endpoint read-only (`shop`, `locations`, `products/count`, `web/pages`, `web/themes`, `web/script_tags`).
  2. Chấm điểm sẵn sàng khai trương trên thang **100 điểm** với 2 nhóm hạng mục: **Blocker (Bắt buộc đạt trước Go-Live)** và **Recommended (Khuyến nghị hoàn thiện)**.
  3. Lập danh sách hành động khắc phục cụ thể, phân rõ mục làm qua API và mục cần thao tác trên Haravan Admin UI (như cổng thanh toán VNPay/MoMo, vận chuyển GHN/GHTK).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Hạng mục kiểm tra | Scope yêu cầu | Endpoint Haravan |
| --- | --- | --- |
| Thông tin cửa hàng, tên miền, VND, múi giờ | `com.read_shop` | `GET https://apis.haravan.com/com/shop.json` |
| Danh sách kho/chi nhánh hoạt động | `com.read_shop` | `GET https://apis.haravan.com/com/locations.json` |
| Số lượng sản phẩm đã đăng bán | `com.read_products` | `GET https://apis.haravan.com/com/products/count.json` |
| Trang chính sách (Đổi trả, Bảo mật, Thanh toán, Vận chuyển) | `com.read_contents` | `GET https://apis.haravan.com/web/pages.json` |
| Giao diện Live Theme | `web.read_themes` | `GET https://apis.haravan.com/web/themes.json` |
| Mã tracking / script bên thứ ba | `web.read_script_tags` | `GET https://apis.haravan.com/web/script_tags.json` |

**Chạy kiểm tra nhanh bằng `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True)
shop = c.get("com", "/shop.json")["shop"]
locations = c.get("com", "/locations.json").get("locations") or []
prod_count = c.get("com", "/products/count.json").get("count", 0)
pages = c.paginate("web", "/pages.json", key="pages", max_records=200)
themes = c.get("web", "/themes.json").get("themes") or []
scripts = c.get("web", "/script_tags.json").get("script_tags") or []
```

**Sample Response (`GET /web/pages.json` & `GET /web/script_tags.json`):**
```json
{
  "pages": [
    { "id": 1001, "title": "Chính sách đổi trả", "handle": "chinh-sach-doi-tra", "published_at": "2026-11-10T03:00:00Z", "body_html": "<p>Đổi trả trong 7 ngày...</p>" },
    { "id": 1002, "title": "Chính sách bảo mật", "handle": "chinh-sach-bao-mat", "published_at": "2026-11-10T03:05:00Z", "body_html": "<p>Cam kết bảo mật thông tin...</p>" }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `required_policies` | array[string] | Không | `["doi-tra", "bao-mat", "van-chuyen", "thanh-toan", "dieu-khoan"]` | Từ khóa slug/tiêu đề trang chính sách bắt buộc tại VN. |
| `min_products_for_launch` | integer | Không | `5` | Số sản phẩm tối thiểu để coi là sẵn sàng khai trương. |
| `require_custom_domain` | boolean | Không | `true` | Yêu cầu đã gắn domain riêng (không dùng `*.myharavan.com`). |
| `check_tracking_scripts` | boolean | Không | `true` | Kiểm tra có script tracking hoặc cảnh báo nếu script trùng lặp. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Thang chấm điểm Go-Live Readiness (100 điểm)
1. **Tên miền & Cấu hình nền (20đ):** Custom domain khác `*.myharavan.com` (+8đ), `currency == "VND"` (+4đ), `timezone` chứa `+07:00` (+4đ), có email/số điện thoại liên hệ hợp lệ (+4đ).
2. **Kho hàng & Địa chỉ lấy hàng (15đ):** Có tối thiểu 1 location `status == "active"` và `is_primary == true` (+10đ), đầy đủ địa chỉ Tỉnh/Quận/Phường để tạo đơn GHN/GHTK (+5đ).
3. **Catalog tối thiểu (15đ):** `products/count >= min_products_for_launch` (+15đ); nếu `0` → đánh dấu **BLOCKER**.
4. **Trang chính sách pháp lý VN (25đ):** Mỗi trang chính sách có `published_at != null` và `len(body_html) >= 200` ký tự được +5đ (tối đa 5 trang: Đổi trả, Bảo mật, Vận chuyển, Thanh toán, Điều khoản/Giới thiệu).
5. **Giao diện Live Theme (15đ):** Tồn tại đúng 1 theme `role == "main"` (+10đ) và có ít nhất 1 bản backup `unpublished` (+5đ).
6. **Tracking & Script Tags (10đ):** Không có script lỗi/HTTP không bảo mật (+5đ), có cấu hình tracking hoặc xác nhận gắn trong `theme.liquid` (+5đ).

**Quy tắc phân loại kết quả:**
- `>= 85đ` và **0 Blocker**: **READY TO LAUNCH**.
- `65–84đ` hoặc có Blocker nhẹ: **CONDITIONAL** (sửa trước khi chạy ads).
- `< 65đ` hoặc có Blocker nghiêm trọng (0 sản phẩm, 0 kho active, chưa có trang chính sách): **NOT READY**.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Đánh giá Khai trương (Go-Live Readiness: 78/100 — CONDITIONAL)
| Hạng mục | Điểm | Trạng thái | Phát hiện & Hành động khắc phục |
| --- | --- | --- | --- |
| Tên miền & Cài đặt | 20/20 | PASS | Đã trỏ `saigonstreetwear.vn`, VND, GMT+7 |
| Kho hàng & Chi nhánh | 15/15 | PASS | 2 kho active (Thủ Đức, Q.1), đủ địa chỉ 3 cấp |
| Danh mục sản phẩm | 15/15 | PASS | 42 sản phẩm đang hiển thị |
| Trang chính sách VN | 15/25 | BLOCKER | Thiếu trang **Chính sách vận chuyển** và **Chính sách thanh toán** (cần cho duyệt Google Shopping & BCT) |
| Giao diện Theme | 10/15 | WARN | Có Live Theme nhưng chưa có bản duplicate backup (`unpublished`) |
| Thanh toán & Vận chuyển | N/A (UI) | CHECKLIST | Cần xác minh thủ công trên `/admin/settings/payments` (COD/Chuyển khoản/VNPay) & `/admin/settings/shipping` |

### JSON Output Schema
```json
{
  "skill": "store-bootstrap-checklist",
  "readiness_score": 78,
  "verdict": "CONDITIONAL",
  "blockers": ["missing_policy:van-chuyen", "missing_policy:thanh-toan"],
  "warnings": ["no_unpublished_theme_backup"],
  "metrics": {
    "custom_domain": "saigonstreetwear.vn",
    "active_locations": 2,
    "product_count": 42,
    "published_policy_pages": 3,
    "live_theme_id": 1000881122,
    "script_tags_count": 2
  },
  "manual_admin_ui_checks": ["/admin/settings/payments", "/admin/settings/shipping", "/admin/settings/domains"]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ Read-Only (`L1`):** Chỉ gọi HTTP `GET`, tuyệt đối không tự tạo trang chính sách hay chỉnh sửa cấu hình cửa hàng.
- **Tách biệt phạm vi API vs Admin UI:** Các thiết lập cổng thanh toán VN (VietQR, VNPay, MoMo, ZaloPay), nhà vận chuyển (GHN, GHTK, Viettel Post) và chứng chỉ SSL tên miền không có endpoint đọc đầy đủ trên REST API → ghi rõ trong mục `manual_admin_ui_checks` để kiểm tra qua `skills/browser-ui/` hoặc thủ công.
- **PII:** Che email/số điện thoại chủ cửa hàng nếu xuất hiện trong object `shop`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` trên `/web/script_tags.json` | Token thiếu `web.read_script_tags` | Vẫn chấm 5 hạng mục còn lại, đánh dấu mục Tracking là `SKIPPED_MISSING_SCOPE` và hạ mẫu số điểm tương ứng. |
| `403 Forbidden` trên `/web/pages.json` | Token thiếu `com.read_contents` | Báo rõ cần bổ sung scope để kiểm tra trang chính sách. |
| `429 Too Many Requests` | Gọi dồn 6 endpoint song song quá nhanh | Gọi tuần tự qua `HaravanClient` với `req_per_sec=2.5`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Trang chính sách tạo bằng mẫu mặc định rỗng chữ:** Nhiều shop bấm tạo trang "Chính sách đổi trả" nhưng để nội dung `<p></p>` hoặc copy nguyên mẫu có chữ `[Tên công ty]`. Phải kiểm tra `len(strip_html(body_html)) >= 200` và cảnh báo nếu chứa placeholder `[...]`.
2. **Mã Facebook Pixel / GA4 / GTM gắn thẳng trong `theme.liquid` thay vì `script_tags`:** Nếu `script_tags` trả mảng rỗng `[]`, không kết luận ngay là "chưa gắn tracking" — cần ghi chú rõ "không có qua ScriptTag API, hãy kiểm tra `layout/theme.liquid` hoặc Cài đặt Google/Facebook trên Admin".
3. **Cửa hàng đang bật mật khẩu bảo vệ storefront:** API `shop.json` vẫn trả `200` nhưng khách thật không vào được web; cần nhắc kiểm tra tắt chế độ bảo trì/mật khẩu trước giờ chạy ads.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup`.
- **Chạy tiếp theo:** `store-config-audit` (kiểm toán sâu chi nhánh/thuế/hành chính), `catalog-data-completeness-audit` (kiểm tra chất lượng sản phẩm), `store-redirect-audit` (nếu migrate từ web cũ).
