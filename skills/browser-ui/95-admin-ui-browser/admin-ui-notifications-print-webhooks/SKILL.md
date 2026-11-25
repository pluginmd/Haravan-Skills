---
name: admin-ui-notifications-print-webhooks
description: "Quản lý 13 mẫu Email khách hàng, Mẫu in (Đơn hàng/Vận đơn/Tồn kho), Thông báo đơn hàng nội bộ và Private Webhooks tại /admin/settings/notifications."
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
    - "UI /admin/settings/notifications"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 30
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

# Haravan Admin UI: Email Templates, Print Forms & Private Webhooks

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Trang **Thông báo** (`/admin/settings/notifications`) tập hợp 4 cấu hình vận hành cốt lõi không có REST API quản lý trực tiếp từ bên ngoài: **13 mẫu Email tự động gửi khách hàng**, **Mẫu in phiếu** (`Đơn hàng`, `Vận đơn`, `Tồn kho`), **Thông báo đơn hàng nội bộ** (gửi email/SMS cho nhân sự khi có đơn mới) và **Private Webhooks** (đẩy sự kiện JSON realtime sang n8n, ERP, CRM nội bộ mà không cần duyệt Public App trên Haravan Partner).
- **Mục tiêu nghiệp vụ:**
  - Chuẩn hóa toàn bộ giao tiếp sau mua hàng (bật/tắt đúng các mẫu email sự kiện, chỉnh sửa mã HTML/Liquid có backup nguyên bản).
  - Tối ưu mẫu in phiếu đơn hàng/vận đơn/phiếu kho phù hợp máy in nhiệt K80/A6 hoặc A4/A5, và thiết lập Private Webhook HTTPS có xác thực chữ ký HMAC an toàn.
- **Phân quyền Owner vs Staff:**
  - **Owner:** Toàn quyền chỉnh sửa 13 mẫu email, mẫu in, thông báo đơn hàng và quản trị Private Webhooks.
  - **Staff:** Cần quyền **Cấu hình > Thông báo** tại `/admin/settings/group_permissions`. Riêng mục `Webhooks` chứa chuỗi chữ ký bảo mật nên chỉ Owner hoặc kỹ thuật viên được ủy quyền thực hiện.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Tất cả các gói đều hỗ trợ 13 mẫu email, 3 mẫu in chuẩn và thông báo đơn hàng nội bộ.
  - Số lượng Private Webhooks hoạt động đồng thời và khả năng lọc thông báo đơn theo chi nhánh/kênh bán có thể khác nhau giữa gói **Standard** và **Grow / Scale**.
- **Pre-flight Check phiên đăng nhập & Backup Liquid:**
  1. Mở `https://{store_domain}/admin/settings/notifications`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Xác nhận 4 section (`Nội dung email`, `Mẫu in`, `Thông báo đơn hàng`, `Webhooks`) đều hiển thị đầy đủ; chuẩn bị thư mục `scratch/` để lưu file backup `.liquid` nguyên bản trước khi sửa bất kỳ mẫu nào.
  4. Kích hoạt chế độ **Zero Secret Exposure** trước khi cuộn tới section `Webhooks` (tuyệt đối không chụp/in chuỗi Signing Secret).

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/notifications` | 1. `Nội dung email` | `Chỉnh sửa mẫu email`, Toggle Switch trên từng mẫu | 13 mẫu email sự kiện: `Xác nhận đơn hàng`, `Hủy đơn hàng`, `Hoàn tiền đơn hàng`, `Xác nhận giao hàng`, `Cập nhật giao hàng`, `Hoàn tất đơn hàng`, `Đơn hàng chưa hoàn tất`, `Xác nhận tài khoản khách hàng`, `Chào mừng khách hàng`, `Thay đổi mật khẩu`, `Hóa đơn đơn hàng nháp`... |
| `/admin/settings/notifications/{template_id}` | Chi tiết Mẫu Email (HTML/Liquid) | `Xem trước`, `Gửi email thử nghiệm`, `Khôi phục mặc định` (CẤM khi chưa backup), `Lưu` | `Tiêu đề email`, `Nội dung email (HTML/Liquid)` dùng biến Liquid như `{{ order_number }}`, `{{ customer.name }}`, `{{ shop.name }}`, `{{ total_price \| money }}` |
| `/admin/settings/notifications` | 2. `Mẫu in` | Click từng mục: `Đơn hàng`, `Vận đơn`, `Tồn kho`; nút `Lưu`, `Khôi phục mặc định` | Trình soạn thảo HTML/Liquid cho phiếu in đơn hàng, phiếu vận đơn dán kiện hàng (A6/K80/A5) và phiếu kiểm kho |
| `/admin/settings/notifications` | 3. `Thông báo đơn hàng` | `Thêm thông báo đơn hàng`, `Xóa` (HARD-BLOCKED) | Danh sách email nội bộ nhận cảnh báo realtime khi có đơn mới (hỗ trợ chọn địa điểm/kênh nhận thông báo) |
| `/admin/settings/notifications` | 4. `Webhooks` | `Thêm webhook`, `Gửi thông báo thử nghiệm`, `Xóa` (HARD-BLOCKED) | `Sự kiện` (`Tạo đơn hàng / orders/create`, `Cập nhật đơn hàng`, `Thanh toán đơn hàng`, `Cập nhật sản phẩm`...), `Định dạng` (`JSON`), `URL` (`https://...`), chuỗi chữ ký bảo mật HMAC (**TUYỆT ĐỐI KHÔNG IN RA LOG**) |

> **Lưu ý cú pháp Liquid:** Haravan kiểm tra cú pháp thẻ Liquid ngay khi bấm `Lưu`. Luôn bấm `Xem trước` trước khi chụp `preview_screenshot` để đảm bảo không thiếu `{% endif %}` / `{% endfor %}` và không vỡ bố cục HTML trên mobile.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `email_templates_ops` | `email_templates_ops` \| `print_templates_ops` \| `internal_order_alerts` \| `private_webhook_setup` |
| `template_name` | `string` | Khi sửa Email / Mẫu in | — | Tên chính xác 1 trong 13 mẫu email hoặc `Đơn hàng` \| `Vận đơn` \| `Tồn kho` |
| `toggle_switches` | `object` | Không | `{}` | Map `{template_name: true\|false}` để bật/tắt email sự kiện |
| `liquid_patch` | `object` | Khi sửa Liquid | `{}` | `{subject?, html_body?}`; phải cân bằng cặp thẻ `{% if %}...{% endif %}`, `{% for %}...{% endfor %}` |
| `notify_email` | `string` | Khi `internal_order_alerts` | — | Email nội bộ hợp lệ (che PII khi báo cáo nếu là email cá nhân) |
| `webhook_config` | `object` | Khi `private_webhook_setup` | `{}` | `{event, format: "json", url: "https://..."}`; **từ chối tuyệt đối `http://` hoặc IP nội bộ** |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi qua cổng Screenshot-Before-Save |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Bật/tắt & Chỉnh sửa mã Liquid 13 mẫu Email khách hàng (`email_templates_ops`)
- **Điều kiện kích hoạt:** Chuẩn hóa nhận diện thương hiệu trong email giao dịch, bổ sung hotline CSKH hoặc bật email nhắc đơn bỏ giỏ.
1. Tại `/admin/settings/notifications` → section `Nội dung email`, rà soát trạng thái Toggle Switch của toàn bộ 13 mẫu email sự kiện.
2. Nếu chỉ bật/tắt sự kiện (ví dụ bật `Xác nhận giao hàng` hoặc `Đơn hàng chưa hoàn tất`), gạt đúng các switch theo `toggle_switches`.
3. Nếu cần sửa nội dung: click vào tên mẫu (hoặc `Chỉnh sửa mẫu email`), **BẮT BUỘC copy toàn bộ HTML/Liquid gốc** lưu vào `scratch/backup_email_{template}.liquid` trước khi sửa bất kỳ dòng nào.
4. Cập nhật `Tiêu đề email` / `Nội dung email (HTML/Liquid)` theo `liquid_patch`, sử dụng đúng các biến chuẩn Haravan (`{{ order_number }}`, `{{ customer.name }}`, `{{ shop.name }}`, `{{ total_price | money }}`, `{{ line.title }}`).
5. Click nút `Xem trước` để kiểm tra lỗi cú pháp Liquid và kiểm tra hiển thị trên khung xem trước. **DỪNG — chưa bấm `Lưu`**.

### Scenario 2: Chỉnh sửa `Mẫu in` Đơn hàng / Vận đơn / Tồn kho (`print_templates_ops`)
- **Điều kiện kích hoạt:** Kho chuyển sang máy in nhiệt A6/K80 hoặc cần bổ sung QR chuyển khoản, ghi chú *“Cho xem hàng, không thử”* lên phiếu dán hộp.
1. Cuộn tới section `Mẫu in` trên `/admin/settings/notifications`.
2. Mở đúng mục mục tiêu (`Đơn hàng`, `Vận đơn` hoặc `Tồn kho`).
3. **BẮT BUỘC sao lưu toàn bộ mã HTML/Liquid gốc** vào `scratch/backup_print_{type}.liquid`.
4. Dán mã mẫu in mới đã căn chuẩn khổ giấy thực tế của kho:
   - Khổ nhiệt `A6 (100×150mm)` hoặc `K80 (80mm)` cho `Vận đơn` dán hộp: ưu tiên mã vạch, SĐT nhận, địa chỉ và tiền thu hộ COD in đậm.
   - Khổ `A4 / A5` cho `Đơn hàng` và phiếu `Tồn kho`: đầy đủ bảng SKU, số lượng, ghi chú đóng gói và chữ ký bàn giao.
5. Kiểm tra không có thẻ Liquid mở chưa đóng và không tràn lề ngang. **DỪNG — chưa bấm `Lưu`**, chụp ảnh preview gửi người dùng duyệt.

### Scenario 3: Thêm / Kiểm tra người nhận `Thông báo đơn hàng` nội bộ (`internal_order_alerts`)
- **Điều kiện kích hoạt:** Cửa hàng muốn thêm email kho/CSKH/quản lý nhận cảnh báo realtime ngay khi có đơn hàng mới phát sinh.
1. Cuộn tới section `Thông báo đơn hàng` trên `/admin/settings/notifications`.
2. Ghi nhận toàn bộ danh sách email nội bộ hiện đang nhận cảnh báo đơn mới (tránh thêm trùng lặp và tuyệt đối không xóa email cũ đang dùng).
3. Click `Thêm thông báo đơn hàng`, chọn phương thức `Email`, nhập `notify_email` (khuyến nghị dùng group email vận hành như `ops@thuonghieu.vn`, `kho-hcm@thuonghieu.vn` thay vì email cá nhân).
4. Chọn phạm vi chi nhánh/kho hoặc kênh bán áp dụng (nếu giao diện hỗ trợ lọc theo địa điểm).
5. **DỪNG — chưa bấm `Lưu` / `Thêm`**, chụp ảnh preview modal gửi người dùng duyệt.

### Scenario 4: Thêm / Kiểm tra Private Webhook HTTPS & Xác thực chữ ký HMAC (`private_webhook_setup`)
- **Điều kiện kích hoạt:** Tích hợp realtime sự kiện Haravan sang n8n, Make, ERP, CRM nội bộ mà không cần tạo Public App trên Haravan Partner.
1. Cuộn xuống cuối trang `/admin/settings/notifications` → section `Webhooks`.
2. Rà soát toàn bộ danh sách webhook hiện có (ghi nhận các sự kiện đang chạy, tuyệt đối không chạm/xóa endpoint của ERP/Kế toán/CRM).
3. Click nút `Thêm webhook`:
   - Chọn đúng `Sự kiện` (`Tạo đơn hàng / orders/create`, `Cập nhật đơn hàng / orders/updated`, `Thanh toán đơn hàng / orders/paid`, `Hủy đơn hàng / orders/cancelled`, `Cập nhật sản phẩm / products/update`).
   - Giữ `Định dạng` = `JSON`.
   - Nhập URL endpoint `https://...` từ `webhook_config.url` (kiểm tra có chứng chỉ SSL hợp lệ; từ chối `http://`).
4. **Quy tắc Zero Secret Exposure & Xác thực HMAC:**
   - Nhắc kỹ thuật viên/Chủ shop tự sao chép chuỗi chữ ký bảo mật hiển thị ở cuối section `Webhooks` trực tiếp trên trình duyệt để cấu hình xác minh header `X-Haravan-Hmac-Sha256` (HMAC-SHA256 Base64 trên raw body) phía server nhận.
   - Agent **TUYỆT ĐỐI KHÔNG đọc, không copy và không ghi chuỗi secret này vào báo cáo, screenshot hay JSON**.
5. **DỪNG — chưa bấm `Lưu`**. (Sau khi lưu ở Pha 4, có thể bấm `Gửi thông báo thử nghiệm` nếu người dùng yêu cầu test kết nối).

### Danh mục nhanh các biến Liquid thường dùng khi chỉnh Mẫu Email / Mẫu in
| Biến Liquid chuẩn | Ý nghĩa hiển thị | Áp dụng |
| :--- | :--- | :--- |
| `{{ order_number }}` | Mã đơn hàng (kèm tiền tố/hậu tố) | Email đơn hàng, Mẫu in Đơn/Vận đơn |
| `{{ customer.name }}` / `{{ shipping_address.phone }}` | Tên & SĐT người nhận | Email & Phiếu vận đơn |
| `{{ total_price \| money }}` | Tổng tiền đơn hàng định dạng VND | Email xác nhận, Mẫu in Đơn/Vận đơn |
| `{{ shop.name }}` / `{{ shop.phone }}` | Tên cửa hàng & Hotline từ `/general` | Chân trang 13 mẫu Email |

## 5. Quy trình An toàn 4 Pha (4-Phase Browser Safety Protocol)

### Pha 1: Pre-State Capture & Liquid Backup
- Mở `/admin/settings/notifications`, chụp ảnh 4 section (`artifacts/notifications_pre.png`, cắt/che hoàn toàn vùng chứa Webhook Signing Secret).
- Nếu sắp chỉnh Mẫu Email hoặc Mẫu In, **bắt buộc sao lưu 100% mã HTML/Liquid gốc** vào `scratch/backup_{type}.liquid` trước khi chỉnh sửa.

### Pha 2: Stage Without Saving (Chỉnh Switch / Liquid / Form Webhook)
- Thực hiện bật/tắt switch, dán mã Liquid đã kiểm tra bằng nút `Xem trước`, hoặc điền form thêm thông báo đơn / Private Webhook HTTPS (`JSON`).
- Kiểm tra mọi endpoint Webhook đều bắt đầu bằng `https://` và không trùng lặp với webhook cũ.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu`**.

### Pha 3: Screenshot-Before-Save & Human Approval Gate
- Chụp ảnh trạng thái đã điền (`artifacts/notifications_preview.png`, không lộ Webhook Secret).
- Trình bày bảng `Before → After` (Mục 6) kèm đường dẫn file backup Liquid, dừng chờ người dùng xác nhận (`confirmation_required: true`).

### Pha 4: Save & Post-Save Reload Verification
- Sau khi người dùng xác nhận, bấm nút `Lưu` và chờ toast thông báo thành công.
- Nhấn `F5` reload trang `/admin/settings/notifications`, xác minh switch, mã Liquid hoặc dòng webhook mới đã lưu bền vững và chụp `artifacts/notifications_post.png`.
- Theo yêu cầu người dùng, bấm `Gửi email thử nghiệm` (với Email) hoặc `Gửi thông báo thử nghiệm` (với Webhook) để kiểm chứng end-to-end.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/notifications`)

| Section | Hạng mục | Trước (Before) | Đề xuất (After) | Kiểm chuẩn an toàn |
| :--- | :--- | :--- | :--- | :--- |
| `Nội dung email` | `Đơn hàng chưa hoàn tất` | `Đang tắt` | `Bật` + cập nhật hotline CSKH | Đã backup Liquid & bấm `Xem trước` |
| `Mẫu in` | `Vận đơn` | Khổ A5 mặc định | Chuẩn hóa khổ nhiệt `A6 (100×150mm)` | Đã backup vào `scratch/` |
| `Thông báo đơn hàng` | Email nhận đơn mới | `ops@abc.vn` | Giữ nguyên + thêm `kho@abc.vn` | Không xóa email cũ |
| `Webhooks` | Sự kiện `orders/create` | *(Chưa có)* | `https://n8n.abc.vn/webhook/hrv` (`JSON`) | Secret HMAC bị che hoàn toàn |

> **Yêu cầu xác nhận:** Cấu hình tại `/admin/settings/notifications` đã được chuẩn bị sẵn (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng xác nhận **"Đồng ý lưu cấu hình thông báo & webhook"** để Agent bấm nút `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-notifications-print-webhooks",
  "scenario": "private_webhook_setup",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/notifications",
  "phase_status": "awaiting_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/notifications_pre.png",
    "preview_screenshot": "artifacts/notifications_preview.png",
    "post_screenshot": "artifacts/notifications_post.png",
    "liquid_backup_path": "scratch/backup_email_order_confirm.liquid"
  },
  "checks_passed": {
    "liquid_preview_ok": true,
    "https_only_enforced": true,
    "hmac_secret_redacted": true,
    "existing_webhooks_preserved": true
  },
  "changes_staged": {
    "webhook_event": "orders/create",
    "webhook_format": "json",
    "webhook_url": "https://n8n.abc.vn/webhook/hrv"
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Xóa` Private Webhook đang chạy live | **HARD-BLOCKED** | Làm đứt đồng bộ realtime sang ERP, kế toán, CRM hoặc n8n đang vận hành |
| `Xóa` email tại `Thông báo đơn hàng` | **HARD-BLOCKED** | Khiến bộ phận vận hành bỏ lỡ cảnh báo đơn mới |
| `Khôi phục mặc định` khi chưa backup Liquid | **HARD-BLOCKED** | Mất vĩnh viễn toàn bộ mã HTML/Liquid tùy biến của thương hiệu |
| Chuỗi ký tự `Webhook Signing Secret` (HMAC) | **ZERO EXPOSURE** | Tuyệt đối không đọc, không copy, không ghi vào chat/JSON/git; Owner tự sao chép trực tiếp |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Toast báo lỗi cú pháp Liquid khi lưu Mẫu Email / Mẫu in:** Thường do thiếu thẻ đóng `{% endif %}`, `{% endfor %}` hoặc sai tên biến object → Không bỏ qua, kiểm tra đối chiếu với file backup ở `scratch/` và bấm `Xem trước` lại đến khi sạch lỗi.
2. **Bấm `Gửi thông báo thử nghiệm` Webhook nhưng server nhận không thấy request:** Kiểm tra endpoint có dùng `https://` với chứng chỉ SSL công khai hợp lệ không, có bị tường lửa/Cloudflare Bot Fight Mode chặn IP Haravan không, và kiểm tra HTTP status trả về (`200 OK` trong `< 5 giây`).
3. **In `Vận đơn` bị nhảy sang 2 trang hoặc mất lề phải:** Do CSS `@page` trong mẫu in chưa khớp khổ giấy máy in nhiệt (`100mm × 150mm` hoặc `80mm`) → Điều chỉnh lại kích thước `width` trong CSS và in thử 1 đơn mẫu.
4. **Staff không thấy mục `Webhooks` hoặc báo 403:** Tài khoản thiếu quyền `Cấu hình > Thông báo` → Yêu cầu Owner đăng nhập hoặc cấp quyền tạm thời.
5. **Email gửi khách bị rơi vào mục Spam:** Kiểm tra `Email chăm sóc khách hàng` tại `/admin/settings/general` và đề xuất Owner cấu hình bản ghi SPF/DKIM tại nhà cung cấp tên miền nếu dùng email theo domain riêng.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Với Mẫu Email / Mẫu in: mở lại mẫu vừa sửa, dán nguyên vẹn nội dung từ file `scratch/backup_*.liquid` đã lưu ở Pha 1 (hoặc dùng `Khôi phục mặc định` nếu trước đó là mẫu gốc) rồi bấm `Lưu`.
2. Với Switch Email: đối chiếu `artifacts/notifications_pre.png` và gạt lại đúng trạng thái cũ.
3. Với Private Webhook mới thêm: Chủ shop tự bấm `Xóa` đúng dòng URL vừa thêm (tuyệt đối không chạm các webhook cũ).

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Bấm `Gửi email thử nghiệm` và kiểm tra hiển thị trên cả Gmail Desktop & Mobile (không vỡ bảng sản phẩm, không lỗi biến `{{ ... }}`).
- [ ] In thử 1 đơn hàng mẫu ra PDF để xác nhận khổ giấy `Mẫu in` khớp máy in kho.
- [ ] Với Webhook mới: kiểm tra server nhận xác thực thành công chữ ký `X-Haravan-Hmac-Sha256` và trả `200 OK`.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `webhook-subscription-ops`: Đăng ký Connect Webhook qua `https://webhook.haravan.com/api/subscribe` cho Public/Private App (tách biệt với Private Webhook trên Admin UI).
- `skills/browser-ui/` → `admin-ui-general-policies-setup` (đồng bộ logo/email CSKH dùng trong 13 mẫu email), `admin-ui-checkout-settings` (đồng bộ bật nhắc đơn bỏ quên 6h/24h).
