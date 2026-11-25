---
name: finance-cod-reconciliation
description: "Đối chiếu tiền thu hộ COD giữa đơn hàng Haravan và biên bản đối soát nhà vận chuyển (GHN/GHTK/VTP/J&T) để phát hiện chênh lệch."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 60-finance-analytics
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/orders/{order_id}/transactions.json"
    - "GET https://apis.haravan.com/com/orders/{order_id}/fulfillments.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
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

# Haravan COD & Carrier Payout Reconciliation Aid (Vietnam)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Đối soát tiền thu hộ **COD (Cash on Delivery)** là điểm nghẽn dòng tiền lớn nhất của doanh nghiệp bán lẻ Việt Nam trên Haravan: mỗi tuần kế toán phải khớp hàng trăm đến hàng nghìn mã vận đơn từ cổng **GHN, GHTK, Viettel Post, J&T** với đơn hàng Haravan để phát hiện đơn đã giao thành công nhưng quá hạn chưa về tiền, đơn bị lệch tiền COD, hoặc đơn hoàn hàng nhưng vẫn bị trừ cước sai. Skill này tự động hóa phép đối chiếu 4 trạng thái (4-State Reconciliation) để rút ngắn thời gian rà soát của kế toán từ hàng giờ xuống vài phút.

**Tiêu chí hoàn thành (Definition of Done):**
- Truy vấn đầy đủ đơn COD trong `[date_from, date_to]` kèm `fulfillments` và `transactions` để tính chính xác `expected_cod` (đã trừ tiền đặt cọc trước).
- Nếu cung cấp `carrier_statement_csv`, đối khớp 1-1 theo `tracking_number` chuẩn hóa để tách chính xác **4 trạng thái đối soát**: `MATCHED`, `AMOUNT_MISMATCH`, `DELIVERED_MISSING_IN_STATEMENT`, và `RETURNED_NOT_RESTOCKED`.
- Đính kèm đầy đủ **Financial Disclaimer** (không khẳng định NVC trả thiếu khi chưa đối chiếu phụ phí bảo hiểm/vượt cân/chuyển hoàn).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/orders/{order_id}/transactions.json`, `GET /com/orders/{order_id}/fulfillments.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate(
    "/com/orders.json",
    params={"status": "any", "created_at_min": "2026-04-01T00:00:00+07:00", "created_at_max": "2026-04-07T23:59:59+07:00", "limit": 50},
    data_key="orders",
    max_records=5000,
)
```

**JSON Response trích xuất từ `GET /com/orders/{id}/fulfillments.json`:**
```json
{
  "fulfillments": [
    {
      "id": 88409112,
      "order_id": 1482081002,
      "tracking_company": "GHN",
      "tracking_number": "GA89X2K1",
      "carrier_status_code": "delivered",
      "carrier_cod_status_code": "codpending",
      "cod_amount": 650000.0,
      "real_shipping_fee": 28500.0,
      "updated_at": "2026-04-03T10:25:00Z"
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `date_from` | string | Yes | — | Ngày bắt đầu kỳ đối soát (`YYYY-MM-DD`, múi giờ `UTC+7`). |
| `date_to` | string | Yes | — | Ngày kết thúc kỳ đối soát (`YYYY-MM-DD`, tối đa 31 ngày/lần). |
| `carrier_statement_csv` | string (path) | No | `null` | File CSV/Excel biên bản đối soát xuất từ cổng NVC (cột bắt buộc: `tracking_number`, `cod_collected`, `shipping_fee`, `other_fee`, `net_payout`). |
| `overdue_payout_days` | integer | No | `7` | Số ngày sau khi `delivered` mà chưa có tiền về được gắn cờ `OVERDUE_COD`. |
| `tolerance_vnd` | integer | No | `1000` | Ngưỡng sai số làm tròn chấp nhận (VND) khi so khớp tiền COD. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Tính COD Kỳ vọng trên Haravan (`expected_cod`):**
   - Với từng đơn có vận đơn hoạt động (`status != "cancelled"`):
     - $\text{PrepaidAmount} = \sum \text{txn.amount}$ (các giao dịch `capture`/`sale` thành công không phải COD).
     - $\text{ExpectedCOD} = \max(0, \text{total\_price} - \text{PrepaidAmount})$ (so đối chiếu thêm với `fulfillment.cod_amount` nếu NVC tự đồng bộ).
2. **Ma trận Đối soát 4 Trạng thái (4-State Reconciliation):**
   - `1. MATCHED`: `tracking_number` khớp trên cả Haravan và `carrier_statement_csv` với $|\text{ExpectedCOD} - \text{StatementCOD}| \le \text{tolerance\_vnd}$.
   - `2. AMOUNT_MISMATCH`: Khớp `tracking_number` nhưng $|\text{ExpectedCOD} - \text{StatementCOD}| > \text{tolerance\_vnd}$ (ghi rõ chênh lệch $\Delta = \text{StatementCOD} - \text{ExpectedCOD}$ và tách riêng `shipping_fee` + `other_fee` như phí vượt cân, phí bảo hiểm, phí giao lại).
   - `3. DELIVERED_MISSING_IN_STATEMENT`: Đơn Haravan ở trạng thái `delivered` quá `overdue_payout_days` nhưng **không xuất hiện** trong biên bản NVC hoặc `carrier_cod_status_code == "codpending"`.
   - `4. RETURNED_NOT_RESTOCKED`: Đơn trên biên bản NVC ghi nhận `returned` (phát sinh phí chuyển hoàn) nhưng trên Haravan chưa hủy/hoàn hoặc chưa ghi nhận nhập kho hoàn.
3. **Tính Tiền thực nhận kỳ vọng (Net Payout Estimate):** $\text{NetPayout} = \sum \text{StatementCOD} - \sum (\text{ShippingFee} + \text{ReturnFee} + \text{InsuranceFee} + \text{OverweightFee})$.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Tổng hợp Đối soát COD theo Nhà vận chuyển (01/04/2026 – 07/04/2026):**
| NVC | Tổng đơn COD | Khớp (`MATCHED`) | Lệch COD (`MISMATCH`) | Đã giao chưa có BB (`MISSING`) | Hoàn chưa khớp (`RETURNED`) | COD kỳ vọng (VND) | Thực nhận NVC (VND) | Chênh lệch (VND) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GHN | 182 | 175 | 2 | 3 | 2 | 118.400.000 | 115.150.000 | -3.250.000 |
| GHTK | 140 | 137 | 1 | 1 | 1 | 84.200.000 | 83.600.000 | -600.000 |
| Viettel Post | 64 | 55 | 2 | 6 | 1 | 42.800.000 | 38.900.000 | -3.900.000 |

**Chi tiết Vận đơn Lệch cần Kế toán Đối chiếu:**
| Trạng thái | Mã đơn | NVC | Mã tracking | Expected COD | Statement COD | Chênh lệch | Ghi chú nguyên nhân nghi ngờ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AMOUNT_MISMATCH` | `#109044` | GHN | `GA89X2K1` | 650.000 | 450.000 | -200.000 | Khách đã cọc CK 200k nhưng vận đơn ghi sai? |
| `DELIVERED_MISSING_IN_STATEMENT` | `#108991` | Viettel Post | `VTP8810293` | 1.150.000 | 0 | -1.150.000 | Giao xong 9 ngày (VTP đối soát chu kỳ T+7) |

```json
{
  "skill": "finance-cod-reconciliation",
  "disclaimer": "Operational Estimate / Reconciliation Aid — không khẳng định sai lệch thanh toán của NVC khi chưa đối chiếu chứng từ gốc và bảng kê phụ phí.",
  "period": { "from": "2026-04-01", "to": "2026-04-07" },
  "summary_by_state": { "MATCHED": 367, "AMOUNT_MISMATCH": 5, "DELIVERED_MISSING_IN_STATEMENT": 10, "RETURNED_NOT_RESTOCKED": 4 },
  "discrepancies": [
    {
      "state": "AMOUNT_MISMATCH",
      "order_id": 1482081002,
      "order_name": "#109044",
      "carrier": "GHN",
      "tracking_number": "GA89X2K1",
      "expected_cod_vnd": 650000,
      "statement_cod_vnd": 450000,
      "delta_vnd": -200000
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Financial Disclaimer Bắt buộc:**
  > *Tuyên bố trách nhiệm tài chính: Báo cáo này là **Operational Estimate / Reconciliation Aid** hỗ trợ kế toán rà soát nhanh, không phải chứng từ kế toán chính thức và không kết luận NVC trả thiếu khi chưa đối chiếu bảng kê phụ phí (phí vượt cân, phí bảo hiểm, phí chuyển hoàn, phí lưu kho) và sao kê ngân hàng.*
- **Chế độ Read-Only (L1):** Tuyệt đối **không tự động bấm xác nhận đã thanh toán (`paid`)** trên đơn hàng Haravan sau khi khớp CSV.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, báo thiếu quyền đọc đơn hàng. |
| `404 Not Found` | Đơn bị xóa hoặc ID sai | Bỏ qua và ghi log vào danh sách `unmatched_rows`. |
| `422 Unprocessable` | Định dạng ngày `date_from`/`date_to` sai | Chuẩn hóa về `YYYY-MM-DD`. |
| `429 Too Many Requests` | Gọi `transactions.json` cho hàng trăm đơn | Chỉ gọi `transactions.json` cho các đơn `partially_paid` hoặc có chênh lệch; backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **GHN/GHTK tự động đồng bộ `carrier_cod_status_code` vs Viettel Post nhập tay:** Với GHN/GHTK, Haravan nhận webhook `codreceipt` khi NVC đối soát; còn với Viettel Post hoặc J&T nhập mã thủ công, trạng thái COD trên Haravan mãi là `codpending` dù tiền đã về ngân hàng — bắt buộc đối chiếu bằng `carrier_statement_csv`.
2. **Giao hàng một phần (Partial Delivery / Khách chỉ nhận 1 trong 2 sản phẩm và trả bớt tiền):** GHTK/GHN cho phép thu hộ ít hơn số ban đầu nếu shop mở tính năng giao 1 phần; sẽ hiện ở `AMOUNT_MISMATCH` và cần kế toán đối chiếu phiếu nhận hoàn phần còn lại.
3. **Đơn giao cuối kỳ đối soát (Cutoff T+3 / T+5):** Đơn giao ngày 06–07/04 thường chỉ lên bảng kê đối soát của tuần sau (10–12/04); chỉ đánh cờ `OVERDUE_COD` khi đã quá `overdue_payout_days` (mặc định 7 ngày) kể từ ngày `delivered`.

## 8. Liên kết Workflow & Skill kế tiếp
- **Kiểm tra NVC có nhiều đơn hoàn/chậm đối soát:** Chuyển sang `fulfillment-carrier-sla-vn`.
- **Kiểm tra nhập kho cho nhóm `RETURNED_NOT_RESTOCKED`:** Chuyển sang `returns-reason-restock-proposal`.
