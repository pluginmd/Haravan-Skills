---
name: fulfillment-status-digest-wismo
description: "Tổng hợp trạng thái giao vận hàng loạt (chưa đóng gói, chờ lấy hàng, đang giao, giao thất bại, hoàn hàng) để xử lý WISMO chủ động."
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
    - "GET https://apis.haravan.com/com/orders/{order_id}/fulfillments.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 2000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---

# Haravan Fulfillment Status Digest & WISMO Report

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Skill này tạo báo cáo **"Where Is My Order?" (WISMO)** hàng ngày cho đội CSKH và Kho vận trên Haravan. Thay vì đợi khách hàng nhắn tin phàn nàn trên Harasocial/Zalo, báo cáo tự động gom nhóm mọi đơn hàng đang mở theo 6 trạng thái giao vận thực tế và **cảnh báo sớm các đơn bị kẹt quá ngưỡng SLA** (chưa đóng gói > 24h, chờ shipper lấy hàng > 24h, giao thất bại lần 1/2 cần gọi khách hẹn lại, hoặc đang chuyển hoàn).

**Tiêu chí hoàn thành (Definition of Done):**
- Quét toàn bộ đơn `status=open` (chưa đóng, chưa hủy) trong `lookback_days` và ánh xạ chuẩn xác `fulfillment_status` + `carrier_status_code`.
- Phân tách rõ danh sách đơn **vi phạm ngưỡng kẹt (`stuck_hours_threshold`)** theo thứ tự ưu tiên xử lý (P0: Giao thất bại/Đang hoàn → P1: Chờ lấy hàng quá hạn → P2: Chưa đóng gói quá hạn).
- Che toàn bộ PII (SĐT dạng `090****567`, ẩn số nhà/đường) trong báo cáo chia sẻ nội bộ.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/orders/{order_id}/fulfillments.json` |

**Ví dụ gọi nhanh qua `scripts/hrv_ops.py` hoặc `scripts/hrv_client.py`:**
```bash
# Chạy báo cáo WISMO với dữ liệu live (hoặc thêm --demo để chạy offline)
python3 scripts/hrv_ops.py wismo
python3 scripts/hrv_ops.py --demo wismo
```

**JSON Response trích xuất từ `GET /com/orders/{order_id}/fulfillments.json`:**
```json
{
  "fulfillments": [
    {
      "id": 88401255,
      "order_id": 1482011209,
      "status": "success",
      "tracking_company": "GHN",
      "tracking_number": "G89XLM22",
      "carrier_status_code": "delivering",
      "carrier_status_name": "Giao không thành công - Khách không nghe máy (lần 1)",
      "created_at": "2026-04-06T08:20:00Z",
      "updated_at": "2026-04-08T09:10:00Z"
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_days` | integer | No | `14` | Số ngày quét đơn mở gần nhất (`1`–`30`). |
| `stuck_hours_threshold` | integer | No | `48` | Ngưỡng giờ không cập nhật trạng thái vận đơn để gắn cờ `STUCK` (`12`–`168`). |
| `unshipped_sla_hours` | integer | No | `24` | Ngưỡng giờ tối đa đơn chưa đóng gói/xuất kho (`4`–`72`). |
| `channel_filter` | array[string] | No | `["all"]` | Lọc theo kênh (`web`, `harasocial`, `pos`, `shopee`, `tiktok`). |
| `include_pos` | boolean | No | `false` | Mặc định loại đơn POS mua trực tiếp tại cửa hàng khỏi báo cáo giao vận. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Lọc phạm vi đơn:** Gọi `GET /com/orders.json?status=open&created_at_min=<T0>`. Loại trừ đơn đã hủy (`cancelled_at != null`) và đơn POS giao tại quầy (nếu `include_pos=false`).
2. **Ánh xạ 6 Bucket Trạng thái WISMO:**
   - `UNPACKED`: `fulfillment_status` là `null` / `unshipped` / `notfulfilled`.
   - `READY_TO_PICK`: Có fulfillment, `carrier_status_code` $\in$ `{"readytopick", "picking"}`.
   - `IN_TRANSIT`: `carrier_status_code` $\in$ `{"delivering", "transporting", "sorting"}`.
   - `DELIVERY_FAILED`: `carrier_status_name` chứa từ khóa thất bại / hẹn lại / không nghe máy hoặc mã `notmeetcustomer`, `waitingforreturn`.
   - `RETURNING`: `carrier_status_code` $\in$ `{"return", "returning"}`.
   - `DELIVERED_OPEN`: `carrier_status_code == "delivered"` nhưng đơn vẫn `open` (thường do COD chưa đối soát `financial_status=pending`).
3. **Tính thời gian kẹt (Stuck Duration):**
   - Với `UNPACKED`: $\text{HoursStuck} = \frac{\text{Now} - \text{order.created\_at}}{3600}$ → cảnh báo nếu $> \text{unshipped\_sla\_hours}$.
   - Với đơn đã có vận đơn: $\text{HoursStuck} = \frac{\text{Now} - \text{fulfillment.updated\_at}}{3600}$ → cảnh báo nếu $> \text{stuck\_hours\_threshold}$.
4. **Xếp hạng ưu tiên hành động:** `P0` (`DELIVERY_FAILED` / `RETURNING` — CSKH gọi khách trong 2h để cứu đơn), `P1` (`READY_TO_PICK` > 24h — kho giục bưu cục lấy hàng), `P2` (`UNPACKED` > 24h — kiểm tra thiếu tồn kho), `P3` (`IN_TRANSIT` > 48h — tạo ticket tra soát NVC).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Tổng hợp Trạng thái Giao vận (WISMO — 14 ngày gần nhất):**
| Bucket trạng thái | Tổng đơn | Đơn kẹt quá SLA | Giá trị COD rủi ro (VND) | Đội phụ trách |
| --- | --- | --- | --- | --- |
| Chưa đóng gói (`UNPACKED`) | 34 | 6 (>24h) | 4.820.000 | Kho vận |
| Chờ lấy hàng (`READY_TO_PICK`) | 28 | 5 (>24h) | 3.150.000 | Kho + Bưu cục NVC |
| Đang giao (`IN_TRANSIT`) | 112 | 9 (>48h) | 11.400.000 | CSKH (tra soát NVC) |
| Giao thất bại (`DELIVERY_FAILED`) | 7 | 7 (P0) | 6.290.000 | CSKH (gọi cứu đơn ngay) |
| Đang chuyển hoàn (`RETURNING`) | 4 | 4 (P0) | 2.980.000 | CSKH + Kho nhận hoàn |

**Danh sách Ưu tiên P0 cần CSKH gọi ngay:**
| Ưu tiên | Mã đơn | SĐT (Redacted) | NVC / Tracking | Trạng thái chi tiết | Giờ kẹt | Gợi ý xử lý |
| --- | --- | --- | --- | --- | --- | --- |
| `P0` | `#108944` | `093****218` | GHN / `G89XLM22` | Không nghe máy lần 1 | 19h | Gọi xác nhận giờ giao lại + báo bưu tá |
| `P0` | `#108910` | `097****501` | GHTK / `S1928371` | Chờ xác nhận hoàn | 28h | Xin lưu kho thêm 24h nếu khách vẫn nhận |

```json
{
  "skill": "fulfillment-status-digest-wismo",
  "generated_at": "2026-04-10T08:30:00+07:00",
  "summary_buckets": { "UNPACKED": 34, "READY_TO_PICK": 28, "IN_TRANSIT": 112, "DELIVERY_FAILED": 7, "RETURNING": 4 },
  "stuck_orders": [
    {
      "priority": "P0",
      "order_id": 1482011209,
      "order_name": "#108944",
      "phone_redacted": "093****218",
      "province": "Hà Nội",
      "carrier": "GHN",
      "tracking_number": "G89XLM22",
      "bucket": "DELIVERY_FAILED",
      "hours_stuck": 19.2,
      "cod_amount_vnd": 890000
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Chỉ đọc trạng thái đơn và vận đơn; tuyệt đối không tự động gửi tin nhắn ZNS/SMS cho khách hay tự bấm hủy vận đơn.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Che số điện thoại (`093****218`), ẩn địa chỉ đường/số nhà (chỉ hiển thị Tỉnh/Thành phố) khi xuất báo cáo cho nhóm vận hành.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, yêu cầu cấp mới `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, kiểm tra cấu hình quyền app. |
| `404 Not Found` | Đơn đã bị xóa vĩnh viễn trong lúc đang quét | Bỏ qua `order_id` đó, ghi log cảnh báo và tiếp tục. |
| `422 Unprocessable` | Bộ lọc ngày giờ sai định dạng | Chuyển đổi sang ISO-8601 có múi giờ `+07:00`. |
| `429 Too Many Requests` | Gọi `fulfillments.json` lẻ cho nhiều đơn liên tiếp | Ưu tiên đọc trường `fulfillments` có sẵn trong `GET /com/orders.json`, chỉ gọi endpoint lẻ khi thiếu chi tiết; backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Đơn có nhiều vận đơn (hủy vận đơn cũ tạo vận đơn mới):** Một đơn hàng bị lỗi tạo vận đơn GHN rồi chuyển sang GHTK sẽ có 2 object trong `fulfillments[]` (1 `cancelled`, 1 `success`). Phải luôn lọc lấy **vận đơn đang hoạt động mới nhất** (`status != "cancelled"`), tránh báo nhầm đơn đang lỗi.
2. **Đơn giao thành công nhưng vẫn nằm ở `status=open`:** Rất phổ biến với đơn COD Viettel Post (nhập mã thủ công) chưa bấm xác nhận thu tiền trên Haravan. Cần tách vào bucket `DELIVERED_OPEN` để chuyển sang kế toán đối soát thay vì báo CSKH giục giao.
3. **Đơn đặt cuối tuần / ngày lễ (Chủ nhật, 30/4, Tết):** Bưu cục không lấy hàng khiến `hours_stuck` tăng giả tạo; cần ghi chú rõ ngày lễ/Chủ nhật khi đánh dấu `READY_TO_PICK` vượt 24h.

## 8. Liên kết Workflow & Skill kế tiếp
- **Tra cứu sâu 1 đơn bị kẹt:** Chuyển `order_id` sang `order-lookup-summary`.
- **Gắn tag phân luồng xử lý cho kho/CSKH:** Chuyển danh sách đơn `P0` sang `order-triage-tagging-proposal` (ví dụ tag `wismo-call-now`).
- **Đánh giá lại NVC có nhiều đơn kẹt:** Chạy `fulfillment-carrier-sla-vn`.
