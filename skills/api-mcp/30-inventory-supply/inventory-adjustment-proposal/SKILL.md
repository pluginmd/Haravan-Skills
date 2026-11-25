---
name: inventory-adjustment-proposal
description: "So sánh tồn thực tế kiểm kê với tồn trên Haravan và tạo phiếu đề xuất điều chỉnh tồn kho (dry-run + backup bắt buộc)."
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
  endpoints:
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "POST https://apis.haravan.com/com/inventories/adjustments.json"
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
# Inventory Adjustment Proposal — Đối Chiếu & Lập Phiếu Điều Chỉnh Tồn Kho An Toàn

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` (**Risk: HIGH, Separate-Turn Confirmation bắt buộc**) đối chiếu số liệu tồn kho thực tế (từ file kiểm kê, báo cáo kho 3PL hoặc xuất nhập tồn nội bộ) với tồn kho hệ thống trên Haravan (`/com/inventory_locations.json`), tính chênh lệch thừa/thiếu theo từng `(location_id, variant_id)` và lập **Phiếu điều chỉnh tồn kho (`POST /com/inventories/adjustments.json`)** ở chế độ Dry-Run trước khi ghi. Trong vận hành bán lẻ đa kênh tại Việt Nam, điều chỉnh tồn kho sai kho hoặc sai dấu (`+` thành `-`) có thể làm âm tồn trên HaraRetail POS, đẩy tồn ảo lên Shopee/TikTok Shop gây phạt hủy đơn (NFR), và làm sai lệch sổ kế toán giá vốn.

- **Khi nào sử dụng:** Sau khi có biên bản kiểm kê đột xuất, ghi nhận hàng hư hỏng/thất lạc/mẫu chụp hình, hoặc nạp tồn đầu kỳ cho từng kho cụ thể sau khi import sản phẩm mới.
- **Khi nào KHÔNG sử dụng:** Khi chuyển hàng giữa 2 kho của cùng cửa hàng (dùng `inventory-transfer-proposal`), hoặc khi nhập hàng từ nhà cung cấp có đơn PO (dùng phiếu nhập kho `purchase_receives`).
- **Definition of Done (DoD):**
  1. Lấy snapshot tồn kho hiện tại (`qty_onhand`, `qty_commited`, `qty_available`) tại đúng `location_id` qua `GET /com/inventory_locations.json`.
  2. Tính chênh lệch `delta = actual_onhand - system_onhand`, áp dụng ngưỡng kiểm soát chênh lệch lớn (`|delta| > 50` hoặc giá trị chênh `> 10.000.000₫` → gắn cờ `HIGH_VARIANCE`).
  3. Sinh `.backup.json` & `.preview.csv` qua `scripts/dry_run_report.py` và **dừng chờ xác nhận ở lượt hội thoại tiếp theo (`separate_turn: true`)** trước khi gọi `POST /com/inventories/adjustments.json`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đọc tồn kho hiện tại theo kho | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?location_ids={loc_id}&limit=50` |
| Tạo phiếu điều chỉnh tồn kho (sau duyệt) | `com.write_inventories` | `POST https://apis.haravan.com/com/inventories/adjustments.json` |

**JSON Request Payload (`POST https://apis.haravan.com/com/inventories/adjustments.json`):**
```json
{
  "inventory_adjustment": {
    "location_id": 1001234,
    "type": "set",
    "reason": "shrinkage",
    "note": "Kiem ke dot xuat Kho Thu Duc 2026-11-25 - Ma phieu KK-261125",
    "line_items": [
      {
        "product_id": 1058923401,
        "product_variant_id": 1129045512,
        "quantity": 42
      },
      {
        "product_id": 1058923401,
        "product_variant_id": 1129045513,
        "quantity": 18
      }
    ]
  }
}
```

**Sample Response (`201 Created`):**
```json
{
  "inventory_adjustment": {
    "id": 88012345,
    "tran_number": "ADJ-20261125-001",
    "location_id": 1001234,
    "type": "set",
    "status": "completed",
    "created_at": "2026-11-25T08:00:15Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `location_id` | integer | Có | — | ID kho cần điều chỉnh (xác minh tồn tại & `status == "active"`). |
| `adjustment_type` | enum (`set`, `adjust`) | Có | `set` | `set`: đặt lại tồn thực tế (`qty_onhand`); `adjust`: cộng/trừ lượng `delta`. |
| `count_file` | string (path) | Có | — | File CSV gồm `sku` (hoặc `variant_id`), `actual_qty`, `reason`. |
| `reason` | string | Có | `"stocktake"` | Lý do chuẩn hóa (`stocktake`, `shrinkage`, `damaged`, `sample`, `opening_balance`). |
| `variance_alert_qty` | integer | Không | `50` | Ngưỡng chênh lệch số lượng cảnh báo kiểm đếm lại trước khi ghi. |
| `max_records` | integer | Không | `100` | Tối đa 100 dòng SKU mỗi phiếu điều chỉnh. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức đối chiếu & Kiểm soát `qty_commited` (Hàng đang giữ cho đơn)
Trên Haravan, tồn kho tại mỗi kho gồm 3 chỉ số liên kết:
```text
qty_available = qty_onhand - qty_commited
delta = actual_onhand - system_qty_onhand
projected_available = actual_onhand - system_qty_commited
```
Quy trình 5 bước bắt buộc:
1. **Snapshot tồn kho hệ thống:** Gọi `GET /com/inventory_locations.json?location_ids={location_id}` lấy `qty_onhand`, `qty_commited`, `qty_available`, `updated_at`.
2. **Kiểm tra ràng buộc vật lý:** Chặn nếu `actual_onhand < 0`. Nếu `projected_available < 0` (tồn thực tế thấp hơn số hàng đang có đơn chưa xuất kho `qty_commited`), gắn cờ **CRITICAL_COMMITED_CONFLICT** để kho xử lý đơn đang mở trước.
3. **Loại bỏ dòng không đổi (Idempotency):** Nếu `delta == 0`, bỏ qua không đưa vào `line_items`.
4. **Ước tính giá trị chênh lệch (Operational Estimate):** `variance_value_vnd = delta * variant.price` (hoặc `cost_price` nếu có) để quản lý nhìn rõ tác động tài chính.
5. **Tạo Dry-Run Artifact & Dừng chờ xác nhận lượt sau:** Lưu snapshot trước khi ghi vào `.backup.json` và bảng diff vào `.preview.csv`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Phiếu Điều Chỉnh Tồn Kho (DRY-RUN — Chờ Xác Nhận Ở Lượt Tiếp Theo)
- **Kho áp dụng:** `Kho Tổng Thủ Đức` (`location_id: 1001234`) | **Loại:** `set` | **Lý do:** `stocktake`
- **Tổng SKU thay đổi:** `14` | **Tổng lệch dương:** `+12` SP | **Tổng lệch âm:** `-27` SP | **Cảnh báo `qty_commited`:** `1` SKU

| Variant ID | SKU | Onhand cũ | Commited | Onhand mới | Chênh lệch (`delta`) | Available dự kiến | Cảnh báo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `1129045512` | `ATN-250-DEN-M` | 45 | 5 | 42 | `-3` | `37` | OK |
| `1129045513` | `ATN-250-DEN-L` | 25 | 20 | 18 | `-7` | `-2` | **CRITICAL (`< commited`)** |

> *Tuyên bố tài chính:* Giá trị chênh lệch ước tính là **Operational Estimate**, không thay thế biên bản hạch toán kế toán kho.

### JSON Output Schema
```json
{
  "skill": "inventory-adjustment-proposal",
  "dry_run": true,
  "separate_turn_confirmation_required": true,
  "location_id": 1001234,
  "summary": { "changed_skus": 14, "positive_delta_units": 12, "negative_delta_units": -27, "commited_conflicts": 1 },
  "artifacts": {
    "backup_json": "artifacts/hrv-inventory-adjustment-proposal-20261125T080000Z.backup.json",
    "preview_csv": "artifacts/hrv-inventory-adjustment-proposal-20261125T080000Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Separate-Turn Confirmation (`separate_turn: true`, `risk: high`):** Không bao giờ gọi `POST /com/inventories/adjustments.json` trong cùng lượt tạo preview.
- **Kiểm tra biến động giữa lúc Dry-Run và Apply:** Trước khi gửi `POST`, gọi lại `GET /com/inventory_locations.json` kiểm tra `qty_onhand` có vừa thay đổi do phát sinh đơn mới không; nếu có thay đổi → dừng và tính lại `delta` (đặc biệt khi dùng `type: "set"`).
- **Post-Write Verification:** Gọi `GET /com/inventory_locations.json` xác nhận `qty_onhand` đã cập nhật đúng số lượng.
- **Rollback:** Haravan không cho phép xóa phiếu điều chỉnh đã hoàn tất; rollback bằng cách tạo **phiếu điều chỉnh bù ngược dấu** (`type: "adjust"`, `delta = -applied_delta`, `note: "Rollback ADJ-..."`) dựa trên `.backup.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | `variant_id` không tồn tại, sản phẩm tắt quản lý tồn (`inventory_management: null`), hoặc `location_id` bị inactive | Lọc bỏ sản phẩm không quản lý tồn kho trước khi lập phiếu; dừng batch theo `partial_failure_policy: stop`. |
| `403 Forbidden` | Thiếu `com.write_inventories` | Bổ sung scope ghi tồn kho cho Private App. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Dùng `type: "set"` trong giờ cao điểm bán hàng (POS + Sàn TMĐT):** Nếu kiểm kê lúc 14:00 (tồn = 42), đến 14:30 mới bấm áp dụng `set = 42`, trong 30 phút đó cửa hàng vừa bán 5 cái thì `set = 42` sẽ vô tình cộng dư 5 cái ảo! Giải pháp: đóng băng giao dịch kho khi kiểm kê hoặc dùng `type: "adjust"` theo `delta` đã kiểm chứng.
2. **Đẩy tồn kho tự động lên Shopee/TikTok/Lazada:** Ngay khi phiếu điều chỉnh hoàn tất, Haravan Omnichannel sẽ đồng bộ tồn mới lên sàn; nếu đẩy về `0` khi đang chạy Flash Sale sàn có thể bị phạt.
3. **Biến thể có 2 dòng trùng SKU trong file CSV kiểm kê:** Phải cộng gộp số đếm cùng SKU/variant từ nhiều kệ hàng trước khi so với `system_qty_onhand`, tránh ghi đè mất số đếm của kệ trước.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `inventory-stocktake-cycle-count`, `catalog-duplicate-sku-barcode`.
- **Chạy tiếp theo:** `inventory-multi-location-audit` (kiểm tra lại cân bằng toàn hệ thống sau khi điều chỉnh).
