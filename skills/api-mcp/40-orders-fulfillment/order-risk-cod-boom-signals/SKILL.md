---
name: order-risk-cod-boom-signals
description: "Phát hiện sớm các tín hiệu rủi ro bom hàng COD tại Việt Nam (địa chỉ thiếu phường/xã, SĐT lịch sử hủy cao, đơn COD giá trị lớn bất thường)."
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
    - com.read_customers
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/customers/{customer_id}.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
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

# Haravan COD Boom-Risk & Order Anomaly Signals

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Tỷ lệ hoàn/bom hàng COD tại Việt Nam thường chiếm 8–18% ở nhóm thời trang, mỹ phẩm và thực phẩm chức năng, gây thiệt hại kép (phí ship đi + phí chuyển hoàn + tồn kho bị giam). Skill này quét tự động các đơn COD mới chưa đóng gói trên Haravan, **chấm điểm rủi ro đa tín hiệu (0–100+)** để phân luồng CSKH gọi điện xác nhận hoặc gửi ZNS trước khi kho xuất hàng sang GHN/GHTK/Viettel Post.

**Tiêu chí hoàn thành (Definition of Done):**
- Quét toàn bộ đơn COD chưa giao (`fulfillment_status=unshipped`, `cancelled_at=null`) trong `lookback_hours`.
- Chấm điểm đầy đủ 6 tín hiệu rủi ro thực chiến VN kèm mã lý do (`signal_codes`) cho từng đơn.
- Phân nhóm chính xác 3 mức: `HIGH` (≥ 60đ — bắt buộc gọi xác nhận), `MEDIUM` (30–59đ — gửi ZNS xác nhận), `LOW` (< 30đ — cho qua kho đóng gói), đồng thời che PII (`090****567`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_customers` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/customers/{customer_id}.json` |

**Ví dụ chạy nhanh qua `scripts/hrv_ops.py`:**
```bash
python3 scripts/hrv_ops.py cod-risk
python3 scripts/hrv_ops.py --demo cod-risk
```

**JSON Response trích xuất từ `GET /com/orders.json` + `GET /com/customers/{id}.json`:**
```json
{
  "order": {
    "id": 1482099881,
    "name": "#109215",
    "created_at": "2026-04-10T02:15:00Z",
    "source_name": "web",
    "gateway": "Thanh toán khi giao hàng (COD)",
    "financial_status": "pending",
    "fulfillment_status": "unshipped",
    "total_price": 3250000.0,
    "line_items": [{ "sku": "TRA-200G", "quantity": 10 }],
    "shipping_address": { "address1": "gan cho", "ward": "", "district": "Huyện Bình Chánh", "province": "Hồ Chí Minh" },
    "customer": { "id": 70199, "phone": "0901234567", "orders_count": 1, "tags": "" }
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `lookback_hours` | integer | No | `24` | Cửa sổ quét đơn mới tính từ hiện tại (`1`–`168` giờ). |
| `high_value_cod_vnd` | integer | No | `2000000` | Ngưỡng giá trị đơn COD cao bất thường (VND). |
| `duplicate_window_minutes` | integer | No | `60` | Cửa sổ phát hiện đặt trùng nhiều đơn giống hệt từ cùng SĐT (phút). |
| `high_qty_first_order` | integer | No | `5` | Ngưỡng tổng số sản phẩm bất thường cho khách mua lần đầu. |
| `exclude_channels` | array[string] | No | `["pos"]` | Bỏ qua kênh mua trực tiếp tại cửa hàng. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Lọc tập đơn COD mục tiêu:** Chỉ giữ đơn `cancelled_at == null`, `fulfillment_status in (null, "unshipped", "notfulfilled")`, `financial_status == "pending"` và `gateway` khớp COD.
2. **Bảng chấm điểm Rủi ro COD (Scoring Rubric):**

| Mã tín hiệu | Điều kiện phát hiện | Điểm |
| --- | --- | --- |
| `HIST_CANCEL_2PLUS` | Khách có $\ge 2$ đơn hủy/hoàn trước đó trong lịch sử Haravan | `+40` |
| `HIGH_VALUE_COD` | `total_price >= high_value_cod_vnd` (mặc định ≥ 2.000.000đ) | `+30` |
| `INCOMPLETE_ADDRESS` | Thiếu `ward` (phường/xã), hoặc `address1` < 8 ký tự / chứa từ khóa mơ hồ (`gần chợ`, `ngã tư`, `test`) | `+25` |
| `DUPLICATE_ORDER_1H` | Cùng SĐT chuẩn hóa (`0xxxxxxxxx`) đặt $\ge 2$ đơn trong `duplicate_window_minutes` | `+25` |
| `FIRST_ORDER_BULK_QTY` | Khách mới (`orders_count <= 1`) nhưng tổng số lượng sản phẩm $\ge$ `high_qty_first_order` | `+20` |
| `INVALID_VN_PHONE` | SĐT chuẩn hóa không đủ 10 số hoặc sai đầu số nhà mạng VN (`03/05/07/08/09`) | `+35` |

3. **Phân tầng hành động (Risk Tiering):**
   - `HIGH` ($\text{Score} \ge 60$): **Bắt buộc CSKH gọi điện xác nhận** (và đề xuất gắn tag `cod-verify` để khóa xuất kho tạm thời).
   - `MEDIUM` ($30 \le \text{Score} \le 59$): Gửi tin nhắn ZNS / Harasocial xác nhận địa chỉ & thời gian nhận hàng.
   - `LOW` ($\text{Score} < 30$): Đủ điều kiện chuyển kho đóng gói bình thường.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Danh sách Đơn COD có Tín hiệu Rủi ro (24h qua — 184 đơn COD đã quét):**
| Mức độ | Mã đơn | SĐT (Redacted) | Giá trị COD (VND) | Khu vực | Điểm | Tín hiệu phát hiện | Khuyến nghị CSKH |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `HIGH` | `#109215` | `090****567` | 3.250.000 | Bình Chánh, HCM | **95** | `HIST_CANCEL_2PLUS`, `HIGH_VALUE_COD`, `INCOMPLETE_ADDRESS` | Gọi xác nhận + yêu cầu cọc ship/10% |
| `HIGH` | `#109218` | `098****102` | 2.150.000 | Thanh Xuân, HN | **75** | `HIGH_VALUE_COD`, `DUPLICATE_ORDER_1H`, `FIRST_ORDER_BULK_QTY` | Gọi xác nhận khách có đặt nhầm 2 đơn không |
| `MEDIUM` | `#109220` | `091****844` | 620.000 | Ninh Kiều, Cần Thơ | **35** | `INVALID_VN_PHONE` | Nhắn Harasocial/email xin lại SĐT đúng |

```json
{
  "skill": "order-risk-cod-boom-signals",
  "scanned_cod_orders": 184,
  "tiers": { "HIGH": 6, "MEDIUM": 19, "LOW": 159 },
  "flagged_orders": [
    {
      "order_id": 1482099881,
      "order_name": "#109215",
      "phone_redacted": "090****567",
      "area": "Huyện Bình Chánh, Hồ Chí Minh",
      "cod_amount_vnd": 3250000,
      "risk_score": 95,
      "risk_tier": "HIGH",
      "signals": ["HIST_CANCEL_2PLUS", "HIGH_VALUE_COD", "INCOMPLETE_ADDRESS"],
      "recommended_action": "CALL_VERIFY_AND_TAG_COD_VERIFY"
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Chỉ xuất **tín hiệu cảnh báo (signals)** hỗ trợ nhân viên duyệt; **tuyệt đối không tự hủy đơn**, không tự chặn tài khoản và không gán nhãn "gian lận" khẳng định cho khách hàng.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Che SĐT (`090****567`) và ẩn số nhà chi tiết trong báo cáo tổng hợp.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng ngay, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.read_orders` hoặc `com.read_customers` | Dừng ngay; nếu chỉ thiếu `read_customers`, cảnh báo không thể tính tín hiệu `HIST_CANCEL_2PLUS`. |
| `404 Not Found` | Đơn khách vãng lai (`customer: null`) | Không gọi `/customers/{id}.json`, mặc định `orders_count = 1`. |
| `422 Unprocessable` | Tham số `created_at_min` sai format | Chuyển về ISO-8601 có múi giờ `+07:00`. |
| `429 Too Many Requests` | Gọi `/customers/{id}.json` liên tục cho 500 đơn | Cache kết quả theo `customer_id` trong phiên chạy và backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Khách VIP / Khách sỉ quen đặt đơn COD giá trị lớn (5–10 triệu):** Nếu khách có $\ge 3$ đơn giao thành công trước đó và tỷ lệ hủy = 0%, cần **giảm trừ `-30` điểm** (`TRUSTED_REPEAT_BUYER`) để tránh làm phiền khách VIP gọi xác nhận lại.
2. **Đơn đặt từ Harasocial không có email và nhân viên nhập địa chỉ tự do vào `address1`:** Trường `ward` có thể rỗng dù khách đã ghi "P. Bến Nghé" trong `address1`. Thuật toán cần kiểm tra regex `(p\.|phường|xã|thị trấn)` trong `address1` trước khi cộng điểm `INCOMPLETE_ADDRESS`.
3. **Đơn đặt nhầm 2 lần do lỗi mạng 4G (Double-click Checkout):** Thường có `line_items` giống hệt nhau cách nhau 1–3 phút; đây là trường hợp CSKH cần gọi gộp/hủy 1 đơn chứ không phải bom hàng ác ý.

## 8. Liên kết Workflow & Skill kế tiếp
- **Gắn tag khóa xuất kho tạm thời:** Chuyển các đơn `HIGH` sang `order-triage-tagging-proposal` để gắn tag `cod-verify`.
- **Chuẩn hóa địa chỉ thiếu phường/xã:** Chuyển các đơn dính `INCOMPLETE_ADDRESS` sang `customer-address-correction-proposal`.
- **Hủy đơn sau khi CSKH gọi khách xác nhận không mua:** Chuyển sang `order-cancel-restock-critical`.
