---
name: admin-ui-tax-einvoice-accounting
description: "Kiểm tra & hỗ trợ thiết lập Thuế/Hóa đơn điện tử (/admin/settings/vat_setting), Tờ khai thuế (/admin/etax/declarations), Sổ kế toán & Sổ quỹ/Công nợ."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 95-admin-ui-browser
layer: L2
wave: 2
mode: proposal
risk: high
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/settings/vat_setting"
    - "UI /admin/etax/declarations"
    - "UI /admin/etax/revenue_ledgers"
    - "UI /admin/accounting/transactions"
    - "UI /admin/accounting/debts"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 25
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

# Haravan Admin UI: VAT, E-Invoice, eTax & Cashbook Governance

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Tại sao bắt buộc dùng Browser UI:** Toàn bộ phân hệ **Thuế & hóa đơn điện tử** (`/admin/settings/vat_setting`), **Tờ khai thuế** (`/admin/etax/declarations`), **Sổ kế toán** doanh thu (`/admin/etax/revenue_ledgers`), **Sổ quỹ** (`/admin/accounting/transactions`) và **Công nợ** (`/admin/accounting/debts`) trên Haravan Admin **không có REST API công khai** để đọc hoặc cấu hình.
- **Mức độ rủi ro High — Tuân thủ Pháp lý Thuế (`separate_turn: true`):** Hóa đơn điện tử (HĐĐT kết nối MISA meInvoice, VNPT, Viettel S-Invoice, Bkav...) và Tờ khai thuế gắn trực tiếp với nghĩa vụ pháp lý với Cơ quan Thuế Việt Nam (Nghị định 123/2020/NĐ-CP & Thông tư 78/2021/TT-BTC). Mọi báo cáo trích xuất chỉ mang tính **Operational Estimate / Reconciliation Aid** cho kế toán; mọi thay đổi cấu hình thuế tại `/admin/settings/vat_setting` bắt buộc **xác nhận ở lượt hội thoại riêng (`separate_turn: true`)**.
- **Phân quyền Owner vs Staff:**
  - **Owner** hoặc **Kế toán** được gán quyền cụ thể cho **Cấu hình > Thuế & hóa đơn điện tử**, **Thuế & kế toán**, **Sổ quỹ / Công nợ** tại `/admin/settings/group_permissions`. Nhân viên bán hàng/kho mặc định không thấy các menu này.
- **Giới hạn gói dịch vụ (Standard / Pro / Grow / Scale):**
  - Cấu hình thuế GTGT cơ bản có trên mọi gói; phân hệ **Tờ khai thuế** (`/admin/etax/declarations`), **Sổ kế toán** (`/admin/etax/revenue_ledgers`) và tích hợp tự động phát hành HĐĐT có thể yêu cầu kích hoạt add-on hoặc gói **Pro / Grow / Scale** cùng hợp đồng riêng với nhà cung cấp HĐĐT.
- **Pre-flight Check phiên đăng nhập & Pháp lý Thuế:**
  1. Mở `https://{store_domain}/admin/settings/vat_setting` (hoặc `/etax/*`, `/accounting/*`).
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để Owner/Kế toán tự đăng nhập; không hỏi hoặc tự nhập mật khẩu/OTP.
  3. Xác nhận kỳ kê khai mục tiêu (`period_filter`) và đảm bảo mọi báo cáo trích xuất đều đính kèm **Financial & Tax Disclaimer** (*Operational Estimate / Reconciliation Aid*).
  4. Khóa cứng chế độ **100% Read-Only** cho 4 route `/admin/etax/declarations`, `/admin/etax/revenue_ledgers`, `/admin/accounting/transactions`, `/admin/accounting/debts`.

## 2. Bản đồ Giao diện Thực tế (Verified Haravan Admin UI Map)

| Route / URL | Section / Tab | Nhãn nút bấm & Điều khiển (Exact UI Labels) | Trường cấu hình / Dữ liệu chính |
| :--- | :--- | :--- | :--- |
| `/admin/settings/vat_setting` | `Cấu hình thuế` & `Hóa đơn điện tử` | Toggle bật/tắt tính thuế, `Kết nối`, `Chỉnh sửa`, `Lưu`, `Ngừng kết nối` (HARD-BLOCKED) | Quy tắc `Giá sản phẩm đã bao gồm thuế`, Thuế suất GTGT mặc định (`0%`, `5%`, `8%`, `10%`), trạng thái kết nối nhà cung cấp HĐĐT (MISA meInvoice, VNPT, Viettel S-Invoice, Bkav...) |
| `/admin/etax/declarations` | `Thuế & kế toán` → `Tờ khai thuế` | `Lọc`, `Xem chi tiết`, `Nộp tờ khai` (HARD-BLOCKED) | Kỳ kê khai (Tháng/Quý), Trạng thái (`Nháp` / `Đã nộp`), Doanh thu kê khai tạm tính |
| `/admin/etax/revenue_ledgers` | `Thuế & kế toán` → `Sổ kế toán` | `Lọc`, `Xem chi tiết`, `Xuất file` (CẤM tự bấm) | Sổ chi tiết doanh thu bán hàng hóa/dịch vụ theo kỳ, mã hóa đơn đối chiếu chứng từ gốc |
| `/admin/accounting/transactions` | `Sổ quỹ` → `Sổ quỹ` | `Lọc`, `Tạo phiếu thu` / `Tạo phiếu chi` (HARD-BLOCKED) | Quỹ đầu kỳ, Tổng thu, Tổng chi, Tồn quỹ cuối kỳ theo phương thức thanh toán |
| `/admin/accounting/debts` | `Sổ quỹ` → `Công nợ` | `Lọc`, `Thanh toán` (HARD-BLOCKED) | Công nợ phải thu / phải trả theo khách hàng, nhà cung cấp hoặc đơn vị vận chuyển |

> **Ranh giới pháp lý:** AI Agent chỉ hỗ trợ rà soát, đối chiếu và chuẩn bị form cấu hình thuế — tuyệt đối không thay mặt doanh nghiệp phát hành HĐĐT, ký số hay nộp tờ khai lên Cơ quan Thuế.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Quy tắc kiểm chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin `*.myharavan.com` |
| `scenario` | `string` | Có | `audit_vat_einvoice` | `audit_vat_einvoice` \| `configure_vat_rules` \| `audit_etax_declarations` \| `audit_revenue_ledgers` \| `audit_cashbook_debts` |
| `vat_updates` | `object` | Khi `configure_vat_rules` | `{}` | `{tax_included_in_price: bool, default_vat_rate_pct: 0\|5\|8\|10}`; chỉ điền khi có yêu cầu rõ từ kế toán/chủ shop |
| `period_filter` | `string` | Không | `current_month` | `current_month` \| `last_month` \| `current_quarter` \| `YYYY-MM` |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true`; mọi thao tác lưu tại `/vat_setting` bắt buộc `separate_turn: true` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (Click-by-Click Scenarios)

### Scenario 1: Kiểm toán cấu hình `Thuế & hóa đơn điện tử` (`audit_vat_einvoice` — Read-Only)
- **Điều kiện kích hoạt:** Trước kỳ khóa sổ kế toán, khi thay đổi chính sách giảm thuế GTGT (`8%` ↔ `10%`) hoặc khi phát hiện đơn hàng không tự đẩy nháp hóa đơn.
1. Điều hướng tới `https://{store_domain}/admin/settings/vat_setting`.
2. Ghi nhận toàn bộ thông số thuế hiện hành:
   - Cờ `Giá sản phẩm đã bao gồm thuế` (`Bật` / `Tắt`) — kiểm tra nhất quán với cách niêm yết giá bán lẻ trên Website & POS.
   - Thuế suất GTGT mặc định (`0%`, `5%`, `8%`, `10%`) và quy tắc tính thuế trên phí vận chuyển (nếu có).
3. Kiểm tra trạng thái kết nối nhà cung cấp HĐĐT (`MISA meInvoice`, `VNPT`, `Viettel S-Invoice`, `Bkav`): đang `Đang kết nối` hay `Mất kết nối` / hết gói số lượng hóa đơn phát hành.
4. Kiểm tra chéo với kho chi nhánh (`admin-ui-locations-inventory-ops`) xem cờ `Cập nhật thông tin xuất hoá đơn` đã đồng bộ đúng pháp nhân/MST chưa. Kết thúc ở chế độ chỉ đọc.

### Scenario 2: Đề xuất điều chỉnh quy tắc VAT (`configure_vat_rules` — `separate_turn: true`)
- **Điều kiện kích hoạt:** Chỉ thực hiện khi có chỉ thị rõ ràng từ Kế toán trưởng hoặc Chủ doanh nghiệp về việc điều chỉnh thuế suất hoặc quy tắc giá đã bao gồm VAT.
1. Tại `/admin/settings/vat_setting`, chụp ảnh trạng thái gốc (`pre_screenshot`).
2. Nếu người dùng muốn kết nối mới nhà cung cấp HĐĐT hoặc nhập Mã số thuế / tài khoản cổng HĐĐT / PIN chữ ký số USB Token/HSM: **DỪNG NGAY LẬP TỨC** để Kế toán/Owner tự nhập trực tiếp trên trình duyệt.
3. Nếu điều chỉnh quy tắc tính thuế (`Giá sản phẩm đã bao gồm thuế` hoặc thuế suất GTGT mặc định `0%`/`5%`/`8%`/`10%`) theo `vat_updates`:
   - Chọn giá trị mới trên giao diện.
   - Ghi cảnh báo rõ tác động trực tiếp lên giá hiển thị trên trang Checkout và tổng giá trị đơn hàng phát sinh sau thời điểm lưu.
4. **DỪNG — chưa bấm `Lưu`**, chuyển sang cổng duyệt bắt buộc ở lượt hội thoại riêng (`separate_turn: true`).

### Scenario 3: Rà soát Read-Only `Tờ khai thuế` (`/admin/etax/declarations`)
- **Điều kiện kích hoạt:** Kế toán cần tổng hợp nhanh hiện trạng tờ khai thuế cuối tháng/cuối quý trước khi đối chiếu sổ sách chính thức.
1. Điều hướng tới `https://{store_domain}/admin/etax/declarations`.
2. Sử dụng bộ lọc `Lọc` chọn đúng kỳ kê khai từ `period_filter` (Tháng/Quý).
3. Đọc danh sách tờ khai, trạng thái (`Nháp` / `Đã nộp`) và tổng doanh thu kê khai tạm tính; mở `Xem chi tiết` nếu cần kiểm tra các khoản chênh lệch giữa doanh thu gộp, chiết khấu và hàng hoàn trả.
4. **TUYỆT ĐỐI KHÔNG bấm `Nộp tờ khai` / `Gửi cơ quan thuế`**. Trình bày bảng tổng hợp kèm tuyên bố *Operational Estimate / Reconciliation Aid* cho kế toán.

### Scenario 4: Rà soát Read-Only `Sổ kế toán` doanh thu (`/admin/etax/revenue_ledgers`)
- **Điều kiện kích hoạt:** Đối chiếu danh sách đơn hàng bán ra với số hóa đơn điện tử đã phát hành trong kỳ.
1. Điều hướng tới `https://{store_domain}/admin/etax/revenue_ledgers`.
2. Lọc theo kỳ `period_filter`, rà soát các dòng chứng từ doanh thu bán hàng hóa/dịch vụ và cột trạng thái phát hành HĐĐT.
3. Gắn cờ các bất thường phổ biến để kế toán xử lý: đơn hàng đã `Hoàn tất` & `Đã thanh toán` nhưng chưa có số HĐĐT, hóa đơn bị lỗi ký số, hoặc đơn hoàn trả chưa có hóa đơn điều chỉnh.
4. Không bấm `Xuất file` nếu chưa được duyệt; lập bảng tóm tắt các chứng từ cần kiểm tra gửi bộ phận kế toán.

### Scenario 5: Rà soát Read-Only `Sổ quỹ` & `Công nợ` (`/admin/accounting/{transactions,debts}`)
- **Điều kiện kích hoạt:** Kiểm tra nhanh dòng tiền thu/chi thực tế và công nợ quá hạn trên Haravan Admin.
1. Điều hướng lần lượt tới `/admin/accounting/transactions` và `/admin/accounting/debts`.
2. Lọc theo `period_filter`, đọc các chỉ số cốt lõi: `Quỹ đầu kỳ`, `Tổng thu`, `Tổng chi`, `Tồn quỹ cuối kỳ` (phân tách tiền mặt, chuyển khoản, COD) và danh sách `Công nợ` quá hạn theo đối tượng.
3. Phối hợp với skill `finance-cashbook-debt-audit` nếu cần lập báo cáo kiểm toán sổ quỹ chuyên sâu.
4. **TUYỆT ĐỐI KHÔNG bấm** `Tạo phiếu thu`, `Tạo phiếu chi` hay `Thanh toán` công nợ.

### Bảng phân tách quyền hạn Read-Only vs Proposal trên 5 phân hệ Thuế & Kế toán
| Route | Chế độ thực thi | Quyền hạn AI Agent | Yêu cầu xác nhận |
| :--- | :--- | :--- | :--- |
| `/admin/settings/vat_setting` | Read-Only / Proposal | Kiểm toán & chọn cấu hình thuế (không bấm phát hành HĐĐT) | **Bắt buộc `separate_turn: true`** |
| `/admin/etax/declarations` | **100% Read-Only** | Lọc kỳ & tổng hợp đối chiếu (CẤM `Nộp tờ khai`) | Không ghi dữ liệu |
| `/admin/etax/revenue_ledgers` | **100% Read-Only** | Đối chiếu chứng từ doanh thu & hóa đơn thiếu số | Không ghi dữ liệu |
| `/admin/accounting/transactions` | **100% Read-Only** | Kiểm toán tồn quỹ đầu/cuối kỳ (CẤM tạo phiếu thu/chi) | Không ghi dữ liệu |
| `/admin/accounting/debts` | **100% Read-Only** | Theo dõi công nợ quá hạn (CẤM bấm `Thanh toán`) | Không ghi dữ liệu |

> **Lưu ý tuân thủ:** Mọi dữ liệu tổng hợp từ 5 phân hệ trên đều phải gắn nhãn *Operational Estimate / Reconciliation Aid* và không thay thế báo cáo tài chính/tờ khai thuế chính thức.

## 5. Quy trình An toàn 4 Pha (High Risk — `separate_turn: true`)

### Pha 1: Pre-State Capture (Chụp Ảnh Trạng Thái Thuế & Chứng Từ Gốc)
- Mở đúng route mục tiêu (`/admin/settings/vat_setting`, `/etax/*`, `/accounting/*`), xác minh phiên đăng nhập của Owner/Kế toán.
- Chụp ảnh trạng thái gốc (`artifacts/tax_einvoice_pre.png`), ghi nhận quy tắc `Giá sản phẩm đã bao gồm thuế`, thuế suất GTGT và tình trạng kết nối cổng HĐĐT.

### Pha 2: Read-Only Audit hoặc Stage Without Saving
- Với 4 route `/etax/*` và `/accounting/*`: chạy **100% Read-Only**, tuyệt đối không bấm nút ghi/phát hành/nộp tờ khai/tạo phiếu thu-chi.
- Với `/admin/settings/vat_setting`: chọn cấu hình thuế theo yêu cầu kế toán (hoặc dừng ngay tại bước nhập tài khoản MISA/VNPT/Viettel & chữ ký số để kế toán tự nhập).
- **ĐIỂM DỪNG CỨNG:** Tuyệt đối **CHƯA bấm nút `Lưu`**.

### Pha 3: Screenshot-Before-Save & Separate-Turn Gate (`separate_turn: true`)
- Chụp ảnh trạng thái đã chọn (`artifacts/tax_einvoice_preview.png`).
- Gửi bảng `Before → After` (Mục 6) kèm **Financial & Tax Disclaimer** bắt buộc và **dừng hoàn toàn chờ Kế toán/Owner xác nhận ở LƯỢT HỘI THOẠI TIẾP THEO**.

### Pha 4: Save & Post-Save Reload Verification (Chỉ với `/vat_setting`)
- Chỉ khi nhận được xác nhận ở lượt riêng, bấm nút `Lưu`, chờ toast *"Cập nhật thành công"*, nhấn `F5` reload trang xác minh cấu hình thuế đã lưu bền vững và chụp `artifacts/tax_einvoice_post.png`.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Kiểm tra / Preview Thuế, HĐĐT & Kế toán

| Phân hệ / Route | Hiện trạng (Before) | Đề xuất / Phát hiện (After) | Ghi chú pháp lý |
| :--- | :--- | :--- | :--- |
| `/admin/settings/vat_setting` | `Giá đã gồm thuế: Bật`, VAT `10%` | Đề xuất kiểm tra chuyển `8%` theo nhóm hàng | Cần kế toán xác nhận lượt riêng |
| Nhà cung cấp HĐĐT | `MISA meInvoice` — `Đang kết nối` | Hoạt động ổn định (đã ẩn thông tin đăng nhập) | Agent không bấm phát hành HĐĐT |
| `/admin/etax/declarations` | Kỳ Tháng 11: `Nháp` | Đã đối chiếu doanh thu tạm tính (Read-Only) | Kế toán tự kiểm chứng từ gốc |
| `/admin/etax/revenue_ledgers` | 142 chứng từ doanh thu | Phát hiện 3 đơn hoàn tất chưa có số HĐĐT | Bàn giao kế toán xử lý ký số |
| `/admin/accounting/transactions` | Tồn quỹ cuối kỳ (Read-Only) | Ghi nhận chênh lệch COD chờ đối soát | Không tự tạo phiếu thu/chi |

> **⚠️ Financial & Tax Disclaimer:** Số liệu và cấu hình trích xuất từ Haravan Admin chỉ là công cụ hỗ trợ đối chiếu vận hành (**Operational Estimate / Reconciliation Aid**), không phải sổ cái kế toán chính thức hay tư vấn pháp lý thuế. Mọi thao tác phát hành HĐĐT, nộp tờ khai thuế và sửa thuế suất phải do Kế toán/Chủ doanh nghiệp đối chiếu chứng từ gốc và xác nhận ở lượt hội thoại riêng (`separate_turn: true`).

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-tax-einvoice-accounting",
  "scenario": "audit_vat_einvoice",
  "risk": "high",
  "separate_turn_required": true,
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/vat_setting",
  "phase_status": "awaiting_separate_turn_confirmation",
  "artifacts": {
    "pre_screenshot": "artifacts/tax_einvoice_pre.png",
    "preview_screenshot": "artifacts/tax_einvoice_preview.png",
    "post_screenshot": "artifacts/tax_einvoice_post.png"
  },
  "checks_passed": {
    "financial_disclaimer_included": true,
    "einvoice_issue_buttons_blocked": true,
    "etax_submit_blocked": true,
    "separate_turn_enforced": true
  },
  "changes_staged": null,
  "saved_verified": false,
  "reload_checked": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

| Hạng mục / Nút bấm trên UI | Chính sách An toàn | Lý do & Hành động thay thế |
| :--- | :--- | :--- |
| `Phát hành hóa đơn` / `Phát hành HĐĐT` / `Ký số` | **HARD-BLOCKED** | Phát sinh hóa đơn pháp lý gửi Tổng cục Thuế, không thể xóa bỏ tùy tiện |
| `Nộp tờ khai` / `Gửi cơ quan thuế` (`/etax/declarations`) | **HARD-BLOCKED** | Nghĩa vụ pháp lý thuế — chỉ Kế toán/Đại diện pháp luật tự thực hiện |
| `Tạo phiếu thu` / `Tạo phiếu chi` / `Thanh toán` (`/accounting/*`) | **HARD-BLOCKED** | Làm sai lệch sổ quỹ & công nợ kế toán nếu không có chứng từ gốc |
| `Ngừng kết nối` nhà cung cấp HĐĐT đang chạy live | **HARD-BLOCKED** | Gây gián đoạn luồng xuất hóa đơn tự động cho đơn hàng bán lẻ |
| Tài khoản cổng HĐĐT, mã PIN USB Token/HSM, cổng Thuế | **HANDOFF GATE** | Tuyệt đối không hỏi/tự nhập; dừng bàn giao Kế toán tự thao tác |

## 8. Xử lý Sự cố UI & Tình huống Biên

1. **Cảnh báo mất kết nối nhà cung cấp HĐĐT (MISA/VNPT/Viettel):** Ghi nhận chính xác mã lỗi hiển thị (thường do hết hạn token đăng nhập hoặc hết gói số lượng hóa đơn) và bàn giao ngay cho kế toán tự xử lý trên cổng nhà cung cấp.
2. **Chênh lệch doanh thu giữa `Sổ kế toán` (`/admin/etax/revenue_ledgers`) và Báo cáo bán hàng:** Thường do khác thời điểm ghi nhận (ngày xuất hóa đơn vs ngày tạo đơn, hoặc đơn hủy/hoàn trả hàng chưa lập biên bản điều chỉnh) → Luôn liệt kê rõ để kế toán đối chiếu.
3. **Thay đổi cờ `Giá sản phẩm đã bao gồm thuế` làm lệch giá bán trên Website:** Cảnh báo kế toán kiểm tra lại giá niêm yết của 1 SKU mẫu ngay sau khi đổi để tránh trường hợp hệ thống cộng thêm 8%–10% VAT chồng lên giá bán lẻ.
4. **Menu `Thuế & kế toán` bị ẩn với Staff:** Tài khoản thiếu quyền Kế toán → Yêu cầu Owner đăng nhập hoặc cấp quyền `accounting_readonly`.
5. **Đơn hàng POS/Website hoàn tất nhưng không tự đẩy sang nháp HĐĐT:** Kiểm tra chéo cờ `Cập nhật thông tin xuất hoá đơn` tại `/admin/settings/locations/{id}` của kho xuất hàng tương ứng.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback thủ công (Chỉ áp dụng cho cấu hình UI tại `/admin/settings/vat_setting`)
1. Đối chiếu `artifacts/tax_einvoice_pre.png` đã chụp ở Pha 1.
2. Mở `/admin/settings/vat_setting`, khôi phục lại đúng cấu hình `Giá đã bao gồm thuế` và thuế suất GTGT gốc rồi bấm `Lưu`.
3. *Lưu ý pháp lý bắt buộc:* Các hóa đơn điện tử đã phát hành hoặc tờ khai đã nộp **không thể rollback** trên Haravan — bắt buộc lập biên bản điều chỉnh/thay thế theo Nghị định 123/2020/NĐ-CP và Thông tư 78/2021/TT-BTC.

### Checklist Kiểm chứng End-to-End sau khi Lưu
- [ ] Kiểm tra 1 đơn hàng nháp hoặc giỏ hàng thử trên storefront: xác nhận cách tính `Tổng tiền` và dòng `Thuế GTGT` khớp đúng quy tắc đã lưu.
- [ ] Xác nhận trạng thái kết nối nhà cung cấp HĐĐT vẫn xanh và không có hóa đơn nào bị phát hành ngoài ý muốn.
- [ ] Đảm bảo báo cáo bàn giao kế toán có đầy đủ **Financial & Tax Disclaimer**.

### Liên kết chéo với `skills/browser-ui/` & `skills/api-mcp/`
- `skills/api-mcp/` → `finance-revenue-margin-report` & `finance-cod-reconciliation`: Đối chiếu doanh thu đơn hàng, thuế trên đơn (`total_tax`) và tiền thu hộ COD qua Commerce API `/com/orders.json`.
- `skills/browser-ui/` → `finance-cashbook-debt-audit`, `admin-ui-locations-inventory-ops` (cờ `Cập nhật thông tin xuất hoá đơn` trên kho).
