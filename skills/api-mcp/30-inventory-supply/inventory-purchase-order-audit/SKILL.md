---
name: inventory-purchase-order-audit
description: "Theo dõi tiến độ đơn đặt hàng nhà cung cấp (PO) và đối chiếu phiếu nhập kho thực tế (/com/inventories/purchase_orders.json & purchase_receives.json)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 30-inventory-supply
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_inventories
  endpoints:
    - "GET https://apis.haravan.com/com/inventories/purchase_orders.json"
    - "GET https://apis.haravan.com/com/v2/inventories/purchase_receives.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 1000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---
# Inventory Purchase Order Audit — Kiểm Toán Đơn Đặt Hàng NCC (PO) & Phiếu Nhập Kho

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` theo dõi toàn bộ vòng đời đơn đặt hàng nhà cung cấp (Purchase Orders — `/com/inventories/purchase_orders.json`) và đối chiếu 3 chiều với phiếu nhập kho thực tế (`/com/v2/inventories/purchase_receives.json`). Trong chuỗi cung ứng bán lẻ Việt Nam (nhập hàng từ xưởng may, nhà phân phối hoặc đánh hàng Quảng Châu/Thái Lan), việc thiếu đối chiếu PO vs Phiếu nhập thường dẫn đến 3 thất thoát lớn: (1) Đơn PO quá hạn giao nhưng thu mua không biết để hối NCC, (2) NCC giao thiếu hàng (short-delivery) kéo dài không đóng phiếu khiến `qty_incoming` bị sai, và (3) Nhập dư hoặc lệch đơn giá nhập so với PO đã duyệt.

- **Khi nào sử dụng:** Họp giao ban chuỗi cung ứng/thu mua hàng tuần, trước khi thanh toán công nợ nhà cung cấp, hoặc khi kiểm tra lượng hàng sắp về (`incoming stock`) trước chiến dịch lớn.
- **Khi nào KHÔNG sử dụng:** Khi muốn tự động tạo hoặc đóng phiếu PO (skill này chỉ đọc và kiểm toán; thao tác ghi PO/nhập kho thực hiện theo quy trình duyệt riêng).
- **Definition of Done (DoD):**
  1. Tải danh sách `purchase_orders` và `purchase_receives` trong cửa sổ thời gian chỉ định (`lookback_days`, mặc định 90 ngày).
  2. Đối chiếu từng PO: tính tỷ lệ hoàn thành nhập kho (`received_qty / ordered_qty`), số ngày quá hạn (`overdue_days`), và chênh lệch số lượng/giá trị nhập.
  3. Xuất báo cáo danh sách PO quá hạn, PO giao thiếu kéo dài, và bảng đánh giá hiệu suất giao hàng theo từng Nhà cung cấp (Supplier On-Time In-Full — OTIF).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Danh sách Đơn đặt hàng NCC (PO) | `com.read_inventories` | `GET https://apis.haravan.com/com/inventories/purchase_orders.json?limit=50` |
| Danh sách Phiếu nhập kho thực tế (v2) | `com.read_inventories` | `GET https://apis.haravan.com/com/v2/inventories/purchase_receives.json?limit=50` |

**Chạy thu thập bằng `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True, req_per_sec=2.5)
pos = c.paginate("com", "/inventories/purchase_orders.json", key="purchase_orders", max_records=1000)
receives = c.paginate("com", "/v2/inventories/purchase_receives.json", key="purchase_receives", max_records=1000)
```

**Sample Response (`GET /com/inventories/purchase_orders.json?limit=1`):**
```json
{
  "purchase_orders": [
    {
      "id": 6001234,
      "tran_number": "PO-202611-018",
      "supplier_name": "Xưởng May Minh Phát",
      "location_id": 1001234,
      "status": "receiving",
      "expected_date": "2026-11-18T00:00:00Z",
      "total_quantity": 500,
      "received_quantity": 320,
      "total_amount": 85000000.0,
      "created_at": "2026-11-05T03:00:00Z"
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | Không | `90` | Cửa sổ ngày quét PO & phiếu nhập (`30..365`). |
| `stale_open_po_days` | integer | Không | `30` | PO mở hoặc nhập dở quá `30` ngày không có phiếu nhập mới → gắn cờ `STALE`. |
| `supplier_filter` | string | Không | `""` | Lọc theo tên hoặc ID nhà cung cấp cụ thể. |
| `max_records` | integer | Không | `1000` | Giới hạn bản ghi quét cho mỗi endpoint. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức Đối chiếu 3 Chiều & Chỉ số OTIF Nhà Cung Cấp
Với mỗi PO `p` không ở trạng thái `cancelled`:
```text
fill_rate_pct = (received_qty / ordered_qty) * 100
remaining_qty = max(0, ordered_qty - received_qty)
overdue_days = (now - expected_date).days   (nếu status chưa completed và now > expected_date)
```
Phân loại 4 nhóm rủi ro PO:
1. **`OVERDUE_PO` (`HIGH`):** `status in ("open", "receiving")` AND `overdue_days > 0`.
2. **`PARTIAL_STALE` (`MEDIUM`):** `0 < fill_rate_pct < 100` AND không có phiếu nhập (`purchase_receives`) mới trong `stale_open_po_days` → thường NCC đã dừng giao phần thiếu nhưng kho quên đóng PO.
3. **`OVER_RECEIVED` (`HIGH`):** `received_qty > ordered_qty` (nhập vượt số lượng đặt ban đầu → cần kiểm tra sai sót đếm hàng hoặc duyệt phát sinh).
4. **Hiệu suất NCC (`Supplier OTIF`):** Tỷ lệ % số PO của từng nhà cung cấp đạt đồng thời **Đúng hạn (`actual_receive_date <= expected_date`)** và **Đủ số lượng (`fill_rate >= 98%`)**.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Kiểm toán PO & Nhập Kho (90 ngày gần nhất)
- **Tổng số PO:** `42` | **Hoàn tất:** `31` | **Đang nhập dở:** `6` | **Quá hạn giao:** `4` | **Nhập vượt PO:** `1`

| Mã PO | Nhà cung cấp | Ngày dự kiến | Đặt / Đã nhập | Tỷ lệ nhập | Trạng thái rủi ro | Hành động đề xuất |
| --- | --- | --- | --- | --- | --- | --- |
| `PO-202611-018` | Xưởng May Minh Phát | 2026-11-18 | `500 / 320` | 64.0% | `OVERDUE (+7 ngày)` | Hối giao 180 SP còn thiếu |
| `PO-202610-009` | NPP Vải Gia Hưng | 2026-10-20 | `200 / 180` | 90.0% | `PARTIAL_STALE (36d)` | Xác nhận chốt đóng PO nếu không giao tiếp |
| `PO-202611-021` | Công ty Bao Bì Việt | 2026-11-22 | `1.000 / 1.050` | 105.0% | `OVER_RECEIVED (+50)` | Đối chiếu biên bản giao hàng trước khi trả công nợ |

> *Tuyên bố tài chính:* Giá trị PO và chênh lệch nhập là **Reconciliation Aid** cho vận hành, không thay thế chứng từ hóa đơn GTGT và đối soát công nợ kế toán.

### JSON Output Schema
```json
{
  "skill": "inventory-purchase-order-audit",
  "lookback_days": 90,
  "summary": { "total_pos": 42, "completed": 31, "overdue": 4, "partial_stale": 3, "over_received": 1 },
  "overdue_pos": [
    { "po_id": 6001234, "tran_number": "PO-202611-018", "supplier": "Xưởng May Minh Phát", "overdue_days": 7, "remaining_qty": 180 }
  ],
  "supplier_otif": [{ "supplier": "Xưởng May Minh Phát", "po_count": 8, "otif_pct": 62.5, "avg_delay_days": 4.2 }]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ đọc `purchase_orders` và `purchase_receives`, không chỉnh sửa trạng thái đơn nhập hay công nợ NCC.
- **Bảo mật dữ liệu thương mại:** Không chia sẻ công khai giá nhập / danh sách nhà cung cấp ra ngoài phạm vi nội bộ quản trị.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Gói dịch vụ chưa bật phân hệ Quản lý tồn kho nâng cao (PO/Receive) hoặc thiếu `com.read_inventories` | Thông báo rõ yêu cầu gói Omni/Inventory và kiểm tra lại scope. |
| `404 Not Found` tại `/v2/inventories/purchase_receives.json` | Phiên bản API cửa hàng dùng v1 hoặc chưa có phiếu nhập | Fallback đọc từ trường `received_quantity` trực tiếp trên `purchase_orders.json` và ghi chú rõ. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **PO không nhập trường `expected_date` (`null`):** Rất nhiều nhân viên thu mua bỏ trống ngày dự kiến giao khi tạo PO → không tính được `overdue_days`; gom vào nhóm `MISSING_EXPECTED_DATE` và dùng `created_at + default_lead_time` để nhắc rà soát.
2. **1 PO chia làm nhiều đợt giao hàng (`purchase_receives` 1-nhiều):** Phải cộng dồn toàn bộ `purchase_receives` cùng `purchase_order_id` thay vì chỉ lấy phiếu nhập gần nhất.
3. **Trả hàng nhà cung cấp (Purchase Return):** Nếu có trả lại hàng lỗi cho NCC, số tồn thực nhập ròng sẽ giảm so với tổng `purchase_receives`; cần ghi chú đối chiếu phiếu trả hàng NCC khi làm công nợ.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `inventory-low-stock-watchdog` (kiểm tra xem SKU sắp hết đã có PO đang về chưa).
- **Chạy tiếp theo:** `inventory-stock-velocity-forecast` (sử dụng `avg_lead_time` thực tế của NCC từ báo cáo này để tính Reorder Point chuẩn xác).
