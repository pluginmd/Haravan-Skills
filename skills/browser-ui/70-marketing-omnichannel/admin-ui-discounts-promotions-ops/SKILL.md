---
name: admin-ui-discounts-promotions-ops
description: "Quản lý Khuyến mãi trên Haravan Admin (/admin/discounts): cấu hình 4 loại mã giảm giá (đơn hàng, sản phẩm, đồng giá, vận chuyển), Mua X tặng Y, Dùng chung khuyến mãi (Grow/Scale+), giới hạn kênh/chi nhánh/nhóm khách và bật/tắt/nhân bản."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 70-marketing-omnichannel
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/discounts"
    - "UI /admin/discounts/new"
    - "UI /admin/discounts/{discount_id}"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 25
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: true
rollback:
  supported: true
  backup_required: true
---

# Haravan Admin UI — Quản Lý Khuyến Mãi & Mã Giảm Giá (`/admin/discounts`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Thiết lập, kiểm tra xung đột và vận hành chính xác các chương trình khuyến mãi trên Haravan Admin (`https://{store_domain}/admin/discounts`) không cần API token: tạo đủ 4 loại mã giảm giá (Giảm theo đơn hàng, Giảm theo sản phẩm/nhóm SP, Đồng giá sản phẩm, Miễn/giảm phí vận chuyển), tạo chương trình tự động **Mua X tặng Y**, cấu hình quy tắc **Dùng chung khuyến mãi (Stacking)**, giới hạn kênh bán/chi nhánh/nhóm khách hàng, và bật/tắt/nhân bản chiến dịch an toàn.
- **Phạm vi UI:** Danh sách khuyến mãi (`/admin/discounts`), màn hình tạo mã khuyến mãi & tạo chương trình khuyến mãi (`/admin/discounts/new` và các phân hệ con). Không bao gồm sửa giá gốc/giá so sánh sản phẩm (dùng `admin-ui-products-catalog-ops`).
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Toàn quyền tạo, sửa, bật/tắt, nhân bản và cấu hình dùng chung khuyến mãi.
  - **Staff:** Yêu cầu quyền `Khuyến mãi` (`Xem`, `Tạo mới`, `Chỉnh sửa`, `Ngưng/Kích hoạt`). Nếu tài khoản Staff không thấy nút `Tạo khuyến mãi`, dừng ngay và báo thiếu quyền.
- **Yêu cầu Gói dịch vụ Haravan:**
  - 4 loại mã giảm giá cơ bản và Mua X tặng Y khả dụng từ gói Standard/Pro trở lên.
  - Tính năng **Dùng chung khuyến mãi** (kết hợp nhiều chương trình/mã trên cùng 1 đơn hàng) yêu cầu gói **Grow / Scale+** (nếu mục này bị khóa hoặc có icon nâng gói, dừng lại và không bấm nút nâng cấp).
- **Pre-flight Check bắt buộc:**
  1. Kiểm tra phiên đăng nhập qua `admin-ui-session-navigator` tại `/admin/discounts`.
  2. Rà soát tab `Đang áp dụng` để phát hiện sớm các chương trình đang chạy cùng thời điểm (tránh tình trạng chồng mã gây lỗ biên lợi nhuận).
  3. Kiểm tra khung giờ máy chủ (UTC+7 Việt Nam) và xác minh rõ ngưỡng giảm tối đa (`Giảm tối đa`) khi dùng giảm theo `%`.

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/discounts` — H1 `Quản lý khuyến mãi`; Empty State CTA: `Gợi ý khuyến mãi`, `Tạo khuyến mãi`.


| Thành phần UI | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Ghi chú thao tác |
| :--- | :--- | :--- | :--- |
| Danh sách khuyến mãi | `/admin/discounts` | Tab lọc trạng thái: `Tất cả`, `Đang áp dụng`, `Chưa áp dụng`, `Đã hết hạn` | Ô tìm kiếm theo mã code hoặc tên chương trình |
| Nút tạo mới | Góc trên bên phải `/admin/discounts` | `Tạo khuyến mãi` (mở modal/menu chọn: `Tạo mã khuyến mãi`, `Tạo chương trình khuyến mãi`, `Mua X tặng Y`) | Phân biệt rõ **Mã khuyến mãi** (khách phải nhập code) và **Chương trình** (tự động áp dụng) |
| Cột bảng danh sách | Bảng chính `/admin/discounts` | `Mã / Tên chương trình`, `Trạng thái`, `Đã sử dụng`, `Thời gian áp dụng` | Click dòng để mở chi tiết, bấm `Ngưng áp dụng` / `Kích hoạt lại` / `Nhân bản` |
| Form — Loại & Mức giảm | `/admin/discounts/new` | `Giảm theo phần trăm (%)`, `Giảm theo số tiền (đ)`, `Đồng giá`, `Miễn phí vận chuyển`, `Mua X tặng Y` | Luôn kiểm tra ô `Mức giảm tối đa` khi chọn giảm `%` |
| Form — Điều kiện & Đối tượng | Trong `/admin/discounts/new` | `Áp dụng cho` (`Tất cả đơn hàng`, `Nhóm sản phẩm`, `Sản phẩm`), `Điều kiện tối thiểu` (`Tổng giá trị đơn`, `Tổng số lượng SP`), `Nhóm khách hàng` | Có ô giới hạn `Tổng số lượt sử dụng` và `Mỗi khách hàng chỉ dùng 1 lần` |
| Form — Phạm vi & Dùng chung | Cột trái dưới & cột phải | `Kênh bán hàng` (`Website`, `POS`, `Harasocial`...), `Chi nhánh áp dụng`, `Dùng chung khuyến mãi` (tick chọn nhóm được cộng dồn) | Cột phải có khung `Tóm tắt` hiển thị tóm lược toàn bộ luật đang cấu hình |
| Form — Thời gian | Cuối trang `/admin/discounts/new` | `Thời gian bắt đầu` (`Ngày`, `Giờ`), checkbox `Đặt thời gian kết thúc` (`Ngày`, `Giờ`) | Không bỏ trống ngày kết thúc với chiến dịch Flash Sale |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `create_discount_code` | `create_discount_code` \| `create_buy_x_get_y` \| `configure_stacking_scope` \| `toggle_or_duplicate` |
| `promo_type` | `enum` | Khi tạo | `order_percent` | `order_percent` \| `order_fixed` \| `product_discount` \| `flat_price` \| `free_shipping` \| `buy_x_get_y` |
| `code_or_title` | `string` | Có | — | Mã code viết hoa không dấu `^[A-Z0-9_-]{4,30}$` (hoặc tên chương trình ≤ 100 ký tự) |
| `discount_value` | `number` | Khi tạo | `0` | Nếu `%`: `1 <= value <= 50` (cảnh báo đỏ nếu `> 50%`); nếu `VND`: `> 0` |
| `max_discount_vnd` | `number` | Khi giảm `%` | `null` | Khuyến nghị bắt buộc khai báo trần giảm tối đa để bảo vệ biên lợi nhuận |
| `min_requirement` | `object` | Không | `{}` | `type` (`none` \| `min_order_amount` \| `min_qty`), `value` (`>= 0`) |
| `usage_limits` | `object` | Không | `{}` | `total_limit` (`>= 1`), `once_per_customer` (`boolean`, mặc định `true`) |
| `scope` | `object` | Không | `{}` | `channels` (`Website`, `POS`...), `locations`, `customer_segments`, `allow_stacking` (`boolean`) |
| `schedule` | `object` | Có | — | `start_at` và `end_at` (`ISO-8601` giờ VN, bắt buộc `end_at > start_at`) |
| `dry_run` | `boolean` | Không | `true` | Bắt buộc `true` ở pha dựng form (Stage Without Saving) |

## 4. Ma trận Kịch bản Thao tác Đa dạng (4 Scenarios Click-by-Click)

### Kịch bản 1: Tạo 4 loại Mã giảm giá chuẩn (Đơn hàng / Sản phẩm / Đồng giá / Vận chuyển)
1. Mở `https://{store_domain}/admin/discounts`, bấm `Tạo khuyến mãi` → chọn `Tạo mã khuyến mãi`.
2. Nhập mã vào ô `Mã khuyến mãi` (hoặc bấm `Tạo mã ngẫu nhiên`), chọn loại giảm giá theo `promo_type`:
   - *Đơn hàng / Sản phẩm:* Chọn `%` hoặc `Số tiền`, điền `discount_value` và điền `Mức giảm tối đa` (`max_discount_vnd`); nếu theo sản phẩm/nhóm SP, bấm `Tìm kiếm` chọn đúng SKU/Collection.
   - *Đồng giá:* Chọn `Đồng giá`, nhập mức giá bán cố định (ví dụ `199.000đ`) và chọn nhóm sản phẩm áp dụng.
   - *Vận chuyển:* Chọn `Miễn phí vận chuyển`, nhập mức phí ship giảm tối đa (ví dụ `30.000đ`) và chọn khu vực tỉnh/thành áp dụng (nếu giới hạn).
3. Cấu hình `Điều kiện áp dụng` (`Tổng giá trị đơn hàng tối thiểu` hoặc `Tổng số lượng sản phẩm tối thiểu`) và tick `Mỗi khách hàng chỉ được sử dụng 1 lần`, nhập `Giới hạn số lần mã giảm giá được áp dụng`.
4. Thiết lập `Thời gian bắt đầu` và tick `Đặt thời gian kết thúc` khớp `schedule`. Kiểm tra khung `Tóm tắt` ở cột phải, **dừng trước nút `Lưu`** và chụp ảnh preview.

### Kịch bản 2: Tạo chương trình Mua X tặng Y (Buy X Get Y)
1. Tại `/admin/discounts`, bấm `Tạo khuyến mãi` → chọn `Mua X tặng Y` (chọn dạng `Tự động` hoặc `Nhập mã`).
2. Tại khối **Khách hàng mua (X)**: chọn điều kiện theo `Số lượng sản phẩm tối thiểu` (ví dụ mua `2`) hoặc `Giá trị tối thiểu` (ví dụ từ `500.000đ`), chọn danh sách `Sản phẩm` hoặc `Nhóm sản phẩm` áp dụng.
3. Tại khối **Khách hàng nhận được (Y)**: nhập `Số lượng quà tặng` (ví dụ `1`), chọn SKU quà tặng (kiểm tra SKU quà có tồn kho > 0), chọn mức ưu đãi (`Miễn phí 100%` hoặc `Giảm %`).
4. Thiết lập giới hạn `Số lần áp dụng tối đa trên mỗi đơn hàng` (ví dụ tối đa `1` hoặc `2` lần/đơn để tránh đầu cơ gom hàng) và thời gian kết thúc. Dừng trước nút `Lưu`, chụp ảnh khung `Tóm tắt`.

### Kịch bản 3: Cấu hình Giới hạn Kênh, Chi nhánh, Nhóm khách & Dùng chung khuyến mãi (`Grow/Scale+`)
1. Trong form tạo/sửa khuyến mãi, cuộn tới khối **Phạm vi áp dụng**:
   - Tại `Kênh bán hàng`: bỏ chọn `Tất cả`, chỉ tick đúng kênh cần chạy (ví dụ chỉ `Website` hoặc chỉ `Haravan POS`).
   - Tại `Chi nhánh`: chọn kho/cửa hàng áp dụng nếu là khuyến mãi khai trương chi nhánh.
   - Tại `Khách hàng áp dụng`: chọn `Nhóm khách hàng đã lưu` (ví dụ `Khách hàng VIP`, `Thành viên Vàng`) thay vì `Tất cả`.
2. Tại khối **Dùng chung khuyến mãi** (nếu gói hỗ trợ): mặc định giữ **Tắt** tất cả để tránh cộng dồn ngoài kiểm soát; chỉ tick cho phép kết hợp với `Khuyến mãi vận chuyển` khi có yêu cầu rõ ràng.
3. Kiểm tra lại khung `Tóm tắt` cột phải để chắc chắn không có cảnh báo xung đột, chụp ảnh preview trước khi lưu.

### Kịch bản 4: Bật / Tắt khẩn cấp hoặc Nhân bản chiến dịch cho đợt mới
1. Tại `/admin/discounts`, lọc tab `Đang áp dụng` hoặc tìm đúng tên/mã chương trình cần thao tác.
2. **Tắt / Bật chương trình:** Mở chi tiết chương trình → chụp trạng thái hiện tại (số lượt đã sử dụng) → chuẩn bị bấm `Ngưng áp dụng` (khi cần dừng khẩn cấp mã bị lộ) hoặc `Kích hoạt lại` → dừng chụp ảnh chờ xác nhận.
3. **Nhân bản chiến dịch:** Mở chương trình cũ đã chạy hiệu quả → bấm `Nhân bản` → đổi `Mã khuyến mãi` / `Tên chương trình` mới (ví dụ đổi `SALE10` thành `SALE11`), cập nhật lại `Thời gian bắt đầu`/`kết thúc` mới và reset giới hạn lượt dùng → chụp preview trước khi bấm `Lưu`.

### Kịch bản 5: Kiểm Tra Chéo Xung Đột Khuyến Mãi Trước Giờ G (Flash Sale Pre-Flight)
1. Trước khi kích hoạt chiến dịch lớn (Black Friday, 11/11, 12/12), mở `/admin/discounts` → lọc tab `Đang áp dụng` và `Chưa áp dụng` (có lịch giao thoa với chiến dịch mới).
2. Liệt kê toàn bộ mã giảm giá và chương trình tự động đang bật `Dùng chung khuyến mãi` (Stacking) trên cùng kênh bán hàng.
3. Tính mức chiết khấu cộng dồn tối đa có thể xảy ra trên 1 đơn hàng mẫu; nếu tổng giảm giá vượt ngưỡng an toàn (ví dụ `> 40%`), đề xuất tắt `Dùng chung` hoặc tạm `Ngưng áp dụng` chương trình nền cũ trước khi bấm `Lưu`.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Protocol)

1. **Pha 1 — Pre-State Capture (Rà soát khuyến mãi đang chạy):**
   - Mở `/admin/discounts` tab `Đang áp dụng`, chụp `pre_screenshot` danh sách các chương trình đang hoạt động để phát hiện sớm nguy cơ chồng mã (Double Discounting).
   - Nếu đang sửa hoặc nhân bản chương trình cũ, mở chi tiết chương trình gốc để chụp lại toàn bộ tham số cũ làm mốc rollback.
2. **Pha 2 — Stage Without Saving (`dry_run: true`):**
   - Điền đầy đủ mã/tên chương trình, loại giảm giá, trần giảm tối đa (`Mức giảm tối đa`), điều kiện tối thiểu, giới hạn lượt dùng, kênh/chi nhánh/nhóm khách, cấu hình `Dùng chung khuyến mãi` và khung giờ bắt đầu/kết thúc.
   - Đọc kỹ khung **Tóm tắt (Summary)** ở cột bên phải để xác minh toàn bộ luật hiển thị đúng ý đồ nghiệp vụ.
   - **Dừng tuyệt đối trước nút `Lưu` / `Ngưng áp dụng` / `Kích hoạt lại`**.
3. **Pha 3 — Screenshot-Before-Save Gate (Mô phỏng & Duyệt ngân sách):**
   - Chụp `preview_screenshot` (bao gồm đầy đủ khung `Tóm tắt` cột phải).
   - Lập bảng `Before → After` kèm **ước tính ngân sách giảm giá tối đa** (`max_discount_vnd × total_limit`) và mô phỏng mức giảm trên 1 đơn hàng mẫu, sau đó dừng chờ người dùng phê duyệt.
4. **Pha 4 — Save & Post-Save Reload Verification (Xác minh trạng thái kích hoạt):**
   - Sau khi người dùng xác nhận, bấm `Lưu`, chờ toast xanh (`Tạo khuyến mãi thành công` / `Cập nhật thành công`).
   - Nhấn `F5` reload lại `/admin/discounts`, xác minh đúng trạng thái (`Chưa áp dụng` theo lịch tương lai hoặc `Đang áp dụng`), kiểm tra chính xác mã code và chụp `post_screenshot`.

### Checklist Bảo Vệ Biên Lợi Nhuận Khuyến Mãi (Margin Guardrails)

- [ ] Mọi mã giảm theo `%` đều có `Mức giảm tối đa (VND)` và `Đơn hàng tối thiểu` hợp lý (không để giảm không trần).
- [ ] Đã bật `Mỗi khách hàng chỉ dùng 1 lần` và đặt `Tổng số lượt sử dụng` cho mã công khai/Flash Sale.
- [ ] Đã đặt rõ `Thời gian kết thúc` (không để khuyến mãi chạy vĩnh viễn ngoài ý muốn).
- [ ] Đã kiểm tra tab `Đang áp dụng` để đảm bảo không cộng dồn trái phép với chương trình giảm giá tự động hiện có.
- [ ] Nếu là **Mua X tặng Y**: đã xác minh SKU quà tặng Y còn tồn kho khả dụng (`> 0`) và giới hạn số lần tặng/đơn.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Cấu hình Khuyến mãi (Operational Estimate)

| Chương trình / Mã | Trường cấu hình | Trước (Before) | Sau (After — Staged) | Kiểm tra rủi ro |
| :--- | :--- | :--- | :--- | :--- |
| `VIP15NOV` | Loại & Mức giảm | *(Tạo mới)* | Giảm `15%` đơn từ `500.000đ`, tối đa `150.000đ` | ✅ Có trần tối đa |
| `VIP15NOV` | Phạm vi & Dùng chung | *(Tạo mới)* | Chỉ `Website`, Nhóm `Khách VIP`, Dùng chung: `Chỉ với Freeship` | ✅ Không chồng mã đơn |
| `VIP15NOV` | Lượt dùng & Lịch | *(Tạo mới)* | Tối đa `200` lượt, `1 lần/khách`, `25/11 00:00 → 30/11 23:59` | ✅ Có ngày kết thúc |
| `VIP15NOV` | Ngân sách tối đa (Est.) | `0đ` | Tối đa `30.000.000đ` (`150.000đ × 200 lượt`) | ⚠️ Chờ duyệt ngân sách |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-discounts-promotions-ops",
  "mode": "proposal",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/discounts/new",
  "scenario": "create_discount_code",
  "session_authenticated": true,
  "dry_run": true,
  "promo_code": "VIP15NOV",
  "stacking_enabled": true,
  "max_budget_exposure_vnd": 30000000,
  "pre_screenshot": "artifacts/discounts_active_pre.png",
  "preview_screenshot": "artifacts/discounts_VIP15NOV_staged.png",
  "post_screenshot": null,
  "changes_staged": [
    {
      "code": "VIP15NOV",
      "type": "order_percent",
      "value_percent": 15,
      "max_discount_vnd": 150000,
      "min_order_vnd": 500000,
      "total_limit": 200,
      "once_per_customer": true,
      "channels": ["Website"],
      "stacking_with": ["shipping_discounts"]
    }
  ],
  "warnings": [],
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm trên `/admin/discounts`:**
  - `Xóa khuyến mãi` (làm mất lịch sử đo lường ROI chiến dịch; luôn ưu tiên dùng `Ngưng áp dụng` thay cho `Xóa`).
  - `Nâng cấp gói` khi mở tính năng `Dùng chung khuyến mãi` trên cửa hàng chưa ở gói Grow/Scale+.
  - Lưu mã giảm giá `> 50%` hoặc `Giảm 100%` không có `Mức giảm tối đa` và không có `Giới hạn số lượt sử dụng` (nguy cơ cháy ngân sách/bị săn mã hàng loạt).
- **Financial & Credential Handoff Gate:**
  - Ước tính ngân sách tối đa (`max_discount_vnd × total_limit`) là **Operational Estimate** — cần bộ phận Marketing/Owner phê duyệt ngân sách trước khi kích hoạt.
  - Gặp `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.

### Ma Trận Tương Thích 4 Loại Khuyến Mãi & Quy Tắc Dùng Chung (Stacking)

| Loại khuyến mãi | Yêu cầu nhập Code? | Trường bắt buộc kiểm tra rủi ro | Khuyến nghị Dùng chung (`Grow/Scale+`) |
| :--- | :--- | :--- | :--- |
| Giảm theo đơn hàng (`%` / `VND`) | Tùy chọn (Mã hoặc Tự động) | `Đơn tối thiểu` + `Giảm tối đa` + `Tổng lượt` | Chỉ nên kết hợp với `Miễn phí vận chuyển` |
| Giảm theo sản phẩm / Nhóm SP | Tùy chọn | Đúng danh sách SKU/Collection, không giảm kép | Tắt cộng dồn với mã giảm đơn hàng |
| Đồng giá sản phẩm | Tùy chọn | Giá đồng giá `> Giá vốn` (trừ đợt xả kho có duyệt) | Tắt tất cả cộng dồn |
| Miễn / Giảm phí vận chuyển | Tùy chọn | Trần hỗ trợ ship (ví dụ `30.000đ`) + khu vực tỉnh | Cho phép kết hợp với mã giảm đơn hàng/sản phẩm |
| Mua X tặng Y | Tùy chọn | Tồn kho SKU quà Y `> 0` + giới hạn số lần tặng/đơn | Tắt cộng dồn với giảm giá sản phẩm |

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Chồng khuyến mãi không mong muốn (Double Discounting):** Khi cửa hàng đang chạy chương trình giảm giá tự động theo sản phẩm và bật thêm mã giảm giá đơn hàng có `Dùng chung`, khách có thể nhận giảm kép vượt biên lợi nhuận. Agent luôn kiểm tra tab `Đang áp dụng` ở Pha 1 và cảnh báo rõ nếu phát hiện khả năng cộng dồn.
2. **Mã giảm giá trùng tên với mã cũ đã hết hạn:** Haravan không cho tạo trùng chính xác mã code đang hoạt động hoặc một số mã đã tồn tại trong hệ thống; nếu gặp lỗi đỏ `Mã khuyến mãi đã tồn tại`, đề xuất hậu tố tháng/năm (ví dụ `SALE20_T11`).
3. **SKU quà tặng Mua X tặng Y hết tồn kho:** Nếu sản phẩm Y có `Tồn kho = 0` và không bật bán âm, chương trình Mua X tặng Y sẽ không tự thêm quà vào giỏ hàng trên Website. Agent nhắc kiểm tra tồn kho SKU quà trước khi chạy.
4. **Lỗi lệch múi giờ bắt đầu Flash Sale:** Haravan sử dụng giờ cửa hàng (thường `GMT+7`). Nếu nhập thời gian bắt đầu trong quá khứ, khuyến mãi kích hoạt ngay lập tức khi bấm `Lưu`; luôn kiểm tra kỹ giờ `00:00` vs `12:00` để tránh chạy sớm 12 tiếng.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback & Ứng cứu Khẩn cấp trên UI
- **Dừng khẩn cấp mã bị lộ / chồng mã gây lỗ biên lợi nhuận:** Mở `/admin/discounts` → tab `Đang áp dụng` → click mã/chương trình sự cố → bấm `Ngưng áp dụng` ngay lập tức. Thao tác có hiệu lực tức thì với các giỏ hàng mới (không làm thay đổi các đơn đã hoàn tất).
- **Khôi phục cấu hình cũ sau khi sửa nhầm điều kiện/phạm vi:** Mở lại chi tiết chương trình, đối chiếu chính xác `pre_screenshot` để đặt lại mức giảm, `Mức giảm tối đa`, kênh áp dụng, nhóm khách hàng và thời gian kết thúc.
- **Xử lý đơn đã lỡ áp mã lỗi:** Kiểm tra danh sách đơn dùng mã tại `/admin/orders` (lọc theo mã khuyến mãi hoặc khoảng giờ sự cố) để CSKH/Owner chủ động rà soát theo chính sách cửa hàng, tuyệt đối không tự ý hủy đơn hàng loạt.
- **Lưu dấu vết đo lường ROI:** Luôn dùng `Ngưng áp dụng` thay cho `Xóa khuyến mãi` để báo cáo `Chi tiết khuyến mãi` tại `/admin/reports/listing` giữ nguyên dữ liệu lịch sử.

### Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan
- Kiểm toán vệ sinh khuyến mãi (mã quá hạn, mã không giới hạn lượt) & đo ROI khuyến mãi qua API: `skills/api-mcp/70-marketing-omnichannel/marketing-promotion-hygiene-audit`, `skills/api-mcp/60-finance-analytics/finance-aov-discount-roi`.
- Tạo đề xuất mã khuyến mãi hàng loạt qua API: `skills/api-mcp/70-marketing-omnichannel/marketing-promo-code-proposal`.
- Thiết lập chiến dịch gửi mã qua Broadcast/Flow CRM & đọc báo cáo chi tiết khuyến mãi trên UI: `skills/browser-ui/95-admin-ui-browser/admin-ui-crm-flows-broadcast`, `skills/browser-ui/60-finance-analytics/admin-ui-reports-analytics-export`.
