---
name: admin-ui-customers-profile-ops
description: "Vận hành Hồ sơ Khách hàng trên Haravan Admin (/admin/customers): tìm theo SĐT Việt Nam, tạo khách mới, sửa địa chỉ/tag/ghi chú, tra cứu lịch sử đơn & điểm Haraloyalty, xử lý khách trùng SĐT và Import/Export có kiểm soát PII."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 50-customer-crm
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/customers"
    - "UI /admin/customers/new"
    - "UI /admin/customers/{customer_id}"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Admin UI — Vận Hành Hồ Sơ Khách Hàng (`/admin/customers`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Quản trị và làm sạch dữ liệu khách hàng hàng ngày trên Haravan Admin (`https://{store_domain}/admin/customers`) mà không cần API token: tìm kiếm nhanh theo số điện thoại Việt Nam (chuẩn hóa `0xxx` vs `+84xxx`), tạo hồ sơ khách hàng mới, cập nhật địa chỉ giao hàng/nhãn (tags)/ghi chú CSKH, tra cứu lịch sử đơn hàng & hạng thành viên/điểm tích lũy **Haraloyalty**, rà soát & xử lý hồ sơ trùng số điện thoại, và chuẩn hóa quy trình Import có kiểm soát chặt chẽ dữ liệu cá nhân (PII).
- **Phạm vi UI:** Danh sách khách hàng (`/admin/customers`), tạo khách mới (`/admin/customers/new`) và chi tiết hồ sơ khách hàng (`/admin/customers/{customer_id}`). Không bao gồm thiết lập Broadcast/Flow tự động (dùng `admin-ui-crm-flows-broadcast`) hay kiểm duyệt đánh giá (dùng `customer-review-rating-moderation`).
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Toàn quyền xem, tạo, sửa, gắn tag, xem lịch sử đơn, quản lý điểm thành viên và Import/Export khách hàng.
  - **Staff:** Yêu cầu quyền `Khách hàng` (`Xem`, `Tạo mới`, `Cập nhật`). Nhiều cửa hàng khóa quyền `Xuất dữ liệu khách hàng` và `Xóa khách hàng` đối với Staff để bảo mật dữ liệu; Agent tôn trọng hoàn toàn phân quyền này.
- **Yêu cầu Gói dịch vụ Haravan:** Quản lý hồ sơ khách hàng khả dụng trên mọi gói. Khối **Hạng thành viên & Điểm tích lũy (Haraloyalty)** hiển thị khi cửa hàng đã kích hoạt cấu hình thành viên tại `/admin/customers/settings` (gói Pro/Grow/Scale hoặc cài app Haraloyalty).
- **Pre-flight Check bắt buộc:**
  1. Xác minh phiên đăng nhập qua `admin-ui-session-navigator` tại `/admin/customers`.
  2. Tuân thủ tuyệt đối `policies/pii-handling.md`: mọi báo cáo/log trả về cho người dùng phải **che số điện thoại (`090****678`)**, **che email (`a***@domain.com`)**, và không xuất danh sách khách hàng thô (`export_allowed: false`).

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

| Thành phần UI | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Ghi chú thao tác |
| :--- | :--- | :--- | :--- |
| Danh sách khách hàng | `/admin/customers` | Nút góc phải: `Nhập dữ liệu`, `Xuất dữ liệu` (PII — Hard-Blocked mặc định), `Tạo khách hàng` | Ô `Tìm kiếm` hỗ trợ tên, SĐT, email; Nút `Thêm điều kiện lọc` (`Nhóm KH`, `Tag`, `Tổng chi tiêu`, `Số đơn hàng`, `Tỉnh/Thành`, `Trạng thái tài khoản`) |
| Cột bảng khách hàng | Bảng chính `/admin/customers` | `Khách hàng`, `Email`, `Số điện thoại`, `Đơn hàng`, `Đơn hàng gần nhất`, `Tổng chi tiêu` | Click tên khách để mở `/admin/customers/{customer_id}` |
| Tạo khách hàng mới | `/admin/customers/new` | `Họ`, `Tên`, `Email`, `Số điện thoại`, `Ngày sinh`, `Giới tính`, `Địa chỉ` (Tỉnh/Quận/Phường/Chi tiết), `Ghi chú`, `Nhãn (Tags)`, checkbox `Nhận email quảng cáo` | Nút cuối trang: `Lưu` |
| Chi tiết hồ sơ — Cột trái | `/admin/customers/{customer_id}` | `Tổng chi tiêu`, `Số đơn hàng`, `Giá trị đơn trung bình`, danh sách `Đơn hàng gần đây`, khối `Thành viên / Haraloyalty` (Hạng, Điểm hiện có, Lịch sử tích/tiêu điểm) | Click từng mã `#10xxx` để kiểm tra chi tiết đơn của khách |
| Chi tiết hồ sơ — Cột phải | `/admin/customers/{customer_id}` | `Thông tin liên hệ` (nút `Sửa`), `Sổ địa chỉ` (`Địa chỉ mặc định`, `Thêm địa chỉ mới`), `Ghi chú`, `Nhãn (Tags)` | Hỗ trợ lưu nhiều địa chỉ giao hàng cho 1 khách |
| Hộp thoại Import | `/admin/customers` → `Nhập dữ liệu` | `Tải file mẫu`, `Chọn file tải lên` (`.xlsx`/`.csv`), checkbox `Ghi đè khách hàng trùng Email/SĐT` | Luôn kiểm tra kỹ tùy chọn ghi đè để tránh mất tag/ghi chú cũ |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `lookup_and_loyalty` | `lookup_and_loyalty` \| `create_customer` \| `update_profile_tags` \| `dedupe_phone_audit` \| `controlled_import` |
| `phone_query` | `string` | Không | `""` | SĐT VN 10 số (`03x/05x/07x/08x/09x`) hoặc `+84xxxxxxxxx`; tự chuẩn hóa khi tìm |
| `customer_id` | `string` | Không | `""` | ID hồ sơ khách hàng trên Haravan nếu đã xác định |
| `profile_payload` | `object` | Khi tạo/sửa | `null` | Gồm `first_name`, `last_name`, `phone`, `email`, `birthday`, `gender`, `address` (đủ 4 cấp VN) |
| `tags_to_add` | `array<string>` | Không | `[]` | Ví dụ `vip-2026`, `khach-si`, `uu-tien-cskh`; mỗi tag ≤ 40 ký tự |
| `cskh_note` | `string` | Không | `""` | Ghi chú CSKH ngắn gọn (≤ 500 ký tự); không lưu CCCD/số tài khoản nhạy cảm |
| `import_file_path` | `string` | Khi Import | `""` | File `.xlsx` đúng mẫu Haravan, tối đa `50` bản ghi/đợt kiểm soát (`max_records: 50`) |
| `dry_run` | `boolean` | Không | `true` | Bắt buộc `true` ở pha dựng form (Stage Without Saving) |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Tìm kiếm theo SĐT Việt Nam & Tra cứu Lịch sử đơn / Điểm Haraloyalty (Read-Only)
1. Mở `https://{store_domain}/admin/customers`, nhập `phone_query` dạng chuẩn `0xxxxxxxxx` vào ô `Tìm kiếm`.
2. Nếu không thấy kết quả, thử lại với biến thể `+84xxxxxxxxx` hoặc 9 số cuối (loại bỏ `0`/`+84`, không khoảng trắng/dấu chấm) để tránh bỏ sót hồ sơ cũ nhập sai định dạng.
3. Click mở hồ sơ khớp nhất (`/admin/customers/{customer_id}`): đọc `Tổng chi tiêu`, `Số đơn hàng`, trạng thái 5 đơn hàng gần nhất, `Hạng thành viên` và `Số điểm Haraloyalty` khả dụng.
4. Trả báo cáo tóm tắt cho CSKH/Sales với SĐT và Email đã được che (`090****678`, `n***@gmail.com`), không cần lưu thay đổi.

### Kịch bản 2: Tạo hồ sơ khách hàng mới chống trùng lặp
1. Bắt buộc chạy bước tìm kiếm SĐT (cả `0xxx` và `+84xxx`) tại `/admin/customers` trước. Nếu đã tồn tại hồ sơ trùng SĐT, **DỪNG NGAY** và chuyển sang Kịch bản 3 (cập nhật hồ sơ sẵn có) thay vì tạo trùng.
2. Nếu chưa tồn tại: bấm nút `Tạo khách hàng` (`/admin/customers/new`).
3. Điền `Họ`, `Tên`, `Số điện thoại` (chuẩn 10 số `0xxxxxxxxx`), `Email` (nếu khách cung cấp), `Ngày sinh`, `Giới tính`.
4. Tại khối **Địa chỉ**, chọn lần lượt từ dropdown `Quốc gia (Việt Nam)` → `Tỉnh/Thành` → `Quận/Huyện` → `Phường/Xã` → nhập `Địa chỉ chi tiết`.
5. Gắn `Tag` phân loại nguồn khách (ví dụ `khach-zalo`, `khach-showroom`) và `Ghi chú`. **Dừng trước nút `Lưu`**, chụp ảnh preview (che PII trong bảng tóm tắt chat) chờ người dùng duyệt.

### Kịch bản 3: Sửa địa chỉ, gắn Tag phân hạng & cập nhật Ghi chú CSKH
1. Mở `/admin/customers/{customer_id}`, chụp trạng thái hiện có (`Thông tin liên hệ`, `Sổ địa chỉ`, `Tag`, `Ghi chú`).
2. **Sửa địa chỉ:** Tại khối `Sổ địa chỉ` cột phải, bấm `Quản lý địa chỉ` → `Sửa` (hoặc `Thêm địa chỉ mới` nếu muốn giữ lại địa chỉ cũ và đặt địa chỉ mới làm mặc định).
3. **Cập nhật Tag & Ghi chú:** Thêm `tags_to_add` vào ô `Nhãn (Tags)` (không xóa các tag phân loại hệ thống đang có trừ khi được yêu cầu), nối thêm `cskh_note` kèm ngày tháng vào ô `Ghi chú` (ví dụ `[25/11/2026] Khách yêu cầu giao giờ hành chính`).
4. **Dừng trước nút `Lưu`**, chụp ảnh form đã điền và xuất bảng `Before → After` chờ người dùng xác nhận.

### Kịch bản 4: Phát hiện & Xử lý hồ sơ Khách hàng trùng Số điện thoại
1. Tại `/admin/customers`, tìm theo 9 số cuối của `phone_query` để liệt kê toàn bộ hồ sơ trùng (ví dụ 1 hồ sơ `0901234567` từ POS và 1 hồ sơ `+84901234567` từ Website).
2. Mở lần lượt từng hồ sơ (tối đa 5 hồ sơ trùng) để đối chiếu: `Số đơn hàng`, `Tổng chi tiêu`, `Điểm Haraloyalty`, `Trạng thái tài khoản Website`.
3. Xác định **Hồ sơ chính (Primary Profile)** — thường là hồ sơ có nhiều đơn hơn hoặc đã kích hoạt tài khoản/điểm Haraloyalty — và **Hồ sơ phụ (Duplicate)**.
4. Vì Haravan Admin không có nút gộp tự động an toàn cho mọi trường hợp và cấm tự bấm `Xóa khách hàng`, Agent đề xuất gắn tag `trung-sdt-can-gop` lên hồ sơ phụ, bổ sung ghi chú trỏ sang ID hồ sơ chính và chuẩn hóa định dạng SĐT trên hồ sơ chính (dừng trước `Lưu` chờ duyệt).

### Kịch bản 5: Import danh sách khách hàng có kiểm soát PII (Không tự Export thô)
1. Kiểm tra file `import_file_path` đáp ứng giới hạn `<= 50` khách/lượt và đã chuẩn hóa SĐT 10 số kiểu `Text` trong Excel.
2. Tại `/admin/customers`, bấm `Nhập dữ liệu`, chọn file `import_file_path` và giữ **tắt** checkbox `Ghi đè khách hàng trùng` (trừ khi người dùng yêu cầu rõ ràng bằng văn bản).
3. **Dừng tại màn hình Preview tải file** trước khi bấm `Nhập dữ liệu`; chụp ảnh hộp thoại xác nhận tên file, số dòng ước tính và tùy chọn ghi đè để người dùng phê duyệt. (Tuyệt đối không bấm `Xuất dữ liệu` toàn bộ tệp khách hàng nếu không có phê duyệt bảo mật riêng).

### Bảng Đối Chiếu Nguồn Hồ Sơ Khách Hàng & Lưu Ý Vận Hành

| Nguồn tạo hồ sơ | Đặc điểm hiển thị trên `/admin/customers` | Lưu ý khi Agent cập nhật hồ sơ |
| :--- | :--- | :--- |
| Website (`Online Store`) | Có Email & trạng thái `Đã kích hoạt tài khoản` | Cảnh báo trước khi sửa Email vì ảnh hưởng đăng nhập của khách |
| Haravan POS / Tại quầy | Chủ yếu có SĐT VN 10 số, thường thiếu Email/Địa chỉ | Chuẩn hóa SĐT `0xxxxxxxxx`, bổ sung tag chi nhánh mua hàng |
| Harasocial (FB / Zalo) | Thường đồng bộ tên Facebook + SĐT trích xuất từ tin nhắn | Kiểm tra kỹ 9 số cuối SĐT để tránh tạo trùng với khách Website |
| Sàn TMĐT (Shopee / TikTok) | SĐT và tên người nhận có thể bị sàn ẩn/mã hóa (`***`) | **Không ghi đè** thông tin mã hóa của sàn lên hồ sơ khách thật |

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Protocol)

1. **Pha 1 — Pre-State Capture (Kiểm tra trùng SĐT & Chụp hồ sơ gốc):**
   - Tìm kiếm bằng cả định dạng `0xxxxxxxxx`, `+84xxxxxxxxx` và 9 số cuối tại `/admin/customers` để chắc chắn không bỏ sót hồ sơ trùng.
   - Mở `/admin/customers/{customer_id}` (nếu sửa), ghi nhận đầy đủ trường cũ (`phone`, `email`, `address`, `tags`, `note`, `loyalty_points`, `orders_count`) và chụp `pre_screenshot`.
2. **Pha 2 — Stage Without Saving (`dry_run: true`):**
   - Điền form tạo khách mới, cập nhật sổ địa chỉ 4 cấp, bổ sung tag phân hạng/ghi chú CSKH hoặc nạp sẵn file `.xlsx` trong hộp thoại `Nhập dữ liệu`.
   - Kiểm tra kỹ không ghi đè mất các tag hệ thống cũ và không làm sai định dạng SĐT 10 số.
   - **Dừng tuyệt đối trước nút `Lưu` / `Nhập dữ liệu`**.
3. **Pha 3 — Screenshot-Before-Save Gate (Cổng xác nhận & Che PII):**
   - Chụp `preview_screenshot` của form đã điền sẵn (trình duyệt cục bộ).
   - Lập bảng `Before → After` trả về khung chat với **toàn bộ PII đã được che theo `policies/pii-handling.md`** (`090****678`, `a***@domain.com`, không in địa chỉ số nhà chi tiết nếu không cần thiết) và dừng chờ người dùng xác nhận.
4. **Pha 4 — Save & Post-Save Reload Verification (Xác minh lưu bền vững):**
   - Sau khi người dùng xác nhận, bấm `Lưu` (hoặc `Nhập dữ liệu`), chờ toast thông báo xanh (`Cập nhật khách hàng thành công` / `Tạo khách hàng thành công`).
   - Nhấn `F5` reload lại trang `/admin/customers/{customer_id}`, kiểm tra SĐT, địa chỉ mặc định, tag và ghi chú mới đã hiển thị đúng, sau đó chụp `post_screenshot`.

### Checklist Bảo Mật PII & Vệ Sinh Hồ Sơ Khách Hàng

- [ ] Đã kiểm tra 9 chữ số cuối SĐT trên `/admin/customers` trước khi tạo mới để tránh nhân bản hồ sơ khách hàng.
- [ ] Mọi đầu ra văn bản/JSON/bảng báo cáo đều đã che SĐT (`091****456`) và Email (`l***@gmail.com`).
- [ ] Không bấm nút `Xuất dữ liệu` (Export danh sách khách thô) và không bấm `Xóa khách hàng`.
- [ ] Ghi chú CSKH có gắn mốc ngày `[DD/MM/YYYY]`, không chứa thông tin nhạy cảm (số CCCD, số thẻ ngân hàng, mật khẩu).
- [ ] Nếu Import file: số bản ghi ≤ `50` (`max_records: 50`), định dạng `.xlsx`, cột SĐT là `Text`, checkbox `Ghi đè` mặc định tắt.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Cập nhật Hồ sơ (PII Redacted)

| Khách hàng (ID / Redacted) | Trường thay đổi | Trước (Before) | Sau (After — Staged) | Kiểm tra PII & Trùng lặp |
| :--- | :--- | :--- | :--- | :--- |
| `#C-88412` — Lê Minh C (`091****456`) | `Địa chỉ mặc định` | `P. 1, Q. 3, TP.HCM` | `P. An Phú, TP. Thủ Đức, TP.HCM` | ✅ Đủ 4 cấp VN |
| `#C-88412` — Lê Minh C (`091****456`) | `Nhãn (Tags)` | `website` | `website, vip-2026, giao-gio-hc` | ✅ Giữ nguyên tag cũ |
| `#C-88412` — Lê Minh C (`091****456`) | `Ghi chú CSKH` | *(Trống)* | `[25/11/2026] Ưu tiên giao trước 17h` | ✅ Không chứa dữ liệu nhạy cảm |
| `#C-90105` — Lê Minh C (`+8491****456`) | `Xử lý trùng SĐT` | Hồ sơ phụ (0 đơn) | Gắn tag `trung-sdt-can-gop`, ghi chú trỏ `#C-88412` | ✅ Không tự xóa hồ sơ |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-customers-profile-ops",
  "mode": "proposal",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/customers/88412",
  "scenario": "update_profile_tags",
  "session_authenticated": true,
  "dry_run": true,
  "pii_redacted": true,
  "export_blocked": true,
  "duplicate_phone_checked": true,
  "pre_screenshot": "artifacts/customer_88412_pre.png",
  "preview_screenshot": "artifacts/customer_88412_staged.png",
  "post_screenshot": null,
  "changes_staged": [
    {
      "customer_id": "88412",
      "phone_masked": "091****456",
      "email_masked": "l***@gmail.com",
      "loyalty_tier": "Gold",
      "loyalty_points": 1250,
      "tags_added": ["vip-2026", "giao-gio-hc"],
      "address_updated": true
    }
  ],
  "warnings": [],
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm trên `/admin/customers`:**
  - `Xóa khách hàng` (`Delete customer`) — gây mất lịch sử liên kết CRM/Haraloyalty không thể phục hồi.
  - `Xuất dữ liệu` (Export toàn bộ danh sách khách hàng chứa SĐT/Email/Địa chỉ thô) — bị chặn tuyệt đối bởi `export_allowed: false` và `policies/pii-handling.md`.
  - `Cộng / Trừ điểm thủ công` trên khối Haraloyalty khi không có yêu cầu và chứng từ duyệt riêng (điểm thưởng quy đổi thành tiền giảm giá).
- **Credential & Privacy Handoff Gate:**
  - Gặp `accounts.haravan.com` → dừng ngay cho người dùng tự đăng nhập.
  - Không bao giờ sao chép hàng loạt SĐT/Email khách hàng ra log, file markdown hoặc chat chưa che PII.

### Quy Tắc Chuẩn Hóa & Che Dữ Liệu Cá Nhân (PII Redaction Rules)

| Trường dữ liệu khách hàng | Chuẩn nhập vào Haravan Admin UI | Chuẩn hiển thị trong Chat / Báo cáo / JSON Log |
| :--- | :--- | :--- |
| Số điện thoại VN | 10 chữ số chuẩn (`0912345678`), không khoảng trắng | Che 4 số giữa: `091****678` |
| Địa chỉ Email | Viết thường, đúng cú pháp (`leminhc@gmail.com`) | Che phần tên: `l***@gmail.com` |
| Địa chỉ giao hàng | Đủ 4 cấp dropdown (`Tỉnh/Quận/Phường`) + số nhà | Chỉ tóm tắt cấp `Phường/Quận/Tỉnh` trong bảng preview |
| Ghi chú CSKH | `[DD/MM/YYYY] Nội dung vận hành/giao nhận` | Không ghi số CCCD, số tài khoản, thông tin y tế/tài chính |

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Khách hàng có 2 định dạng SĐT (`090...` và `+8490...`) hoặc có khoảng trắng:** Tìm kiếm chính xác dễ bỏ sót hồ sơ cũ. Agent luôn tìm theo 9 chữ số cuối trước khi kết luận khách mới để tránh nhân bản hồ sơ.
2. **Không thể xóa hoặc sửa Email của khách đã kích hoạt tài khoản Website:** Với khách đã đăng ký tài khoản đăng nhập storefront, việc đổi Email sẽ ảnh hưởng đến thông tin đăng nhập của khách; Agent cảnh báo và yêu cầu xác nhận trước khi sửa Email.
3. **Excel tự động mất số `0` đầu của SĐT khi Import:** File `.csv` mở trực tiếp trên Excel hay biến `0901234567` thành `901234567`. Agent yêu cầu kiểm tra cột SĐT phải ở định dạng `Text` (`.xlsx`) trước khi tải lên.
4. **Điểm Haraloyalty hiển thị chậm sau đơn hàng vừa hoàn tất:** Điểm tích lũy chỉ cộng sau khi đơn chuyển trạng thái `Đã giao hàng` & `Đã thanh toán` (tùy cấu hình cửa hàng); không kết luận lỗi hệ thống khi đơn mới ở trạng thái `Đang giao`.
5. **Trùng SĐT giữa khách mua tại POS và khách mua trên Sàn TMĐT (Shopee/TikTok):** Đơn từ sàn thường bị mã hóa SĐT (`090*****89`); tuyệt đối không sửa đè SĐT mã hóa của sàn lên hồ sơ khách thật đang dùng trên Website/POS.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback Thủ công trên UI (Bảo toàn Dữ liệu CRM)
- **Tag / Ghi chú sửa nhầm:** Mở lại `/admin/customers/{customer_id}`, bấm dấu `x` gỡ từng tag vừa thêm sai, khôi phục nguyên văn `Ghi chú` từ `pre_screenshot` và bấm `Lưu`.
- **Địa chỉ mặc định cập nhật nhầm:** Mở khối `Sổ địa chỉ` → chọn lại địa chỉ cũ làm `Địa chỉ mặc định` (hoặc chỉnh lại đúng 4 cấp `Tỉnh/Quận/Phường/Số nhà` theo `pre_screenshot`).
- **Tạo nhầm hồ sơ mới trùng lặp:** Không tự ý bấm `Xóa khách hàng` nếu hồ sơ đã phát sinh đơn hoặc điểm thưởng; gắn tag `ho-so-nhap-trung` và ghi chú mã ID hồ sơ chính để Owner rà soát.
- **Import hàng loạt sai cột SĐT/Tag:** Đối chiếu danh sách ID vừa tạo/cập nhật trong lịch sử Import, không chạy lại Import với tùy chọn `Ghi đè` khi chưa sửa xong file gốc `.xlsx`.

### Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan
- Quét trùng SĐT toàn hệ thống, phân khúc RFM, giữ chân cohort & danh sách VIP có nguy cơ rời bỏ bằng API: `skills/api-mcp/50-customer-crm/customer-duplicate-phone-finder`, `customer-rfm-segmentation`, `customer-cohort-retention`, `customer-vip-churn-watchlist`.
- Đề xuất gắn tag/ghi chú & chuẩn hóa địa chỉ khách hàng quy mô lớn qua API: `customer-tag-note-proposal`, `customer-address-correction-proposal`.
- Chạy Broadcast/Flow chăm sóc khách hàng, quản lý đánh giá & xử lý đơn hàng theo khách trên UI: `skills/browser-ui/95-admin-ui-browser/admin-ui-crm-flows-broadcast`, `skills/browser-ui/50-customer-crm/customer-review-rating-moderation`, `skills/browser-ui/40-orders-fulfillment/admin-ui-orders-daily-ops`.
