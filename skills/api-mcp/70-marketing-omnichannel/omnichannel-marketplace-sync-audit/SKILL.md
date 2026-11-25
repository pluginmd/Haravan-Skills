---
name: omnichannel-marketplace-sync-audit
description: "Kiểm tra sức khỏe đồng bộ đơn hàng và tồn kho giữa Haravan Omni với Harasocial, HaraRetail POS và các sàn TMĐT (Shopee, Lazada, TikTok Shop)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 70-marketing-omnichannel
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_inventories
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/products.json"
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

# Haravan Omnichannel & Marketplace Sync Health Audit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Giám sát sức khỏe đồng bộ đa kênh giữa lõi Haravan Omni với Haraweb, HaraRetail POS, Harasocial và các sàn TMĐT (Shopee, Lazada, TikTok Shop, Tiki) nhằm phát hiện sớm 3 sự cố đắt giá nhất: (1) Đứt kết nối token sàn (một kênh đột ngột về 0 đơn), (2) SKU sàn chưa mapping về `variant_id` Haravan khiến tồn kho không tự trừ, và (3) Bán vượt tồn (`oversell`) dẫn đến phạt điểm sao quả tạ/hủy đơn trên Shopee và TikTok Shop.
- **Ngữ cảnh Haravan:** Trong hệ sinh thái Haravan Omni, đơn hàng từ các kênh đổ về `/com/orders.json` kèm trường `source_name` (ví dụ: `web`, `pos`, `harasocial`, `shopee`, `lazada`, `tiktokshop`). Khi token sàn hết hạn hoặc nhân sự đổi SKU trên Seller Center mà quên map lại trên Haravan, đơn vẫn về nhưng `line_items[].variant_id == null` hoặc dừng hẳn luồng đơn mà không ai hay biết cho đến khi kho báo lệch.
- **Definition of Done (DoD):**
  1. Dựng bảng Channel Pulse (số đơn từng ngày theo `source_name` trong `lookback_days`, mặc định 7 ngày) và phát hiện kênh sụt giảm bất thường.
  2. Thống kê toàn bộ `line_items` thiếu mapping (`variant_id == null` hoặc `sku == ""`) từ các đơn sàn TMĐT.
  3. Đối chiếu tồn kho khả dụng (`qty_available`) tại các kho bán đa kênh để cảnh báo SKU có `qty_available <= 0` hoặc tồn âm.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_inventories`, `com.read_products` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/inventory_locations.json`, `GET /com/products.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from datetime import datetime, timedelta, timezone
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
orders = client.paginate("com", "/orders.json", "orders", params={"created_at_min": since}, limit=50, max_pages=100)
inv_locs = client.paginate("com", "/inventory_locations.json", "inventory_locations", limit=50, max_pages=100)
```

**Ví dụ JSON đơn sàn có lỗi chưa mapping SKU (`variant_id: null`):**
```json
{
  "id": 1492099112,
  "order_number": "#SP26110045",
  "source_name": "shopee",
  "created_at": "2026-11-25T09:15:00+07:00",
  "line_items": [
    { "id": 9981201, "product_id": null, "variant_id": null, "sku": "SP-AO-KHOAC-XL", "title": "Áo khoác gió 2 lớp (Shopee)", "quantity": 2, "price": "350000" }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | `integer` | Không | `7` | Phạm vi `3..30` ngày để tính đường cơ sở nhịp độ đơn theo kênh. |
| `drop_alert_threshold_pct` | `number` | Không | `80` | Cảnh báo đứt đồng bộ nếu số đơn hôm nay/hôm qua giảm > `80%` so với trung bình 6 ngày trước (khi TB >= 5 đơn/ngày). |
| `low_buffer_qty` | `integer` | Không | `3` | Ngưỡng tồn kho đệm nguy hiểm trên sàn TMĐT (`0 < qty_available <= 3`). |
| `max_records` | `integer` | Không | `5000` | Giới hạn bản ghi tối đa cho mỗi lần quét. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Phát hiện Đứt kết nối Kênh (Channel Pulse Anomaly):**
   - Nhóm đơn theo `(source_name, date_vn)`. Với mỗi kênh có trung bình 6 ngày trước $\bar{O}_{\text{prev6}} \ge 5$ đơn/ngày:
     $$\text{Drop \%} = \frac{\bar{O}_{\text{prev6}} - O_{\text{latest}}}{\bar{O}_{\text{prev6}}} \times 100\%$$
   - Nếu $O_{\text{latest}} == 0$ -> gắn **`P0: SYNC_SILENT_FAILURE`** (nghi ngờ hết hạn token sàn Shopee/TikTok/Lazada).
   - Nếu $\text{Drop \%} \ge \text{drop\_alert\_threshold\_pct}$ -> gắn **`P1: CHANNEL_DROP_ALERT`**.
2. **Phát hiện Lỗi Mapping SKU trên Đơn Sàn:**
   - Duyệt toàn bộ `line_items` của các đơn có `source_name` thuộc sàn TMĐT (`shopee`, `lazada`, `tiktokshop`, `tiki`).
   - Đánh dấu **`P0: UNMAPPED_MARKETPLACE_SKU`** nếu `variant_id == null` hoặc `product_id == null`. Tính tỷ lệ lỗi mapping:
     $$\text{Unmapped Rate} = \frac{N_{\text{unmapped\_lines}}}{N_{\text{total\_marketplace\_lines}}} \times 100\%$$
3. **Phát hiện Rủi ro Bán Vượt Tồn (Oversell Risk):**
   - Từ `GET /com/inventory_locations.json`, lọc các bản ghi có `qty_available < 0` (**`P0: NEGATIVE_INVENTORY_OVERSELL`**) hoặc `0 <= qty_available <= low_buffer_qty` trên những SKU có phát sinh đơn sàn trong 7 ngày qua (**`P1: LOW_OMNI_BUFFER`**).
4. **Đề xuất khắc phục:** Chỉ rõ đường dẫn trong Haravan Admin để nhân sự kết nối lại token sàn hoặc mapping lại SKU.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Sức khỏe Đồng bộ Đa kênh Haravan Omni (7 ngày gần nhất)
- **Tổng đơn quét:** 1,284 | **Tỷ lệ Unmapped SKU sàn:** 2.4% (14 dòng hàng) | **SKU tồn âm:** 3 SKU

#### 1. Nhịp độ Kênh bán (Channel Pulse)
| Kênh (`source_name`) | TB 6 ngày trước | Hôm qua | Biến động | Trạng thái |
| --- | ---: | ---: | ---: | --- |
| `shopee` | 82 đơn/ngày | 79 | -3.7% | Ổn định |
| `tiktokshop` | 54 đơn/ngày | 0 | -100.0% | **P0: Nghi đứt token đồng bộ** |
| `web` | 31 đơn/ngày | 35 | +12.9% | Ổn định |
| `pos` | 22 đơn/ngày | 20 | -9.1% | Ổn định |

#### 2. Top SKU Chưa Mapping & Nguy cơ Oversell
| Mức độ | Kênh / Kho | SKU / Variant | Chi tiết lỗi | Hành động |
| --- | --- | --- | --- | --- |
| P0 | `tiktokshop` | Toàn kênh | 0 đơn trong 24h (TB 54 đơn/ngày) | Vào Haravan Admin > Kênh bán hàng > TikTok Shop kết nối lại OAuth |
| P0 | `shopee` | `SP-AO-KHOAC-XL` | 9 đơn chưa map `variant_id` (tồn kho không trừ) | Mapping SKU trên trang quản lý liên kết sàn |
| P0 | Kho HCM | `variant_11203344` | `qty_available = -4` (bán vượt tồn) | Kiểm kê kho thực tế & cập nhật tồn an toàn trên sàn |
```

```json
{
  "skill": "omnichannel-marketplace-sync-audit",
  "lookback_days": 7,
  "channel_pulse": [
    { "source_name": "tiktokshop", "avg_prev6": 54.0, "latest_day": 0, "drop_pct": 100.0, "status": "P0_SYNC_SILENT_FAILURE" }
  ],
  "unmapped_skus": [
    { "source_name": "shopee", "sku": "SP-AO-KHOAC-XL", "affected_orders": 9, "total_qty_untracked": 14 }
  ],
  "oversell_risks": [
    { "severity": "P0", "variant_id": 11203344, "location_id": 10293, "qty_available": -4 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ gọi các endpoint `GET`. Không tự ý điều chỉnh tồn kho hay hủy đơn sàn.
- **Bảo mật & PII:** `pii_level: none`. Không in thông tin khách hàng từ đơn hàng ra báo cáo.
- **Rollback:** Không áp dụng (`rollback.supported: false`). Mọi thao tác điều chỉnh tồn kho sau khi kiểm kê phải đi qua `inventory-adjustment-executor` (L3) có xác nhận riêng.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng audit, báo làm mới `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu 1 trong 3 scope (`orders`/`inventories`/`products`) | Báo chính xác scope còn thiếu để cấp bổ sung. |
| `404 Not Found` | Endpoint inventory bị sai đường dẫn | Xác minh dùng `/com/inventory_locations.json`. |
| `422 Unprocessable` | Tham số `created_at_min` sai định dạng | Dùng ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`). |
| `429 Too Many Requests` | Quét đồng thời orders + inventories vượt 4 req/s | Chạy tuần tự qua `HaravanClient` (rate 2.5 req/s + backoff). |

- **Edge Case 1 — Kênh mới bật hoặc shop nghỉ lễ / tạm nghỉ POS:** Nếu cửa hàng đóng cửa POS vào Chủ nhật, `pos` về 0 đơn là bình thường. Cần ghi chú kiểm tra lịch hoạt động cửa hàng/gian hàng trước khi kết luận lỗi kỹ thuật.
- **Edge Case 2 — Sản phẩm Combo / Bundle trên sàn:** Một số sàn tạo SKU combo không tồn tại 1-1 trên Haravan khiến `variant_id == null` dù kho vẫn trừ qua app trung gian. Cần phân biệt SKU có tiền tố `COMBO-` để tránh cảnh báo giả.
- **Edge Case 3 — Quá 5.000 đơn trong 7 ngày (Mega Sale):** Khi chạm `max_records: 5000`, thu hẹp `lookback_days` xuống `3` ngày và cảnh báo rõ trong báo cáo.

## 8. Liên kết Workflow & Skill kế tiếp

- **Cân chỉnh tồn kho sau khi phát hiện tồn âm:** Chuyển sang `inventory-stockout-velocity-audit` (L1) và `inventory-adjustment-executor` (L3).
- **Xử lý khẩn cấp khi đứt đồng bộ sàn diện rộng (SEV-2):** Tham chiếu `ops-incident-runbook-escalation` (L0, `incident_type: oversell_sync_break`).
- **Theo dõi hàng ngày vào 8h sáng:** Tích hợp kết quả vào `ops-daily-morning-briefing` (L1).
