---
name: ops-weekly-business-review
description: "Báo cáo tổng kết kinh doanh tuần (so sánh WoW): doanh thu đa kênh, AOV, tỷ lệ hoàn/hủy, hiệu suất NVC VN và sức khỏe tồn kho."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 90-control-tower-governance
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_products
    - com.read_inventories
    - com.read_customers
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/customers.json"
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

# Haravan Weekly Business Review (WBR)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Chuẩn hóa bộ báo cáo **Weekly Business Review (WBR)** cho cuộc họp giao ban sáng thứ Hai hàng tuần, so sánh trực diện tuần vừa qua với tuần trước đó (**WoW — Week-over-Week**) trên cùng một trục dữ liệu: Kinh doanh đa kênh, Khách hàng mới vs quay lại, Top sản phẩm tăng/giảm mạnh, Sức khỏe kho vận và SLA các nhà vận chuyển Việt Nam (GHTK, GHN, SPX, ViettelPost, J&T).
- **Ngữ cảnh Haravan:** Trong vận hành TMĐT thực chiến, nhìn doanh thu tổng là chưa đủ — một tuần doanh thu tăng 15% nhưng tỷ lệ hoàn đơn tăng từ 5% lên 11% hoặc tỷ lệ khách cũ giảm mạnh là tín hiệu cảnh báo chất lượng traffic/sản phẩm. WBR kết nối các mảng Marketing, Kho, Giao vận và CSKH để ban lãnh đạo chốt đúng 3–5 đầu việc trọng tâm cho tuần mới.
- **Definition of Done (DoD):**
  1. Thu thập đầy đủ đơn hàng của 2 tuần liên tiếp (Tuần này `W` và Tuần trước `W-1`, Thứ Hai `00:00:00+07:00` → Chủ Nhật `23:59:59+07:00`), tồn kho hiện tại và thông tin khách hàng.
  2. Xây dựng đủ 5 khối báo cáo chuẩn WBR: Executive Summary, Bảng KPI WoW, Phân rã Kênh & Top 10 SKU biến động mạnh, Hiệu suất ĐVVC & Kho, và Kế hoạch hành động tuần tới (Owner + Metric).
  3. Đảm bảo Read-Only, ẩn toàn bộ PII và đính kèm Financial Disclaimer.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_products`, `com.read_inventories`, `com.read_customers` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/inventory_locations.json`, `GET /com/customers.json` |

**Ví dụ gọi qua `scripts/hrv_client.py` (lấy cửa sổ 14 ngày để tách `W` và `W-1` trong 1 lượt paginate):**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
orders_14d = client.paginate(
    surface="com",
    path="/orders.json",
    resource_key="orders",
    params={
        "created_at_min": "2026-11-09T00:00:00+07:00",
        "created_at_max": "2026-11-22T23:59:59+07:00",
        "status": "any",
    },
    limit=50,
    max_pages=100,
)
inv_locs = client.paginate("com", "/inventory_locations.json", "inventory_locations", limit=50, max_pages=60)
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `week_end_date` | `string` | Không | Chủ nhật gần nhất (`UTC+7`) | Định dạng `YYYY-MM-DD`; tự động lùi 6 ngày để ra ngày Thứ Hai đầu tuần `W` và thêm 7 ngày trước đó cho `W-1`. |
| `top_movers_limit` | `integer` | Không | `10` | Số lượng sản phẩm tăng trưởng / sụt giảm mạnh nhất cần hiển thị (`5..20`). |
| `carrier_sla_days` | `number` | Không | `3.5` | Ngưỡng thời gian giao hàng trung bình (ngày) để đánh giá ĐVVC đạt/không đạt SLA. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Tính toán Bộ KPI So sánh WoW (`W` vs `W-1`):**
   - **Doanh thu thuần ước tính**, **Số đơn hợp lệ**, **AOV**, **Tỷ lệ Hủy/Hoàn**, **Tỷ lệ Chiết khấu (`Discounts / GMV`)**:
     $$\Delta \text{WoW \%} = \frac{\text{Metric}_{W} - \text{Metric}_{W-1}}{\text{Metric}_{W-1}} \times 100\%$$
   - **Tỷ lệ Khách quay lại (Repeat Customer Rate):** Phân loại dựa trên `customer.orders_count > 1` (hoặc có đơn trước ngày đầu tuần `W`):
     $$\text{Repeat Rate} = \frac{N_{\text{orders\_from\_returning\_customers}}}{N_{\text{valid\_orders}}} \times 100\%$$
2. **Phân rã Kênh bán (Omnichannel Mix) & Top Movers:**
   - So sánh doanh thu WoW của từng `source_name` (`web`, `pos`, `harasocial`, `shopee`, `tiktokshop`, `lazada`).
   - Tính biến động doanh thu từng SKU giữa `W` và `W-1` để chọn ra Top 5 Tăng trưởng mạnh nhất (Winners) và Top 5 Sụt giảm mạnh nhất (Losers — đối chiếu ngay xem có phải do hết hàng OOS hay không).
3. **Đánh giá Hiệu suất Nhà vận chuyển VN (Carrier SLA) & Sức khỏe Kho:**
   - Nhóm các đơn có `fulfillments` theo `carrier_service_name` / `tracking_company` (GHTK, GHN, SPX, ViettelPost, J&T): tính tổng số vận đơn, tỷ lệ giao thành công, tỷ lệ hoàn (RTO) và số đơn đang kẹt > `carrier_sla_days`.
   - Thống kê số SKU hết hàng (`qty_available <= 0`) và số SKU sắp hết (`1..5`).
4. **Đề xuất Action Plan tuần mới:** Gắn mỗi vấn đề chính với 1 bộ phận phụ trách (Marketing / Kho / Vận hành / CSKH) và 1 chỉ số mục tiêu rõ ràng.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### WEEKLY BUSINESS REVIEW (WBR) — Tuần 47 (16/11 – 22/11/2026)
> **Executive Summary:** Doanh thu thuần ước tính đạt `342.5 triệu VND` (**+11.4% WoW**) nhờ bứt phá từ TikTok Shop (+28%) và Web (+14%). Tuy nhiên, tỷ lệ hoàn đơn GHN tăng lên `8.2%` và `12 SKU` chủ lực vừa chạm ngưỡng OOS cần nhập kho ngay đầu tuần 48.

#### 1. Bảng KPI Kinh doanh (WoW)
| Chỉ số | Tuần 47 (W) | Tuần 46 (W-1) | Biến động WoW | Đánh giá |
| --- | ---: | ---: | ---: | --- |
| Doanh thu thuần ước tính | 342,500,000đ | 307,450,000đ | **+11.4%** | Tích cực |
| Số đơn hợp lệ | 438 | 402 | **+9.0%** | Tích cực |
| AOV | 781,963đ | 764,801đ | **+2.2%** | Ổn định |
| Tỷ lệ khách quay lại | 31.5% | 29.8% | **+1.7 pts** | Tích cực |
| Tỷ lệ Hủy / Hoàn | 6.8% | 5.4% | **+1.4 pts** | Cần theo dõi |

#### 2. Hiệu suất Giao vận VN & Tồn kho
- **ĐVVC:** GHTK (RTO `4.1%`, TB `2.4 ngày`) • SPX (RTO `5.0%`, TB `2.1 ngày`) • GHN (RTO `8.2%`, **11 đơn kẹt > 3.5 ngày** — cần làm việc lại bưu cục)
- **Kho:** `12 SKU` hết hàng hoàn toàn (gây hụt doanh thu Top Losers), `19 SKU` còn ≤ 5 sản phẩm.

#### 3. Trọng tâm Hành động Tuần 48
1. **[Kho / Mua hàng]** Ưu tiên nhập lại 5 SKU bán chạy nhất vừa OOS trước thứ Tư.
2. **[Vận hành]** Rà soát 11 đơn GHN kẹt > 3.5 ngày và điều chuyển tuyến miền Trung sang GHTK/ViettelPost.
3. **[Marketing]** Chạy chiến dịch Win-Back cho nhóm khách 60–180 ngày nhằm đẩy Repeat Rate lên > 33%.

> *Financial Disclaimer:* Số liệu doanh thu là ước tính vận hành từ Haravan API, không thay thế báo cáo tài chính đã kiểm toán.
```

```json
{
  "skill": "ops-weekly-business-review",
  "week_range": { "start": "2026-11-16", "end": "2026-11-22" },
  "kpi_wow": {
    "net_revenue_est_vnd": { "w": 342500000, "w_prev": 307450000, "wow_pct": 11.4 },
    "valid_orders": { "w": 438, "w_prev": 402, "wow_pct": 9.0 },
    "aov_vnd": { "w": 781963, "w_prev": 764801, "wow_pct": 2.2 },
    "repeat_rate_pct": { "w": 31.5, "w_prev": 29.8, "delta_pts": 1.7 },
    "cancel_rto_rate_pct": { "w": 6.8, "w_prev": 5.4, "delta_pts": 1.4 }
  },
  "action_items": [
    { "owner": "Inventory", "priority": "P0", "task": "Nhập lại 5 SKU bán chạy vừa OOS trước thứ Tư" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ đọc dữ liệu qua `GET`. Không thay đổi trạng thái đơn hàng, tồn kho hay thông tin khách hàng.
- **Bảo vệ PII (`pii_level: financial`):** Tuyệt đối không đưa tên, SĐT hay địa chỉ khách hàng vào slide/báo cáo WBR (`export_allowed: false`).
- **Financial Disclaimer:** Bắt buộc ghi rõ tính chất *Operational Estimate* ở chân báo cáo.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng báo cáo, báo cập nhật `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu 1 trong 4 scope đọc | Báo chính xác scope bị thiếu (ví dụ thiếu `com.read_customers` sẽ không tính được Repeat Rate). |
| `404 Not Found` | Endpoint sai | Kiểm tra surface `com`. |
| `422 Unprocessable` | Định dạng `week_end_date` không hợp lệ | Xác thực `YYYY-MM-DD`. |
| `429 Too Many Requests` | Quét 14 ngày đơn hàng vượt rate limit | `HaravanClient` tự backoff `1s -> 2s -> 4s`; tách riêng 2 truy vấn tuần `W` và `W-1` nếu đơn lớn. |

- **Edge Case 1 — Tuần có ngày đôi Mega Sale (11.11 / 12.12 / Payday 25):** So sánh WoW tuần sau Mega Sale sẽ thấy sụt giảm mạnh (-40% đến -60%) là bình thường. Agent cần gắn cờ chú thích *Post-Mega-Sale Normalization* để tránh báo động giả.
- **Edge Case 2 — Khách mua vãng lai trên POS không lưu thông tin khách hàng (`customer == null`):** Không tính đơn `customer == null` vào mẫu số `Repeat Rate` (hoặc ghi rõ tỷ lệ đơn POS vãng lai) để không làm méo tỷ lệ khách quay lại.
- **Edge Case 3 — Đơn đặt cuối tuần `W` chưa kịp giao nên RTO tuần `W` nhìn thấp giả tạo:** Ghi chú rõ chỉ số RTO tuần `W` là sơ bộ vì một phần đơn đặt Thứ Sáu–Chủ Nhật vẫn đang trên đường giao.

## 8. Liên kết Workflow & Skill kế tiếp

- **Đào sâu nguyên nhân tăng tỷ lệ hoàn/chậm giao của từng ĐVVC:** Chạy `fulfillment-carrier-sla-audit` (L1).
- **Kéo tăng Repeat Rate tuần mới bằng chiến dịch chăm sóc khách cũ:** Chuyển sang `marketing-winback-campaign` (L2).
- **Tổng hợp 4 tuần WBR thành báo cáo đóng sổ cuối tháng:** Chạy `ops-monthly-financial-close` (L1).
