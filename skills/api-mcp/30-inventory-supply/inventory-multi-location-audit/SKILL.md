---
name: inventory-multi-location-audit
description: "Kiểm toán tồn kho đa chi nhánh/kho (/com/inventory_locations.json), phát hiện tồn âm, mất cân bằng giữa kho online và cửa hàng POS."
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
    - com.read_shop
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/locations.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
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
# Inventory Multi-Location Audit — Kiểm Toán Tồn Kho Đa Chi Nhánh & Kho HaraRetail POS

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` kiểm toán phân bổ tồn kho trên tất cả các kho và chi nhánh bán lẻ (`/com/locations.json` kết hợp `/com/inventory_locations.json`) để phát hiện **3 bệnh kinh điển của hệ thống đa kho Haravan Omni**: (1) **Tồn âm (`qty_onhand < 0` hoặc `qty_available < 0`)** do nhân viên POS bán hàng trước khi nhập kho hoặc đồng bộ sàn TMĐT bị trễ, (2) **Kẹt tồn ở kho đóng cửa / kho không bán online (`is_unavailable_quantity: true`)**, và (3) **Mất cân bằng tồn kho (Imbalance)** — kho online/chi nhánh bán chạy cạn hàng trong khi chi nhánh khác ôm tồn số lượng lớn.

- **Khi nào sử dụng:** Định kỳ hàng tuần cho chuỗi cửa hàng có `>= 2` kho/chi nhánh HaraRetail POS, trước các đợt đẩy mạnh đơn online, hoặc khi khách phàn nàn web báo hết hàng dù cửa hàng vẫn còn nhiều.
- **Khi nào KHÔNG sử dụng:** Cửa hàng chỉ có duy nhất 1 kho và chỉ cần kiểm tra hàng sắp hết (dùng `inventory-low-stock-watchdog`).
- **Definition of Done (DoD):**
  1. Đọc toàn bộ `locations` (phân biệt `active` vs `inactive`, `is_primary`, `is_unavailable_quantity`) và `inventory_locations`.
  2. Phát hiện 100% bản ghi **tồn âm**, **tồn kẹt ở kho inactive**, **`qty_commited > qty_onhand`**, và danh sách **cặp kho mất cân bằng** có thể điều chuyển ngay.
  3. Xuất ma trận phân bổ tồn theo từng kho kèm danh sách ưu tiên xử lý.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Danh sách kho & chi nhánh POS | `com.read_shop` | `GET https://apis.haravan.com/com/locations.json` |
| Tồn kho chi tiết theo `(location_id, variant_id)` | `com.read_inventories` | `GET https://apis.haravan.com/com/inventory_locations.json?limit=50` |
| Tên sản phẩm & SKU để hiển thị báo cáo | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,variants` |

**Chạy thu thập đa kho qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True, req_per_sec=2.5)
locations = {loc["id"]: loc for loc in (c.get("com", "/locations.json").get("locations") or [])}
inv_rows = c.paginate("com", "/inventory_locations.json", key="inventory_locations", max_records=5000)
```

**Sample Response (`GET /com/inventory_locations.json`):**
```json
{
  "inventory_locations": [
    { "location_id": 1001234, "variant_id": 1129045512, "qty_onhand": 0, "qty_commited": 2, "qty_available": -2 },
    { "location_id": 1001235, "variant_id": 1129045512, "qty_onhand": 38, "qty_commited": 0, "qty_available": 38 },
    { "location_id": 1001239, "variant_id": 1129045512, "qty_onhand": 15, "qty_commited": 0, "qty_available": 15 }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `primary_online_location_id` | integer | Không | Auto-detect (`is_primary == true`) | Kho chính phục vụ đơn online để kiểm tra mất cân bằng. |
| `surplus_threshold` | integer | Không | `15` | Kho phụ có `qty_available >= 15` trong khi kho chính `<= 3` bị gắn cờ `IMBALANCED`. |
| `flag_commited_overflow` | boolean | Không | `true` | Cảnh báo khi `qty_commited > qty_onhand` (oversell). |
| `max_records` | integer | Không | `5000` | Trần số dòng `inventory_locations` quét. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### 4 Luật Kiểm Toán Đa Kho (Multi-Location Anomaly Rules)
1. **Rule M1 — Tồn Âm (`CRITICAL`):** `qty_onhand < 0` OR `qty_available < 0`. Phân biệt rõ 2 nguyên nhân:
   - `qty_onhand < 0`: lỗi thao tác POS bán vượt tồn thực tế hoặc chưa nhập phiếu PO.
   - `qty_onhand >= 0` nhưng `qty_available < 0` (`qty_commited > qty_onhand`): oversell do đồng bộ đơn sàn TMĐT chậm hơn thực tế.
2. **Rule M2 — Tồn Kẹt Ở Kho Đóng Cửa / Kho Ẩn (`HIGH`):** `qty_onhand > 0` tại `location` có `status != "active"` hoặc `is_unavailable_quantity == true` (hàng tồn trong hệ thống nhưng khách online không mua được).
3. **Rule M3 — Mất Cân Bằng Kho Online vs POS (`MEDIUM`):** Tại cùng `variant_id`, `primary_loc.qty_available <= 3` nhưng tồn tại kho phụ `other_loc.qty_available >= surplus_threshold` → tính ngay lượng đề xuất chuyển `suggested_transfer = floor(other_loc.qty_available * 0.5)`.
4. **Rule M4 — Độ phủ tồn kho theo chi nhánh:** Tính `% SKU còn hàng (In-stock rate)` tại từng chi nhánh để nhận diện chi nhánh bị hụt hàng nghiêm trọng.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Kiểm toán Tồn kho Đa Chi Nhánh (Markdown)
| Kho / Chi nhánh | Trạng thái | Tổng tồn (Onhand) | Đang giữ (Commited) | SKU Tồn âm | Tỷ lệ còn hàng |
| --- | --- | --- | --- | --- | --- |
| `Kho Tổng Thủ Đức` (`1001234`, Primary) | Active | 6.420 | 185 | `2` (Oversell) | 88.4% |
| `Cửa hàng Quận 1` (`1001235`, POS) | Active | 2.150 | 12 | `3` (POS âm) | 74.2% |
| `Kho Sự Kiện Popup` (`1001239`) | Inactive | `145` (**Kẹt tồn!**) | 0 | `0` | N/A |

**Cặp mất cân bằng sẵn sàng điều chuyển (Top 2):**
- `ATN-250-DEN-M`: Kho Tổng `available = -2`, Kho Quận 1 `available = 38` → Đề xuất chuyển `20` cái từ Q.1 về Kho Tổng (hoặc xử lý oversell).

### JSON Output Schema
```json
{
  "skill": "inventory-multi-location-audit",
  "locations_count": 3,
  "summary": { "negative_onhand_rows": 3, "oversell_available_rows": 2, "stranded_inactive_units": 145, "imbalanced_skus": 11 },
  "transfer_candidates": [
    { "variant_id": 1129045512, "sku": "ATN-250-DEN-M", "from_location_id": 1001235, "to_location_id": 1001234, "suggested_qty": 20 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ phân tích và đề xuất; mọi thao tác sửa tồn âm hoặc chuyển kho phải chuyển sang `inventory-adjustment-proposal` hoặc `inventory-transfer-proposal`.
- **Cảnh báo Partial Sample:** Cửa hàng có 5 kho × 2.000 SKU = 10.000 dòng `inventory_locations` sẽ vượt `max_records=5000`; bắt buộc lọc theo từng `location_ids` hoặc bật cảnh báo `partial_sample: true`.
- **Tách biệt kho bán online vs kho trưng bày/lỗi:** Luôn gắn nhãn rõ trạng thái `is_unavailable_quantity` của từng kho trong báo cáo để tránh đề xuất chuyển nhầm hàng lỗi sang kho bán chính.
- **PII:** Không chứa thông tin cá nhân (`pii_level: none`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu `com.read_inventories` hoặc `com.read_shop` | Cấp đủ 2 scope đọc. |
| `429 Too Many Requests` | Bảng `inventory_locations` rất lớn | Truyền `location_ids=` để chia nhỏ theo từng kho và chạy `<= 2.5 req/s`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Kho hàng lỗi / Kho bảo hành / Kho mẫu chụp ảnh cố tình để `is_unavailable_quantity: true`:** Không nên báo lỗi oan các kho có tên chứa `"lỗi"`, `"bảo hành"`, `"hủy"` ở Rule M2 — tách riêng thành nhóm `Non-Sellable Stock` để theo dõi định kỳ.
2. **Đơn hàng đã hủy nhưng `qty_commited` chưa được giải phóng (kẹt tồn ảo):** Nếu phát hiện SKU có `qty_commited > 0` liên tục nhiều ngày dù không có đơn mới, cảnh báo kiểm tra các đơn đang treo trạng thái `pending` / `picking` chưa hủy hẳn.
3. **Bản ghi `inventory_locations` của biến thể đã bị xóa:** Một số dòng `variant_id` không khớp với `products.json` hiện tại → đánh dấu `orphan_inventory_record` và bỏ qua khi lập lệnh chuyển kho.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `store-config-audit` (kiểm tra danh sách kho hợp lệ).
- **Chạy tiếp theo:** `inventory-transfer-proposal` (điều chuyển giữa các kho mất cân bằng), `inventory-adjustment-proposal` (xử lý tồn âm sau khi kiểm đếm thực tế).
