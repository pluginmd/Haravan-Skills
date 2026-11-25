---
name: catalog-pricing-list-b2b-proposal
description: "Thiết kế và kiểm chuẩn Bảng giá riêng cho kênh bán hàng (Web/POS/Harasocial), chi nhánh và nhóm khách sỉ B2B (/admin/products/pricing_list)."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 20-catalog-merchandising
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/products.json"
    - "UI /admin/products/pricing_list"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 100
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

# Haravan Multi-Channel & B2B Pricing List Proposal

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Quản lý toàn bộ vòng đời **Bảng giá đa kênh & Bảng giá sỉ B2B** tại `/admin/products/pricing_list`, `/admin/products/pricing_list/new` và `/admin/products/pricing_list/{id}` trên Haravan Admin.
- **Lý do bắt buộc dùng Browser UI:** Haravan Commerce API (`/com/products.json`) chỉ hỗ trợ cập nhật giá bán lẻ mặc định (`price`, `compare_at_price`) của từng biến thể, **không có endpoint công khai** để tạo hoặc quản lý Bảng giá phân tách theo Kênh bán hàng (Website, POS, Harasocial), Chi nhánh/Kho hoặc Nhóm khách hàng B2B.
- **Mục tiêu nghiệp vụ (`layer: L2`, `mode: proposal`):** Kiểm toán chồng lấn bảng giá hiện hành, kiểm chuẩn biên lợi nhuận tối thiểu (`min_margin_floor_pct`) để chặn bán dưới giá vốn, và dựng sẵn bản nháp bảng giá mới trên giao diện mà không làm biến đổi giá lẻ niêm yết.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền tạo, sửa, ngừng áp dụng và xóa bảng giá.
  - **Staff:** Yêu cầu có quyền **Xem & Tạo/Sửa Bảng giá** trong nhóm quyền **Sản phẩm** tại `/admin/settings/group_permissions`.
  - **Giới hạn gói dịch vụ:** Tính năng `Bảng giá` yêu cầu gói **Haravan Pro / Grow / Scale / Omnichannel** trở lên. Nếu mở `/admin/products/pricing_list` thấy màn hình giới thiệu kèm nút `Nâng cấp gói`, **dừng ngay lập tức** và báo giới hạn gói.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/products/pricing_list`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Xác nhận nút `Tạo bảng giá` hiển thị khả dụng và danh sách bảng giá hiện có tải hoàn tất.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/products/pricing_list` | Danh sách Bảng giá | `Tạo bảng giá`, `Lọc`, `Tìm kiếm` | Bộ lọc: `Trạng thái` (`Đang áp dụng` / `Chưa áp dụng` / `Hết hạn`), `Kênh bán hàng`, `Chi nhánh`. Cột: Tên bảng giá, Mã bảng giá, Phạm vi áp dụng, Thời gian hiệu lực, Trạng thái |
| `/admin/products/pricing_list/new` | Thông tin chung & Phạm vi | `Lưu`, `Hủy`, Radio/Dropdown chọn phạm vi | Trường: `Tên bảng giá`, `Mã bảng giá`, `Kênh bán hàng` (`Website`, `POS`, `Harasocial`), `Chi nhánh áp dụng`, `Nhóm khách hàng` |
| `/admin/products/pricing_list/new` | Thời gian hiệu lực | Datepicker, Checkbox `Không có ngày kết thúc` | Trường: `Ngày bắt đầu` (`DD/MM/YYYY HH:mm`), `Ngày kết thúc` |
| `/admin/products/pricing_list/new` | Danh sách sản phẩm & Điều chỉnh giá | `Thêm sản phẩm`, `Điều chỉnh giá hàng loạt`, `Nhập file` | Cột: Tên sản phẩm / Biến thể (SKU), `Giá bán lẻ gốc`, `Loại điều chỉnh` (`Giảm theo %` / `Tăng theo %` / `Giá cố định`), `Giá mới (VND)` |
| `/admin/products/pricing_list/{id}` | Chi tiết Bảng giá | `Lưu`, `Ngừng áp dụng` (CẤM tự bấm), `Xóa` (HARD-BLOCKED) | Hiển thị đầy đủ phạm vi, danh sách SKU đã lưu, trạng thái áp dụng thực tế |

### Quy ước Ưu tiên & Quy tắc Hiển thị Bảng giá trên Haravan
- **Thứ tự ưu tiên khi trùng phạm vi:** Nếu một khách hàng thỏa mãn đồng thời 2 bảng giá đang áp dụng trên cùng kênh, Haravan ưu tiên áp dụng theo quy tắc mức giá phù hợp/thứ tự cấu hình; do đó luôn chạy Kịch bản 1 (`overlap_audit`) để tránh chiết khấu chồng chéo ngoài ý muốn.
- **Tách biệt Giá lẻ vs Giá sỉ:** Giá bán lẻ gốc trên `/admin/products` không bị ghi đè khi tạo bảng giá; mọi điều chỉnh chỉ hiệu lực trong đúng Kênh + Chi nhánh + Nhóm khách hàng + Khung thời gian khai báo.
- **Điều kiện hiển thị trên Website:** Bảng giá gắn Nhóm khách hàng chỉ hiển thị trên Website khi khách hàng đã đăng nhập tài khoản thuộc đúng nhóm đó; tuyệt đối không tích kênh `Website` khi mục `Nhóm khách hàng` đang để `Tất cả khách hàng` đối với bảng giá sỉ.
- **Phím tắt điều hướng nhanh:** Có thể dùng `Ctrl+K` trên Haravan Admin và gõ `Bảng giá` để mở nhanh `/admin/products/pricing_list` từ bất kỳ màn hình nào.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `b2b_percent_create` | `overlap_audit` \| `b2b_percent_create` \| `sku_fixed_price_create` \| `bulk_file_stage` \| `expiry_review` |
| `price_list_name` | `string` | Khi tạo mới | — | Quy ước rõ ràng, không trùng tên hiện có (ví dụ `Gia-Si-DaiLyC1-Q4-2026`) |
| `target_channels` | `array<string>` | Không | `["POS"]` | Giá trị hợp lệ: `POS`, `Harasocial`, `Website` (cấm chọn `Website` nếu `target_customer_groups` rỗng với bảng giá sỉ) |
| `target_customer_groups` | `array<string>` | Không | `[]` | Phải khớp chính xác tên nhóm đã có tại `/admin/customers/segments` |
| `target_locations` | `array<string>` | Không | `[]` | Tên chi nhánh/kho hợp lệ tại `/admin/settings/locations` |
| `pricing_rule_type` | `string` | Khi tạo mới | `percent_discount` | `percent_discount` (giảm theo %) hoặc `fixed_price` (nhập giá cố định theo SKU) |
| `discount_or_fixed_rules` | `object/array` | Khi tạo mới | — | `% giảm` (`1..70`) hoặc mảng `{sku, new_price, cost_price}` (tối đa `max_records: 100` SKU qua UI) |
| `min_margin_floor_pct` | `number` | Không | `10` | Ngưỡng biên lợi nhuận tối thiểu `(new_price - cost_price) / new_price * 100` (`>= 0`) |
| `start_date` / `end_date` | `string` | Không | Hiện tại / Không giới hạn | Định dạng `DD/MM/YYYY HH:mm`; nếu có `end_date` phải lớn hơn `start_date` |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi bấm `Lưu` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Kiểm toán chồng lấn bảng giá hiện hành & Kiểm chuẩn biên lợi nhuận (`overlap_audit`)
- **Khi nào dùng:** Trước mỗi chiến dịch B2B hoặc mở kênh mới, cần rà soát xung đột giá giữa các bảng giá đang chạy và chặn SKU bị bán dưới giá vốn.
- **Thao tác từng bước:**
  1. Mở `https://{store_domain}/admin/products/pricing_list`, lọc `Trạng thái` = `Đang áp dụng` và chụp `pre_screenshot`.
  2. Quét toàn bộ bảng giá đang chạy để lập ma trận phạm vi: `Tên bảng giá × Kênh × Chi nhánh × Nhóm khách hàng × Thời gian hiệu lực`.
  3. Phát hiện các cặp bảng giá bị **xung đột phạm vi** (ví dụ cùng áp dụng kênh `POS` + `Tất cả khách hàng` trong cùng khung ngày) hoặc bảng giá sỉ bị tích nhầm kênh `Website` công khai.
  4. Đối chiếu dữ liệu giá mới dự kiến với giá vốn (`cost_price`) từ đầu vào hoặc `catalog-product-audit`: gắn cờ đỏ mọi SKU có `new_price < cost_price` (bán lỗ) và cờ vàng mọi SKU có biên `< min_margin_floor_pct`.
- **Điểm dừng an toàn:** Chỉ đọc và xuất bảng kiểm toán để người dùng chốt danh sách SKU sạch trước khi tạo bảng giá mới.

### Kịch bản 2: Tạo Bảng giá sỉ B2B theo Nhóm khách hàng & Giảm giá % hàng loạt (`b2b_percent_create`)
- **Khi nào dùng:** Thiết lập nhanh mức chiết khấu đồng loạt (ví dụ -15% cho Đại lý cấp 1, -10% cho VIP) áp dụng tự động trên POS/Harasocial hoặc cho nhóm khách đã đăng nhập Website.
- **Thao tác từng bước:**
  1. Tại `/admin/products/pricing_list`, bấm nút `Tạo bảng giá` để mở `/admin/products/pricing_list/new`.
  2. Nhập `Tên bảng giá` = `price_list_name` và `Mã bảng giá` viết liền không dấu, đảm bảo không trùng bảng giá hiện hữu.
  3. Tại mục **Phạm vi áp dụng**: tích chọn `target_channels` (ưu tiên `POS` / `Harasocial`; nếu chọn `Website` bắt buộc khóa đúng `target_customer_groups` đã có trên `/admin/customers/segments` để khách lẻ không thấy giá sỉ).
  4. Thiết lập `Ngày bắt đầu` và `Ngày kết thúc` (hoặc tích `Không có ngày kết thúc` cho bảng giá sỉ dài hạn).
  5. Bấm `Thêm sản phẩm`, chọn tối đa ≤ 100 SKU, sau đó bấm `Điều chỉnh giá hàng loạt` → chọn `Giảm theo %` → nhập mức chiết khấu và kiểm tra cột `Giá mới (VND)`.
- **Điểm dừng an toàn:** **DỪNG LẠI — CHƯA BẤM `Lưu`**, chụp `preview_screenshot` thể hiện rõ phạm vi áp dụng và mức giảm.

### Kịch bản 3: Tạo Bảng giá cố định (Fixed Price) theo từng SKU cho Đại lý / Chi nhánh (`sku_fixed_price_create`)
- **Khi nào dùng:** Mỗi SKU có mức giá sỉ hoặc giá bán riêng theo vùng/showroom không theo tỷ lệ % cố định.
- **Thao tác từng bước:**
  1. Mở `/admin/products/pricing_list/new`, nhập `Tên bảng giá`, chọn `Chi nhánh áp dụng` = `target_locations` (ví dụ Showroom Hà Nội hoặc Đại lý cấp 1).
  2. Bấm `Thêm sản phẩm`, tìm kiếm lần lượt theo từng mã SKU trong `discount_or_fixed_rules` (tối đa ≤ 100 SKU/lượt UI) để thêm vào bảng.
  3. Tại cột `Giá mới (VND)` của từng biến thể, nhập chính xác `new_price` (đã loại bỏ mọi SKU có `new_price < cost_price`).
  4. Rà soát lại cột so sánh `Giá bán lẻ gốc` vs `Giá mới` và mức chênh lệch % hiển thị trên bảng để phát hiện ngay lỗi gõ thừa/thiếu số `0` (ví dụ `45,000₫` thay vì `450,000₫`).
- **Điểm dừng an toàn:** **DỪNG LẠI — CHƯA BẤM `Lưu`**, chụp `preview_screenshot` toàn bộ bảng giá SKU để đối chiếu.

### Kịch bản 4: Chuẩn bị & Kiểm chuẩn Nhập file Excel/CSV cho bảng giá lớn (`> 100 SKU`) (`bulk_file_stage`)
- **Khi nào dùng:** Danh mục B2B có hàng trăm đến hàng nghìn SKU vượt giới hạn thao tác tay `max_records: 100` trên UI.
- **Thao tác từng bước:**
  1. Mở `/admin/products/pricing_list/new`, điền trước Thông tin chung, Phạm vi áp dụng và Thời gian hiệu lực.
  2. Click nút `Nhập file` để kiểm tra chính xác cấu trúc cột mẫu (SKU, Mã vạch, Giá mới) mà Haravan yêu cầu.
  3. Kiểm chuẩn file đề xuất của người dùng trước khi tải lên: phát hiện SKU trùng lặp, ô giá trống/âm/bằng 0, giá thấp hơn giá vốn hoặc giảm bất thường > 70% so với giá lẻ.
  4. Trình bày báo cáo kiểm chuẩn file kèm ảnh chụp hộp thoại `Nhập file` (`preview_screenshot`).
- **Điểm dừng an toàn:** Chưa bấm tải file lên nếu còn bất kỳ lỗi validation hoặc SKU bán lỗ nào chưa được Owner duyệt.

### Kịch bản 5: Rà soát Bảng giá sắp hết hạn & Đề xuất gia hạn tại `/admin/products/pricing_list/{id}` (`expiry_review`)
- **Khi nào dùng:** Kiểm tra định kỳ cuối tháng/quý để tránh bảng giá đại lý hết hạn đột ngột làm đơn POS nhảy về giá lẻ.
- **Thao tác từng bước:**
  1. Tại `/admin/products/pricing_list`, lọc các bảng giá có `Ngày kết thúc` trong vòng 7 ngày tới hoặc trạng thái `Hết hạn` gần đây.
  2. Mở chi tiết `/admin/products/pricing_list/{id}` (chỉ đọc) để ghi nhận danh sách SKU, kênh và nhóm khách hàng đang phụ thuộc vào bảng giá đó.
  3. Đề xuất gia hạn `Ngày kết thúc` hoặc lập bảng giá mới nối tiếp chu kỳ mà không làm gián đoạn bán hàng.
- **Điểm dừng an toàn:** Không tự bấm `Ngừng áp dụng` hay `Xóa` bảng giá đang hoạt động.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Kiểm tra gói)
- Mở `/admin/products/pricing_list`, xác nhận phiên đăng nhập hợp lệ và cửa hàng có hỗ trợ tính năng Bảng giá (không hiện banner nâng gói).
- Rà soát trùng tên và xung đột phạm vi với các bảng giá `Đang áp dụng`, chụp `pre_screenshot`.

### Pha 2 — Stage Without Saving (Điền cấu hình & Kiểm chuẩn giá)
- Điền đầy đủ Tên bảng giá, Phạm vi (Kênh/Chi nhánh/Nhóm khách), Thời gian hiệu lực và đơn giá từng SKU trên `/admin/products/pricing_list/new`.
- Chặn mọi SKU dưới giá vốn, kiểm tra không mở công khai giá sỉ trên `Website`, và **tuyệt đối chưa bấm `Lưu`**.

### Pha 3 — Screenshot-Before-Save & Human Approval Gate (Duyệt bảng giá)
- Chụp `preview_screenshot` rõ nét toàn bộ form đã điền và bảng giá mẫu.
- Lập bảng `Before → After` kèm cảnh báo biên mỏng (`< min_margin_floor_pct`) và dừng chờ người dùng xác nhận tường minh.

### Pha 4 — Save & Post-Save Reload Verification (Lưu & Xác minh bền vững)
- Chỉ khi người dùng xác nhận rõ ràng, bấm nút `Lưu`, chờ toast *"Tạo bảng giá thành công"* và chuyển trang `/admin/products/pricing_list/{id}`.
- Nhấn `F5` reload trang xác minh tên bảng giá, phạm vi, số lượng SKU và đơn giá bền vững, chụp `post_screenshot`.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Preview Before → After (B2B Pricing List)

| Hạng mục / SKU | Trước (Before) | Cấu hình Đề xuất (After) | Chênh lệch & Kiểm chuẩn biên |
| :--- | :--- | :--- | :--- |
| Tên bảng giá | *(Chưa tồn tại)* | `Gia-Si-DaiLyC1-Q4-2026` | Không trùng tên hiện có |
| Phạm vi áp dụng | Giá bán lẻ mặc định | Kênh `POS`, `Harasocial` + Nhóm `Đại lý cấp 1` | Không mở công khai trên `Website` |
| Thời gian hiệu lực | — | `01/12/2026 00:00` → `31/12/2026 23:59` | Không chồng lấn bảng giá đang chạy |
| SKU `SP-001-L` | `500,000₫` (Giá vốn `330,000₫`) | `425,000₫` (-15%) | ✅ Biên `22.4%` (Đạt ngưỡng ≥ 10%) |
| SKU `SP-002-M` | `300,000₫` (Giá vốn `220,000₫`) | `240,000₫` (-20%) | ⚠️ Biên `8.3%` (< 10% — Cần duyệt lại) |

> **Yêu cầu xác nhận:** Đã điền sẵn bảng giá `Gia-Si-DaiLyC1-Q4-2026` (`25 SKU`, có `1 SKU` biên mỏng < 10%) trên `/admin/products/pricing_list/new` (chưa lưu). Vui lòng xác nhận **"Đồng ý lưu bảng giá"** hoặc yêu cầu điều chỉnh giá SKU `SP-002-M`.

### JSON Execution Log Schema

```json
{
  "skill": "catalog-pricing-list-b2b-proposal",
  "scenario": "b2b_percent_create",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/products/pricing_list/new",
  "screenshots": {
    "pre": "artifacts/pricing_list_pre.png",
    "preview": "artifacts/pricing_list_preview.png",
    "post": null
  },
  "changes_staged": {
    "price_list_name": "Gia-Si-DaiLyC1-Q4-2026",
    "channels": ["POS", "Harasocial"],
    "customer_groups": ["Đại lý cấp 1"],
    "locations": ["Kho Trung Tam HCM"],
    "sku_count": 25,
    "below_cost_blocked_count": 0,
    "low_margin_warnings_count": 1,
    "public_website_exposure_checked": true,
    "overlap_conflicts_detected": 0
  },
  "verification_checks": {
    "pre_state_captured": true,
    "margin_floor_pct_applied": 10,
    "reload_verified": false
  },
  "saved_verified": false,
  "awaiting_human_confirmation": true
}
```

### Checklist Bàn giao & Kiểm tra sau khi Áp dụng
- [ ] Đã xác nhận bảng giá mới không trùng tên và không chồng lấn khung ngày với bảng giá đang chạy.
- [ ] Đã khóa đúng Nhóm khách hàng B2B nếu có tích kênh `Website` (không lộ giá sỉ cho khách lẻ).
- [ ] Đã kiểm thử thực tế 1 đơn nháp trên POS/Website với tài khoản thuộc nhóm mục tiêu để xác nhận giá tự động nhảy đúng.
- [ ] Đã lưu giữ `pre_screenshot`, `preview_screenshot` và `post_screenshot` để đối chiếu/rollback.

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click):**
  - `Xóa` / `Xóa bảng giá` đối với các bảng giá đang hoạt động hoặc có lịch sử đơn hàng.
  - `Ngừng áp dụng` trên bảng giá B2B/POS đang chạy khi chưa có yêu cầu tường minh.
  - `Nâng cấp gói` / `Mua thêm` nếu cửa hàng chưa kích hoạt tính năng Bảng giá.
- **Pricing & Security Handoff Gates:**
  - **Cấm mở công khai giá sỉ lên `Website`:** Nếu `target_channels` có `Website` nhưng `target_customer_groups` trống, bắt buộc chặn và cảnh báo nguy cơ lộ giá sỉ cho toàn bộ khách lẻ.
  - **Cấm lưu SKU bán lỗ (`new_price < cost_price`):** Phải loại bỏ hoặc dừng yêu cầu xác nhận đặc biệt từ Owner (trường hợp xả kho chủ đích).
  - Gặp màn hình đăng nhập `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Gói dịch vụ không hỗ trợ Bảng giá:** Màn hình hiển thị banner giới thiệu tính năng kèm nút `Nâng cấp gói` → Dừng ngay, báo rõ giới hạn gói và gợi ý giải pháp thay thế bằng Đơn hàng nháp (`draft-orders-quote-proposal`) hoặc Mã khuyến mãi.
2. **Thiếu quyền Staff (`Tạo bảng giá` bị ẩn hoặc báo 403):** Chụp ảnh màn hình và hướng dẫn Chủ shop cấp quyền **Sản phẩm → Bảng giá** tại `/admin/settings/group_permissions`.
3. **Nhóm khách hàng B2B chưa tồn tại trong dropdown:** Không thể gắn phạm vi khách sỉ → Dừng staging, hướng dẫn tạo nhóm trước bằng skill `admin-ui-crm-flows-broadcast` tại `/admin/customers/segments`.
4. **Toast lỗi validation khi bấm `Lưu`:** Thường do trùng `Mã bảng giá`, bỏ trống đơn giá của 1 biến thể, hoặc `Ngày kết thúc < Ngày bắt đầu` → Giữ nguyên form (không F5 làm mất dữ liệu), đọc chính xác nội dung toast và sửa đúng trường lỗi.
5. **Lỗi gõ nhầm đơn vị giá (thiếu số 0 gây giảm > 80%):** Trước khi chụp `preview_screenshot`, luôn rà soát lại mọi dòng có tỷ lệ giảm `> 50%` so với giá bán lẻ gốc để chống sai sót nhập liệu.
6. **Danh sách SKU quá lớn (> 100 SKU) gây chậm trình duyệt:** Chuyển sang Kịch bản 4 (`Nhập file` Excel/CSV) thay vì chọn tay từng dòng.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: true`):**
  1. Đối chiếu `pre_screenshot` để kiểm tra danh sách bảng giá trước khi thao tác.
  2. Mở `/admin/products/pricing_list/{id}` vừa tạo, bấm `Ngừng áp dụng` để lập tức đưa kênh/nhóm khách hàng quay về giá bán lẻ mặc định (hoặc để Chủ shop tự bấm `Xóa` nếu tạo nhầm hoàn toàn).
  3. Reload `/admin/products/pricing_list` để xác nhận trạng thái đã chuyển sang `Ngừng áp dụng`.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/20-catalog-merchandising/catalog-product-audit` (API): Trích xuất danh sách SKU, giá bán lẻ (`price`) và giá so sánh qua `GET /com/products.json` trước khi lập bảng giá.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-crm-flows-broadcast` (UI): Tạo Nhóm khách hàng VIP/Đại lý tại `/admin/customers/segments`.
  - `skills/browser-ui/40-orders-fulfillment/draft-orders-quote-proposal` (UI): Lập báo giá linh hoạt theo từng đơn khi chưa cần áp dụng bảng giá cố định.
