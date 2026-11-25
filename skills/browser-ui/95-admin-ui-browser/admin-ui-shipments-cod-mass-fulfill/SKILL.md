---
name: admin-ui-shipments-cod-mass-fulfill
description: "Điều phối giao hàng hàng loạt (/admin/orders/mass_fulfill), Quản lý thu hộ COD (/admin/shipments/managecod), Đóng gói, Biên bản bàn giao & Hoàn hàng."
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
    - "UI /admin/orders/mass_fulfill"
    - "UI /admin/shipments/dashboard"
    - "UI /admin/shipments/managecod"
    - "UI /admin/shipments/packed"
    - "UI /admin/shipments/shipment_handovers"
    - "UI /admin/shipments/shipment_returns"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 25
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: true
---

# Haravan Admin UI: Mass Fulfillment, COD Management & Handover Forms

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Bao phủ toàn bộ 6 màn hình kho vận & giao nhận lõi trên Haravan Admin (`*.myharavan.com/admin`): **Tổng quan vận chuyển** (`/admin/shipments/dashboard`), **Giao hàng hàng loạt** (`/admin/orders/mass_fulfill`), **Đóng gói** (`/admin/shipments/packed`), **Biên bản bàn giao** (`/admin/shipments/shipment_handovers`), **Biên bản hoàn hàng** (`/admin/shipments/shipment_returns`) và **Quản lý thu hộ COD** (`/admin/shipments/managecod`).
- **Lý do bắt buộc dùng Browser UI:** Haravan Commerce API chỉ tạo từng vận đơn đơn lẻ, không hỗ trợ thao tác hàng loạt theo cụm NVC (GHN, GHTK, Viettel Post, J&T, Ahamove), lập biên bản bàn giao/hoàn hàng có mã vạch in phiếu, hay đối soát upload file Excel COD của Viettel Post.
- **Mức độ rủi ro `high` (`separate_turn: true`, `max_records: 25`, `rollback.supported: false`):** Đẩy vận đơn hàng loạt lập tức sinh mã vận đơn thực tế trên hệ thống đối tác NVC và phát sinh cước vận chuyển; xác nhận thu hộ/nhận hoàn làm thay đổi số dư COD và tồn kho thực tế. Mọi thao tác ghi bắt buộc **xác nhận tường minh ở lượt hội thoại riêng**.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền trên tất cả 6 màn hình vận chuyển và đối soát COD.
  - **Staff:** Yêu cầu có quyền **Xử lý đơn hàng**, **Quản lý vận chuyển** và **Quản lý thu hộ COD** (nếu đối soát tài chính) tại `/admin/settings/group_permissions`. Nhân viên kho chỉ được gán quyền theo **Chi nhánh/Kho phụ trách** sẽ chỉ thấy đơn thuộc kho đó.
  - **Giới hạn gói:** Tính năng kết nối đa NVC tự động và quản lý đóng gói/biên bản bàn giao khả dụng đầy đủ từ gói Haravan Pro/Omnichannel trở lên; nếu màn hình yêu cầu nâng cấp gói, dừng ngay.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/shipments/dashboard`.
  2. Nếu bị redirect về `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập (không hỏi/nhập mật khẩu hay OTP).
  3. Kiểm tra nhanh cảnh báo mất kết nối NVC (badge đỏ trên `/admin/shipments/dashboard`) trước khi xử lý batch.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/shipments/dashboard` | Tổng quan vận chuyển | `Lọc thời gian`, `Chọn nhà vận chuyển`, `Xem chi tiết` | Thẻ KPI: `Chờ lấy hàng`, `Đang giao hàng`, `Chờ giao lại`, `Đang chuyển hoàn`, `Đã giao`, `Chưa nhận tiền COD` |
| `/admin/orders/mass_fulfill` | Giao hàng hàng loạt | `Lọc`, `Tìm kiếm`, `Chọn kho xuất`, `Chọn nhà vận chuyển`, `Tạo vận đơn` / `Giao hàng` (HARD-GATE) | Bộ lọc: `Trạng thái xác nhận`, `Nhãn (Tag)`, `Kho hàng`, `Phương thức thanh toán`. Cột: Checkbox, Mã đơn, Khách hàng, Địa chỉ 3 cấp, Khối lượng (g), Tiền thu hộ COD, Cước dự kiến |
| `/admin/shipments/packed` | Đóng gói | `Lọc`, `In phiếu đóng gói`, `Xác nhận đã đóng gói` | Bộ lọc: `Trạng thái đóng gói` (`Chờ đóng gói` / `Đã đóng gói`), `Kho lấy hàng`, `NVC`. Cột: Mã đơn, Mã đóng gói, Số lượng SP, Kho, Trạng thái, Thời gian tạo |
| `/admin/shipments/shipment_handovers` | Biên bản bàn giao | `Tạo biên bản bàn giao`, `In biên bản`, `Xác nhận bàn giao` (CẤM tự bấm) | Bộ lọc: `Nhà vận chuyển`, `Kho hàng`, `Trạng thái` (`Chờ bàn giao` / `Đã bàn giao`). Cột: Mã biên bản, NVC, Số vận đơn, Tổng COD, Người tạo, Ngày tạo |
| `/admin/shipments/shipment_returns` | Biên bản hoàn hàng | `Tạo biên bản hoàn hàng`, `Quét mã vận đơn`, `Xác nhận nhận hoàn` (CẤM tự bấm) | Bộ lọc: `Nhà vận chuyển`, `Trạng thái hoàn` (`Đang chuyển hoàn` / `Đã nhận hoàn`), `Kho nhận`. Cột: Mã biên bản, Mã vận đơn, Mã đơn gốc, Lý do hoàn, Trạng thái nhập kho |
| `/admin/shipments/managecod` | Quản lý thu hộ COD | `Lọc`, `Nhập file đối soát`, `Xác nhận đã nhận tiền` (CẤM tự bấm), `Xuất dữ liệu` (CẤM) | Bộ lọc: `Nhà vận chuyển` (`GHN`/`GHTK` tự đồng bộ vs `Viettel Post` thủ công), `Trạng thái thu hộ` (`Chưa nhận` / `Đã nhận`), `Ngày giao thành công`. Cột: Mã vận đơn, Mã đơn, NVC, Tiền COD, Phí ship, Đối soát |

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Đúng định dạng `*.myharavan.com` hoặc custom admin domain hợp lệ |
| `scenario` | `string` | Có | `cod_reconcile_audit` | Một trong: `mass_fulfill_stage`, `packed_monitoring`, `handover_prepare`, `returns_qc_audit`, `cod_reconcile_audit` |
| `carrier_filter` | `string` | Không | `all` | `all` \| `GHN` \| `GHTK` \| `Viettel Post` \| `J&T` \| `Ahamove` \| `VNPost` |
| `warehouse_name` | `string` | Khi `mass_fulfill_stage` | — | Phải khớp chính xác tên kho đang hoạt động tại `/admin/settings/locations` |
| `exclude_tags` | `array<string>` | Không | `["cod-verify", "fraud-risk", "hold", "waiting-stock"]` | Danh sách tag bắt buộc loại khỏi batch đẩy vận đơn |
| `max_batch_size` | `integer` | Không | `25` | Bắt buộc `1 <= max_batch_size <= 25` theo `max_records: 25` |
| `cod_overdue_days` | `integer` | Không | `5` | Số ngày từ lúc giao thành công chưa về tiền COD (`1..60`) |
| `inspection_note` | `string` | Không | `Cho xem hàng, không cho thử` | Ghi chú giao hàng truyền sang phiếu vận đơn NVC (tối đa 120 ký tự) |
| `dry_run` | `boolean` | Có | `true` | Bắt buộc `true` ở lượt chuẩn bị; chỉ thực thi ở lượt riêng sau khi duyệt |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Lọc & Đẩy vận đơn hàng loạt tại `/admin/orders/mass_fulfill` (Loại đơn `cod-verify`)
- **Khi nào dùng:** Cuối ca sáng/chiều cần đẩy lô ≤ 25 đơn đã xác nhận sang một NVC cụ thể mà không bị lẫn đơn rủi ro bom hàng.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/orders/mass_fulfill` (hoặc nhấn `Ctrl+K` gõ `Giao hàng hàng loạt`), chờ danh sách tải xong và chụp `pre_screenshot`.
  2. Mở thanh `Lọc`: chọn `Kho xuất hàng` = `warehouse_name`, trạng thái đơn = `Đã xác nhận`, trạng thái giao hàng = `Chưa giao hàng`, sắp xếp đơn cũ nhất lên đầu để đảm bảo SLA.
  3. Rà soát cột `Nhãn (Tag)` và `Địa chỉ 3 cấp`: **bỏ chọn 100%** các đơn có gắn bất kỳ tag nào trong `exclude_tags` (`cod-verify`, `fraud-risk`, `hold`, `waiting-stock`) hoặc dòng bị bôi đỏ thiếu Phường/Xã, Quận/Huyện.
  4. Tick chọn tối đa `<= max_batch_size` (≤ 25) đơn sạch; ở khung cấu hình vận chuyển, chọn `Nhà vận chuyển` (`carrier_filter`), gói dịch vụ (Chuẩn/Nhanh), kiểm tra khối lượng kiện (gram) và điền `Ghi chú xem hàng` = `inspection_note`.
  5. Kiểm tra cột `Tiền thu hộ COD` đối chiếu với trạng thái đã thanh toán/chuyển khoản trước (tránh thu hộ nhầm đơn đã trả tiền).
  6. Chờ hệ thống tính xong cột `Cước dự kiến` cho từng đơn và tổng cước cả batch.
- **Điểm dừng an toàn:** **DỪNG LẠI — TUYỆT ĐỐI CHƯA BẤM `Tạo vận đơn` / `Giao hàng`**. Chụp `preview_screenshot` và gửi duyệt ở lượt hội thoại riêng (`separate_turn: true`).

### Kịch bản 2: Theo dõi tồn đọng đóng gói & Chuẩn bị in phiếu tại `/admin/shipments/packed`
- **Khi nào dùng:** Giám sát vận hành kho cần phát hiện đơn đã sinh mã vận đơn nhưng kho đóng gói chậm quá SLA 12–24 giờ.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/shipments/packed`, chụp `pre_screenshot`.
  2. Nhấn `Lọc`, chọn `Kho lấy hàng` = `warehouse_name` và trạng thái `Chờ đóng gói`; sắp xếp theo `Thời gian tạo` tăng dần.
  3. Đối chiếu số lượng sản phẩm/SKU và ghi chú đóng gói đặc biệt (hàng dễ vỡ, bọc chống sốc, combo quà tặng).
  4. Nhóm danh sách đơn chờ đóng gói theo từng NVC (`GHN`, `GHTK`, `Viettel Post`, `J&T`) để thủ kho gom lô in phiếu đóng gói và phiếu giao hàng đồng bộ.
  5. Kiểm tra khả năng khả dụng của nút `In phiếu đóng gói` trên các đơn đã lọc, lập danh sách đơn trễ SLA > 12h.
- **Điểm dừng an toàn:** Không bấm `Xác nhận đã đóng gói` khi chưa có xác nhận đóng kiện vật lý từ thủ kho; chụp `preview_screenshot` bàn giao kho.

### Kịch bản 3: Lập & Chuẩn bị in Biên bản bàn giao NVC tại `/admin/shipments/shipment_handovers`
- **Khi nào dùng:** Trước giờ bưu tá các hãng tới kho lấy hàng, cần gom vận đơn vào biên bản bàn giao có chữ ký đối chứng.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/shipments/shipment_handovers`, kiểm tra các biên bản ngày hôm nay đang ở trạng thái `Chờ bàn giao` và chụp `pre_screenshot`.
  2. Nhấn `Tạo biên bản bàn giao`, chọn đúng `Kho lấy hàng` và đúng 1 `Nhà vận chuyển` (bắt buộc tách riêng từng NVC, không gộp GHN chung Viettel Post).
  3. Tick chọn danh sách mã vận đơn đã đóng gói xong chờ bàn giao (tối đa ≤ 25 vận đơn/lượt staging), kiểm tra chéo tổng số kiện và tổng COD hiển thị trên form.
  4. Đối chiếu không có mã vận đơn nào thuộc trạng thái `Đã hủy` hoặc chưa đóng gói lọt vào biên bản.
- **Điểm dừng an toàn:** **CHƯA BẤM `Xác nhận bàn giao` hoặc `Lưu`**. Chụp `preview_screenshot` để thủ kho kiểm đếm số kiện thực tế trước khi in biên bản cho bưu tá ký nhận.

### Kịch bản 4: Kiểm toán Biên bản hoàn hàng & Đối chiếu QC tại `/admin/shipments/shipment_returns`
- **Khi nào dùng:** Rà soát hàng hoàn về kho định kỳ, tránh thất lạc hàng hoàn hoặc cộng nhầm tồn kho ảo cho sản phẩm hư hỏng.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/shipments/shipment_returns`, chụp `pre_screenshot`.
  2. Lọc theo trạng thái `Đang chuyển hoàn` (đánh dấu đơn hoàn treo quá 7 ngày chưa về kho) và `Chờ nhận hoàn` theo từng `Nhà vận chuyển`.
  3. Mở chi tiết từng biên bản hoàn (chỉ đọc): ghi nhận mã vận đơn, mã đơn gốc, lý do hoàn (`Khách không nghe máy`, `Sai địa chỉ`, `Từ chối nhận`), danh sách SKU hoàn.
  4. Lập bảng kiểm đếm QC (Quality Check) yêu cầu thủ kho kiểm tra niêm phong, tình trạng vỏ hộp, đủ phụ kiện trước khi nhập kho bán lại hoặc tách sang kho hàng lỗi.
- **Điểm dừng an toàn:** **TUYỆT ĐỐI KHÔNG bấm `Xác nhận nhận hoàn`** vì thao tác này tự động cộng lại tồn kho bán hàng ngay cả khi sản phẩm hoàn bị hỏng/thiếu lõi.

### Kịch bản 5: Đối soát & Chuẩn bị upload file thu hộ COD tại `/admin/shipments/managecod`
- **Khi nào dùng:** Kế toán/Vận hành đối soát dòng tiền thu hộ COD quá hạn theo từng NVC định kỳ hàng tuần.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/shipments/managecod`, chụp `pre_screenshot`.
  2. Nhấn `Lọc`: chọn `Trạng thái thu hộ` = `Chưa nhận`, trạng thái vận đơn = `Đã giao`, ngày giao thành công cách hiện tại `> cod_overdue_days` ngày.
  3. Phân tách rõ 2 nhóm NVC theo cơ chế Haravan:
     - **Nhóm tự đồng bộ (`GHN`, `GHTK`, `J&T`):** Kiểm tra trạng thái đồng bộ phiên đối soát tự động; nếu quá hạn chưa chuyển `Đã nhận`, gắn cờ cần tra cứu mã phiên chuyển tiền trên cổng NVC.
     - **Nhóm đối soát thủ công (`Viettel Post`, NVC ngoài):** Mở popup `Nhập file đối soát` để đối chiếu đúng cấu trúc cột file mẫu (`.xlsx`/`.csv`) — kiểm tra khớp mã vận đơn và số tiền thu hộ.
  4. Tổng hợp tổng tiền COD treo, cước vận chuyển trừ cấn và số ngày quá hạn theo từng NVC.
- **Điểm dừng an toàn:** **CHƯA bấm tải file lên hay `Xác nhận đã nhận tiền`**. Chụp `preview_screenshot` đính kèm Financial Disclaimer để kế toán đối chiếu sao kê ngân hàng gốc.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Kiểm tra phiên)
- Mở `/admin/shipments/dashboard` và route đích theo `scenario`, xác nhận không bị redirect về `accounts.haravan.com`.
- Kiểm tra cảnh báo kết nối NVC, ghi nhận số lượng đơn chờ giao / COD treo hiện có và chụp `pre_screenshot`.

### Pha 2 — Stage Without Saving (Dàn batch không kích hoạt API NVC)
- Thực hiện lọc đơn, loại 100% đơn `cod-verify` và đơn lỗi địa chỉ 3 cấp, tick chọn ≤ 25 đơn, chọn kho xuất/NVC hoặc dựng sẵn biên bản trên UI.
- Tuyệt đối không bấm `Tạo vận đơn`, `Xác nhận bàn giao`, `Xác nhận nhận hoàn` hay `Xác nhận đã nhận tiền`.

### Pha 3 — Screenshot-Before-Save & Separate-Turn Approval (`separate_turn: true`)
- Chụp `preview_screenshot` thấy rõ danh sách mã đơn, NVC, tổng cước dự kiến và tổng tiền COD.
- Lập bảng `Before → After` đã che toàn bộ PII (`090****678`, ẩn địa chỉ chi tiết), dừng hoàn toàn và chờ người dùng xác nhận tường minh ở **lượt hội thoại tiếp theo**.

### Pha 4 — Save & Post-Save Reload Verification (Thực thi & Kiểm chứng)
- Chỉ khi có lệnh xác nhận ở lượt riêng, bấm đúng nút đã duyệt cho đúng danh sách ≤ 25 đơn.
- Áp dụng `partial_failure_policy: stop`: gặp lỗi API NVC đầu tiên phải dừng ngay, ghi nhận chính xác đơn đã tạo thành công vs đơn lỗi.
- Reload (`F5`) tại `/admin/shipments`, xác minh mã vận đơn mới sinh ra bền vững và chụp `post_screenshot`.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Preview Before → After (Mass Fulfill & COD Reconciliation)

| Hạng mục / Màn hình | Trạng thái Trước (Before) | Đề xuất Staging (After) | Cảnh báo / Lưu ý An toàn |
| :--- | :--- | :--- | :--- |
| `/admin/orders/mass_fulfill` | `21 đơn` chờ giao tại Kho HCM | Chọn `18 đơn` hợp lệ → NVC `GHN` (`512,000₫` cước dự kiến) | Đã loại `2 đơn` tag `cod-verify`, `1 đơn` thiếu Phường/Xã |
| `/admin/shipments/packed` | `9 đơn` chờ đóng gói > 12h | Gom lô in phiếu: `6 GHN`, `3 Viettel Post` | Chưa bấm `Xác nhận đã đóng gói` |
| `/admin/shipments/shipment_handovers` | `0` biên bản ngày hôm nay | Dự thảo biên bản `GHN` (`18 vận đơn`, COD `14,200,000₫`) | Chờ kho kiểm đếm kiện trước khi bấm lưu |
| `/admin/shipments/shipment_returns` | `4 vận đơn` đang hoàn > 7 ngày | Bảng QC hoàn hàng (`3 GHTK`, `1 VTP`) | Chưa bấm `Xác nhận nhận hoàn` |
| `/admin/shipments/managecod` | `7 vận đơn` COD quá hạn > 5 ngày | Tổng treo `6,850,000₫` (`5 VTP` thủ công, `2 GHN` tự động) | **Operational Aid** — cần đối chiếu sao kê ngân hàng |

> **⚠️ High Risk (`separate_turn: true`):** Agent đã dàn sẵn `18 đơn` tại `/admin/orders/mass_fulfill` (chưa bấm `Tạo vận đơn`). Vui lòng phản hồi ở lượt tiếp theo: **"Xác nhận tạo vận đơn cho 18 đơn GHN này"** để thực thi. *(Financial Disclaimer: Số liệu COD chỉ mang tính hỗ trợ đối soát vận hành, không thay thế sao kê NVC/ngân hàng).*

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-shipments-cod-mass-fulfill",
  "scenario": "mass_fulfill_stage",
  "risk": "high",
  "separate_turn_required": true,
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/orders/mass_fulfill",
  "screenshots": {
    "pre": "artifacts/shipments_pre.png",
    "preview": "artifacts/mass_fulfill_preview.png",
    "post": null
  },
  "batch_staged": {
    "warehouse": "Kho Trung Tam HCM",
    "carrier": "GHN",
    "selected_orders_count": 18,
    "excluded_orders": {
      "cod_verify": 2,
      "invalid_address": 1
    },
    "estimated_shipping_fee_vnd": 512000,
    "total_cod_vnd": 14200000
  },
  "partial_failure_policy": "stop",
  "pii_redacted": true,
  "saved_verified": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click khi chưa có xác nhận `separate_turn: true`):**
  - `Tạo vận đơn` / `Giao hàng` hàng loạt tại `/admin/orders/mass_fulfill` (sinh cước thật & đẩy đơn qua cổng NVC).
  - `Xác nhận đã nhận tiền` tại `/admin/shipments/managecod` (chỉ kế toán bấm sau khi tiền thực về tài khoản ngân hàng).
  - `Xác nhận nhận hoàn` tại `/admin/shipments/shipment_returns` (chỉ thủ kho bấm sau khi mở kiện kiểm đếm vật lý).
  - `Xác nhận bàn giao` tại `/admin/shipments/shipment_handovers` khi bưu tá chưa ký nhận thực tế.
  - `Hủy vận đơn` hàng loạt và nút `Xuất dữ liệu` (tránh rò rỉ file raw PII khách hàng).
- **Credential / OTP / Financial Handoff Gates:**
  - Gặp `accounts.haravan.com` hoặc popup yêu cầu đăng nhập lại tài khoản đối tác NVC (GHN/GHTK/Viettel Post OTP) → **dừng ngay**, bàn giao người dùng tự nhập.
  - Mọi số liệu COD và phí vận chuyển phải kèm **Financial Disclaimer** và che toàn bộ SĐT (`090****678`), địa chỉ chi tiết người nhận.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Lỗi địa chỉ không khớp danh mục NVC khi đẩy hàng loạt:** Haravan tô đỏ hàng đơn thiếu Phường/Xã hoặc dùng tên địa giới cũ (trước sáp nhập) → Bỏ tick ngay các đơn lỗi khỏi batch, giữ lại đơn sạch và xuất danh sách mã đơn cần CSKH cập nhật địa chỉ.
2. **Lỗi `Tài khoản NVC mất kết nối / Token hết hạn` (thường gặp với GHN/VTP):** Áp dụng `partial_failure_policy: stop` — dừng batch ngay lập tức, ghi lại danh sách đơn đã tạo thành công vs chưa tạo, chuyển sang `admin-ui-shipping-carriers-setup` để người dùng kết nối lại NVC.
3. **Đơn bị trùng mã vận đơn do bấm đúp hoặc mạng lag:** Trước khi thử lại cho đơn bị timeout, luôn reload `/admin/shipments` tìm theo Mã đơn hàng để xác minh xem NVC đã sinh mã vận đơn hay chưa (đảm bảo `idempotency_required: true`).
4. **Cước dự kiến hiển thị `0₫` hoặc báo vượt khối lượng/kích thước tối đa:** Kiểm tra sản phẩm trong đơn có bị để trống trọng lượng (0g) hay vượt ngưỡng hàng cồng kềnh của GHTK/GHN → Tách riêng đơn hàng nặng sang NVC phù hợp (Viettel Post / Giao xe tải).
5. **Nhân viên Staff không thấy mục `Quản lý thu hộ` hoặc bị ẩn kho:** Do phân quyền hạn chế chi nhánh/kế toán → Chụp ảnh và báo Owner kiểm tra tại `/admin/settings/group_permissions`.
6. **File đối soát COD Viettel Post bị báo sai định dạng cột:** Kiểm tra lại dòng tiêu đề file `.xlsx` theo đúng template tải từ nút `Nhập file đối soát` trên Haravan, không tự sửa số tiền COD trong file kế toán.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: false`):**
  1. Nếu đã lỡ tạo nhầm vận đơn (khi bưu tá **chưa lấy hàng**): mở `/admin/shipments`, lọc theo mã đơn hàng vừa đẩy, vào từng vận đơn và để người dùng tự bấm `Hủy giao hàng` nhằm hủy lệnh trên cổng GHN/GHTK/VTP và đưa đơn về `Chờ giao hàng`.
  2. Nếu bưu tá đã quét lấy hàng: không thể hủy trên UI, phải tạo yêu cầu **Chuyển hoàn** trực tiếp trên app/portal NVC.
  3. Nếu lỡ tạo nhầm biên bản bàn giao (chưa xác nhận): mở chi tiết biên bản tại `/admin/shipments/shipment_handovers` để gỡ vận đơn hoặc hủy biên bản nháp.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/60-finance-analytics/finance-cod-reconciliation` (API): Đối soát tự động trạng thái COD và phát hiện lệch doanh thu theo đơn hàng qua `GET /com/orders.json`.
  - `skills/api-mcp/40-orders-fulfillment/fulfillment-carrier-sla-vn` (API): Phân tích SLA giao hàng, tỷ lệ giao thành công và tỷ lệ hoàn theo từng NVC Việt Nam.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-shipping-carriers-setup` (UI): Cấu hình lại kết nối NVC, kho lấy hàng mặc định và biểu phí ship tại `/admin/settings/shipments`.
