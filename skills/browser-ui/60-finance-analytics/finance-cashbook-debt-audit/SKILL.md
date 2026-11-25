---
name: finance-cashbook-debt-audit
description: "Rà soát Sổ quỹ thu chi (/admin/accounting/transactions) và Công nợ (/admin/accounting/debts) để phát hiện khoản treo quá hạn."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 60-finance-analytics
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: admin_ui
  scopes:
    - com.read_orders
  endpoints:
    - "UI /admin/accounting/transactions"
    - "UI /admin/accounting/debts"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 1000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: financial
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---

# Haravan Cashbook & Payables/Receivables Debt Audit

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Kiểm toán chỉ đọc 2 phân hệ tài chính vận hành trên Haravan Admin (`*.myharavan.com/admin`): **Sổ quỹ thu chi** (`/admin/accounting/transactions`) và **Công nợ Phải thu / Phải trả** (`/admin/accounting/debts`, `/admin/accounting/debts/{id}`).
- **Lý do bắt buộc dùng Browser UI:** Haravan Commerce API không cung cấp endpoint đọc đầy đủ sổ quỹ thu chi theo ca POS/chi nhánh, phân loại phiếu thu/chi (`PT...`/`PC...`) và chi tiết tuổi nợ khách hàng B2B, nhà cung cấp hay đơn vị vận chuyển.
- **Mục tiêu nghiệp vụ (`layer: L1`, `mode: read`, `pii_level: financial`):** Cung cấp **Operational Estimate / Reconciliation Aid** định kỳ cho chủ shop và kế toán: phát hiện phiếu chi lớn thiếu chứng từ, phiếu chưa phân loại lý do, dấu hiệu lệch ca tiền mặt POS và công nợ phải thu/phải trả treo quá hạn — **tuyệt đối không tạo/sửa/hủy phiếu hay tất toán công nợ**.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền xem sổ quỹ toàn chuỗi và công nợ tổng hợp.
  - **Staff:** Yêu cầu quyền **Xem Sổ quỹ & Công nợ** trong nhóm quyền **Sổ quỹ / Tài chính** (`/admin/settings/group_permissions`). Nhân viên bán hàng/CSKH thông thường bị ẩn hoàn toàn menu `Sổ quỹ`.
  - **Giới hạn gói dịch vụ:** Phân hệ Sổ quỹ đa chi nhánh và Công nợ đầy đủ khả dụng trên các gói Haravan Retail/Omnichannel/Grow/Scale; nếu chỉ thấy giao diện giới thiệu gói, dừng ngay.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/accounting/transactions`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Chờ 4 thẻ KPI tổng quan (`Quỹ đầu kỳ`, `Tổng thu`, `Tổng chi`, `Tồn quỹ cuối kỳ`) tải hoàn tất trước khi lọc dữ liệu.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/accounting/transactions` | Tổng quan Sổ quỹ | `Tạo phiếu thu` (HARD-BLOCKED), `Tạo phiếu chi` (HARD-BLOCKED), `Xuất file` (HARD-BLOCKED), `Lọc` | 4 thẻ chỉ số: `Quỹ đầu kỳ`, `Tổng thu`, `Tổng chi`, `Tồn quỹ cuối kỳ` |
| `/admin/accounting/transactions` | Bảng danh sách Phiếu thu/chi | Bộ lọc `Chi nhánh`, `Loại phiếu` (`Thu`/`Chi`), `Phương thức` (`Tiền mặt`/`Chuyển khoản`/`Quẹt thẻ`), `Thời gian`, `Trạng thái` | Cột: Mã phiếu (`PT...`/`PC...`), Thời gian ghi nhận, Loại thu/chi (Lý do), Đối tượng, Giá trị, Phương thức thanh toán, Chi nhánh, Trạng thái (`Hoàn thành`/`Đã hủy`) |
| `/admin/accounting/debts` | Danh sách Công nợ | Tab `Phải thu` / `Phải trả` (hoặc lọc theo `Khách hàng`, `Nhà cung cấp`, `Nhà vận chuyển`), `Lọc`, `Tìm kiếm` | Cột: Đối tượng công nợ, Nợ đầu kỳ, Phát sinh tăng, Phát sinh giảm, Dư nợ cuối kỳ, Hạn thanh toán |
| `/admin/accounting/debts/{id}` | Chi tiết Công nợ đối tượng | `Thanh toán` (HARD-BLOCKED), `Tạo phiếu thu-chi` (HARD-BLOCKED) | Lịch sử các chứng từ đơn hàng bán sỉ, phiếu nhập kho, phiếu thu/chi cấu thành số dư nợ hiện tại |

### Nguyên tắc Đối soát Sổ quỹ & Công nợ trên Haravan
- **Cơ sở ghi nhận Cash Basis:** Sổ quỹ chỉ phản ánh tiền thực thu/thực chi theo phiếu `PT...`/`PC...`; không trùng khớp 1:1 với Báo cáo doanh thu theo ngày đặt đơn (Accrual Basis).
- **Quy ước Dư nợ âm (`-`):** Dư nợ âm trên tab `Phải thu` thường là khoản khách đặt cọc/ứng trước; dư nợ âm trên tab `Phải trả` là khoản shop đã thanh toán trước cho nhà cung cấp.
- **Phạm vi Operational Aid:** Mọi bảng kê trích xuất từ UI chỉ dùng làm tài liệu đối soát vận hành hỗ trợ kế toán, bắt buộc đính kèm Financial Disclaimer và đối chiếu sao kê ngân hàng gốc.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `full_cashbook_debt_audit` | `cashbook_summary_audit` \| `large_expense_screening` \| `pos_cash_vs_bank_check` \| `receivables_overdue_audit` \| `payables_overdue_audit` \| `full_cashbook_debt_audit` |
| `period_days` | `integer` | Không | `30` | Khoảng thời gian rà soát (`7`, `14`, `30`, `60`, `90` ngày; khuyến nghị ≤ 30 ngày/lượt) |
| `location_filter` | `string` | Không | `all` | Tên chi nhánh/cửa hàng POS cụ thể hoặc `all` |
| `large_expense_threshold_vnd` | `number` | Không | `5000000` | Ngưỡng gắn cờ kiểm tra phiếu chi lớn (`>= 100000`) |
| `overdue_days_threshold` | `integer` | Không | `15` | Ngưỡng số ngày công nợ treo bị đánh dấu quá hạn (`1..180`) |
| `max_records` | `integer` | Không | `1000` | Giới hạn bản ghi đọc kiểm toán tối đa trong 1 lượt |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Kiểm toán Tổng quan Sổ quỹ theo Chi nhánh & Phương thức (`cashbook_summary_audit`)
- **Khi nào dùng:** Chốt dòng tiền vận hành định kỳ tuần/tháng theo từng chi nhánh và phương thức thanh toán.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/accounting/transactions`, chọn bộ lọc `Thời gian` = `period_days` và `Chi nhánh` = `location_filter`.
  2. Chụp `pre_screenshot` ghi nhận 4 chỉ số tổng hợp: `Quỹ đầu kỳ`, `Tổng thu`, `Tổng chi`, `Tồn quỹ cuối kỳ`.
  3. Kiểm tra đẳng thức sổ quỹ (`Quỹ đầu kỳ + Tổng thu - Tổng chi = Tồn quỹ cuối kỳ`) và lọc tách cơ cấu dòng tiền theo `Phương thức` (`Tiền mặt` vs `Chuyển khoản` vs `Quẹt thẻ/QR`).
  4. Phát hiện chi nhánh có `Tồn quỹ tiền mặt` tích tụ bất thường (dấu hiệu chưa làm phiếu nộp tiền mặt về quỹ tổng/ngân hàng).
- **Điểm dừng an toàn:** Chỉ đọc tổng quan; tuyệt đối không bấm `Tạo phiếu thu`, `Tạo phiếu chi` hay `Xuất file`.

### Kịch bản 2: Sàng lọc Phiếu chi lớn, Thiếu phân loại & Phiếu hủy bất thường (`large_expense_screening`)
- **Khi nào dùng:** Kiểm soát nội bộ các khoản chi vượt hạn mức, phát hiện phiếu chi thiếu chứng từ hoặc có dấu hiệu ghi trùng.
- **Thao tác từng bước:**
  1. Tại `/admin/accounting/transactions`, lọc `Loại phiếu` = `Phiếu chi` trong `period_days` ngày (quét tối đa `max_records: 1000` dòng, chỉ đọc).
  2. Rà soát toàn bộ phiếu chi có giá trị `>= large_expense_threshold_vnd`: ghi nhận Mã phiếu (`PC...`), Ngày, Lý do chi, Giá trị, Phương thức, Ghi chú chứng từ.
  3. Gắn cờ kiểm tra 3 nhóm rủi ro vận hành:
     - **Phiếu chi thiếu lý do / ghi chú chứng từ:** Mục `Loại thu/chi` để `Khác` hoặc mô tả trống.
     - **Phiếu chi trùng số tiền trong cùng ngày:** Nghi vấn nhập lặp 2 lần cùng 1 khoản thanh toán.
     - **Phiếu `Đã hủy` lặp lại nhiều lần:** Cần kế toán kiểm tra lại quy trình lập và duyệt chi.
- **Điểm dừng an toàn:** Chỉ lập danh sách mã phiếu cần kiểm tra; không bấm `Chỉnh sửa` hay `Hủy phiếu`.

### Kịch bản 3: Đối chiếu chênh lệch Ca POS / Tiền mặt vs Doanh thu Báo cáo (`pos_cash_vs_bank_check`)
- **Khi nào dùng:** Chủ shop thấy tồn quỹ tiền mặt tại cửa hàng khác với báo cáo doanh thu POS trong cùng kỳ.
- **Thao tác từng bước:**
  1. Lọc Sổ quỹ theo từng `Chi nhánh` POS và phương thức `Tiền mặt`, đối chiếu các phiếu `Thu tiền bán hàng` với các phiếu `Chi hoàn tiền trả hàng` và `Nộp tiền về quỹ tổng`.
  2. Giải thích rõ chênh lệch giữa **Sổ quỹ (`Cash Basis`)** và **Báo cáo Doanh thu (`Accrual Basis`)** do đơn COD chưa đối soát và đơn chuyển khoản chưa ghi nhận thu tiền.
  3. Liệt kê các ngày phát sinh chi tiền mặt lẻ lớn tại quầy POS để quản lý cửa hàng đối chiếu hóa đơn giấy.
- **Điểm dừng an toàn:** Không điều chỉnh số dư quỹ trên giao diện Admin.

### Kịch bản 4: Kiểm toán Công nợ Phải thu quá hạn (Khách hàng B2B & NVC COD) (`receivables_overdue_audit`)
- **Khi nào dùng:** Theo dõi công nợ đại lý B2B và tiền thu hộ COD từ nhà vận chuyển bị treo quá hạn.
- **Thao tác từng bước:**
  1. Chuyển sang `https://{store_domain}/admin/accounting/debts`, chọn tab **Phải thu** (lọc theo `Khách hàng` và `Nhà vận chuyển`), chụp `preview_screenshot`.
  2. Sắp xếp theo `Dư nợ cuối kỳ` giảm dần; mở xem chỉ đọc `/admin/accounting/debts/{id}` cho các đối tượng có khoản nợ treo quá `overdue_days_threshold` ngày.
  3. Phân tách rõ **Công nợ Khách sỉ B2B** (đã che SĐT/MST) và **Công nợ NVC COD** (đối chiếu chéo với `/admin/shipments/managecod`).
- **Điểm dừng an toàn:** **TUYỆT ĐỐI KHÔNG bấm `Thanh toán` hay `Tạo phiếu thu-chi`**.

### Kịch bản 5: Kiểm toán Công nợ Phải trả quá hạn (Nhà cung cấp) & Bàn giao Kế toán (`payables_overdue_audit`)
- **Khi nào dùng:** Chuẩn bị lịch thanh toán nhà cung cấp và bàn giao báo cáo đối soát tài chính cuối kỳ.
- **Thao tác từng bước:**
  1. Tại `/admin/accounting/debts`, chuyển sang tab **Phải trả** (Nhà cung cấp).
  2. Liệt kê các Nhà cung cấp có `Dư nợ cuối kỳ > 0` sắp đến hạn hoặc quá `overdue_days_threshold` ngày; xem chỉ đọc phiếu nhập kho cấu thành dư nợ.
  3. Tổng hợp bảng bàn giao cho kế toán kèm **Financial Disclaimer** bắt buộc và che toàn bộ số tài khoản ngân hàng/dữ liệu nhạy cảm.
- **Điểm dừng an toàn:** Không bấm tất toán hay điều chỉnh công nợ; bàn giao nguyên trạng để kế toán đối chiếu ủy nhiệm chi gốc.

## 5. Quy trình An toàn 4 Pha (4-Phase Read-Only UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Kiểm tra quyền Tài chính)
- Mở `/admin/accounting/transactions`, xác nhận phiên đăng nhập hợp lệ và tài khoản có quyền xem Sổ quỹ.
- Thiết lập bộ lọc `period_days` và `location_filter`, chụp `pre_screenshot` 4 thẻ KPI tổng quan.

### Pha 2 — Read-Only Filter & Extraction (Kiểm toán không ghi dữ liệu)
- Rà soát phiếu chi lớn, phiếu thiếu phân loại và chuyển sang `/admin/accounting/debts` kiểm tra công nợ Phải thu/Phải trả.
- Tuyệt đối không bấm `Tạo phiếu thu`, `Tạo phiếu chi`, `Thanh toán` hay `Xuất file`.

### Pha 3 — Screenshot, Financial PII Redaction & Disclaimer Gate
- Chụp `preview_screenshot` màn hình Công nợ làm bằng chứng đối chiếu.
- Che 100% số tài khoản ngân hàng, MST cá nhân, SĐT/email và đính kèm **Financial Disclaimer** bắt buộc.

### Pha 4 — Session Audit & Read-Only Closure (Chốt phiên chỉ đọc)
- Xác nhận `saved_verified: false`, `mode: read`, không phát sinh bất kỳ chứng từ tài chính nào.
- Bàn giao bảng tổng hợp cho bộ phận kế toán đối chiếu sao kê ngân hàng và chứng từ gốc.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Tóm tắt Kiểm toán Sổ quỹ & Công nợ (Current UI State → Accounting Action)

| Hạng mục rà soát (30 ngày) | Số liệu trên Haravan UI (Before / Current) | Điểm bất thường phát hiện | Hành động đề xuất cho Kế toán (After / Target) |
| :--- | :--- | :--- | :--- |
| Tồn quỹ đầu kỳ → Cuối kỳ | `120.0M₫` → `185.4M₫` (Thu `410.2M₫` / Chi `344.8M₫`) | Tồn tiền mặt Chi nhánh Q1 tăng cao (`42.5M₫`) | Kiểm tra phiếu nộp quỹ tiền mặt cuối tháng |
| Phiếu chi lớn (`>= 5,000,000₫`) | `6 phiếu` (Tổng `192,000,000₫`) | `2 phiếu` (`PC0412`, `PC0419`) trống ghi chú chứng từ | Đối chiếu hóa đơn đỏ / ủy nhiệm chi gốc |
| Công nợ Phải thu quá hạn (> 15 ngày) | `4 đối tượng` (Tổng `38,500,000₫`) | `2` đại lý B2B + `2` kỳ COD Viettel Post | Gửi biên bản đối chiếu B2B & kiểm tra `managecod` |
| Công nợ Phải trả quá hạn | `1 nhà cung cấp` (`22,000,000₫`) | Quá hạn 8 ngày theo phiếu nhập kho | Kế toán đối chiếu UNC trước khi bấm tất toán |

> **Financial Disclaimer:** Báo cáo này là công cụ hỗ trợ đối soát vận hành (**Operational Estimate / Reconciliation Aid**) đọc từ giao diện Haravan Admin, **không phải sổ cái kế toán chính thức** và không cấu thành bằng chứng sai lệch tài chính hay sai lệch thanh toán trước khi kế toán đối chiếu chứng từ và sao kê ngân hàng gốc.

### JSON Execution Log Schema

```json
{
  "skill": "finance-cashbook-debt-audit",
  "scenario": "full_cashbook_debt_audit",
  "mode": "read",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/accounting/transactions",
  "screenshots": {
    "pre": "artifacts/cashbook_pre.png",
    "preview": "artifacts/debts_overview.png",
    "post": null
  },
  "financial_disclaimer_included": true,
  "audit_summary": {
    "period_days": 30,
    "location_filter": "all",
    "opening_balance_vnd": 120000000,
    "total_receipts_vnd": 410200000,
    "total_payments_vnd": 344800000,
    "closing_balance_vnd": 185400000,
    "flagged_large_expenses_count": 6,
    "unclassified_vouchers_count": 2,
    "cancelled_vouchers_anomaly_count": 1,
    "overdue_receivables_count": 4,
    "overdue_receivables_vnd": 38500000,
    "overdue_payables_count": 1,
    "overdue_payables_vnd": 22000000,
    "cash_basis_vs_accrual_note_included": true
  },
  "pii_redacted": true,
  "saved_verified": false
}
```

### Checklist Bàn giao Bộ phận Kế toán & Chủ cửa hàng
- [ ] Đã đính kèm **Financial Disclaimer** (Operational Estimate / Reconciliation Aid) ở đầu và cuối báo cáo.
- [ ] Đã kiểm tra đẳng thức `Quỹ đầu kỳ + Tổng thu - Tổng chi = Tồn quỹ cuối kỳ` theo từng chi nhánh POS.
- [ ] Đã liệt kê đầy đủ mã phiếu chi lớn thiếu ghi chú chứng từ (`PC...`) để kế toán đối chiếu hóa đơn/UNC gốc.
- [ ] Đã tách riêng công nợ NVC COD (đối chiếu `/admin/shipments/managecod`) khỏi công nợ khách sỉ B2B.
- [ ] Xác nhận 100% phiên chỉ đọc: không tạo/sửa/hủy phiếu thu chi, không tất toán công nợ, không xuất file raw.

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click trong L1 Read-Only):**
  - `Tạo phiếu thu`, `Tạo phiếu chi`, `Chỉnh sửa`, `Hủy phiếu` tại `/admin/accounting/transactions`.
  - `Thanh toán`, `Tất toán công nợ`, `Điều chỉnh công nợ` tại `/admin/accounting/debts`.
  - `Xuất file` (tải bảng kê tài chính/PII thô — vi phạm `export_allowed: false`).
- **Credential & Financial PII Handoff Gates:**
  - Gặp `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.
  - Tuân thủ `pii_level: financial`: tuyệt đối không ghi số tài khoản ngân hàng, MST cá nhân, SĐT/email đầy đủ vào báo cáo text hay JSON.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Số liệu Sổ quỹ lệch với Báo cáo Doanh thu:** Tình huống phổ biến do khác biệt kế toán tiền mặt (`Cash Basis`) vs thời điểm tạo đơn (`Accrual Basis`) → Luôn giải thích rõ trong báo cáo để tránh gây hoang mang cho chủ shop.
2. **Thiếu quyền Staff (403 hoặc ẩn hoàn toàn menu `Sổ quỹ`):** Tài khoản nhân viên thường không có quyền tài chính → Báo Chủ shop kiểm tra phân quyền **Sổ quỹ & Công nợ** tại `/admin/settings/group_permissions`.
3. **Spinner tải lâu hoặc timeout khi lọc khoảng thời gian > 90 ngày:** Thu hẹp `period_days` xuống từng chu kỳ 30 ngày và lọc tách theo từng chi nhánh (`location_filter`).
4. **Dư nợ hiển thị số âm (`-`) trên tab Phải thu hoặc Phải trả:** Thường do khách đặt cọc trước (ứng trước tiền hàng) hoặc shop đã thanh toán trước cho nhà cung cấp trước khi lập phiếu nhập kho → Ghi nhận rõ là khoản ứng trước, không đánh nhầm thành nợ quá hạn.
5. **Phiếu thu tự động sinh từ đơn POS bị hủy nhưng chưa đối trừ:** Đánh dấu mã phiếu liên kết đơn hàng để kế toán đối chiếu với lịch sử hủy đơn tại `/admin/orders`.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: false`):** Không áp dụng vì skill vận hành 100% ở chế độ `L1 mode: read`, không ghi, sửa hay xóa bất kỳ chứng từ tài chính nào.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/60-finance-analytics/finance-cod-reconciliation` (API): Đối chiếu chi tiết doanh thu và COD từng đơn hàng qua `GET /com/orders.json`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-shipments-cod-mass-fulfill` (UI): Đối soát chi tiết vận đơn COD chưa về tiền theo từng NVC tại `/admin/shipments/managecod`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-tax-einvoice-accounting` (UI): Rà soát đồng bộ Thuế GTGT, Hóa đơn điện tử (`/admin/settings/vat_setting`) và Sổ kế toán (`/admin/etax/revenue_ledgers`).
