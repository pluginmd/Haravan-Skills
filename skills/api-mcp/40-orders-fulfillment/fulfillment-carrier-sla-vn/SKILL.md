---
name: fulfillment-carrier-sla-vn
description: "So sánh hiệu suất giao hàng và tỷ lệ hoàn đơn giữa các nhà vận chuyển VN (GHN, GHTK, Viettel Post, J&T, Ahamove) theo tuyến nội tỉnh/liên miền."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 40-orders-fulfillment
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

# Vietnam Shipping Carrier SLA & Return-Rate Benchmark

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này phân tích dữ liệu vận đơn thực tế trên Haravan để **chấm điểm và so sánh hiệu suất các nhà vận chuyển (NVC) Việt Nam** (GHN, GHTK, Viettel Post, J&T Express, SPX, Ahamove/GrabExpress) theo 3 tuyến địa lý: **Nội thành (HN/HCM)**, **Nội miền**, và **Liên miền (Bắc–Trung–Nam)**. Kết quả giúp bộ phận vận hành điều chỉnh luật định tuyến NVC (carrier routing) nhằm giảm thời gian toàn trình và cắt giảm tỷ lệ hoàn hàng.

**Tiêu chí hoàn thành (Definition of Done):**
- Quét đủ các đơn đã có vận đơn trong `lookback_days` (tối đa 5.000 đơn) và chuẩn hóa tên NVC về danh mục chuẩn VN.
- Tính đủ 5 chỉ số cho từng cặp `(NVC × Tuyến)`: Cỡ mẫu $N$, Median & P90 thời gian giao (giờ), Tỷ lệ đạt SLA (%), Tỷ lệ hoàn hàng (%), và Phí ship bình quân/đơn (VND).
- Gắn cờ cảnh báo độ tin cậy thống kê với các nhóm có cỡ mẫu $N < 20$ đơn và đưa ra khuyến nghị định tuyến cụ thể.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders` |
| **Endpoints** | `GET /com/orders.json` (filter `created_at_min`, `fulfillment_status=shipped`, `limit=50`) |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate(
    "/com/orders.json",
    params={"created_at_min": "2026-03-11T00:00:00+07:00", "status": "any", "limit": 50},
    data_key="orders",
    max_records=5000,
)
```

**JSON Response trích xuất từ `GET /com/orders.json`:**
```json
{
  "orders": [
    {
      "id": 1481902311,
      "name": "#108912",
      "created_at": "2026-03-20T03:10:00Z",
      "shipping_address": { "province": "Hà Nội", "district": "Quận Cầu Giấy" },
      "shipping_lines": [{ "title": "GHN - Chuẩn", "price": 32000.0 }],
      "fulfillments": [
        {
          "id": 88390112,
          "tracking_company": "Giao Hàng Nhanh",
          "tracking_number": "GA89X2K1",
          "carrier_status_code": "delivered",
          "carrier_cod_status_code": "codreceipt",
          "created_at": "2026-03-20T05:00:00Z",
          "updated_at": "2026-03-22T07:30:00Z",
          "real_shipping_fee": 28500.0
        }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `30` | Khoảng thời gian phân tích (`7`–`90` ngày). |
| `origin_province` | string | No | `"Hồ Chí Minh"` | Tỉnh/thành đặt kho xuất hàng chính để phân loại Nội thành / Nội miền / Liên miền. |
| `sla_intra_city_hours` | integer | No | `24` | Ngưỡng SLA mục tiêu cho đơn nội tỉnh/thành (giờ). |
| `sla_intra_region_hours` | integer | No | `48` | Ngưỡng SLA mục tiêu cho đơn nội miền (giờ). |
| `sla_inter_region_hours` | integer | No | `96` | Ngưỡng SLA mục tiêu cho đơn liên miền Bắc–Trung–Nam (giờ). |
| `min_sample_size` | integer | No | `20` | Ngưỡng cỡ mẫu tối thiểu để xếp hạng tin cậy (dưới ngưỡng gắn cờ `LOW_SAMPLE`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Chuẩn hóa tên NVC (Carrier Normalization):** Ánh xạ chuỗi `tracking_company` không đồng nhất trên Haravan: `["GHN", "Giao Hàng Nhanh", "GHN Express"] → GHN`; `["GHTK", "Giao Hàng Tiết Kiệm"] → GHTK`; `["VTP", "ViettelPost", "Viettel Post"] → Viettel Post`; `["J&T", "JT Express"] → J&T`; `["Ahamove", "GrabExpress"] → Instant`.
2. **Phân loại tuyến vận chuyển:**
   - `intra_city`: `shipping_address.province == origin_province`.
   - `intra_region`: Cùng vùng miền (Bắc / Trung / Nam) nhưng khác tỉnh.
   - `inter_region`: Khác vùng miền với `origin_province`.
3. **Công thức đo lường:**
   - Thời gian toàn trình (giờ): $T_{\text{delivery}} = \frac{\text{delivered\_at} - \text{fulfillment.created\_at}}{3600}$ (chỉ tính trên đơn `carrier_status_code == "delivered"`).
   - Tỷ lệ đạt SLA: $\text{SLA\%} = \frac{\text{Số đơn } T_{\text{delivery}} \le \text{SLA}_{\text{tuyến}}}{\text{Tổng đơn đã giao thành công}} \times 100\%$.
   - Tỷ lệ hoàn hàng: $\text{Return\%} = \frac{\text{Số đơn } \in \{\text{return}, \text{returned}, \text{cancel}\}}{\text{Tổng đơn đã bàn giao NVC}} \times 100\%$.
   - Điểm tổng hợp Carrier Score (thang 100): $\text{Score} = 0.45 \times \text{SLA\%} + 0.35 \times (100 - \text{Return\%} \times 3) + 0.20 \times \text{CostScore}$ (trong đó $\text{CostScore} = 100 \times \frac{\min(\text{AvgFee})}{\text{AvgFee}_{\text{NVC}}}$).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Bảng Xếp Hạng NVC Việt Nam (30 ngày, Kho gốc: TP.HCM):**
| Tuyến | NVC | Cỡ mẫu (Đơn) | Median (h) | P90 (h) | Đạt SLA (%) | Tỷ lệ hoàn (%) | Ship TB (VND) | Điểm (100) | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nội thành HCM | Ahamove | 145 | 3.2 | 6.5 | 98.6% | 1.4% | 34.000 | 92.4 | Ưu tiên đơn hỏa tốc |
| Nội thành HCM | GHTK | 412 | 16.5 | 26.0 | 89.1% | 4.8% | 22.000 | 88.7 | Tối ưu chi phí |
| Liên miền (HCM→HN) | GHN | 328 | 62.0 | 88.5 | 93.0% | 6.1% | 31.500 | 87.9 | Nhanh, ổn định |
| Liên miền (HCM→HN) | Viettel Post | 190 | 74.0 | 108.0 | 81.5% | 5.2% | 29.000 | 81.2 | Chậm ở tuyến huyện |
| Liên miền (HCM→HN) | J&T | 14 | 68.0 | 95.0 | 85.7% | 7.1% | 27.500 | — | `LOW_SAMPLE (<20)` |

```json
{
  "skill": "fulfillment-carrier-sla-vn",
  "period_days": 30,
  "origin_province": "Hồ Chí Minh",
  "total_fulfillments_analyzed": 1089,
  "benchmarks": [
    {
      "route": "inter_region",
      "carrier": "GHN",
      "sample_size": 328,
      "low_sample_warning": false,
      "median_hours": 62.0,
      "p90_hours": 88.5,
      "sla_pass_rate_pct": 93.0,
      "return_rate_pct": 6.1,
      "avg_shipping_fee_vnd": 31500,
      "composite_score": 87.9
    }
  ],
  "routing_recommendations": [
    "Tuyến Nội thành HCM (tiêu chuẩn): ưu tiên GHTK (22.000đ, SLA 89.1%).",
    "Tuyến Liên miền HCM → Bắc: ưu tiên GHN (P90 88.5h, vượt trội Viettel Post 19.5h)."
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Tuyệt đối chỉ gọi `GET`, không thay đổi cấu hình nhà vận chuyển hay đơn hàng trên Haravan.
- **Bảo vệ PII (`pii_level: none`):** Báo cáo chỉ tổng hợp ở cấp độ NVC và Tỉnh/Thành phố; không in tên khách hàng, số điện thoại hay địa chỉ chi tiết.
- **Chống sai lệch thống kê:** Không khuyến nghị cắt/chuyển NVC đối với nhóm có `sample_size < 20`; loại trừ các đơn giao thử nghiệm nội bộ (tag `test`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn hoặc thu hồi | Dừng, yêu cầu kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, báo thiếu quyền đọc đơn hàng. |
| `404 Not Found` | Endpoint sai cấu trúc | Kiểm tra lại `base_url` (`https://apis.haravan.com/com`). |
| `422 Unprocessable` | Tham số `created_at_min` sai định dạng ISO-8601 | Chuẩn hóa timestamp về `YYYY-MM-DDTHH:MM:SS+07:00`. |
| `429 Too Many Requests` | Quá tải phân trang 5.000 đơn | `hrv_client.py` tự backoff (1s → 2s → 4s) và giảm tốc độ gọi. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Viettel Post / NVC nhập tay không có webhook cập nhật `delivered_at`:** Nhiều shop tự nhập mã VTP nên `carrier_status_code` vẫn đứng ở `delivering` hoặc `updated_at` bị cập nhật trễ khi kế toán bấm hoàn tất thủ công. Cần tách riêng nhóm `manual_tracking` khỏi nhóm `integrated_carrier` để không làm méo P90.
2. **Đơn bị hoàn vì lý do khách bom COD vs lỗi NVC giao chậm:** Một NVC chạy tuyến tỉnh lẻ (tỷ lệ COD cao) thường có tỷ lệ hoàn cao hơn nội thành; cần luôn so sánh **cùng tuyến** và ghi chú tỷ trọng COD của từng NVC.
3. **Mùa cao điểm Mega Sale (11.11, 12.12, cận Tết):** Thời gian chờ lấy hàng (pickup delay) có thể tăng gấp 2–3 lần; nên so sánh thêm với cửa sổ `lookback_days=7` để phát hiện NVC đang quá tải cục bộ.

## 8. Liên kết Workflow & Skill kế tiếp
- **Liên kết vận hành:** Dùng cùng `fulfillment-status-digest-wismo` để xử lý các đơn đang kẹt tại NVC kém hiệu suất.
- **Liên kết tài chính:** Chuyển sang `finance-cod-reconciliation` để kiểm tra tốc độ đối soát tiền COD và phụ phí thực tế của từng NVC.
