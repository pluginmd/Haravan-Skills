---
name: inventory-stocktake-cycle-count
description: "Chuẩn hóa quy trình kiểm kho định kỳ (cycle count), đối chiếu chênh lệch thừa/thiếu theo SKU và lập đề xuất cân bằng kho."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 30-inventory-supply
layer: L2
wave: 2
mode: proposal
risk: high
haravan:
  api_surface: com
  scopes:
    - com.read_inventories
    - com.write_inventories
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "POST https://apis.haravan.com/com/inventories/adjustments.json"
    - "UI /admin/products/inventories"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
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
# Inventory Stocktake & Cycle Count — Quy Trình Kiểm Kho Định Kỳ & Cân Bằng Chênh Lệch

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` (**Risk: HIGH, Separate-Turn Confirmation bắt buộc**) chuẩn hóa toàn bộ quy trình kiểm kho tuần hoàn (**Cycle Count** theo phân nhóm ABC) hoặc kiểm kho tổng định kỳ trên Haravan: từ bước tạo danh sách SKU cần kiểm (Blind Count Sheet — ẩn tồn hệ thống để nhân viên đếm trung thực), nhập kết quả đếm thực tế, tính chênh lệch thừa/thiếu + tỷ lệ chính xác tồn kho (**Inventory Record Accuracy — IRA%**), cho đến lập phiếu đề xuất cân bằng kho (`POST /com/inventories/adjustments.json`).

- **Khi nào sử dụng:** Kiểm kho tuần hoàn hàng tuần cho nhóm A (Hero SKU), hàng tháng cho nhóm B, hàng quý cho toàn kho, hoặc kiểm tra bàn giao ca/bàn giao thủ kho mới.
- **Khi nào KHÔNG sử dụng:** Khi chỉ cần điều chỉnh lẻ 1–2 SKU bị hỏng đột xuất không theo đợt kiểm kê (dùng trực tiếp `inventory-adjustment-proposal`).
- **Definition of Done (DoD):**
  1. Xuất được danh sách kiểm kê chuẩn (`Blind Count Sheet`) theo `location_id` và phạm vi lọc (nhóm A, theo thương hiệu, hoặc theo nhóm sản phẩm).
  2. Đối chiếu kết quả đếm thực tế với snapshot hệ thống (`/com/inventory_locations.json`), tính **IRA%**, phân loại rõ `MATCH`, `MINOR_VARIANCE`, và `RECOUNT_REQUIRED` (chênh lệch lớn bắt buộc đếm lại lần 2).
  3. Chỉ lập phiếu Dry-Run cân bằng kho (`.backup.json` + `.preview.csv`) cho các dòng đã qua kiểm chứng và **chờ xác nhận ở lượt riêng (`separate_turn: true`)** trước khi ghi.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Danh sách kho kiểm kê | `com.read_shop` | `GET https://apis.haravan.com/com/locations.json` |
| Snapshot tồn kho hệ thống tại thời điểm cắt số | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?location_ids={loc_id}` |
| Lập phiếu cân bằng sau khi duyệt đối chiếu | `com.write_inventories` | `POST https://apis.haravan.com/com/inventories/adjustments.json` |
| Giao diện quản lý phiếu kiểm kho mở rộng | Admin UI | `UI /admin/products/inventories` (nếu cần in phiếu giấy/ký duyệt nội bộ) |

**JSON Request Payload cân bằng sau kiểm kho (`POST /com/inventories/adjustments.json`):**
```json
{
  "inventory_adjustment": {
    "location_id": 1001235,
    "type": "set",
    "reason": "cycle_count",
    "note": "Cycle Count Nhom A - Cua hang Quan 1 - Dot 2026-W48 (IRA: 92.5%)",
    "line_items": [
      { "product_id": 1058923401, "product_variant_id": 1129045512, "quantity": 36 },
      { "product_id": 1051120045, "product_variant_id": 112001, "quantity": 12 }
    ]
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `phase` | enum (`generate_sheet`, `reconcile_dry_run`, `apply_approved`) | Có | `generate_sheet` | Tách rõ 3 pha: Tạo phiếu đếm mù → Đối chiếu & Dry-Run → Ghi sau duyệt. |
| `location_id` | integer | Có | — | ID kho/chi nhánh thực hiện kiểm kho. |
| `counted_csv_path` | string (path) | Có (pha 2) | — | Tệp kết quả kiểm đếm gồm `sku, counted_qty, counter_name`. |
| `recount_threshold_units` | integer | Không | `10` | Chênh lệch `|delta| >= 10` cái hoặc giá trị `>= 3.000.000₫` bắt buộc đếm lại lần 2 trước khi cân bằng. |
| `tolerance_units` | integer | Không | `0` | Sai số cho phép để tính chỉ số IRA% (mặc định `0` cho hàng thời trang/điện tử). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức Đánh giá Độ chính xác Tồn kho (IRA%) & Ngưỡng Đếm lại
```text
delta_i = counted_qty_i - system_qty_onhand_i
IRA_pct = (count(|delta_i| <= tolerance_units) / total_counted_skus) * 100
Net_Variance_Units = sum(delta_i)
Absolute_Variance_Units = sum(|delta_i|)
```
Quy trình chuẩn 3 pha (chống gian lận kiểm kho):
1. **Pha 1 — `generate_sheet` (Tạo phiếu Blind Count):** Xuất file CSV danh sách SKU cần đếm tại `location_id` nhưng **ẩn cột `qty_onhand`** để nhân viên kho buộc phải đếm vật lý từng sản phẩm (không điền đối phó theo số máy tính). Ghi nhận mốc thời gian cắt số `cutoff_timestamp`.
2. **Pha 2 — `reconcile_dry_run` (Đối chiếu & Phân loại):**
   - `MATCH` (`delta == 0`): đạt chuẩn, không cần điều chỉnh.
   - `RECOUNT_REQUIRED` (`|delta| >= recount_threshold_units` hoặc `counted_qty < qty_commited`): **tạm chặn không đưa vào phiếu ghi**, yêu cầu quản lý kho kiểm đếm lại lần 2 và xác nhận nguyên nhân.
   - `READY_TO_ADJUST` (`0 < |delta| < recount_threshold_units`): đưa vào Dry-Run Proposal (`.backup.json` + `.preview.csv`).
3. **Pha 3 — `apply_approved` (Ghi cân bằng ở lượt riêng):** Chỉ chạy sau khi người dùng xác nhận tường minh ở lượt tiếp theo; kiểm tra lại `updated_at` để phát hiện giao dịch phát sinh trong lúc kiểm kho.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Kết Quả Đối Chiếu Cycle Count — Cửa hàng Quận 1 (Đợt 2026-W48)
- **Tổng SKU kiểm đếm:** `40` | **Khớp tuyệt đối:** `35` (**IRA = 87.5%**, mục tiêu `>= 95%`)
- **Lệch nhỏ sẵn sàng cân bằng:** `3` SKU | **Lệch lớn cần đếm lại lần 2:** `2` SKU (`BLOCKED`)

| SKU | Tồn hệ thống | Đếm thực tế | Chênh lệch (`delta`) | Giá trị lệch (ước tính) | Phân loại | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| `ATN-250-DEN-M` | 38 | 36 | `-2` | `-658.000₫` | `READY_TO_ADJUST` | Đưa vào Dry-Run |
| `AKD-DEN-L` | 25 | 12 | `-13` | `-7.137.000₫` | `RECOUNT_REQUIRED` | **Chặn — Yêu cầu đếm lại lần 2** |
| `POLO-TRG-M` | 20 | 20 | `0` | `0₫` | `MATCH` | Bỏ qua |

### JSON Output Schema
```json
{
  "skill": "inventory-stocktake-cycle-count",
  "phase": "reconcile_dry_run",
  "location_id": 1001235,
  "ira_pct": 87.5,
  "summary": { "total_skus": 40, "matched": 35, "ready_to_adjust": 3, "recount_required": 2, "net_variance_units": -16 },
  "separate_turn_confirmation_required": true,
  "artifacts": {
    "backup_json": "artifacts/hrv-inventory-stocktake-cycle-count-20261125T083000Z.backup.json",
    "preview_csv": "artifacts/hrv-inventory-stocktake-cycle-count-20261125T083000Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Separate-Turn Confirmation (`separate_turn: true`, `risk: high`):** Dừng sau pha 2, chỉ ghi ở pha 3 khi quản lý xác nhận biên bản.
- **Giới hạn batch `<= 100` SKU/phiếu:** Nếu tổng kiểm kho có 500 SKU bị lệch, tự động tách thành nhiều phiếu `<= 100` SKU theo từng ngành hàng/kệ kho để dễ kiểm soát và đối soát kế toán.
- **Post-Write Verification & Rollback:** Gọi `GET /com/inventory_locations.json` xác nhận khớp số sau ghi; rollback bằng phiếu bù ngược dấu từ `.backup.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | SKU trong file kiểm đếm không khớp `variant_id` trên Haravan hoặc sai `location_id` | Báo danh sách SKU chưa ánh xạ được (`unmapped_skus`) để rà soát trước khi ghi. |
| `429 Too Many Requests` | Quét tồn kho toàn chi nhánh lớn | Dùng `location_ids={loc_id}` để chỉ tải đúng 1 kho cần kiểm. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Đơn hàng POS/Online phát sinh ngay giữa lúc đang kiểm đếm (Cut-off Drift):** Nếu không tạm dừng xuất/bán tại chi nhánh lúc kiểm kê, số lượng đếm được sẽ lệch đúng bằng số đơn bán ra trong khung giờ kiểm. Bắt buộc ghi nhận `cutoff_timestamp` và đối chiếu các đơn tạo sau mốc đó trước khi bấm cân bằng.
2. **Hàng đang đóng gói chờ shipper lấy (đã tạo vận đơn nhưng còn nằm ở góc kho):** Nhân viên mới hay đếm nhầm cả đống hàng đã đóng gói vào tồn thực tế → phải nhắc tách khu vực hàng đã xuất vận đơn ra khỏi khu vực kiểm đếm.
3. **Hàng trùng SKU khiến tổng đếm sai lệch:** Luôn yêu cầu chạy `catalog-duplicate-sku-barcode` trước đợt tổng kiểm kho.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-duplicate-sku-barcode`, `inventory-stock-velocity-forecast` (lấy danh sách nhóm A để ưu tiên kiểm tuần hoàn).
- **Chạy tiếp theo:** `inventory-multi-location-audit` (xác nhận toàn bộ hệ thống sạch tồn âm sau kiểm kho).
