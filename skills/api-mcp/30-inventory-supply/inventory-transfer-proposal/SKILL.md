---
name: inventory-transfer-proposal
description: "Đề xuất và tạo phiếu điều chuyển hàng giữa kho trung tâm và các chi nhánh HaraRetail POS (/com/inventories/transfers.json)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 30-inventory-supply
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_inventories
    - com.write_inventories
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/inventories/transfers.json"
    - "POST https://apis.haravan.com/com/inventories/transfers.json"
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
# Inventory Transfer Proposal — Đề Xuất & Tạo Phiếu Điều Chuyển Kho Nội Bộ

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` tính toán lượng hàng tối ưu cần điều chuyển giữa **Kho Tổng (Warehouse)** và các **Chi nhánh HaraRetail POS** (hoặc luân chuyển ngang giữa các chi nhánh), kiểm tra đủ tồn khả dụng tại kho xuất, và lập phiếu điều chuyển nội bộ qua `POST /com/inventories/transfers.json` theo quy trình Dry-Run trước. Điều chuyển nội bộ đúng lúc giúp giải cứu các chi nhánh/kho online đang sắp cháy hàng mà không phải chờ 10–15 ngày đặt hàng từ nhà cung cấp, đồng thời giảm tồn đọng tại các cửa hàng bán chậm.

- **Khi nào sử dụng:** Khi `inventory-multi-location-audit` hoặc `inventory-low-stock-watchdog` phát hiện kho chính/chi nhánh bán chạy cạn hàng trong khi kho khác đang dư tồn, hoặc khi phân bổ hàng mới nhập từ Kho Tổng ra chuỗi cửa hàng bán lẻ.
- **Khi nào KHÔNG sử dụng:** Khi thay đổi tổng tồn toàn công ty do thất thoát/kiểm kê (dùng `inventory-adjustment-proposal`), hoặc khi kho xuất và kho nhận trùng nhau (`from_location_id == to_location_id`).
- **Definition of Done (DoD):**
  1. Kiểm tra `qty_available` thực tế tại `from_location_id` và các phiếu điều chuyển đang mở (`GET /com/inventories/transfers.json`) để tránh chuyển trùng hàng đang trên đường đi.
  2. Đảm bảo quy tắc an toàn: `transfer_qty <= from_available - min_buffer_at_source` (không rút cạn kho xuất làm kho xuất bị hết hàng theo).
  3. Xuất bản xem trước Dry-Run (`.backup.json` + `.preview.csv`), chờ xác nhận của người dùng rồi mới gọi `POST /com/inventories/transfers.json` (tạo phiếu ở trạng thái chờ xuất/nhận, có xác minh sau ghi).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đọc danh sách kho hoạt động | `com.read_shop` | `GET https://apis.haravan.com/com/locations.json` |
| Kiểm tra tồn khả dụng kho xuất & kho nhận | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?location_ids={from},{to}` |
| Kiểm tra phiếu chuyển kho đang trên đường đi | `com.read_inventories` | `GET https://apis.haravan.com/com/inventories/transfers.json?status=open` |
| Tạo phiếu điều chuyển nội bộ (sau duyệt) | `com.write_inventories` | `POST https://apis.haravan.com/com/inventories/transfers.json` |

**JSON Request Payload (`POST https://apis.haravan.com/com/inventories/transfers.json`):**
```json
{
  "inventory_transfer": {
    "from_location_id": 1001235,
    "to_location_id": 1001234,
    "note": "Dieu chuyen can bang kho Q1 -> Kho Tong Thu Duc (2026-11-25)",
    "line_items": [
      {
        "product_id": 1058923401,
        "product_variant_id": 1129045512,
        "quantity": 20
      },
      {
        "product_id": 1058923401,
        "product_variant_id": 1129045513,
        "quantity": 15
      }
    ]
  }
}
```

**Sample Response (`201 Created`):**
```json
{
  "inventory_transfer": {
    "id": 7704512,
    "tran_number": "TR-20261125-004",
    "from_location_id": 1001235,
    "to_location_id": 1001234,
    "status": "pending",
    "total_quantity": 35,
    "created_at": "2026-11-25T08:45:00Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `from_location_id` | integer | Có | — | ID kho xuất hàng (phải `status == "active"`). |
| `to_location_id` | integer | Có | — | ID kho nhận hàng (bắt buộc `!= from_location_id` và `status == "active"`). |
| `transfer_items` | array[object] | Có | — | Danh sách `{variant_id, requested_qty}` hoặc tự tính từ kết quả `inventory-multi-location-audit`. |
| `min_buffer_at_source` | integer | Không | `3` | Số lượng tối thiểu phải giữ lại tại kho xuất để không làm trống quầy trưng bày POS. |
| `max_records` | integer | Không | `100` | Tối đa 100 SKU trên một phiếu điều chuyển. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức Tính Lượng Điều Chuyển An Toàn & Chống Trùng Lặp
Với mỗi SKU trong danh sách yêu cầu:
```text
in_transit_qty = sum(open_transfer.qty cho cặp from -> to & variant_id này)
max_transferable = max(0, from_qty_available - min_buffer_at_source)
effective_transfer_qty = min(max(0, requested_qty - in_transit_qty), max_transferable)
```
Quy trình thực thi 5 bước:
1. **Xác thực 2 đầu kho:** Kiểm tra cả `from_location_id` và `to_location_id` đều đang `active` trong `/com/locations.json`.
2. **Kiểm tra hàng đang trên đường đi (`in_transit_qty`):** Đọc `GET /com/inventories/transfers.json` các phiếu chưa hoàn tất để không tạo trùng 2 phiếu cho cùng một nhu cầu bổ sung.
3. **Tính toán & Cắt trần an toàn:** Áp dụng công thức `effective_transfer_qty`; nếu bị cắt giảm so với `requested_qty`, ghi rõ lý do (`capped_by_source_buffer` hoặc `already_in_transit`).
4. **Xuất Dry-Run Preview & Backup:** Gọi `write_dry_run_artifact()` lưu tồn hiện tại 2 đầu kho vào `.backup.json` và bảng chuyển vào `.preview.csv`.
5. **Tạo phiếu sau xác nhận & Post-Write Verification:** Gọi `POST /com/inventories/transfers.json`, sau đó gọi `GET /com/inventories/transfers/{id}.json` xác nhận `tran_number`, `status`, và tổng số lượng khớp 100%.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Phiếu Điều Chuyển Kho (Dry-Run Preview)
- **Tuyến điều chuyển:** `Cửa hàng Quận 1 (1001235)` → `Kho Tổng Thủ Đức (1001234)`
- **Tổng SKU chuyển:** `2` | **Tổng số lượng:** `35` sản phẩm | **Giữ lại tối thiểu tại kho xuất:** `3` cái/SKU

| Variant ID | SKU | Tồn Q.1 (Xuất) | Tồn Thủ Đức (Nhận) | Đang trên đường | Đề xuất chuyển | Tồn Q.1 sau chuyển | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `1129045512` | `ATN-250-DEN-M` | 38 | 0 | 0 | `20` | `18` | Hợp lệ |
| `1129045513` | `ATN-250-DEN-L` | 18 | 2 | 0 | `15` | `3` | Chạm ngưỡng buffer (giữ lại 3) |

### JSON Output Schema
```json
{
  "skill": "inventory-transfer-proposal",
  "dry_run": true,
  "from_location_id": 1001235,
  "to_location_id": 1001234,
  "summary": { "total_skus": 2, "total_units": 35, "skipped_zero_qty": 0 },
  "artifacts": {
    "backup_json": "artifacts/hrv-inventory-transfer-proposal-20261125T084500Z.backup.json",
    "preview_csv": "artifacts/hrv-inventory-transfer-proposal-20261125T084500Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run & Xác nhận bắt buộc (`confirmation_required: true`):** Luôn hiển thị bảng tồn kho 2 đầu trước và sau chuyển để quản lý kho duyệt.
- **Không tự ý xác nhận đã nhận hàng:** Phiếu tạo ra ở trạng thái chờ xuất/chờ nhận (`pending`) để thủ kho 2 đầu kiểm đếm thực tế rồi mới bấm Xuất kho / Nhận kho trên Haravan Admin.
- **Rollback:** Nếu phiếu mới tạo sai thông tin và chưa xuất kho vật lý, hủy phiếu (`cancel`) trực tiếp trên Haravan Admin hoặc qua endpoint hủy phiếu tương ứng; nếu đã lỡ hoàn tất nhập kho thì lập phiếu điều chuyển ngược lại `to → from`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | `from_location_id == to_location_id`, số lượng `<= 0`, hoặc vượt quá tồn khả dụng kho xuất | Kiểm tra ràng buộc đầu vào trước khi gửi; dừng ngay nếu lỗi (`partial_failure_policy: stop`). |
| `403 Forbidden` | Thiếu `com.write_inventories` hoặc gói dịch vụ chưa bật tính năng chuyển kho đa chi nhánh | Kiểm tra lại gói cước Omni & quyền Private App. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Kho xuất bị trừ tồn ngay khi bấm "Xuất kho" nhưng kho nhận chưa có tồn cho đến khi bấm "Nhận hàng":** Trong thời gian vận chuyển giữa 2 tỉnh (1–3 ngày), hàng nằm ở trạng thái `in_transit` (không bán được online trên cả 2 kho). Cần lưu ý thời điểm chuyển để tránh làm đứt hàng tạm thời trên web.
2. **Chi nhánh POS chỉ còn 1–2 cái hàng mẫu trưng bày (Display Unit):** Nếu rút hết về `0` sẽ làm trống kệ cửa hàng và mất khách walk-in; luôn giữ `min_buffer_at_source >= 2..3` cho các chi nhánh bán lẻ.
3. **Phiếu chuyển kho bị treo ở trạng thái "Đang vận chuyển" quá 7 ngày:** Nhân viên kho nhận hàng ngoài đời thật nhưng quên bấm "Nhận hàng" trên Haravan khiến tồn ảo bị treo. Khuyến nghị rà soát các phiếu `open/in_transit > 7 ngày` mỗi lần chạy skill.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `inventory-multi-location-audit`, `inventory-low-stock-watchdog`.
- **Chạy tiếp theo:** `inventory-multi-location-audit` (kiểm tra lại cân bằng sau khi 2 đầu kho hoàn tất xuất-nhận).
