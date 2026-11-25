---
name: draft-orders-quote-proposal
description: "Chuẩn hóa quy trình lập Đơn hàng nháp (/admin/draft_orders) cho báo giá khách sỉ B2B, đơn đặt qua Zalo/Harasocial và theo dõi chuyển đổi."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 40-orders-fulfillment
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    - com.read_products
    - com.read_inventories
    - com.read_customers
  endpoints:
    - "GET https://apis.haravan.com/com/products.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "UI /admin/draft_orders"
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

# Haravan Draft Orders & B2B Quote Management Proposal

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Quản lý toàn bộ quy trình **Đơn hàng nháp & Báo giá** tại `/admin/draft_orders`, `/admin/draft_orders/new` và `/admin/draft_orders/{id}` trên Haravan Admin (`*.myharavan.com/admin`).
- **Lý do bắt buộc dùng Browser UI:** Giao diện Đơn hàng nháp của Haravan tích hợp trực quan khả năng tìm nhanh tồn kho khả dụng theo kho, thêm sản phẩm tùy chỉnh (`Thêm sản phẩm tùy chỉnh`), áp dụng chiết khấu tay (`%`/`VND`), nhập phí giao chành xe, gắn thông tin xuất hóa đơn VAT và lấy link thanh toán (`Sao chép link thanh toán`) để gửi khách qua Zalo/Harasocial.
- **Mục tiêu nghiệp vụ (`layer: L2`, `mode: proposal`):**
  - Chuẩn hóa quy trình tạo báo giá B2B / đơn Zalo-Harasocial ở trạng thái **Nháp (`Đang mở`)**, kiểm tra tồn kho khả dụng trước khi báo giá và **tuyệt đối không tự ý xác nhận thanh toán hay gửi email hóa đơn thật**.
  - Kiểm toán định kỳ các đơn nháp bị treo quá hạn (`stale_days`) để nhắc đội Sales chốt đơn hoặc dọn dẹp.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền tạo, sửa, gửi hóa đơn, xác nhận thanh toán và xóa đơn nháp.
  - **Staff:** Yêu cầu quyền **Xem & Tạo đơn hàng nháp** trong nhóm quyền **Đơn hàng** (`/admin/settings/group_permissions`). Nhân viên bị giới hạn chi nhánh chỉ thấy tồn kho và tạo đơn nháp tại kho được phân công.
  - **Giới hạn gói:** Tính năng Đơn hàng nháp khả dụng trên hầu hết các gói Haravan (Standard trở lên); riêng tính năng chọn đa kho xuất hàng phụ thuộc số kho của gói dịch vụ.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/draft_orders`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Xác nhận bảng danh sách tải xong và nút `Tạo đơn hàng` khả dụng.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/draft_orders` — Empty State CTA: `Tạo đơn` (link `Trợ giúp về Đơn hàng nháp`).


| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/draft_orders` | Danh sách Đơn hàng nháp | `Tạo đơn hàng`, `Lọc`, `Tìm kiếm`, `Xuất dữ liệu` (CẤM tự bấm) | Bộ lọc: `Trạng thái` (`Đang mở` / `Đã gửi hóa đơn` / `Đã hoàn tất`), `Ngày tạo`, `Nhân viên tạo`, `Nhãn (Tag)`. Cột: Mã đơn nháp (`#D...`), Ngày tạo, Khách hàng, Trạng thái, Tổng tiền |
| `/admin/draft_orders/new` | Khu vực Sản phẩm | `Thêm sản phẩm`, `Thêm sản phẩm tùy chỉnh` | Ô tìm kiếm SKU/Tên, hiển thị `Tồn khả dụng` theo kho, Số lượng, Đơn giá, Giảm giá từng dòng |
| `/admin/draft_orders/new` | Khuyến mãi, Phí ship & Ghi chú | `Thêm khuyến mãi`, `Thêm phí giao hàng`, Checkbox `Xuất hóa đơn công ty` | Chiết khấu tổng đơn (`%` / `VND`), Phí ship tùy chỉnh (giao chành xe/nội thành), `Ghi chú đơn hàng`, `Nhãn (Tags)` |
| `/admin/draft_orders/new` | Khách hàng & Kho xuất | `Tìm kiếm hoặc tạo mới khách hàng`, `Chỉnh sửa`, Dropdown `Kho xuất hàng` | Hồ sơ khách hàng (che PII khi báo cáo), Địa chỉ giao hàng 3 cấp, Thông tin xuất VAT (MST, Tên công ty) |
| `/admin/draft_orders/new` | Thanh tác vụ lưu | `Lưu nháp`, `Gửi hóa đơn` (HARD-BLOCKED), `Xác nhận thanh toán` (HARD-BLOCKED) | Chỉ được dùng `Lưu nháp` sau khi người dùng xác nhận |
| `/admin/draft_orders/{id}` | Chi tiết Đơn hàng nháp | `Lưu`, `Sao chép link thanh toán`, `Gửi hóa đơn` (CẤM), `Xóa đơn nháp` (HARD-BLOCKED) | Mã đơn `#Dxxxx`, lịch sử hoạt động, trạng thái `Đang mở`, link checkout tự động |

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `audit_stale_drafts` | `audit_stale_drafts` \| `b2b_quote_create` \| `social_custom_item_draft` \| `payment_link_prep` \| `multi_warehouse_stock_check` |
| `stale_days` | `integer` | Khi `audit_stale_drafts` | `7` | Số ngày đơn nháp ở trạng thái `Đang mở` bị coi là treo (`1..90`) |
| `customer_query` | `string` | Khi tạo báo giá | — | Tên, SĐT hoặc Email khách hàng (bắt buộc che PII trong báo cáo) |
| `line_items` | `array<object>` | Khi tạo báo giá | `[]` | Mảng `{sku, quantity, custom_discount}` (tối đa `max_records: 50` dòng) |
| `custom_items` | `array<object>` | Không | `[]` | Sản phẩm/dịch vụ ngoài danh mục `{title, price, quantity, taxable}` (ví dụ phí in ấn, đóng kiện) |
| `shipping_fee` | `number` | Không | `0` | Phí vận chuyển báo giá (VND, `>= 0`) |
| `warehouse_name` | `string` | Không | Kho mặc định | Tên kho xuất hàng hợp lệ để đối chiếu tồn khả dụng |
| `order_note` | `string` | Không | `""` | Điều khoản báo giá, thời hạn hiệu lực, thông tin VAT (tối đa 500 ký tự) |
| `tags` | `array<string>` | Không | `["b2b-quote"]` | Nhãn phân loại (`b2b-quote`, `zalo-order`, `need-stock-check`) |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi bấm `Lưu nháp` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Rà soát & Phân loại Đơn hàng nháp treo quá hạn (`audit_stale_drafts`)
- **Khi nào dùng:** Cuối tuần hoặc cuối tháng cần kiểm tra các báo giá B2B / đơn Zalo bị treo lâu chưa chốt để nhắc Sales theo sát.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/draft_orders`, chụp `pre_screenshot`.
  2. Mở bộ lọc `Lọc`: chọn `Trạng thái` = `Đang mở` (và `Đã gửi hóa đơn`), sắp xếp theo `Ngày tạo` từ cũ nhất đến mới nhất.
  3. Quét tối đa 50 đơn nháp tạo trước `stale_days` ngày: ghi nhận Mã đơn (`#D...`), Số ngày treo, Giá trị đơn, Nhân viên tạo, Nhãn (`b2b-quote`/`zalo-order`).
  4. Phân nhóm hành động đề xuất: nhóm giá trị cao (`>= 5,000,000₫` ưu tiên Sales gọi lại chốt) vs nhóm nháp quá 30 ngày không phản hồi (đề xuất người dùng tự dọn dẹp).
- **Điểm dừng an toàn:** Không bấm `Xóa đơn nháp`, `Xác nhận thanh toán` hay `Xuất dữ liệu`; che toàn bộ PII (`090****678`) trước khi trả báo cáo.

### Kịch bản 2: Lập báo giá B2B / Khách sỉ có chiết khấu tay & phí giao chành xe (`b2b_quote_create`)
- **Khi nào dùng:** Khách sỉ/doanh nghiệp hỏi báo giá theo lô kèm chiết khấu thương lượng và giao hàng qua chành xe/vận tải ngoài.
- **Thao tác từng bước:**
  1. Tại `/admin/draft_orders`, bấm `Tạo đơn hàng` để mở `/admin/draft_orders/new`.
  2. Chọn `Kho xuất hàng` = `warehouse_name`. Trong khung **Sản phẩm**, tìm từng SKU theo `line_items`, kiểm tra cột `Tồn khả dụng` (gắn cờ đỏ nếu `quantity > tồn khả dụng`) và nhập đúng số lượng.
  3. Bấm `Thêm khuyến mãi`, chọn chiết khấu `%` hoặc `VND` theo thỏa thuận sỉ và nhập lý do chiết khấu rõ ràng.
  4. Bấm `Thêm phí giao hàng`, nhập phương thức `Giao chành xe / Vận tải B2B` và mức phí `shipping_fee`.
  5. Tìm và chọn hồ sơ khách hàng theo `customer_query`, nhập điều khoản hiệu lực báo giá vào `Ghi chú đơn hàng`, gắn tag `b2b-quote`.
- **Điểm dừng an toàn:** **DỪNG LẠI — TUYỆT ĐỐI CHƯA BẤM `Lưu nháp`, `Gửi hóa đơn` hay `Xác nhận thanh toán`**, chụp `preview_screenshot`.

### Kịch bản 3: Lập đơn nháp Zalo / Harasocial có Sản phẩm tùy chỉnh & Yêu cầu VAT (`social_custom_item_draft`)
- **Khi nào dùng:** Đơn đặt qua chat có phát sinh hạng mục ngoài catalog (phí in ấn, đóng kiện quà) hoặc khách doanh nghiệp cần xuất hóa đơn đỏ VAT.
- **Thao tác từng bước:**
  1. Mở `/admin/draft_orders/new`, thêm các SKU chuẩn từ danh mục sản phẩm (nếu có).
  2. Bấm `Thêm sản phẩm tùy chỉnh` để nhập các hạng mục phát sinh ngoài catalog (`Phí in logo lên hộp quà`, `Phí đóng kiện gỗ`) kèm đơn giá, số lượng và tùy chọn tính thuế.
  3. Tích chọn mục xuất hóa đơn công ty (nếu có) và điền thông tin MST, tên đơn vị, email nhận hóa đơn điện tử vào `Ghi chú đơn hàng` (che MST/email khi tóm tắt báo cáo).
  4. Gắn tag `zalo-order`, `vat-required` để bộ phận kế toán và vận hành lọc nhanh.
- **Điểm dừng an toàn:** **DỪNG LẠI — CHƯA BẤM `Lưu nháp`**, chụp `preview_screenshot` kiểm tra tổng tiền gồm thuế/phí.

### Kịch bản 4: Chuẩn bị Link thanh toán & Tin nhắn báo giá cho Sales (`payment_link_prep`)
- **Khi nào dùng:** Sau khi đơn nháp đã được duyệt và lưu thành công ở trạng thái `Đang mở`, cần gửi nhanh link checkout cho khách qua Zalo/Messenger.
- **Thao tác từng bước:**
  1. Mở `/admin/draft_orders/{id}` vừa lưu, kiểm tra lại mã đơn `#Dxxxx`, tổng tiền và danh sách SKU khớp 100% bản duyệt.
  2. Tại thanh tác vụ chi tiết đơn nháp, chỉ dùng nút `Sao chép link thanh toán` để lấy URL checkout tự động của Haravan.
  3. Soạn sẵn mẫu tin nhắn báo giá tiếng Việt kèm link thanh toán đã sao chép và thông tin chuyển khoản/đặt cọc để nhân viên Sales tự gửi cho khách.
- **Điểm dừng an toàn:** **TUYỆT ĐỐI KHÔNG tự bấm `Gửi hóa đơn`** (tránh hệ thống tự gửi email thật ra ngoài khi Sales chưa kiểm tra).

### Kịch bản 5: Kiểm tra tồn kho khả dụng đa kho trước khi chốt báo giá lớn (`multi_warehouse_stock_check`)
- **Khi nào dùng:** Đơn sỉ số lượng lớn có nguy cơ vượt tồn tại kho mặc định, cần kiểm tra chéo các kho chi nhánh trước khi cam kết giao hàng.
- **Thao tác từng bước:**
  1. Mở `/admin/draft_orders/new`, thêm các SKU số lượng lớn trong `line_items` và lần lượt đổi `Kho xuất hàng` qua từng chi nhánh để đọc `Tồn khả dụng` thực tế.
  2. Nếu không có kho đơn lẻ nào đủ hàng cho cả đơn, ghi nhận bảng tồn kho từng chi nhánh và đề xuất tách thành 2 đơn nháp theo 2 kho xuất (gắn tag `need-stock-check`).
  3. Cảnh báo rõ rủi ro bán âm kho nếu giữ chung một đơn nháp mà chưa điều chuyển hàng.
- **Điểm dừng an toàn:** Chụp `preview_screenshot` tình trạng tồn kho trên form (chưa lưu) để người dùng quyết định phương án điều phối.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Chống tạo trùng)
- Mở `/admin/draft_orders`, xác nhận phiên đăng nhập hợp lệ (không redirect `accounts.haravan.com`).
- Kiểm tra xem khách hàng `customer_query` đã có đơn nháp tương tự tạo trong ngày chưa (đảm bảo `idempotency_required: true`), chụp `pre_screenshot`.

### Pha 2 — Stage Without Saving (Điền báo giá không ghi nhận doanh thu)
- Điền đầy đủ SKU, số lượng, sản phẩm tùy chỉnh, chiết khấu, phí vận chuyển, khách hàng, ghi chú và tag trên `/admin/draft_orders/new`.
- Tuyệt đối không bấm `Lưu nháp`, `Gửi hóa đơn` hay `Xác nhận thanh toán` và không reload trang (vì form không tự lưu).

### Pha 3 — Screenshot-Before-Save & Human Approval Gate (Duyệt trước khi lưu nháp)
- Chụp `preview_screenshot` thấy rõ danh sách sản phẩm, chiết khấu, phí vận chuyển và **Tổng cộng**.
- Lập bảng `Before → After` đã che PII (`090****678`, `a***@domain.com`), dừng chờ người dùng xác nhận.

### Pha 4 — Save Draft & Post-Save Reload Verification (Lưu nháp & Reload xác minh)
- Chỉ khi người dùng xác nhận *"Đồng ý lưu đơn nháp"*, bấm nút `Lưu nháp` (tuyệt đối không bấm `Xác nhận thanh toán`).
- Chờ chuyển sang `/admin/draft_orders/{id}` kèm mã `#Dxxxx`, nhấn `F5` reload xác minh trạng thái `Đang mở` và tổng tiền bền vững, chụp `post_screenshot`.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Preview Before → After (Draft Order B2B Quote)

| Hạng mục | Trước (Before) | Bản nháp Đề xuất (After) | Kiểm chuẩn Tồn kho & An toàn |
| :--- | :--- | :--- | :--- |
| Mã đơn nháp | *(Chưa tạo)* | Dự kiến `#D-NEW` (`Đang mở`) | Chưa trừ tồn kho, chưa ghi nhận doanh thu |
| Khách hàng | — | Công ty TNHH A*** (`090****678`) | Đã che PII theo `policies/pii-handling.md` |
| Sản phẩm (3 SKU + 1 tùy chỉnh) | — | Tạm tính `15,500,000₫` | Đủ tồn khả dụng tại `Kho Trung Tâm HCM` |
| Chiết khấu & Phí vận chuyển | `0₫` | Chiết khấu `-1,500,000₫` \| Phí ship `+150,000₫` | Giao chành xe, báo giá hiệu lực 7 ngày |
| **Tổng cộng dự kiến** | — | **`14,150,000₫`** | Nhãn: `b2b-quote`, `vat-required` |

> **Yêu cầu xác nhận:** Bản nháp báo giá tổng `14,150,000₫` đã được điền sẵn tại `/admin/draft_orders/new` (chưa lưu). Vui lòng xác nhận **"Đồng ý lưu đơn nháp"** để Agent bấm `Lưu nháp` (không gửi email cho khách và không xác nhận thanh toán).

### JSON Execution Log Schema

```json
{
  "skill": "draft-orders-quote-proposal",
  "scenario": "b2b_quote_create",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/draft_orders/new",
  "screenshots": {
    "pre": "artifacts/draft_orders_pre.png",
    "preview": "artifacts/draft_orders_preview.png",
    "post": null
  },
  "changes_staged": {
    "customer_masked": "Công ty TNHH A*** (090****678)",
    "warehouse": "Kho Trung Tâm HCM",
    "line_items_count": 3,
    "custom_items_count": 1,
    "stock_shortage_warnings": 0,
    "subtotal_vnd": 15500000,
    "discount_vnd": 1500000,
    "shipping_vnd": 150000,
    "total_vnd": 14150000,
    "tags": ["b2b-quote", "vat-required"]
  },
  "pii_redacted": true,
  "saved_verified": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click):**
  - `Xác nhận thanh toán` / `Đánh dấu đã thanh toán` (biến đơn nháp thành đơn chính thức, trừ tồn kho và ghi nhận doanh thu khi chưa có chứng từ thanh toán/đặt cọc).
  - `Gửi hóa đơn` (tự động gửi email báo giá thật tới khách hàng khi người dùng chưa duyệt nội dung).
  - `Xóa đơn nháp` / `Xóa` đối với các đơn nháp đang mở.
  - `Xuất dữ liệu` (tránh tải file raw chứa SĐT/email khách hàng — vi phạm `export_allowed: false`).
- **Credential & PII Handoff Gates:**
  - Gặp màn hình đăng nhập `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.
  - Mọi SĐT (`090****678`), email (`a***@domain.com`), mã số thuế cá nhân và địa chỉ nhà chi tiết phải được che hoàn toàn trong báo cáo và log.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Trang `/admin/draft_orders/new` không có Auto-save:** Nếu bấm `F5` hoặc mất kết nối trước khi lưu nháp, toàn bộ form sẽ mất sạch → Luôn kiểm tra kỹ toàn bộ dòng SKU và chụp `preview_screenshot` trước khi thao tác tiếp, tuyệt đối không reload trong Pha B.
2. **SKU không tìm thấy trong ô `Thêm sản phẩm`:** Thường do sản phẩm đang ở trạng thái ẩn khỏi kênh bán hàng hoặc hết tồn kho và tắt cho phép bán âm → Kiểm tra lại mã SKU và báo người dùng thay vì tự tạo `Sản phẩm tùy chỉnh` (vì sản phẩm tùy chỉnh không liên kết trừ tồn kho).
3. **Toast lỗi validation khi lưu nháp:** Do số lượng `<= 0`, chiết khấu vượt quá tổng tiền hàng, hoặc chưa thêm ít nhất 1 sản phẩm → Giữ nguyên form, báo rõ lỗi để điều chỉnh.
4. **Khách hàng chưa có hồ sơ trong hệ thống:** Nếu tìm `customer_query` không ra kết quả, không tự tạo hồ sơ khách hàng mới khi chưa đủ thông tin chuẩn (tên, SĐT, địa chỉ 3 cấp); hỏi lại người dùng xác nhận trước.
5. **Thiếu quyền Staff (ẩn menu `Đơn hàng nháp` hoặc nút `Tạo đơn hàng`):** Báo Chủ shop kiểm tra phân quyền **Đơn hàng → Đơn hàng nháp** tại `/admin/settings/group_permissions`.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: true`):**
  1. Mở lại `/admin/draft_orders/{id}` vừa tạo.
  2. Do đơn vẫn ở trạng thái `Đang mở` (chưa chuyển thành đơn chính thức), chưa phát sinh trừ kho hay ghi nhận doanh thu/công nợ.
  3. Người dùng có thể tự chỉnh sửa lại SKU/giá hoặc tự bấm `Xóa đơn nháp` nếu hủy báo giá.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/30-inventory-supply/inventory-low-stock-check` (API): Đối chiếu tồn khả dụng đa kho qua `GET /com/inventory_locations.json` trước khi lập báo giá sỉ số lượng lớn.
  - `skills/browser-ui/20-catalog-merchandising/catalog-pricing-list-b2b-proposal` (UI): Thiết lập bảng giá sỉ cố định thay vì nhập chiết khấu thủ công trên từng đơn nháp.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-checkout-settings` (UI): Cấu hình quy tắc đặt cọc / phương thức thanh toán hiển thị trên link thanh toán của đơn nháp.
