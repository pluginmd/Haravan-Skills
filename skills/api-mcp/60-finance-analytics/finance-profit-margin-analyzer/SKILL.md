---
name: finance-profit-margin-analyzer
description: "Ước tính biên lợi nhuận gộp theo sản phẩm/danh mục/kênh bán dựa trên giá bán thuần, giá vốn (COGS), chiết khấu và ước tính phí ship/sàn."
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
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/products.json"
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

# Haravan Product & Order Gross Margin Estimator

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Doanh thu cao trên Haravan chưa đồng nghĩa với lợi nhuận cao: rất nhiều SKU bán chạy (Hero SKU) thực tế đang có **biên lợi nhuận gộp mỏng hoặc âm** sau khi trừ mã giảm giá, trợ giá Freeship và phí sàn TMĐT (Shopee/TikTok/Lazada thường chiếm 8–14%). Skill này ghép dữ liệu bán hàng từ `/com/orders.json` với giá vốn (COGS) từ `/com/products.json` (hoặc file `cogs_csv` bổ sung) để **ước tính Gross Margin theo SKU, Danh mục và Kênh bán**, đồng thời báo cáo minh bạch tỷ lệ SKU thiếu dữ liệu giá vốn.

**Tiêu chí hoàn thành (Definition of Done):**
- Tổng hợp doanh thu thuần (đã trừ giảm giá dòng hàng, giảm giá đơn phân bổ và hoàn tiền) theo từng SKU và kênh trong `lookback_days`.
- Ghép giá vốn (COGS) chính xác; **tuyệt đối không tự bịa COGS** cho SKU thiếu `cost_price` (gắn cờ `MISSING_COGS` và báo cáo % doanh thu thiếu COGS).
- Xếp hạng Top 15 SKU sinh lời cao nhất và Top 15 SKU biên thấp/âm kèm **Financial Disclaimer** đầy đủ.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_products` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/products.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate("/com/orders.json", params={"status": "any", "created_at_min": "2026-03-11T00:00:00+07:00", "limit": 50}, data_key="orders", max_records=5000)
products = client.paginate("/com/products.json", params={"limit": 50}, data_key="products", max_records=2000)
```

**JSON Response trích xuất giá vốn & giá bán (`GET /com/products.json`):**
```json
{
  "products": [
    {
      "id": 1001,
      "title": "Trà Thảo Mộc Thanh Nhiệt 200g",
      "product_type": "Trà",
      "variants": [
        { "id": 5001, "sku": "TRA-200G", "price": 185000.0, "compare_at_price": 220000.0, "cost_price": 92000.0 }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `30` | Kỳ phân tích (`7`–`90` ngày, múi giờ `Asia/Ho_Chi_Minh`). |
| `cogs_csv` | string (path) | No | `null` | File CSV bổ sung `(sku, cost_price_vnd)` ưu tiên dùng khi Haravan để trống `cost_price`. |
| `channel_fee_pct` | object | No | `{"web":1.5,"pos":0.5,"harasocial":1.5,"shopee":11.0,"tiktok":10.5,"lazada":11.5}` | Ước tính % phí sàn + phí cổng thanh toán theo kênh. |
| `low_margin_threshold_pct` | number | No | `15.0` | Ngưỡng biên lợi nhuận gộp (%) để gắn cờ cảnh báo `LOW_MARGIN`. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Phân bổ Doanh thu thuần theo dòng hàng (Line-Item Net Revenue):**
   - Loại bỏ đơn `cancelled_at != null`; trừ số lượng & tiền hoàn từ `refunds[].refund_line_items`.
   - Với giảm giá cấp đơn hàng (`order.total_discounts`), phân bổ tỷ lệ thuận theo giá trị từng `line_item`:
     $$\text{NetRev}_i = (\text{price}_i \times \text{net\_qty}_i) - \text{line\_discount}_i - \text{allocated\_order\_discount}_i$$
2. **Ước tính Chi phí trực tiếp (Direct Costs):**
   - $\text{COGS}_i = \text{cost\_price}_i \times \text{net\_qty}_i$. Nếu `cost_price` bằng `null` hoặc `0` (và không có trong `cogs_csv`) → đưa vào nhóm `MISSING_COGS`, **không tính vào tử số/mẫu số Gross Margin**.
   - Trợ giá vận chuyển (Shipping Subsidy): $\text{ShipSubsidy} = \max(0, \text{real\_shipping\_fee} - \text{customer\_paid\_shipping})$ (phân bổ theo tỷ trọng doanh thu dòng hàng).
   - Phí kênh/sàn ước tính: $\text{EstChannelFee}_i = \text{NetRev}_i \times \frac{\text{channel\_fee\_pct}[\text{channel}]}{100}$.
3. **Công thức Biên lợi nhuận gộp ước tính (Contribution / Gross Margin Estimate):**
   $$\text{GrossProfit}_i = \text{NetRev}_i - \text{COGS}_i - \text{ShipSubsidy}_i - \text{EstChannelFee}_i$$
   $$\text{GrossMargin\%}_i = \frac{\text{GrossProfit}_i}{\text{NetRev}_i} \times 100\%$$

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Tổng hợp Ước tính Biên Lợi nhuận Gộp theo Kênh (30 ngày — Độ phủ COGS: 94.2% doanh thu):**
| Kênh bán | Doanh thu thuần (VND) | COGS (VND) | Phí kênh ước tính | Trợ giá ship | Lãi gộp ước tính | Gross Margin (%) |
| --- | --- | --- | --- | --- | --- | --- |
| `pos` (Cửa hàng) | 310.000.000 | 148.800.000 | 1.550.000 | 0 | 159.650.000 | **51.5%** |
| `web` (Haraweb) | 285.000.000 | 142.500.000 | 4.275.000 | 9.400.000 | 128.825.000 | **45.2%** |
| `shopee` | 240.000.000 | 132.000.000 | 26.400.000 | 12.100.000 | 69.500.000 | **29.0%** |
| `tiktok` | 165.000.000 | 95.700.000 | 17.325.000 | 14.800.000 | 37.175.000 | **22.5%** |

**Cảnh báo Top SKU Biên Thấp / Âm:**
| SKU | Sản phẩm | SL bán | Doanh thu thuần | COGS | Lãi gộp ước tính | Margin (%) | Cờ cảnh báo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `COMBO-TET-01` | Combo Quà Tặng mini | 142 | 21.300.000 | 17.040.000 | -480.000 | **-2.3%** | `NEGATIVE_MARGIN` (Freeship + phí sàn) |
| `TD-50ML` | Tinh Dầu Sả Chanh 50ml | 95 | 13.200.000 | `N/A` | `N/A` | `N/A` | `MISSING_COGS` |

```json
{
  "skill": "finance-profit-margin-analyzer",
  "disclaimer": "Operational Estimate / Reconciliation Aid — chưa bao gồm chi phí quảng cáo (Ads), nhân sự, mặt bằng, khấu hao và thuế TNDN.",
  "period_days": 30,
  "cogs_coverage_revenue_pct": 94.2,
  "blended_gross_margin_pct": 39.5,
  "low_or_negative_margin_skus": [
    { "sku": "COMBO-TET-01", "net_revenue_vnd": 21300000, "cogs_vnd": 17040000, "est_gross_profit_vnd": -480000, "gross_margin_pct": -2.3, "flag": "NEGATIVE_MARGIN" }
  ],
  "missing_cogs_skus": ["TD-50ML"]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Financial Disclaimer Bắt buộc:**
  > *Tuyên bố trách nhiệm tài chính: Kết quả là **Operational Estimate / Reconciliation Aid**, chưa bao gồm chi phí quảng cáo (Facebook/TikTok/Google Ads), chi phí nhân sự, thuê mặt bằng, hao hụt kho và thuế TNDN — không thay thế báo cáo kết quả kinh doanh của kế toán.*
- **Chế độ Read-Only (L1):** Không tự sửa giá bán hay giá vốn trên Haravan.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_products` hoặc `com.read_orders` | Dừng, báo chính xác scope bị thiếu. |
| `404 Not Found` | Sản phẩm trong đơn cũ đã bị xóa khỏi catalog | Fallback khớp theo `line_item.sku` trong `cogs_csv`; nếu không có gắn `MISSING_COGS`. |
| `422 Unprocessable` | Tham số ngày không hợp lệ | Chuẩn hóa về ISO-8601 (`+07:00`). |
| `429 Too Many Requests` | Quét 5.000 đơn + 2.000 sản phẩm | Throttle & backoff tự động qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Haravan lưu giá vốn hiện tại (`cost_price`) chứ không lưu giá vốn lịch sử theo từng lô nhập (FIFO/Bình quân gia quyền):** Nếu giá nhập tăng mạnh giữa tháng, phép tính dùng `cost_price` hiện tại chỉ mang tính ước lượng vận hành; cần ghi chú rõ cho kế toán.
2. **Hàng tặng kèm 0đ (`price = 0`) trong chương trình "Mua 2 tặng 1":** Nếu loại bỏ dòng 0đ sẽ bỏ sót giá vốn của hàng tặng kèm! Phải **vẫn cộng `COGS` của dòng hàng tặng** vào tổng chi phí đơn hàng để phản ánh đúng biên thực tế.
3. **SKU bị trùng giữa 2 biến thể khác nhau:** Luôn ưu tiên khớp giá vốn theo `variant_id` trước, chỉ fallback theo `sku` khi sản phẩm cũ đã xóa.

## 8. Liên kết Workflow & Skill kế tiếp
- **Tìm mã giảm giá gây âm biên:** Chuyển sang `finance-aov-discount-roi`.
- **Xem doanh thu đa kênh chi tiết theo chi nhánh POS:** Chuyển sang `finance-sales-by-channel-omni`.
