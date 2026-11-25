---
name: returns-reason-restock-proposal
description: "Phân tích nguyên nhân hoàn/trả hàng (size, lỗi SX, bom hàng COD) và lập phiếu đề xuất nhập lại kho hàng đạt chuẩn."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 40-orders-fulfillment
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_inventories
    - com.write_inventories
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/orders/{order_id}/refunds.json"
    - "POST https://apis.haravan.com/com/inventories/adjustments.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 100
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Returns Analysis & Restock Proposal

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này giải quyết 2 bài toán vận hành thực tế sau hoàn hàng trên Haravan: (1) **Phân tích nguyên nhân gốc rễ (Root-Cause Analysis)** các đơn hoàn/trả theo SKU, NVC và nhóm lý do (sai size/mẫu, lỗi sản xuất, giao chậm, bom hàng COD) để tìm ra Top SKU "đốt tiền hoàn"; và (2) **Lập phiếu đề xuất nhập lại tồn kho (Restock Proposal)** qua `/com/inventories/adjustments.json` **chỉ cho các mặt hàng hoàn đã về kho vật lý và vượt qua kiểm tra QC đạt chuẩn bán lại**.

**Tiêu chí hoàn thành (Definition of Done):**
- Tổng hợp đầy đủ tỷ lệ hoàn theo SKU và phân loại 5 nhóm nguyên nhân trong `lookback_days`.
- Nếu cung cấp `qc_passed_items_file`, chỉ lập đề xuất điều chỉnh dương (`+qty`) cho bản ghi có `qc_status == "PASS"`, kèm Backup JSON snapshot tồn kho trước khi ghi và Preview CSV.
- Chờ duyệt trước khi gọi `POST /com/inventories/adjustments.json` và xác minh tồn kho mới sau khi ghi.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_inventories`, `com.write_inventories` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/orders/{order_id}/refunds.json`, `POST /com/inventories/adjustments.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=False)  # Chỉ False sau khi duyệt preview
refunds = client.get(f"/com/orders/{order_id}/refunds.json")["refunds"]
res = client.post("/com/inventories/adjustments.json", json_body=adjustment_payload)
```

**JSON Request Payload (`POST /com/inventories/adjustments.json`):**
```json
{
  "inventory_adjustment": {
    "location_id": 101,
    "type": "adjust",
    "reason": "other",
    "note": "Restock hàng hoàn QC-PASS đợt 10/04/2026 (Ref: RET-20260410-01)",
    "line_items": [
      { "product_id": 1001, "product_variant_id": 5001, "quantity": 4 },
      { "product_id": 1003, "product_variant_id": 5003, "quantity": 2 }
    ]
  }
}
```

**JSON Response Payload (HTTP 201 Created):**
```json
{
  "inventory_adjustment": {
    "id": 4401928,
    "location_id": 101,
    "type": "adjust",
    "reason": "other",
    "note": "Restock hàng hoàn QC-PASS đợt 10/04/2026 (Ref: RET-20260410-01)",
    "created_at": "2026-04-10T11:30:00Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `30` | Cửa sổ phân tích đơn hoàn/trả (`7`–`90` ngày). |
| `qc_passed_items_file` | string (path/JSON) | No | `null` | Danh sách hàng hoàn đã QC: `(order_id, location_id, product_variant_id, sku, qty, qc_status)`. Tối đa `100` dòng. |
| `min_sku_orders` | integer | No | `10` | Cỡ mẫu tối thiểu để xếp hạng Top SKU có tỷ lệ hoàn cao bất thường. |
| `dry_run` | boolean | Yes | `true` | Mặc định `true`; bắt buộc chạy preview nếu có `qc_passed_items_file`. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Thu thập & Phân loại Nguyên nhân Hoàn (5 Nhóm chuẩn VN):**
   - Quét đơn có `refunds[]`, `cancelled_at != null` sau khi đã tạo fulfillment, hoặc `fulfillments[].carrier_status_code` $\in$ `{"return", "returning", "returned"}`.
   - Ánh xạ văn bản từ `refund.note` / `cancel_reason` / `carrier_status_name`:
     - `COD_BOOM`: "không nghe máy", "từ chối nhận", "khách không nhận hàng".
     - `SIZE_FIT`: "chật", "rộng", "đổi size", "sai kích cỡ".
     - `PRODUCT_DEFECT`: "lỗi", "rách", "vỡ", "hư hỏng", "thiếu phụ kiện".
     - `DELIVERY_DELAY`: "giao chậm", "quá hẹn", "không cần nữa".
     - `OTHER`: Các lý do khác / chưa ghi chú.
2. **Công thức đo lường theo SKU:**
   - $\text{SKU\_Return\_Rate\%} = \frac{\text{Tổng SL hoàn của SKU}}{\text{Tổng SL đã giao của SKU}} \times 100\%$.
   - $\text{Estimated\_Return\_Loss} = \text{Giá trị hàng hoàn} + (\text{Số đơn hoàn} \times \text{Phí ship 2 chiều ước tính})$.
3. **Kiểm soát Đề xuất Restock (QC Gate):**
   - Lọc cứng: chỉ chấp nhận dòng có `qc_status == "PASS"` và kiểm tra trên Haravan xem `refund_line_items` của `order_id` đó **chưa từng được `restock_type: "return"` tự động** (tránh nhập kho 2 lần!).
   - Sinh Backup JSON ghi nhận `qty_onhand` hiện tại trước khi cộng tồn và Preview CSV qua `scripts/dry_run_report.py`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Phân tích Nguyên nhân Hoàn hàng (30 ngày — 92 đơn hoàn / 1.410 đơn đã giao = 6.5%):**
| Nhóm nguyên nhân | Số đơn hoàn | Tỷ trọng (%) | Giá trị hàng hoàn (VND) | Khuyến nghị khắc phục |
| --- | --- | --- | --- | --- |
| Bom hàng / Không nhận COD (`COD_BOOM`) | 46 | 50.0% | 34.500.000 | Siết gọi xác nhận nhóm `HIGH` COD |
| Sai size / Đổi mẫu (`SIZE_FIT`) | 24 | 26.1% | 16.800.000 | Bổ sung bảng quy đổi chiều cao/cân nặng |
| Lỗi sản xuất / Vỡ khi vận chuyển (`PRODUCT_DEFECT`) | 12 | 13.0% | 8.400.000 | Gia cố chống sốc cho nhóm chai lọ thủy tinh |
| Giao hàng chậm (`DELIVERY_DELAY`) | 10 | 10.9% | 6.200.000 | Đổi NVC tuyến liên miền chậm |

**Preview Đề xuất Nhập lại Kho (QC-PASS — Dry-Run):**
| Kho (`location_id`) | SKU | Variant ID | SL QC-PASS | Trạng thái kiểm tra trùng Restock | Dự kiến điều chỉnh |
| --- | --- | --- | --- | --- | --- |
| Kho HCM (`101`) | `TRA-200G` | `5001` | `+4` | Chưa restock trên refund | `ADJUST +4` |
| Kho HCM (`101`) | `TD-50ML` | `5002` | `0` (`QC_FAIL`: vỡ nắp) | Bỏ qua (chuyển kho hàng lỗi) | `SKIP` |

```json
{
  "skill": "returns-reason-restock-proposal",
  "period_days": 30,
  "overall_return_rate_pct": 6.5,
  "top_return_skus": [
    { "sku": "AO-LEN-M", "shipped_qty": 85, "returned_qty": 15, "return_rate_pct": 17.6, "primary_reason": "SIZE_FIT" }
  ],
  "restock_proposal": {
    "mode": "dry_run",
    "backup_artifact": "artifacts/returns-reason-restock-proposal_20260410_backup.json",
    "eligible_adjustments": [{ "location_id": 101, "variant_id": 5001, "sku": "TRA-200G", "delta_qty": 4 }],
    "skipped_qc_fail": [{ "variant_id": 5002, "sku": "TD-50ML", "reason": "QC_FAIL" }]
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chặn Restock Mù (QC Gate):** Tuyệt đối không tự động cộng tồn kho chỉ dựa trên trạng thái `returned` từ NVC khi kho chưa mở kiện kiểm tra vật lý (`qc_status == "PASS"`).
- **Chống Nhập Kho Kép (Double-Restock Guard):** Kiểm tra kỹ trường `restock` trong `refunds.json` để tránh cộng tồn lần 2 nếu nhân viên đã tick "Hoàn trả kho" khi bấm hoàn tiền trên Haravan Admin.
- **Rollback (`supported: true`):** Nếu nhập sai số lượng, tạo phiếu `POST /com/inventories/adjustments.json` với số lượng âm đối ứng (`-delta_qty`) dựa trên Backup JSON.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.write_inventories` khi apply restock | Chạy được phần phân tích (read), chặn bước tạo phiếu adjust và báo thiếu scope. |
| `404 Not Found` | `product_variant_id` hoặc `location_id` đã bị xóa/ẩn | Dừng theo `partial_failure_policy: stop`, báo mã biến thể lỗi. |
| `422 Unprocessable` | Biến thể không bật theo dõi tồn kho (`inventory_management: null`) | Bỏ qua biến thể không quản lý tồn kho, ghi chú rõ trong báo cáo. |
| `429 Too Many Requests` | Quét `refunds.json` cho nhiều đơn | Throttle & backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Hàng hoàn bị móp hộp / rách tem nhưng sản phẩm còn tốt:** Không nên nhập chung vào `location_id` kho bán mới (`Kho Trung Tam`); nên đề xuất chuyển sang `location_id` kho hàng thanh lý/outlet nếu shop có cấu hình nhiều kho.
2. **Đơn hoàn từ sàn Shopee/TikTok chưa về tới kho vật lý (đang nằm ở bưu cục hoàn 5–7 ngày):** Trạng thái trên Haravan có thể đã ghi `refunded` nhưng hàng chưa về kho; tuyệt đối chỉ restock theo danh sách quét mã vạch nhập hoàn thực tế tại kho.
3. **Combo / Bundle sản phẩm:** Nếu SKU bán là combo, khi restock phải kiểm tra xem Haravan quản lý tồn theo SKU combo hay trừ theo từng SKU thành phần để tránh lệch tồn kho gốc.

## 8. Liên kết Workflow & Skill kế tiếp
- **Định lượng thiệt hại tài chính:** Chuyển sang `finance-refund-rate-analysis`.
- **Giảm nhóm nguyên nhân `COD_BOOM`:** Siết ngưỡng cảnh báo tại `order-risk-cod-boom-signals`.
- **Cập nhật tồn kho / kiểm tra NVC gây vỡ/chậm:** Kết hợp `fulfillment-carrier-sla-vn`.
