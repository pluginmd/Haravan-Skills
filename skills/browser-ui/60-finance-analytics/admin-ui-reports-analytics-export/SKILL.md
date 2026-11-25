---
name: admin-ui-reports-analytics-export
description: "Khai thác & xuất Báo cáo trên Haravan Admin (/admin/reports/dashboard & /admin/reports/listing): Bán hàng đa kênh, Chi tiết khuyến mãi, Lợi nhuận, Tồn kho, Công nợ COD và Báo cáo khách hàng RFM theo bộ lọc ngày/chi nhánh/kênh."
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
    []
  endpoints:
    - "UI /admin/reports/dashboard"
    - "UI /admin/reports/listing"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 100
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

# Haravan Admin UI — Khai Thác & Đọc Báo Cáo Phân Tích (`/admin/reports`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Khai thác chuẩn xác, chỉ đọc (`Read-Only L1`) toàn bộ hệ thống bảng phân tích và danh sách báo cáo có sẵn trên Haravan Admin (`https://{store_domain}/admin/reports/dashboard` và `/admin/reports/listing`) mà không cần API token: đọc KPI bán hàng đa kênh, hiệu quả chi tiết khuyến mãi, báo cáo lợi nhuận gộp (doanh thu trừ giá vốn), tồn kho theo chi nhánh, công nợ COD đối soát đơn vị vận chuyển, và phân tích khách hàng RFM / tỷ lệ quay lại.
- **Phạm vi UI:** Bảng phân tích tổng quan (`/admin/reports/dashboard`), danh sách báo cáo chuyên sâu (`/admin/reports/listing`) và từng báo cáo con theo bộ lọc ngày, chi nhánh, kênh bán hàng, nhân viên. Skill **chỉ đọc và tổng hợp**; không thay đổi bất kỳ cấu hình hay dữ liệu kinh doanh nào.
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Xem đầy đủ toàn bộ nhóm báo cáo (Bán hàng, Tài chính/Lợi nhuận, Kho hàng, Khách hàng, Khuyến mãi, Công nợ COD).
  - **Staff:** Yêu cầu quyền `Báo cáo` tương ứng từng nhóm; đặc biệt báo cáo **Lợi nhuận** yêu cầu thêm quyền `Xem giá vốn sản phẩm`. Nếu báo cáo bị ẩn hoặc cột `Lợi nhuận gộp` hiển thị `--`, dừng lại và ghi nhận thiếu quyền Staff.
- **Yêu cầu Gói dịch vụ Haravan:** Bảng phân tích cơ bản có trên mọi gói; các báo cáo nâng cao (Báo cáo lợi nhuận chi tiết, Phân tích khách hàng RFM, Tùy chỉnh cột/lọc đa chi nhánh) khả dụng từ gói **Pro / Grow / Scale**. Nếu gặp màn hình khóa tính năng yêu cầu nâng gói, ghi nhận và tuyệt đối không bấm nút nâng cấp.
- **Pre-flight Check bắt buộc:**
  1. Kiểm tra phiên đăng nhập qua `admin-ui-session-navigator` tại `/admin/reports/dashboard`.
  2. Xác định rõ khoảng thời gian phân tích (ngày bắt đầu – kết thúc, múi giờ `GMT+7`), kênh bán hàng và chi nhánh mục tiêu trước khi đọc số liệu.
  3. **Tuyên bố tài chính bắt buộc:** Mọi số liệu doanh thu, lợi nhuận, công nợ COD trích xuất từ UI là **Operational Estimate / Reconciliation Aid**, không thay thế sổ cái kế toán hoặc chứng từ đối soát chính thức từ cổng thanh toán/ĐVVC.

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Cross-Origin Iframe (Live-Verified):** `/admin/reports/dashboard` & `/admin/reports/listing` nhúng `https://reports.haravan.app`. Nếu sandbox browser ẩn iframe, tự động chuyển sang bộ báo cáo `skills/api-mcp/60-finance-analytics/` & `90-control-tower-governance/` (`hrv_ops.py`).


| Màn hình / Nhóm Báo cáo | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Bộ lọc & Chỉ số chính |
| :--- | :--- | :--- | :--- |
| Bảng phân tích tổng quan | `/admin/reports/dashboard` | Bộ chọn `Thời gian` (`Hôm nay`, `7 ngày qua`, `30 ngày qua`, `Tùy chọn`), `So sánh kỳ trước`, bộ lọc `Kênh bán hàng`, `Chi nhánh` | Thẻ KPI: `Doanh thu thuần`, `Tổng đơn hàng`, `Giá trị đơn trung bình (AOV)`, `Tỷ lệ khách quay lại`, biểu đồ `Doanh thu theo kênh` |
| Danh sách báo cáo | `/admin/reports/listing` | Các nhóm thẻ: `Báo cáo bán hàng`, `Báo cáo tài chính`, `Báo cáo sản phẩm & tồn kho`, `Báo cáo khách hàng`, `Báo cáo khuyến mãi`, `Báo cáo vận chuyển / COD` | Click từng tên báo cáo để mở trang bảng chi tiết |
| Báo cáo Bán hàng đa kênh | `/admin/reports/listing` → `Bán hàng theo kênh` / `theo thời gian` | Nút `Lọc`, `Hiển thị cột`, `Xuất báo cáo` (bị khóa mặc định với PII/Financial trừ khi duyệt) | `Kênh`, `Số đơn`, `Doanh thu gộp`, `Giảm giá`, `Trả hàng`, `Doanh thu thuần`, `Phí ship`, `Tổng tiền` |
| Báo cáo Lợi nhuận & Khuyến mãi | `/admin/reports/listing` → `Lợi nhuận theo sản phẩm` & `Chi tiết khuyến mãi` | Lọc theo `Khoảng ngày`, `Mã khuyến mãi`, `Loại SP`, `Nhà cung cấp` | `Doanh thu thuần`, `Giá vốn hàng bán (COGS)`, `Lợi nhuận gộp`, `Biên lợi nhuận (%)`, `Số lượt dùng mã`, `Tổng tiền giảm` |
| Báo cáo Tồn kho & Công nợ COD | `/admin/reports/listing` → `Xuất nhập tồn`, `Tồn kho cuối kỳ`, `Công nợ COD` | Lọc theo `Chi nhánh/Kho`, `Nhà vận chuyển (GHN/GHTK/VTP...)`, `Trạng thái đối soát` | `Tồn đầu`, `Nhập`, `Xuất`, `Tồn cuối`, `Giá trị tồn`, `Tiền thu hộ COD`, `Đã đối soát`, `Còn phải thu` |
| Báo cáo Khách hàng (RFM) | `/admin/reports/listing` → `Khách hàng theo thời gian` / `Phân tích RFM` | Lọc theo `Khoảng ngày`, `Kênh`, `Nhóm khách` | `Khách mới`, `Khách quay lại`, `Tỷ lệ quay lại (%)`, `Số lượng khách theo nhóm RFM` (không xuất danh sách SĐT thô) |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `omnichannel_sales_dashboard` | `omnichannel_sales_dashboard` \| `profit_and_promo_report` \| `inventory_valuation_report` \| `cod_debt_reconciliation` \| `customer_rfm_retention` |
| `date_from` | `string` | Có | — | Định dạng `YYYY-MM-DD` (giờ VN), `date_from <= date_to` |
| `date_to` | `string` | Có | — | Định dạng `YYYY-MM-DD`, khoảng đọc khuyến nghị ≤ 90 ngày/lượt để tránh timeout UI |
| `compare_previous_period` | `boolean` | Không | `true` | Bật so sánh cùng kỳ trước trên `/admin/reports/dashboard` |
| `channel_filter` | `array<string>` | Không | `["ALL"]` | Ví dụ `Website`, `POS`, `Harasocial`, `Shopee`, `Lazada`, `TikTok` |
| `location_filter` | `array<string>` | Không | `["ALL"]` | Tên chi nhánh/kho hàng chính xác trên hệ thống |
| `carrier_filter` | `string` | Khi đọc COD | `"ALL"` | Ví dụ `GHN`, `GHTK`, `Viettel Post`, `VNPost` |
| `prepare_export_only` | `boolean` | Không | `false` | `false` (mặc định chỉ đọc bảng UI); nếu người dùng muốn tải Excel, chỉ dừng ở bước cấu hình bộ lọc và bàn giao người dùng tự bấm `Xuất báo cáo` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Đọc Bảng phân tích & Báo cáo Bán hàng đa kênh (`/admin/reports/dashboard`)
1. Điều hướng tới `https://{store_domain}/admin/reports/dashboard`, chờ tất cả biểu đồ và thẻ KPI tải xong (không còn skeleton loading).
2. Bấm bộ chọn `Thời gian` → chọn `Tùy chọn` → nhập `date_from` và `date_to`; nếu `compare_previous_period: true`, tick `So sánh kỳ trước`.
3. Áp dụng bộ lọc `Kênh bán hàng` (`channel_filter`) và `Chi nhánh` (`location_filter`), chờ số liệu cập nhật lại.
4. Đọc và ghi nhận đầy đủ: `Doanh thu gộp`, `Giảm giá`, `Hoàn/Trả hàng`, `Doanh thu thuần`, `Số đơn hàng`, `AOV`, cơ cấu tỷ trọng từng kênh (`Website`, `POS`, `Harasocial`, Sàn TMĐT) và mức tăng/giảm `%` so với kỳ trước.
5. Chụp ảnh màn hình dashboard làm bằng chứng số liệu (`preview_screenshot`).

### Kịch bản 2: Khai thác Báo cáo Chi tiết Khuyến mãi & Lợi nhuận gộp (`/admin/reports/listing`)
1. Mở `/admin/reports/listing`, vào mục `Báo cáo khuyến mãi` → chọn `Chi tiết khuyến mãi` (hoặc `Doanh thu theo mã khuyến mãi`).
2. Thiết lập khoảng ngày `date_from` → `date_to` và lọc kênh bán hàng; đọc bảng Top 10 mã/chương trình theo `Tổng giá trị giảm`, `Số đơn áp dụng`, `Doanh thu mang lại` và tính `Tỷ lệ giảm giá / Doanh thu gộp`.
3. Quay lại `/admin/reports/listing`, mở mục `Báo cáo tài chính` → `Lợi nhuận theo sản phẩm` (hoặc `Lợi nhuận theo thời gian`).
4. Đọc `Doanh thu thuần`, `Giá vốn hàng bán`, `Lợi nhuận gộp`, `Biên lợi nhuận (%)`; gắn cờ cảnh báo cho các SKU/nhóm hàng có `Giá vốn = 0` (chưa nhập giá vốn làm phồng biên lợi nhuận giả) hoặc `Lợi nhuận gộp < 0`.

### Kịch bản 3: Khai thác Báo cáo Xuất-Nhập-Tồn & Giá trị Tồn kho theo chi nhánh
1. Tại `/admin/reports/listing`, mở nhóm `Báo cáo sản phẩm & tồn kho` → chọn `Báo cáo xuất nhập tồn` (hoặc `Tồn kho cuối kỳ`).
2. Lọc đúng `Chi nhánh / Kho` (`location_filter`) và khoảng thời gian chốt kỳ (`date_from` → `date_to`).
3. Đọc tổng hợp `Tồn đầu kỳ`, `SL Nhập`, `SL Xuất`, `Tồn cuối kỳ`, `Tổng giá trị tồn kho` (tính theo giá vốn bình quân) và nhận diện Top SKU tồn kho giá trị lớn nhất hoặc tồn âm.
4. Chụp ảnh bảng tổng hợp, lưu ghi chú các kho có tồn âm cần đối chiếu với `admin-ui-inventory-advanced-ops`.

### Kịch bản 4: Khai thác Báo cáo Công nợ COD theo Nhà vận chuyển
1. Tại `/admin/reports/listing`, mở mục `Báo cáo vận chuyển` → chọn `Công nợ thu hộ COD` (hoặc đối chiếu nhanh tại `/admin/shipments/managecod`).
2. Lọc theo khoảng ngày giao hàng thành công, chọn `Nhà vận chuyển` (`carrier_filter`) và lọc trạng thái `Chưa đối soát` / `Chưa nhận tiền COD`.
3. Tổng hợp số lượng vận đơn và tổng tiền COD chờ thu hộ theo từng hãng vận chuyển (`GHN`, `GHTK`, `Viettel Post`...), tách riêng nhóm quá hạn đối soát (> 7 ngày kể từ ngày giao thành công).
4. Đính kèm tuyên bố tài chính: số liệu là công cụ hỗ trợ đối soát nội bộ, cần khớp với bảng kê chuyển tiền chính thức từ hãng vận chuyển.

### Kịch bản 5: Đọc Báo cáo Khách hàng & Phân tích RFM (Ẩn danh hóa PII)
1. Tại `/admin/reports/listing`, mở mục `Báo cáo khách hàng` → `Khách hàng mới & quay lại` và `Phân tích khách hàng (RFM)` (nếu gói hỗ trợ).
2. Thiết lập khoảng ngày và kênh bán; đọc tỷ lệ `Khách hàng mới` vs `Khách hàng quay lại`, doanh thu đóng góp của từng nhóm và phân bổ số lượng khách theo phân khúc RFM (`VIP`, `Trung thành`, `Có nguy cơ rời bỏ`, `Ngủ đông`).
3. **Tuyệt đối không xuất danh sách SĐT/Email cá nhân**; chỉ trích xuất số liệu tổng hợp ở cấp nhóm (aggregate metrics) để phục vụ ra quyết định chiến dịch CRM.

### Bảng Định Nghĩa Chỉ Số Báo Cáo Haravan (Tránh Hiểu Nhầm Khi Đối Soát)

| Chỉ số trên Haravan UI | Công thức / Định nghĩa vận hành | Lưu ý đối chiếu với Kế toán / Sổ quỹ |
| :--- | :--- | :--- |
| `Doanh thu gộp` (Gross Sales) | `Đơn giá bán × Số lượng` (chưa trừ giảm giá, chưa gồm ship) | Không dùng làm căn cứ tính doanh thu thực nhận |
| `Doanh thu thuần` (Net Sales) | `Doanh thu gộp − Giảm giá − Giá trị trả hàng` | Ghi nhận theo ngày tạo đơn/trả hàng, chưa trừ cước ĐVVC |
| `Lợi nhuận gộp` (Gross Profit) | `Doanh thu thuần − Giá vốn hàng bán (COGS)` | Sai lệch nếu có SKU chưa nhập giá vốn (`Giá vốn = 0đ`) |
| `Công nợ COD` | Tiền ĐVVC thu hộ khách chưa chuyển đối soát về cửa hàng | Phải khớp bảng kê thanh toán chính thức từ GHN/GHTK/VTP |

## 5. Quy trình An toàn 4 Pha (Read-Only Verification Protocol)

1. **Pha 1 — Pre-State & Scope Capture (Chốt bộ lọc & Múi giờ):**
   - Mở `/admin/reports/dashboard` hoặc `/admin/reports/listing`, xác nhận đúng `store_domain` (không nhầm cửa hàng `staging` và `production`).
   - Thiết lập chính xác `date_from`, `date_to` (giờ VN `GMT+7`), bộ lọc `Kênh bán hàng` và `Chi nhánh/Kho`, sau đó chụp `pre_screenshot`.
2. **Pha 2 — Non-Destructive Filter & Read (`mode: read`):**
   - Chỉ thao tác chọn bộ lọc ngày, kênh, chi nhánh, bật/tắt so sánh kỳ trước, sắp xếp cột và chuyển trang bảng báo cáo.
   - Chờ toàn bộ biểu đồ và số liệu cập nhật xong hoàn toàn (không còn skeleton loading) trước khi ghi nhận con số.
   - **Tuyệt đối không thay đổi bất kỳ dữ liệu hay cấu hình nào trên hệ thống**.
3. **Pha 3 — Evidence Screenshot & Redaction Check (Kiểm tra ẩn danh & Tài chính):**
   - Chụp `preview_screenshot` của biểu đồ/bảng tổng hợp làm bằng chứng số liệu.
   - Kiểm tra kỹ không để lộ SĐT, Email hay danh sách khách hàng cá nhân trong output (chỉ xuất chỉ số tổng hợp cấp nhóm).
   - Gắn rõ tuyên bố **Operational Estimate / Reconciliation Aid** cho mọi chỉ số doanh thu, lợi nhuận gộp và công nợ COD.
4. **Pha 4 — Structured Report Delivery & Export Handoff:**
   - Trình bày báo cáo dạng bảng so sánh kỳ `Before → Current` + JSON tổng hợp có cờ cảnh báo bất thường (SKU giá vốn = 0đ, vận đơn COD treo quá hạn).
   - Nếu người dùng cần tải file Excel `.xlsx`/`.csv` thô về máy kế toán, giữ nguyên màn hình đã lọc sẵn và mời người dùng **tự bấm nút `Xuất báo cáo`** trên trình duyệt.

### Checklist Kiểm Định Độ Tin Cậy Số Liệu Báo Cáo (Data Sanity Check)

- [ ] Khoảng ngày đọc ≤ `90 ngày/lượt` để đảm bảo bảng báo cáo tải đầy đủ, không bị cắt trang hoặc timeout.
- [ ] Đã kiểm tra sự khác biệt định nghĩa giữa `Doanh thu gộp` (Gross Sales) và `Doanh thu thuần` (Net Sales = Gộp - Giảm giá - Trả hàng).
- [ ] Khi đọc `Báo cáo lợi nhuận`: đã lọc kiểm tra số lượng SKU có `Giá vốn = 0đ` để cảnh báo sai số biên lợi nhuận.
- [ ] Khi đọc `Công nợ COD`: đã tách rõ nhóm vận đơn `Đang giao` vs `Đã giao thành công > 7 ngày chưa đối soát`.
- [ ] Không tự bấm `Xuất báo cáo` (`export_allowed: false`) và không xuất danh sách PII khách hàng.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Tổng hợp Báo cáo Vận hành (Operational Estimate)

| Chỉ số báo cáo (25/10 – 25/11) | Kỳ trước (Before) | Kỳ hiện tại (Current) | Biến động | Lưu ý đối soát |
| :--- | :--- | :--- | :--- | :--- |
| Doanh thu thuần đa kênh | `412.500.000đ` | `486.200.000đ` | `+17.9%` | Website 52%, POS 31%, Sàn 17% |
| Tổng tiền giảm giá (Khuyến mãi) | `28.400.000đ` | `39.100.000đ` | `+37.7%` | Tỷ lệ giảm = `7.4%` doanh thu gộp |
| Lợi nhuận gộp ước tính | `148.500.000đ` | `171.200.000đ` | `+15.3%` | ⚠️ 12 SKU có giá vốn = 0đ cần kiểm tra |
| Giá trị tồn kho cuối kỳ (3 kho) | `920.000.000đ` | `885.400.000đ` | `-3.8%` | 2 SKU có tồn âm tại Kho HN |
| Công nợ COD chưa đối soát (> 7 ngày) | `14.200.000đ` | `19.850.000đ` | `+39.8%` | Tập trung 23 vận đơn (cần khớp bảng kê ĐVVC) |
| Tỷ lệ khách hàng quay lại (RFM) | `26.4%` | `29.1%` | `+2.7%` | Chỉ số tổng hợp nhóm, không xuất PII |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-reports-analytics-export",
  "mode": "read",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/reports/dashboard",
  "scenario": "omnichannel_sales_dashboard",
  "session_authenticated": true,
  "dry_run": true,
  "pii_redacted": true,
  "export_triggered": false,
  "financial_disclaimer": "Operational Estimate / Reconciliation Aid only — not an official accounting ledger.",
  "date_range": {
    "from": "2026-10-25",
    "to": "2026-11-25",
    "timezone": "Asia/Ho_Chi_Minh"
  },
  "filters_applied": {
    "channels": ["ALL"],
    "locations": ["ALL"]
  },
  "pre_screenshot": "artifacts/reports_dashboard_pre.png",
  "preview_screenshot": "artifacts/reports_dashboard_summary.png",
  "post_screenshot": null,
  "metrics_summary": {
    "net_sales_vnd": 486200000,
    "orders_count": 742,
    "aov_vnd": 655256,
    "discount_total_vnd": 39100000,
    "gross_profit_estimate_vnd": 171200000,
    "overdue_cod_estimate_vnd": 19850000
  },
  "data_quality_warnings": [
    "12 SKUs have unit_cost = 0 VND, inflating estimated gross margin."
  ],
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm trên `/admin/reports`:**
  - `Xuất báo cáo` / `Export Excel` tự động tải dữ liệu tài chính/khách hàng thô ra ngoài khi chưa có yêu cầu trực tiếp của người dùng (`export_allowed: false`).
  - `Nâng cấp gói` trên các báo cáo nâng cao bị khóa theo gói dịch vụ (RFM, Lợi nhuận chi tiết).
  - Bất kỳ thao tác tạo/xóa/chốt kỳ sổ kế toán hoặc nộp tờ khai thuế tại `/admin/etax/declarations`.
- **Financial & Credential Handoff Gate:**
  - Mọi nhận định về doanh thu, lợi nhuận, công nợ COD chỉ mang tính **Operational Estimate / Reconciliation Aid**; không kết luận sai lệch gian lận của ĐVVC/cổng thanh toán khi chưa đối chiếu sao kê gốc.
  - Gặp `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Báo cáo Lợi nhuận bị phồng cao bất thường (Biên lợi nhuận > 80–100%):** Nguyên nhân phổ biến là sản phẩm mới tạo chưa nhập `Giá vốn` (mặc định `0đ`). Agent phải rà soát cột `Giá vốn = 0` và cảnh báo ngay để tránh đọc sai biên lợi nhuận thực tế.
2. **Chênh lệch doanh thu giữa `Bảng phân tích` và tổng đơn ở `/admin/orders`:** `Doanh thu thuần` trong báo cáo tính theo **ngày ghi nhận doanh thu / hoàn trả** và đã trừ `Giảm giá + Trả hàng + Thuế/Phí ship` (tùy bộ lọc), trong khi `/admin/orders` tính theo `Ngày tạo đơn`. Agent phải giải thích rõ định nghĩa cột khi đối chiếu.
3. **Báo cáo khoảng thời gian dài (> 6 tháng) tải chậm hoặc báo timeout:** Chia nhỏ kỳ đọc thành từng tháng/quý (≤ 90 ngày/lượt) thay vì để trình duyệt treo vô hạn.
4. **Nhân viên (Staff) không thấy mục `Báo cáo tài chính` / `Lợi nhuận`:** Do thiếu quyền `Xem giá vốn` hoặc `Báo cáo tài chính` trong `/admin/settings/group_permissions`; dừng và báo rõ hạng mục quyền cần Owner cấp nếu cần xem.
5. **Đơn hủy/trả hàng phát sinh sang tháng sau làm thay đổi số kỳ trước:** Báo cáo Haravan ghi nhận hoàn trả theo ngày phát sinh bút toán trả hàng; luôn ghi chú ngày chốt ảnh chụp (`as_of_timestamp`) khi gửi báo cáo định kỳ.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Chính sách Rollback & Kiểm chứng Số liệu (Read-Only L1)
- **Rollback thủ công:** Không áp dụng — skill hoạt động ở chế độ `L1 mode: read`, tuyệt đối không ghi, xóa hay chỉnh sửa bất kỳ dữ liệu kinh doanh, bút toán sổ quỹ hoặc cấu hình báo cáo nào.
- **Lưu trữ bằng chứng đối soát:** Khi gửi báo cáo cho Ban giám đốc hoặc Kế toán, luôn đính kèm `preview_screenshot`, khung ngày `date_from` → `date_to` (`GMT+7`), bộ lọc kênh/chi nhánh đã áp dụng và dấu thời gian chụp (`as_of_timestamp`) để có thể tái lập lại đúng con số khi đối chiếu sau này.
- **Quy trình bàn giao Export thủ công:** Nếu bộ phận kế toán cần file `.xlsx` chi tiết để chạy pivot/đối soát chứng từ gốc, Agent thiết lập sẵn đúng bộ lọc trên màn hình và mời người dùng tự bấm `Xuất báo cáo` trên trình duyệt.

### Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan
- Phân tích sâu doanh thu đa kênh, biên lợi nhuận, tỷ lệ hoàn trả, ROI khuyến mãi, đối soát COD & tổng hợp thuế VAT qua API: `skills/api-mcp/60-finance-analytics/finance-sales-by-channel-omni`, `finance-profit-margin-analyzer`, `finance-refund-rate-analysis`, `finance-aov-discount-roi`, `finance-cod-reconciliation`, `finance-tax-vat-summary`.
- Báo cáo vận hành định kỳ (Daily Briefing / Weekly Business Review / Monthly Close): `skills/api-mcp/90-control-tower-governance/ops-daily-morning-briefing`, `ops-weekly-business-review`, `ops-monthly-financial-close`.
- Đối chiếu sổ quỹ, công nợ, hóa đơn điện tử & thu hộ COD trên UI: `skills/browser-ui/60-finance-analytics/finance-cashbook-debt-audit`, `skills/browser-ui/95-admin-ui-browser/admin-ui-tax-einvoice-accounting`, `skills/browser-ui/95-admin-ui-browser/admin-ui-shipments-cod-mass-fulfill`.
