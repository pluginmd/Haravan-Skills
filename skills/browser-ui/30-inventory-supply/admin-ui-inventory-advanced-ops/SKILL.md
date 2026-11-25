---
name: admin-ui-inventory-advanced-ops
description: "Vận hành Tồn kho Nâng cao trên Haravan Admin (/admin/products/inventories & phân hệ kho): Đặt hàng nhập PO, Nhập hàng cập nhật giá vốn, Trả hàng NCC, Điều chuyển giữa 2 kho + duyệt xuất/nhận, Kiểm kho barcode/Excel và Cân bằng kho."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 30-inventory-supply
layer: L2
wave: 2
mode: proposal
risk: high
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/products/inventories"
    - "UI /admin/purchase_orders"
    - "UI /admin/purchase_receives"
    - "UI /admin/purchase_returns"
    - "UI /admin/transfers"
    - "UI /admin/inventory_adjustments"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 50
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

# Haravan Admin UI — Vận Hành Tồn Kho Nâng Cao (`/admin/products/inventories`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Thực thi chuẩn hóa và an toàn các nghiệp vụ chuỗi cung ứng và quản trị kho chuyên sâu trực tiếp trên Haravan Admin (những thao tác ảnh hưởng trực tiếp tới số lượng tồn khả dụng, giá vốn bình quân gia quyền `MAC` và công nợ nhà cung cấp): lập đơn Đặt hàng nhập (`PO`), Nhập hàng vào kho & cập nhật giá vốn, Trả hàng nhà cung cấp (`NCC`), Điều chuyển tồn kho giữa 2 chi nhánh/kho (lập phiếu → duyệt xuất → xác nhận nhận), và Kiểm kho bằng Barcode/Excel kèm Cân bằng kho.
- **Phạm vi UI:** Phân hệ `Sản phẩm > Tồn kho` (`/admin/products/inventories`) và các phân hệ kho nâng cao (`Đặt hàng nhập`, `Nhập hàng`, `Trả hàng nhập`, `Điều chuyển`, `Kiểm kho`). Không bao gồm thêm/xóa địa chỉ kho (dùng `admin-ui-locations-inventory-ops`).
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Toàn quyền thao tác trên tất cả kho hàng, xem/sửa giá vốn nhập và duyệt cân bằng kho.
  - **Staff:** Yêu cầu quyền chi tiết theo từng phân hệ kho (`Quản lý tồn kho`, `Đặt hàng nhập`, `Nhập hàng`, `Điều chuyển`, `Kiểm kho`, `Xem giá vốn`) và được phân quyền đúng kho nguồn/kho đích. Nếu nút `Cân bằng kho` hoặc cột `Giá nhập` bị ẩn, dừng ngay và báo thiếu quyền.
- **Yêu cầu Gói dịch vụ Haravan:** Quản lý tồn kho đa chi nhánh, phiếu Điều chuyển, Đặt hàng nhập/Nhập hàng và Kiểm kho nâng cao yêu cầu gói **Pro / Grow / Scale** (hoặc đã kích hoạt phân hệ Quản lý kho nâng cao). Nếu màn hình hiện banner yêu cầu nâng gói, dừng lại và thông báo rõ cho người dùng (không bấm nút nâng gói).
- **Pre-flight Check bắt buộc:**
  1. Xác minh phiên đăng nhập qua `admin-ui-session-navigator` và kiểm tra đúng cửa hàng đích.
  2. Chốt danh sách `Kho` đang hoạt động tại `/admin/settings/locations` để tránh chọn nhầm kho.
  3. **Bắt buộc xác nhận ở lượt riêng (`separate_turn: true`)** trước khi bấm bất kỳ nút nào làm biến động tồn kho thực tế hoặc giá vốn (`Nhập kho`, `Duyệt xuất/nhận điều chuyển`, `Cân bằng kho`, `Trả hàng NCC`).

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/products/inventories` — Tab: `Tất cả`; Nút: `Xuất file`, `Lưu`; Cột: `Sản phẩm/Biến thể`, `SKU`, `Barcode`, `Cập nhật tồn kho`, `Tồn kho`.


| Phân hệ kho | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Cột / Bộ lọc chính |
| :--- | :--- | :--- | :--- |
| Tồn kho tổng hợp | `/admin/products/inventories` | Bộ lọc `Kho hàng`, `Loại SP`, `Nhà cung cấp`; Nút `Xuất dữ liệu`, `Lịch sử tồn kho` | `Sản phẩm/SKU`, `Tồn kho`, `Đang giao dịch`, `Có thể bán`, `Hàng đang về` |
| Đặt hàng nhập (PO) | Menu kho → `Đặt hàng nhập` (`/admin/purchase_orders`) | Nút `Tạo đơn đặt hàng nhập`, `Duyệt đơn`, `Nhập hàng`, `Hủy đơn` | `Mã đơn đặt`, `Nhà cung cấp`, `Kho nhập`, `Trạng thái`, `Ngày dự kiến`, `Tổng tiền` |
| Nhập hàng (Receive) | Menu kho → `Nhập hàng` (`/admin/purchase_receives`) | Nút `Tạo đơn nhập hàng`, `Nhập hàng vào kho`, `Thanh toán NCC`, `Chi phí nhập hàng` | `Mã phiếu nhập`, `NCC`, `Kho nhập`, `SL nhập`, `Đơn giá nhập`, `Thành tiền` |
| Trả hàng NCC | Menu kho → `Trả hàng nhập` (`/admin/purchase_returns`) | Nút `Tạo phiếu trả hàng`, `Hoàn trả hàng`, `Nhận tiền hoàn từ NCC` | `Mã phiếu trả`, `Mã phiếu nhập gốc`, `Kho xuất trả`, `SL trả`, `Giá trị trả` |
| Điều chuyển kho | Menu kho → `Điều chuyển` (`/admin/transfers`) | Nút `Tạo phiếu điều chuyển`, `Chuyển hàng` (xuất kho nguồn), `Nhận hàng` (nhập kho đích) | `Mã phiếu`, `Kho xuất`, `Kho nhận`, `Trạng thái` (`Chờ chuyển`/`Đang chuyển`/`Đã nhận`), `SL` |
| Kiểm kho & Cân bằng | Menu kho → `Kiểm kho` (`/admin/inventory_adjustments`) | Nút `Tạo phiếu kiểm kho`, `Nhập file Excel`, `Quét mã vạch`, `Lưu nháp`, `Cân bằng kho` | `SKU`, `Tồn hệ thống`, `Tồn thực tế`, `SL lệch`, `Giá trị lệch`, `Lý do` |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `create_po` | `create_po` \| `receive_goods_cost` \| `return_to_supplier` \| `transfer_between_warehouses` \| `stocktake_reconcile` |
| `source_location` | `string` | Có | — | Tên kho chính xác như trên Haravan (kho nhập, kho xuất hoặc kho kiểm) |
| `destination_location` | `string` | Khi điều chuyển | `""` | Khác `source_location`, phải tồn tại trong danh sách kho đang hoạt động |
| `supplier_name` | `string` | Khi PO/Nhập/Trả | `""` | Tên Nhà cung cấp đã khai báo trên hệ thống |
| `items` | `array<object>` | Có | `[]` | Tối đa `50` dòng SKU (`max_records: 50`); mỗi dòng gồm `sku`, `qty` (`>= 0`), `unit_cost_vnd` (khi nhập) |
| `landed_cost_vnd` | `number` | Không | `0` | Chi phí vận chuyển/nhập hàng phân bổ vào giá vốn (`>= 0`) |
| `stocktake_excel_path` | `string` | Khi kiểm Excel | `""` | File `.xlsx` đúng mẫu kiểm kho Haravan gồm cột `SKU` và `Số lượng thực tế` |
| `reason_note` | `string` | Có | — | Lý do nghiệp vụ rõ ràng (ví dụ `Nhap hang dot 11/2026`, `Kiem ke dinh ky thang 11`) |
| `dry_run` | `boolean` | Không | `true` | Luôn `true` ở lượt 1; chỉ áp dụng ở lượt 2 sau xác nhận tường minh (`separate_turn: true`) |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Lập đơn Đặt hàng nhập (PO) cho Nhà cung cấp
1. Điều hướng tới phân hệ `Đặt hàng nhập`, bấm nút `Tạo đơn đặt hàng nhập`.
2. Chọn `Nhà cung cấp` (`supplier_name`), chọn `Kho nhập` (`source_location`) và thiết lập `Ngày dự kiến nhận hàng`.
3. Tại ô tìm sản phẩm, thêm từng SKU theo `items`, điền `Số lượng đặt`, `Đơn giá nhập`, `Chiết khấu` (nếu có) và `Thuế VAT` theo thỏa thuận NCC.
4. Nhập `Mã tham chiếu` và `Ghi chú` (`reason_note`); kiểm tra tổng số lượng đặt và tổng giá trị PO.
5. **Dừng trước khi bấm `Đặt hàng` / `Duyệt đơn`** (có thể bấm `Lưu nháp` nếu người dùng muốn giữ bản nháp), chụp ảnh preview và chờ xác nhận lượt riêng.

### Kịch bản 2: Nhập hàng vào kho & Cập nhật Giá vốn bình quân (`MAC`)
1. Mở đơn PO đã duyệt (bấm `Nhập hàng`) hoặc vào `Nhập hàng` → `Tạo đơn nhập hàng` trực tiếp.
2. Xác nhận đúng `Kho nhập` và `Nhà cung cấp`; nhập `Số lượng thực nhận` cho từng SKU (hỗ trợ nhập một phần nếu NCC giao thiếu).
3. Kiểm tra kỹ `Đơn giá nhập` từng SKU và bấm `Thêm chi phí` (nếu có `landed_cost_vnd` như phí vận tải/bốc xếp) để Haravan phân bổ vào **giá vốn bình quân gia quyền** chính xác.
4. **Dừng tuyệt đối trước nút `Nhập kho` / `Xác nhận nhập hàng`**, chụp ảnh bảng SKU + đơn giá + tổng tiền nhập để người dùng đối chiếu hóa đơn đỏ/phiếu giao của NCC ở lượt riêng trước khi xác nhận.

### Kịch bản 3: Trả hàng Nhà cung cấp (Hàng lỗi / Giao sai quy cách)
1. Vào phân hệ `Trả hàng nhập` → bấm `Tạo phiếu trả hàng` (hoặc mở phiếu `Nhập hàng` gốc → bấm `Hoàn trả hàng`).
2. Chọn đúng `Kho xuất trả`, điền `Số lượng trả` cho từng SKU bị lỗi (kiểm tra `SL trả <= Tồn khả dụng tại kho`).
3. Kiểm tra `Giá trị hoàn trả` khớp giá nhập gốc, nhập `Lý do trả hàng` chi tiết (ví dụ `Loi duong may - Bien ban NCC #04`).
4. **Dừng trước nút `Hoàn trả` / `Xác nhận trả hàng`**, chụp ảnh preview gửi người dùng duyệt ở lượt riêng trước khi trừ tồn kho và giảm công nợ NCC.

### Kịch bản 4: Điều chuyển tồn kho giữa 2 kho (Lập phiếu → Duyệt Xuất → Xác nhận Nhận)
1. Vào phân hệ `Điều chuyển` → bấm `Tạo phiếu điều chuyển`.
2. Chọn `Kho xuất` (`source_location`) và `Kho nhận` (`destination_location`); thêm danh sách SKU và `Số lượng chuyển` (xác minh không vượt `Có thể bán` của kho xuất).
3. Chụp ảnh phiếu ở trạng thái nháp; sau khi người dùng xác nhận ở lượt riêng, bấm `Tạo phiếu` → bấm `Chuyển hàng` để trừ tồn kho xuất (trạng thái chuyển sang `Đang chuyển`).
4. Khi kho nhận đã kiểm đếm hàng thực tế tới nơi và người dùng xác nhận ở bước nhận hàng: mở lại mã phiếu đang chuyển, điền `Số lượng thực nhận` (ghi nhận chênh lệch nếu thất thoát vận chuyển), chụp preview rồi mới bấm `Nhận hàng`.

### Kịch bản 5: Kiểm kho bằng Barcode / Import Excel & Cân bằng kho
1. Vào phân hệ `Kiểm kho` → bấm `Tạo phiếu kiểm kho`, chọn đúng `Kho kiểm` (`source_location`) và nhập `Ghi chú` kỳ kiểm kê.
2. Nạp số liệu thực tế bằng 1 trong 2 cách:
   - **Quét Barcode / Nhập tay:** Đặt con trỏ vào ô `Tìm kiếm / Quét mã vạch`, nhập/quét từng SKU và cập nhật cột `Tồn thực tế`.
   - **Import Excel:** Bấm `Nhập file Excel` → tải file `stocktake_excel_path` đã đối chiếu.
3. Kiểm tra kỹ 3 cột `Tồn hệ thống`, `Tồn thực tế`, `SL lệch` và `Giá trị lệch` (đặc biệt các dòng lệch âm lớn hoặc lệch giá trị cao).
4. Bấm `Lưu nháp` (nếu cần), chụp ảnh toàn bộ bảng chênh lệch và **dừng tuyệt đối trước nút `Cân bằng kho`**. Chỉ bấm `Cân bằng kho` ở lượt hội thoại tiếp theo sau khi quản lý kho/Owner xác nhận tường minh.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Protocol)

1. **Pha 1 — Pre-State Capture (Chụp mốc tồn kho gốc):**
   - Mở `/admin/products/inventories`, lọc chính xác `source_location` (và `destination_location` nếu là điều chuyển kho).
   - Chụp `pre_screenshot` ghi nhận đủ 4 cột `Tồn kho`, `Đang giao dịch`, `Có thể bán`, `Hàng đang về`, đồng thời xuất file Excel tồn kho hiện tại làm căn cứ đối chiếu & rollback.
2. **Pha 2 — Stage Without Saving (`dry_run: true`):**
   - Lập phiếu PO / Nhập hàng / Trả hàng NCC / Điều chuyển / Kiểm kho (chỉ cho phép bấm `Lưu nháp` với phiếu kiểm kho cần giữ số đếm tạm).
   - Kiểm tra chéo tổng số lượng SKU, tổng giá trị nhập, chi phí nhập hàng phân bổ và biên độ lệch kiểm kho.
   - **Dừng tuyệt đối trước mọi nút chốt biến động kho (`Nhập kho` / `Hoàn trả` / `Chuyển hàng` / `Nhận hàng` / `Cân bằng kho`)**.
3. **Pha 3 — Separate-Turn Confirmation Gate (`separate_turn: true`):**
   - Chụp `preview_screenshot` toàn bộ bảng dòng SKU và tổng giá trị trên phiếu.
   - Trình bày bảng `Before → After` kèm ước tính biến động tồn & tác động giá vốn bình quân (`MAC`), gắn rõ cờ cảnh báo nếu có SKU lệch âm lớn hoặc giá nhập bất thường.
   - **Dừng hoàn toàn ở lượt hội thoại hiện tại** và chờ quản lý kho / Owner xác nhận tường minh ở **lượt hội thoại tiếp theo**.
4. **Pha 4 — Apply & Post-Save Reload Verification (Xác minh Lịch sử tồn kho):**
   - Sau khi người dùng xác nhận ở lượt mới, bấm nút thực thi tương ứng đúng 1 lần và chờ toast xanh xác nhận hoàn tất.
   - Mở lại `/admin/products/inventories`, nhấn `F5` reload, kiểm tra cột `Có thể bán` và mục `Lịch sử tồn kho` (Inventory History) của ít nhất 2 SKU đại diện khớp 100% số lượng biến động, sau đó chụp `post_screenshot`.

### Checklist An Toàn Kho & Giá Vốn (Warehouse Safety Gate)

- [ ] Đã chốt giờ cắt đơn (cut-off time) hoặc kiểm tra cột `Đang giao dịch (Committed)` trước khi thực hiện `Cân bằng kho`.
- [ ] Mọi dòng nhập hàng đều có `Đơn giá nhập > 0` và nhỏ hơn `Giá bán lẻ` (không bị nhập thiếu/dư số `0` gây méo giá vốn `MAC`).
- [ ] Phiếu điều chuyển đã xác minh `Số lượng chuyển <= Có thể bán` tại `Kho xuất` và `Kho xuất != Kho nhận`.
- [ ] Số dòng SKU trên mỗi phiếu ≤ `50` (`max_records: 50`); gặp lỗi 1 dòng phải dừng toàn bộ (`partial_failure_policy: stop`).
- [ ] Đã nhận xác nhận ở **lượt hội thoại riêng** (`separate_turn: true`) trước khi bấm nút chốt kho.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Biến động Tồn kho (Operational Estimate)

| SKU | Kho áp dụng | Tồn hệ thống (Before) | Biến động / Thực tế | Tồn sau dự kiến (After) | Ghi chú giá vốn / Lý do |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POLO-BLK-M` | Kho Tổng HCM | `42` | `+100` (Nhập hàng PO) | `142` | Giá nhập `145.000đ` (+phí ship phân bổ) |
| `POLO-BLK-L` | Kho Tổng HCM → Kho HN | `30` / `5` | `-15` / `+15` (Điều chuyển) | `15` / `20` | Bổ sung hàng bán tuần 48 |
| `JEAN-IND-30` | Kho Tổng HCM | `18` | `16` (Kiểm kho: `-2`) | `16` | Lệch âm 2 chiếc — chờ duyệt cân bằng |
| `HOODIE-GRY-L` | Kho Tổng HCM | `12` | `-3` (Trả hàng NCC) | `9` | Hàng lỗi đường may — Biên bản NCC #04 |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-inventory-advanced-ops",
  "mode": "proposal",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/inventory_adjustments/new",
  "scenario": "stocktake_reconcile",
  "session_authenticated": true,
  "dry_run": true,
  "separate_turn_confirmed": false,
  "backup_exported": true,
  "source_location": "Kho Tổng HCM",
  "destination_location": null,
  "skus_affected": 3,
  "pre_screenshot": "artifacts/inventory_stocktake_pre.png",
  "preview_screenshot": "artifacts/inventory_stocktake_staged.png",
  "post_screenshot": null,
  "changes_staged": [
    {
      "sku": "JEAN-IND-30",
      "system_qty": 18,
      "actual_qty": 16,
      "delta_qty": -2,
      "estimated_cost_impact_vnd": -420000,
      "reason": "Kiem ke dinh ky thang 11"
    }
  ],
  "warnings": [
    "Separate-turn confirmation required before clicking 'Cân bằng kho'."
  ],
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm khi chưa qua xác nhận lượt riêng (`separate_turn: true`):**
  - `Cân bằng kho` (ghi đè trực tiếp tồn kho thực tế, ảnh hưởng báo cáo xuất-nhập-tồn và kế toán kho).
  - `Nhập kho` / `Xác nhận nhập hàng` (tính lại giá vốn bình quân gia quyền `MAC` toàn hệ thống, không thể hoàn tác đơn giản).
  - `Hoàn trả hàng` (trừ tồn kho và phát sinh bút toán công nợ NCC).
  - `Xóa phiếu` / `Hủy phiếu` đã hoàn tất hoặc nút `Thanh toán NCC` ghi nhận chi tiền sổ quỹ.
- **Financial & Credential Handoff Gate:**
  - Mọi số liệu giá vốn, giá trị lệch kiểm kho và công nợ NCC là **Operational Estimate** — cần đối chiếu hóa đơn/chứng từ gốc với bộ phận kế toán.
  - Gặp `accounts.haravan.com` → dừng ngay cho người dùng tự đăng nhập.

### Bảng Quy Chuẩn Trạng Thái Phiếu Kho & Điều Kiện Chuyển Tiếp

| Loại phiếu | Trạng thái Nháp / Chờ (An toàn khi Stage) | Nút Chốt (Bắt buộc `separate_turn: true`) | Tác động hệ thống sau khi Chốt |
| :--- | :--- | :--- | :--- |
| Đặt hàng nhập (`PO`) | `Lưu nháp` / `Đang đặt hàng` | `Duyệt đơn` → `Nhập hàng` | Tăng cột `Hàng đang về` tại kho nhập |
| Nhập hàng (`Receive`) | Đã điền SKU, SL, đơn giá & chi phí | `Nhập kho` / `Xác nhận nhập` | Tăng `Tồn kho`, cập nhật lại giá vốn `MAC` & công nợ NCC |
| Điều chuyển (`Transfer`) | `Chờ chuyển` → `Đang chuyển` | `Chuyển hàng` (xuất) / `Nhận hàng` (nhập) | Trừ kho xuất trước, cộng kho nhận khi xác nhận nhận |
| Kiểm kho (`Stocktake`) | `Lưu nháp` (chưa thay đổi tồn) | `Cân bằng kho` | Ghi đè `Tồn kho = Tồn thực tế`, ghi log `Lịch sử tồn kho` |

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Tồn kho `Đang giao dịch` (Committed) khác 0 khi kiểm kho:** Nếu đang có đơn hàng chưa xuất kho trong lúc kiểm kê, `Có thể bán` sẽ nhỏ hơn `Tồn kho`. Agent phải cảnh báo người dùng chốt giờ cắt đơn (cut-off time) trước khi bấm `Cân bằng kho` để tránh lệch tồn kép.
2. **Nhập sai đơn giá (thiếu hoặc dư số `0`) làm hỏng giá vốn bình quân (`MAC`):** Trước khi duyệt `Nhập kho`, Agent kiểm tra biên độ chênh lệch giữa `Đơn giá nhập` mới và giá bán hiện tại; nếu `Đơn giá nhập >= Giá bán` hoặc chênh > 30% so với giá vốn cũ, hiển thị cảnh báo đỏ ngay trên bảng Preview.
3. **Điều chuyển bị treo trạng thái `Đang chuyển`:** Hàng đã trừ ở kho xuất nhưng chưa cộng ở kho nhận, làm giảm tổng tồn có thể bán trên Website. Agent nhắc lịch xác nhận `Nhận hàng` ngay khi kho đích ký nhận biên bản.
4. **SKU không bật `Quản lý tồn kho`:** Các sản phẩm đặt chế độ `Không quản lý tồn kho` sẽ không thể thêm vào phiếu kiểm kho/điều chuyển; Agent liệt kê các SKU bị loại và đề xuất bật quản lý tồn trong `admin-ui-products-catalog-ops`.
5. **File Excel kiểm kho bị lỗi trùng dòng SKU:** Nếu file kiểm kho có 2 dòng cùng 1 SKU (do quét ở 2 kệ khác nhau), phải cộng gộp số lượng trước khi tải lên Haravan để tránh hệ thống chỉ ghi nhận dòng sau cùng.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Rollback thủ công trên UI:**
  - *Phiếu nháp (PO/Kiểm kho chưa chốt):* Mở lại phiếu nháp và chỉnh sửa hoặc hủy phiếu nháp.
  - *Đã lỡ Cân bằng kho hoặc Điều chuyển sai số lượng:* Haravan không cho xóa phiếu đã hoàn tất để đảm bảo dấu vết kiểm toán kho; phải tạo **phiếu Kiểm kho điều chỉnh ngược** (hoặc phiếu Điều chuyển ngược chiều) căn cứ vào `pre_screenshot` và file Excel tồn kho sao lưu ở Pha 1, ghi rõ mã phiếu gốc trong phần lý do.
- **Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan:**
  - Kiểm toán tồn kho đa kho, hàng tồn lâu, cảnh báo sắp hết hàng qua API: `skills/api-mcp/30-inventory-supply/inventory-multi-location-audit`, `inventory-low-stock-watchdog`, `inventory-aging-dead-stock`, `inventory-purchase-order-audit`, `inventory-stocktake-cycle-count`.
  - Đề xuất điều chỉnh/điều chuyển tồn qua API: `inventory-adjustment-proposal`, `inventory-transfer-proposal`.
  - Cấu hình danh sách chi nhánh/kho hàng trên UI: `skills/browser-ui/95-admin-ui-browser/admin-ui-locations-inventory-ops`.
