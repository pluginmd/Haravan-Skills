---
name: admin-ui-payment-methods-setup
description: "Cấu hình Haravan QR, Cổng thanh toán trực tuyến (VNPay, MoMo, ZaloPay) và Thanh toán thủ công (COD, Chuyển khoản) tại /admin/settings/payments."
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
    - "UI /admin/settings/payments"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 10
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: financial
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: true
---

# Haravan Admin UI: Payment Methods, Haravan QR & COD Setup (Critical L3)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Toàn bộ cấu hình nhận tiền trên trang thanh toán — gồm **Haravan QR** (sinh mã VietQR động và tự động gạch nợ đơn hàng), **Cổng thanh toán trực tuyến** (VNPay, MoMo, ZaloPay, OnePay, Payoo, Fundiin, Kredivo...) và **Thanh toán thủ công** (`Thanh toán khi giao hàng (COD)`, `Chuyển khoản qua ngân hàng`) tại `/admin/settings/payments` — **không có REST API công khai** và chỉ thao tác được trên Haravan Admin UI.
- **Mức độ rủi ro L3 Critical (`separate_turn: true`):** Mọi thay đổi trên màn hình này tác động trực tiếp tới **dòng tiền sống** của doanh nghiệp. Sai 1 chữ số tài khoản ngân hàng, dán sai Merchant Key hoặc tắt nhầm COD có thể làm đứt luồng đặt hàng hoặc khiến khách chuyển khoản nhầm.
- **Phân quyền Owner vs Staff:**
  - **Bắt buộc tài khoản Chủ cửa hàng (Owner):** Mặc định quyền **Cấu hình > Phương thức thanh toán** bị khóa với Staff thường. Chỉ Owner (hoặc Staff cấp cao được Owner ủy quyền tường minh) mới thấy nút `Thêm`, `Thêm tài khoản` và `Thao tác`.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Tất cả các gói đều hỗ trợ `Thanh toán thủ công` (COD, Chuyển khoản) và kết nối cổng thanh toán đối tác (VNPay/MoMo/ZaloPay yêu cầu hợp đồng doanh nghiệp/hộ kinh doanh riêng với từng cổng).
  - `Haravan QR` hỗ trợ các ngân hàng đối tác liên kết (Vietcombank, Techcombank, BIDV, MB, ACB, VPBank...) theo điều kiện gói và định danh tài khoản của cửa hàng.
- **Pre-flight Check phiên đăng nhập & Quyền Owner:**
  1. Mở `https://{store_domain}/admin/settings/payments`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để Owner tự đăng nhập; tuyệt đối không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Kiểm tra tài khoản hiện tại có hiển thị đầy đủ nút `Thêm tài khoản` (Haravan QR), `Thêm` (Cổng thanh toán) và `Thao tác` (Thanh toán thủ công) không; nếu bị ẩn, dừng ngay vì thiếu quyền Owner.
  4. Xác nhận trước với Owner cửa hàng đang thao tác là `staging` hay `production`, đồng thời chuẩn bị chế độ che toàn bộ dữ liệu tài chính (STK `****5678`, ẩn hoàn toàn Secret Key).

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/settings/payments` — 3 sections: `Haravan QR` (`Thêm tài khoản`), `Cổng thanh toán` (`Thêm`), `Thanh toán thủ công` (`Thêm`, `Thao tác` trên `Thanh toán khi giao hàng (COD)` & `Chuyển khoản qua ngân hàng`).


| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình chính & Hành vi thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/payments` | 1. `Haravan QR` | `Thêm tài khoản`, `Cấu hình`, `Ngừng kết nối` (HARD-BLOCKED) | Liên kết tài khoản ngân hàng (VCB, TCB, BIDV, MB, ACB, VPBank...) để sinh mã VietQR động kèm số tiền & mã đơn, tự động gạch nợ chuyển `Đã thanh toán` |
| `/admin/settings/payments` | 2. `Cổng thanh toán` | `Thêm`, `Kết nối`, `Chỉnh sửa`, `Ngừng kích hoạt` (HARD-BLOCKED) | Chọn nhà cung cấp (VNPay, MoMo, ZaloPay, OnePay, Payoo, Fundiin...), nhập `Merchant ID`, `Terminal ID`, `Access Code`, `Hash Secret / Secret Key` (**Owner tự nhập**) |
| `/admin/settings/payments` | 3. `Thanh toán thủ công` | `Thêm`, `Thao tác` (mở chi tiết từng phương thức), `Lưu`, `Ngừng kích hoạt` (HARD-BLOCKED) | Gồm `Thanh toán khi giao hàng (COD)`, `Chuyển khoản qua ngân hàng`, hoặc phương thức tùy chỉnh; cấu hình `Tên phương thức thanh toán` và `Hướng dẫn thanh toán` |

> **Cảnh báo rủi ro tài chính:** Mọi thay đổi tại `/admin/settings/payments` có hiệu lực tức thì trên trang Checkout công khai ngay khi bấm `Lưu`. Luôn kiểm tra chéo với `/admin/settings/checkouts` nếu cửa hàng có bật `Thiết lập đặt cọc`.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `audit_payments` | `audit_payments` \| `setup_haravan_qr` \| `connect_online_gateway` \| `configure_cod` \| `configure_bank_transfer` |
| `gateway_provider` | `string` | Khi `connect_online_gateway` | — | `VNPay` \| `MoMo` \| `ZaloPay` \| `OnePay` \| `Payoo` \| `Fundiin` |
| `method_display_name` | `string` | Không | — | Tên hiển thị cho khách tại bước checkout (ngắn gọn, rõ ràng, không gây hiểu nhầm) |
| `instructions_text` | `string` | Khi `configure_cod` / `configure_bank_transfer` | — | Nội dung hướng dẫn hiển thị trên trang checkout & trang cảm ơn; **tuyệt đối không chứa mật khẩu/secret** |
| `dry_run` | `boolean` | Có | `true` | Bắt buộc `true`; mọi thao tác ghi L3 bắt buộc `separate_turn: true` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Kiểm toán hiện trạng Phương thức thanh toán (`audit_payments` — Read-Only)
- **Điều kiện kích hoạt:** Trước các đợt sale lớn (Mega Sale, Tết) hoặc khi rà soát tỷ lệ đơn chờ thanh toán tăng bất thường.
1. Điều hướng tới `https://{store_domain}/admin/settings/payments`, chờ cả 3 section (`Haravan QR`, `Cổng thanh toán`, `Thanh toán thủ công`) tải đầy đủ.
2. Ghi nhận danh sách phương thức đang ở trạng thái `Đang kích hoạt` so với `Chưa kết nối` / `Ngừng kích hoạt`.
3. Kiểm tra nhanh 4 rủi ro vận hành phổ biến:
   - Có đang bật trùng lặp quá nhiều phương thức tương tự nhau gây rối khách trên mobile không?
   - `Thanh toán khi giao hàng (COD)` có đang bị tắt nhầm không?
   - Nội dung `Hướng dẫn thanh toán` chuyển khoản có khớp tên doanh nghiệp & hotline tại `/admin/settings/general` không?
   - Cổng thanh toán trực tuyến có đang bị để nhầm ở chế độ `Sandbox / Test` không?
4. **Che hoàn toàn số tài khoản ngân hàng (`****5678`) và mọi khóa bảo mật** trong báo cáo kiểm toán; kết thúc mà không thực hiện bất kỳ thao tác ghi nào.

### Scenario 2: Kết nối `Haravan QR` tự động gạch nợ đơn hàng (`setup_haravan_qr`)
- **Điều kiện kích hoạt:** Cửa hàng muốn sinh mã VietQR động kèm sẵn số tiền + mã đơn và tự động xác nhận `Đã thanh toán` khi tiền về tài khoản.
1. Tại section `Haravan QR` trên `/admin/settings/payments`, chụp ảnh trạng thái ban đầu (`pre_screenshot`).
2. Click nút `Thêm tài khoản` để mở luồng chọn ngân hàng liên kết (Vietcombank, Techcombank, BIDV, MB, ACB, VPBank...).
3. **DỪNG NGAY LẬP TỨC (Financial & OTP Handoff Gate):** Yêu cầu Chủ cửa hàng tự chọn ngân hàng, tự nhập số tài khoản/CCCD/MST định danh và nhập mã **OTP ngân hàng** trực tiếp trên trình duyệt.
4. Sau khi Chủ shop hoàn tất liên kết trên trình duyệt, Agent hỗ trợ chụp ảnh xác minh trạng thái `Đã kết nối` (đã che STK) và khuyến nghị test 1 đơn hàng trị giá nhỏ (`10.000đ`) để xác nhận đơn tự động chuyển `Đã thanh toán`.

### Scenario 3: Kết nối Cổng thanh toán trực tuyến VNPay / MoMo / ZaloPay (`connect_online_gateway`)
- **Điều kiện kích hoạt:** Cửa hàng đã ký hợp đồng merchant và nhận bộ thông số Production từ VNPay, MoMo, ZaloPay, OnePay, Payoo hoặc Fundiin.
1. Tại section `Cổng thanh toán`, kiểm tra xem `gateway_provider` đã tồn tại trong danh sách chưa (tránh tạo trùng lặp gây lỗi hiển thị checkout).
2. Click nút `Thêm` → tìm và chọn đúng nhà cung cấp (`VNPay`, `MoMo`, `ZaloPay`, `OnePay`, `Payoo`).
3. Mở tới form cấu hình thông số kết nối (`Merchant ID`, `Terminal ID`, `Access Code`, `Hash Secret / Secret Key`, chế độ `Production`).
4. **DỪNG NGAY LẬP TỨC (Zero Credential Exposure Gate):** Yêu cầu Chủ cửa hàng tự copy/paste các khóa bí mật trực tiếp từ cổng quản trị VNPay/MoMo/ZaloPay vào trình duyệt và tự kiểm tra không dính khoảng trắng thừa ở đầu/cuối chuỗi.

### Scenario 4: Cấu hình `Thanh toán khi giao hàng (COD)` & Hướng dẫn kiểm hàng (`configure_cod`)
- **Điều kiện kích hoạt:** Cửa hàng muốn chuẩn hóa trải nghiệm COD, giảm tỷ lệ hoàn hàng/bom hàng và minh bạch quy định đồng kiểm.
1. Tại section `Thanh toán thủ công`, tìm dòng `Thanh toán khi giao hàng (COD)` và click nút `Thao tác`.
2. Đọc và sao lưu toàn bộ văn bản trong ô `Hướng dẫn thanh toán` hiện tại vào `scratch/backup_payment_instructions.txt`.
3. Cập nhật `Tên phương thức thanh toán` (nếu có `method_display_name`) và nhập nội dung rõ ràng từ `instructions_text`:
   - Nêu rõ chính sách *“Được kiểm tra ngoại quan/đồng kiểm trước khi thanh toán”*.
   - Ghi chú không thanh toán thêm phụ phí ngoài tổng tiền ghi trên vận đơn và kèm hotline CSKH xử lý ngay khi có tranh chấp với bưu tá.
4. Đảm bảo trạng thái phương thức vẫn là `Đang kích hoạt` (tuyệt đối không chạm nút `Ngừng kích hoạt`).
5. **DỪNG — chưa bấm `Lưu`**, chuyển sang cổng duyệt L3 `separate_turn: true`.

### Scenario 5: Cấu hình `Chuyển khoản qua ngân hàng` & Hướng dẫn VietQR thủ công (`configure_bank_transfer`)
- **Điều kiện kích hoạt:** Cửa hàng chưa kết nối `Haravan QR` (hoặc dùng tài khoản ngân hàng chưa nằm trong danh sách liên kết tự động) và cần kênh chuyển khoản dự phòng.
1. Tại section `Thanh toán thủ công`, tìm dòng `Chuyển khoản qua ngân hàng` và click nút `Thao tác` (hoặc click `Thêm` nếu chưa tạo).
2. Sao lưu toàn bộ nội dung `Hướng dẫn thanh toán` cũ trước khi chỉnh sửa vào `scratch/backup_payment_instructions.txt`.
3. Nhập mẫu hướng dẫn chuẩn từ `instructions_text`:
   - `Ngân hàng`: Tên đầy đủ & chi nhánh (nếu cần).
   - `Chủ tài khoản`: Đúng tên pháp nhân / chủ hộ kinh doanh.
   - `Số tài khoản`: Nhập chính xác theo yêu cầu Owner trên trình duyệt (**che còn `****5678` trong báo cáo chat & JSON**).
   - `Nội dung chuyển khoản`: Cú pháp chuẩn `SDT + Ma Don Hang` để kế toán dễ đối chiếu sao kê ngân hàng.
4. Rà soát kỹ từng chữ số STK và tên chủ tài khoản khớp 100% với thông tin gốc Owner cung cấp; kiểm tra không dính ký tự xuống dòng lỗi.
5. **DỪNG — chưa bấm `Lưu`**, chờ xác nhận tường minh ở lượt hội thoại riêng (`separate_turn: true`).

## 5. Quy trình An toàn 4 Pha (L3 Critical — `separate_turn: true`)

### Pha 1: Pre-State Capture (Chụp Ảnh & Sao Lưu Hướng Dẫn Cũ)
- Mở `/admin/settings/payments`, xác minh quyền Owner và chụp ảnh hiện trạng cả 3 section (`artifacts/payments_pre.png`, đảm bảo không chụp lộ khóa bí mật).
- Với COD / Chuyển khoản thủ công, copy toàn bộ nội dung `Hướng dẫn thanh toán` cũ lưu vào `scratch/backup_payment_instructions.txt`.

### Pha 2: Stage Without Saving / Financial Handoff
- Điền nội dung hướng dẫn COD hoặc Chuyển khoản thủ công theo Scenario 4/5.
- Với `Haravan QR` hoặc `Cổng thanh toán` (VNPay/MoMo/ZaloPay), mở tới đúng màn hình liên kết rồi **DỪNG NGAY** để Chủ cửa hàng tự nhập STK ngân hàng, OTP, `Merchant ID` và `Hash Secret` trực tiếp trên trình duyệt.
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu` / `Kết nối`**.

### Pha 3: Screenshot-Before-Save & Separate-Turn Gate (`separate_turn: true`)
- Chụp ảnh màn hình form đã điền (`artifacts/payments_preview.png`, che hoàn toàn STK/Secret trong báo cáo văn bản).
- Gửi bảng `Before → After` (Mục 6) kèm cảnh báo rủi ro dòng tiền và **dừng hoàn toàn chờ Owner xác nhận tường minh ở LƯỢT HỘI THOẠI TIẾP THEO**.

### Pha 4: Save & Post-Save Reload Verification
- Chỉ khi nhận được xác nhận ở lượt hội thoại riêng, click nút `Lưu` và chờ toast *"Cập nhật thành công"*.
- Nhấn `F5` reload trang `/admin/settings/payments`, xác minh phương thức vẫn giữ trạng thái `Đang kích hoạt` và nội dung hiển thị chính xác, chụp `artifacts/payments_post.png`.
- Đề nghị Owner mở tab ẩn danh trên storefront, thêm 1 sản phẩm vào giỏ tới bước chọn thanh toán để kiểm chứng thực tế trước mắt khách hàng.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Before → After (`/admin/settings/payments` — L3 Critical)

| Section / Phương thức | Trước (Before) | Đề xuất (After) | Kiểm chuẩn an toàn dòng tiền |
| :--- | :--- | :--- | :--- |
| `Haravan QR` | Chưa kết nối | Đã mở form `Thêm tài khoản` | ⏸️ Chờ Owner tự nhập STK & OTP ngân hàng |
| `Cổng thanh toán` → `VNPay` | Chưa kết nối | Đã chọn `VNPay` (chờ nhập khóa) | ⏸️ Chờ Owner tự dán `Terminal ID` & `Hash Secret` |
| `Thanh toán thủ công` → `COD` | Hướng dẫn cũ (thiếu quy định đồng kiểm) | Bổ sung quy định đồng kiểm & hotline | Giữ nguyên trạng thái `Đang kích hoạt` |
| `Thanh toán thủ công` → `Chuyển khoản` | Chưa có cú pháp chuẩn | Bổ sung cú pháp `SDT + Ma Don Hang` | STK đã che trong log (`****5678`) |

> **⚠️ L3 Critical (`separate_turn: true`) — Yêu cầu xác nhận ở lượt hội thoại riêng:** Nội dung cấu hình tại `/admin/settings/payments` đã được điền sẵn (chưa bấm `Lưu`, xem `preview_screenshot`). Vui lòng kiểm tra kỹ thông tin tài khoản/hướng dẫn và trả lời **"Xác nhận lưu cấu hình phương thức thanh toán"** ở lượt tiếp theo để Agent bấm `Lưu`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-payment-methods-setup",
  "scenario": "configure_cod",
  "risk": "critical",
  "separate_turn_required": true,
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/payments",
  "phase_status": "awaiting_separate_turn_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/payments_pre.png",
    "preview_screenshot": "artifacts/payments_preview.png",
    "post_screenshot": "artifacts/payments_post.png",
    "instructions_backup_path": "scratch/backup_payment_instructions.txt"
  },
  "checks_passed": {
    "cod_remains_active": true,
    "zero_secret_in_logs": true,
    "bank_account_redacted": true,
    "separate_turn_enforced": true
  },
  "changes_staged": {
    "method_name": "Thanh toán khi giao hàng (COD)",
    "status_preserved": "active",
    "bank_account_or_secret_redacted": true
  },
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Ngừng kích hoạt` / `Ngừng kết nối` / `Xóa` phương thức live | **HARD-BLOCKED** | Cắt ngang dòng tiền & khiến khách không thể đặt đơn trên website |
| Nút `Lưu` / `Kết nối` trong cùng lượt Preview | **HARD-BLOCKED** | Vi phạm quy tắc L3 `separate_turn: true`; bắt buộc chờ lượt xác nhận riêng |
| Form nhập STK ngân hàng & OTP `Haravan QR` | **HANDOFF GATE** | Chủ cửa hàng tự nhập trực tiếp trên trình duyệt; tuyệt đối không gửi qua chat |
| Form nhập `Merchant ID` / `Hash Secret` VNPay, MoMo, ZaloPay | **HANDOFF GATE** | Zero Secret Exposure — không đọc, không lưu, không ghi vào log hay artifact |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Cổng VNPay / MoMo báo lỗi *"Invalid Signature / Sai chữ ký"* khi test thanh toán:** Thường do dán thừa dấu cách ở đầu/cuối `Merchant ID` hoặc `Secret Key`, hoặc đang chọn nhầm môi trường `Sandbox` thay vì `Production` → Dừng, nhờ Owner kiểm tra và nhập lại trực tiếp trên trình duyệt.
2. **Haravan QR không tự động gạch nợ đơn hàng dù tiền đã vào tài khoản:** Kiểm tra xem khách có sửa nội dung chuyển khoản mặc định, chuyển thiếu số tiền hay phiên ủy quyền ngân hàng đã hết hạn cần xác thực lại OTP.
3. **Nút `Thao tác` / `Thêm` bị ẩn hoặc trang báo 403:** Tài khoản hiện tại là Staff không có quyền Phương thức thanh toán → Dừng, yêu cầu Chủ cửa hàng (Owner) đăng nhập thực hiện.
4. **Cả `Haravan QR` và `Chuyển khoản qua ngân hàng` thủ công cùng bật gây bối rối cho khách:** Đề xuất đổi tên hiển thị rõ ràng (ví dụ *“Chuyển khoản nhanh bằng mã QR (Xác nhận tự động)”*) hoặc chỉ giữ phương thức thủ công làm phương án dự phòng theo quyết định của Owner.
5. **Khách hàng báo chọn xong phương thức thanh toán nhưng trang cảm ơn không hiện hướng dẫn chuyển khoản:** Kiểm tra lại xem nội dung đã nhập đúng vào ô `Hướng dẫn thanh toán` của phương thức đó và đã bấm `Lưu` thành công chưa, đồng thời kiểm tra mẫu email `Xác nhận đơn hàng` tại `/admin/settings/notifications`.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công
1. Đối chiếu `artifacts/payments_pre.png` và mở file `scratch/backup_payment_instructions.txt` đã sao lưu ở Pha 1.
2. Tại `/admin/settings/payments`, bấm `Thao tác` trên phương thức tương ứng (`Thanh toán khi giao hàng (COD)` hoặc `Chuyển khoản qua ngân hàng`), dán lại chính xác nội dung hướng dẫn cũ và bấm `Lưu`.
3. Nếu vừa cấu hình một cổng thanh toán mới (VNPay/MoMo/ZaloPay) phát sinh lỗi chữ ký khi khách đặt hàng, Chủ cửa hàng tự bấm tạm tắt cổng mới đó (giữ nguyên COD & Haravan QR hoạt động bình thường) để tránh gián đoạn đơn hàng.
4. Kiểm tra lại trang Checkout bằng cửa sổ ẩn danh để chắc chắn khách vẫn chọn được phương thức thanh toán và đặt đơn thành công.

### Checklist Kiểm chứng End-to-End sau khi Lưu (Khuyến nghị cho Owner)
- [ ] Mở trang Checkout bằng tab ẩn danh: xác minh tên phương thức thanh toán và `Hướng dẫn thanh toán` hiển thị đầy đủ, không sai số tài khoản.
- [ ] Với `Haravan QR`: đặt thử 1 đơn hàng test giá trị nhỏ (`10.000đ`), quét mã VietQR chuyển khoản đúng cú pháp và xác nhận đơn tự động chuyển `Đã thanh toán` trên `/admin/orders`.
- [ ] Với cổng `VNPay` / `MoMo` / `ZaloPay`: thử điều hướng sang trang cổng thanh toán để xác nhận không dính lỗi `Invalid Signature` hay lỗi môi trường Sandbox.
- [ ] Kiểm tra log/JSON đầu ra: xác nhận 100% không lộ mật khẩu, OTP, `Hash Secret` hay đầy đủ số tài khoản ngân hàng.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `finance-cod-reconciliation` & `finance-revenue-margin-report`: Đối soát dòng tiền COD, kiểm tra tỷ lệ đơn `financial_status = paid` vs `pending` qua Commerce API (`/com/orders.json`) sau khi bật Haravan QR hoặc cổng thanh toán.
- `skills/api-mcp/` → `order-ops`: Kiểm tra chi tiết giao dịch (`transactions`) gắn trên đơn hàng mẫu sau khi hoàn tất cấu hình cổng thanh toán.
- `skills/browser-ui/` → `admin-ui-checkout-settings` (cấu hình luồng đặt hàng, OTP Zalo, đặt cọc), `finance-cashbook-debt-audit` (kiểm toán dòng tiền thực thu trên Sổ quỹ `/admin/accounting/transactions`).
