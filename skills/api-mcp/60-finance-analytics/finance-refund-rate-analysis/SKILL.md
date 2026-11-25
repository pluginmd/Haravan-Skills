---
name: finance-refund-rate-analysis
description: "Đo lường tỷ lệ hoàn tiền, hủy đơn và tổn thất doanh thu theo kênh bán, phương thức thanh toán và dòng sản phẩm."
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
    - "GET https://apis.haravan.com/com/orders/{order_id}/refunds.json"
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

# Haravan Refund & Cancellation Financial Impact Analysis

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Hủy đơn và hoàn tiền gây thất thoát âm thầm nhưng rất lớn: không chỉ mất doanh thu mà còn mất **phí ship 2 chiều, chi phí đóng gói, và chi phí quảng cáo (CPA) đã chi để có đơn hàng đó**. Skill này đo lường chính xác **tỷ lệ hủy trước giao (Pre-Shipment Cancel)** tách biệt hoàn toàn với **tỷ lệ hoàn sau giao (Post-Shipment Return/Refund)** theo từng kênh bán (`web`, `harasocial`, `pos`, `shopee`, `tiktok`), theo phương thức thanh toán (`COD` vs `Prepaid`), và chỉ mặt các SKU có tỷ lệ hoàn vượt quá `2x` trung bình toàn shop.

**Tiêu chí hoàn thành (Definition of Done):**
- Quét toàn bộ đơn hàng (`status=any`) trong `lookback_days`, tách rõ 3 lớp: Đơn thành công, Hủy trước xuất kho, và Hoàn/Trả tiền sau xuất kho.
- Tính cả **Tỷ lệ theo số đơn (Count Rate %)** và **Tỷ lệ theo giá trị tiền (Value Rate %)** vì đơn giá trị cao bị hoàn thường gây tổn thất lớn hơn nhiều so với số đếm.
- Liệt kê Top SKU vượt ngưỡng `2x` trung bình shop, ước tính tổng chi phí chìm vận chuyển hoàn và đính kèm **Financial Disclaimer**.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/orders/{order_id}/refunds.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate("/com/orders.json", params={"status": "any", "created_at_min": "2026-03-11T00:00:00+07:00", "limit": 50}, data_key="orders", max_records=5000)
# Chỉ gọi refunds.json cho đơn có financial_status in ("refunded", "partially_refunded")
refunds = client.get(f"/com/orders/{order_id}/refunds.json")["refunds"]
```

**JSON Response trích xuất từ `GET /com/orders/{id}/refunds.json`:**
```json
{
  "refunds": [
    {
      "id": 5510298,
      "order_id": 1482044112,
      "created_at": "2026-04-05T07:15:00Z",
      "note": "Khách đổi size nhưng hết hàng, hoàn tiền chuyển khoản",
      "refund_line_items": [
        { "line_item_id": 291003112, "quantity": 1, "subtotal": 450000.0, "restock_type": "return" }
      ],
      "transactions": [
        { "kind": "refund", "status": "success", "amount": 450000.0 }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `30` | Cửa sổ phân tích (`7`–`90` ngày, múi giờ `Asia/Ho_Chi_Minh`). |
| `est_roundtrip_ship_vnd` | integer | No | `45000` | Chi phí ước tính cho 1 đơn hoàn sau khi đã bàn giao NVC (ship đi + ship hoàn + bao bì). |
| `outlier_multiplier` | number | No | `2.0` | Hệ số vượt tỷ lệ hoàn trung bình toàn shop để gắn cờ `SKU_OUTLIER`. |
| `min_sku_orders` | integer | No | `15` | Cỡ mẫu đơn tối thiểu của SKU trước khi gắn cờ outlier. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Phân tách 2 Giai đoạn Thất thoát:**
   - **Pre-Shipment Cancel:** `cancelled_at != null` VÀ không có fulfillment nào đã bàn giao NVC (`carrier_status_code` không qua `delivering`/`returned`) → không tốn cước ship hoàn.
   - **Post-Shipment Return/Refund:** Có `refunds[]` với `amount > 0` HOẶC có fulfillment ở trạng thái `return`/`returned` → phát sinh chi phí chìm `est_roundtrip_ship_vnd`.
2. **Công thức các tỷ lệ tài chính:**
   - $\text{CancelRate\_Count\%} = \frac{\text{Số đơn hủy + hoàn}}{\text{Tổng đơn đặt}} \times 100\%$.
   - $\text{LostGMV\_Rate\%} = \frac{\sum \text{Giá trị đơn hủy} + \sum \text{Tổng tiền hoàn}}{\sum \text{Tổng GMV đặt hàng}} \times 100\%$.
   - $\text{EstSunkLogisticsCost} = \text{Số đơn Post-Shipment Return} \times \text{est\_roundtrip\_ship\_vnd}$.
3. **Phát hiện SKU Outlier:** Với mỗi SKU có tổng số lượng bán $\ge$ `min_sku_orders`, tính `sku_return_rate`. Gắn cờ `SKU_OUTLIER` nếu $\text{sku\_return\_rate} \ge \text{outlier\_multiplier} \times \text{shop\_avg\_return\_rate}$.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Dashboard Thất thoát Doanh thu do Hủy & Hoàn tiền (30 ngày — 1.620 đơn đặt):**
| Kênh / Thanh toán | Tổng đơn | Hủy trước giao | Hoàn sau giao | Tỷ lệ mất đơn (%) | GMV thất thoát (VND) | Tỷ lệ mất GMV (%) | Chi phí ship hoàn ước tính |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `harasocial` (COD) | 520 | 38 | 49 | **16.7%** | 61.400.000 | **18.2%** | 2.205.000 |
| `web` (COD) | 380 | 22 | 29 | 13.4% | 36.800.000 | 14.5% | 1.305.000 |
| `web` (Prepaid) | 290 | 9 | 7 | **5.5%** | 11.200.000 | **5.1%** | 315.000 |
| `shopee` | 310 | 18 | 19 | 11.9% | 22.900.000 | 12.4% | 855.000 |
| `pos` (Cửa hàng) | 120 | 2 | 1 | **2.5%** | 1.950.000 | **2.1%** | 0 |

**Top SKU Outlier (Tỷ lệ hoàn ≥ 2x trung bình toàn shop `6.5%`):**
| SKU | Sản phẩm | Tổng SL giao | SL hoàn/trả | Tỷ lệ hoàn (%) | Tiền hoàn (VND) | Gấp TB shop |
| --- | --- | --- | --- | --- | --- | --- |
| `VAY-LUA-S` | Váy Lụa Dáng Ôm Size S | 64 | 13 | **20.3%** | 9.750.000 | `3.1x` |
| `GIAY-DA-41` | Giày Da Công Sở 41 | 48 | 7 | **14.6%** | 8.400.000 | `2.2x` |

```json
{
  "skill": "finance-refund-rate-analysis",
  "disclaimer": "Operational Estimate / Reconciliation Aid — không thay thế sổ cái kế toán hoặc báo cáo tài chính chính thức.",
  "period_days": 30,
  "total_orders": 1620,
  "pre_shipment_cancel_count": 89,
  "post_shipment_return_count": 105,
  "lost_gmv_vnd": 134250000,
  "lost_gmv_rate_pct": 12.1,
  "est_sunk_logistics_cost_vnd": 4680000,
  "cod_vs_prepaid": { "cod_return_rate_pct": 15.3, "prepaid_return_rate_pct": 4.9 },
  "outlier_skus": [
    { "sku": "VAY-LUA-S", "shipped_qty": 64, "returned_qty": 13, "return_rate_pct": 20.3, "refund_value_vnd": 9750000 }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Financial Disclaimer Bắt buộc:**
  > *Tuyên bố trách nhiệm tài chính: Số liệu thất thoát GMV và chi phí vận chuyển hoàn là **Operational Estimate / Reconciliation Aid**, chưa bao gồm chi phí quảng cáo (CPA) bị đốt và không thay thế báo cáo kế toán chính thức.*
- **Chế độ Read-Only (L1):** Chỉ đọc và phân tích; không tự tạo phiếu hoàn tiền hay hủy đơn.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, báo thiếu quyền đọc đơn hàng. |
| `404 Not Found` | Đơn không tồn tại khi gọi `refunds.json` | Ghi log bỏ qua đơn lỗi, tiếp tục tổng hợp. |
| `422 Unprocessable` | Tham số ngày sai định dạng | Chuẩn hóa về ISO-8601 (`+07:00`). |
| `429 Too Many Requests` | Gọi `refunds.json` nhiều lần | Chỉ gọi `refunds.json` cho đơn có `financial_status` chứa `refund`; backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Đơn đổi hàng (Exchange) tạo thành 1 đơn hủy/hoàn + 1 đơn mới:** Nếu không tách đơn đổi size có ghi chú/tag `doi-size`, báo cáo sẽ phóng đại tỷ lệ thất thoát doanh thu dù thực tế shop vẫn giữ được khách và tiền hàng. Cần đếm riêng nhóm `exchange_orders` nếu phát hiện tag/ghi chú đổi hàng.
2. **Đơn hủy nội bộ / đơn test / đơn đặt trùng double-click:** Một khách đặt nhầm 2 đơn giống hệt trong 2 phút rồi CSKH hủy 1 đơn sẽ làm tăng giả tạo tỷ lệ hủy trước giao; nên ghi chú tỷ lệ hủy do trùng đơn nếu phát hiện.
3. **Độ trễ ghi nhận hoàn hàng (Return Lag 7–14 ngày):** Các đơn đặt trong 7 ngày cuối của `lookback_days` vẫn đang trên đường giao nên chưa phát sinh hoàn; báo cáo cần ghi rõ cảnh báo **Right-Censoring** cho tuần gần nhất.

## 8. Liên kết Workflow & Skill kế tiếp
- **Phân tích sâu nguyên nhân hoàn & nhập lại kho QC:** Chuyển sang `returns-reason-restock-proposal`.
- **Giảm tỷ lệ hoàn nhóm COD cao (15.3% vs 4.9% Prepaid):** Kích hoạt quy trình sàng lọc tại `order-risk-cod-boom-signals`.
