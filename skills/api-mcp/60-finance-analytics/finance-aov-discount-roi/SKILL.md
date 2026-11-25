---
name: finance-aov-discount-roi
description: "Phân tích xu hướng giá trị đơn trung bình (AOV), tỷ lệ đơn dùng mã giảm giá và hiệu quả thực tế của các chương trình khuyến mãi."
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
    - com.read_discounts
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/promotions.json"
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

# Haravan AOV Trend & Discount ROI Analyzer

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Nhiều cửa hàng Haravan đốt 8–15% doanh thu vào mã giảm giá nhưng không biết chương trình nào thực sự **kéo tăng giá trị đơn hàng (AOV), tăng số sản phẩm/đơn (UPT) và thu hút khách mới**, hay chỉ đang **tự ăn mòn biên lợi nhuận (Cannibalization)** bằng cách giảm giá cho khách quen vốn đã định mua nguyên giá. Skill này đối chiếu dữ liệu đơn hàng (`/com/orders.json`) với danh sách chương trình khuyến mãi (`/com/promotions.json`) để đo lường ROI vận hành của từng mã giảm giá.

**Tiêu chí hoàn thành (Definition of Done):**
- Phân tách rõ nhóm đơn **Có khuyến mãi (`total_discounts > 0`)** vs **Nguyên giá (`total_discounts == 0`)** theo tuần và toàn kỳ `lookback_days`.
- Tính đầy đủ cho từng mã khuyến mãi: Lượt dùng, Tổng tiền giảm (Discount Cost), Doanh thu thuần kéo theo, AOV Uplift (%), UPT Uplift (%), Tỷ lệ khách mới (New-to-Brand %) và Hệ số Cannibalization.
- Đính kèm đầy đủ **Financial Disclaimer** chuẩn vận hành trong mọi báo cáo.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_discounts` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/promotions.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate("/com/orders.json", params={"status": "any", "created_at_min": "2026-03-11T00:00:00+07:00", "limit": 50}, data_key="orders", max_records=5000)
promos = client.paginate("/com/promotions.json", params={"limit": 50}, data_key="promotions", max_records=500)
```

**JSON Response trích xuất từ `GET /com/orders.json`:**
```json
{
  "orders": [
    {
      "id": 1482071005,
      "created_at": "2026-04-04T12:10:00Z",
      "cancelled_at": null,
      "subtotal_price": 720000.0,
      "total_discounts": 100000.0,
      "total_price": 650000.0,
      "discount_codes": [
        { "code": "CHAOHE100K", "amount": 100000.0, "type": "fixed_amount" }
      ],
      "line_items": [{ "quantity": 3 }],
      "customer": { "id": 71022, "orders_count": 1 }
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `30` | Cửa sổ phân tích (`7`–`90` ngày, múi giờ `Asia/Ho_Chi_Minh`). |
| `exclude_cancelled` | boolean | No | `true` | Loại trừ đơn hủy/hoàn toàn phần khỏi phép tính doanh thu thuần và chi phí giảm giá. |
| `min_code_uses` | integer | No | `5` | Số lượt sử dụng tối thiểu để xếp hạng chi tiết từng mã khuyến mãi. |
| `target_discount_rate_pct` | number | No | `10.0` | Ngưỡng trần tỷ lệ chiết khấu/doanh thu gộp để cảnh báo mã "đốt biên". |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Các chỉ số nền tảng (Loại trừ đơn hủy):**
   - $\text{AOV} = \frac{\sum \text{NetSales}}{\text{Số đơn thành công}}$; $\text{UPT} = \frac{\sum \text{line\_items.quantity}}{\text{Số đơn thành công}}$.
   - Tỷ lệ đơn dùng khuyến mãi: $\text{PromoPenetration\%} = \frac{\text{Số đơn có } \text{total\_discounts} > 0}{\text{Tổng số đơn}} \times 100\%$.
   - Tỷ lệ chiết khấu thực tế (Effective Discount Rate): $\text{EDR\%} = \frac{\sum \text{total\_discounts}}{\sum (\text{subtotal\_price} + \text{total\_discounts})} \times 100\%$.
2. **Đo lường hiệu quả từng mã khuyến mãi (`discount_codes[].code`):**
   - $\text{AOV\_Uplift\%} = \frac{\text{AOV}_{\text{mã}} - \text{AOV}_{\text{nguyên giá}}}{\text{AOV}_{\text{nguyên giá}}} \times 100\%$.
   - $\text{Revenue\_per\_Discount\_VND} = \frac{\sum \text{NetSales}_{\text{mã}}}{\sum \text{DiscountAmount}_{\text{mã}}}$ (bội số doanh thu thuần trên mỗi 1đ giảm giá).
   - $\text{NewCustomerShare\%} = \frac{\text{Số đơn mã từ khách mới (orders\_count = 1)}}{\text{Tổng lượt dùng mã}} \times 100\%$.
3. **Phân loại cảnh báo Cannibalization:** Gắn cờ `HIGH_CANNIBALIZATION` nếu mã có `AOV_Uplift% <= 0%` VÀ `NewCustomerShare% < 25%` (giảm giá cho khách cũ mà không kéo tăng giá trị giỏ hàng).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**So sánh Tổng quan: Đơn Khuyến mãi vs Đơn Nguyên giá (30 ngày):**
| Nhóm đơn | Số đơn | Tỷ trọng (%) | AOV (VND) | UPT (SP/đơn) | Tổng tiền giảm (VND) | Tỷ lệ chiết khấu (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Có khuyến mãi | 520 | 38.5% | 745.000 | 2.8 | 51.400.000 | 11.7% |
| Nguyên giá | 830 | 61.5% | 580.000 | 1.9 | 0 | 0.0% |
| **Toàn cửa hàng** | **1.350** | **100%** | **643.500** | **2.25** | **51.400.000** | **5.6%** |

**Bảng Hiệu quả Từng Mã Khuyến mãi:**
| Mã giảm giá | Lượt dùng | Tiền giảm (VND) | Doanh thu thuần (VND) | AOV Uplift | Khách mới (%) | Đánh giá |
| --- | --- | --- | --- | --- | --- | --- |
| `COMBO100K` | 210 | 21.000.000 | 189.000.000 | **+55.2%** | 41.0% | Hiệu quả cao (kéo UPT lên 3.4) |
| `WELCOME10` | 145 | 8.200.000 | 73.800.000 | -12.1% | **94.5%** | Tốt cho thu hút khách mới |
| `SALE15ALL` | 112 | 16.800.000 | 61.200.000 | **-5.8%** | 14.3% | `HIGH_CANNIBALIZATION` (cần siết ngưỡng min-order) |

```json
{
  "skill": "finance-aov-discount-roi",
  "disclaimer": "Operational Estimate / Reconciliation Aid — không thay thế sổ cái kế toán hoặc tờ khai thuế chính thức.",
  "period_days": 30,
  "overall": { "orders": 1350, "aov_vnd": 643500, "promo_penetration_pct": 38.5, "effective_discount_rate_pct": 5.6 },
  "codes": [
    {
      "code": "SALE15ALL",
      "uses": 112,
      "discount_cost_vnd": 16800000,
      "net_revenue_vnd": 61200000,
      "aov_uplift_pct": -5.8,
      "new_customer_share_pct": 14.3,
      "flag": "HIGH_CANNIBALIZATION"
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Financial Disclaimer Bắt buộc:**
  > *Tuyên bố trách nhiệm tài chính: Báo cáo này là **Operational Estimate / Reconciliation Aid** dựa trên dữ liệu đơn hàng Haravan, không thay thế sổ cái kế toán, báo cáo tài chính kiểm toán hay tờ khai thuế chính thức.*
- **Chế độ Read-Only (L1):** Không tự động tắt mã giảm giá hay sửa điều kiện khuyến mãi.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_discounts` | Vẫn chạy phân tích trên `order.discount_codes`, cảnh báo không đối chiếu được cấu hình chương trình từ `promotions.json`. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `/com/`. |
| `422 Unprocessable` | Tham số ngày sai định dạng | Chuyển sang ISO-8601 (`+07:00`). |
| `429 Too Many Requests` | Quét 5.000 đơn | Throttle & backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Khuyến mãi tự động không có mã (`discount_codes: []` nhưng `total_discounts > 0`):** Các chương trình "Mua 2 giảm 10%" hoặc giảm giá trực tiếp tại POS thường không sinh `code`; cần gom vào dòng riêng `AUTO_PROMO_OR_POS_DISCOUNT` thay vì bỏ sót khỏi tổng chi phí khuyến mãi.
2. **Đơn sàn TMĐT (Shopee/TikTok) có voucher đồng tài trợ của sàn vs của shop:** Haravan có thể ghi nhận tổng voucher vào `total_discounts` mà không tách phần sàn trợ giá; cần ghi chú tách riêng đơn sàn khỏi đơn Web/POS khi tính ROI khuyến mãi nội bộ.
3. **Freeship được ghi nhận như giảm giá vận chuyển thay vì `total_discounts`:** Cần kiểm tra thêm `shipping_lines[].discounted_price` so với phí ship thực tế để không đánh giá thấp chi phí ưu đãi Freeship.

## 8. Liên kết Workflow & Skill kế tiếp
- **Kiểm tra tác động lên biên lợi nhuận gộp:** Chuyển các mã có `EDR% > 10%` sang `finance-profit-margin-analyzer`.
- **So sánh hiệu quả theo từng kênh Omni:** Chạy `finance-sales-by-channel-omni`.
