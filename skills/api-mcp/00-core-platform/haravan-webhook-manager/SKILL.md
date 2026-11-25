---
name: haravan-webhook-manager
description: "Thiết kế, kiểm tra và xác thực chữ ký HMAC-SHA256 (X-Haravan-Hmacsha256) cho Private Webhook và Connect Webhook (wh_api)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 00-core-platform
layer: L0
wave: 1
mode: reference
risk: low
haravan:
  api_surface: webhook
  scopes:
    - wh_api
  endpoints:
    - "POST https://webhook.haravan.com/api/subscribe"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 50
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
# Haravan Webhook Manager — Thiết kế, Đăng ký & Xác thực HMAC-SHA256

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L0 / reference` cung cấp chuẩn kiến trúc để đăng ký, xác thực chữ ký bảo mật `X-Haravan-Hmacsha256` và xử lý idempotent cho các sự kiện thời gian thực từ Haravan (đơn hàng mới, cập nhật tồn kho, tạo vận đơn, hủy đơn). Trong vận hành đa kênh Việt Nam (đồng bộ ERP, kế toán MISA, kho vận, chatbot Zalo ZNS), webhook không có xác thực HMAC hoặc không xử lý trùng lặp sẽ gây tạo trùng đơn, gửi trùng tin nhắn ZNS hoặc sập server khi Haravan retry.

- **Khi nào sử dụng:** Khi tích hợp hệ thống bên thứ ba (ERP, CRM, kho, ZNS, Slack/Telegram alert) nhận sự kiện từ Haravan, hoặc khi cần debug webhook bị mất sự kiện / bị Haravan tự động vô hiệu hóa.
- **Khi nào KHÔNG sử dụng:** Khi chỉ cần chạy báo cáo định kỳ 1 lần/ngày (dùng polling API `GET` kết hợp `updated_at_min` sẽ đơn giản và dễ kiểm soát hơn).
- **Definition of Done (DoD):**
  1. Xác định đúng kênh webhook: **Private Webhook** (cấu hình trong Haravan Admin) hay **Connect Webhook** (`POST https://webhook.haravan.com/api/subscribe` với scope `wh_api`).
  2. Endpoint nhận webhook cài đặt đầy đủ 3 lớp bảo vệ: (a) Xác thực `X-Haravan-Hmacsha256` trên raw body, (b) Trả HTTP `200 OK` trong `< 3 giây` bằng hàng đợi bất đồng bộ (queue), (c) Chống xử lý trùng bằng Idempotency Key.
  3. Kiểm thử thành công cả trường hợp chữ ký hợp lệ (`200`) và chữ ký giả mạo (`401`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Loại Webhook | Scope yêu cầu | Endpoint / Cấu hình | Lưu ý quan trọng |
| --- | --- | --- | --- |
| **Connect Webhook (OAuth2 App)** | `wh_api` | `POST https://webhook.haravan.com/api/subscribe` | Phải gọi subscribe sau khi shop cài app và verify challenge `GET`. |
| **Private Webhook** | Quản trị Admin | Haravan Admin → Cấu hình → Thông báo / Webhook | Dùng `WEBHOOK_SECRET` cấu hình trong Admin. |

**Ví dụ 1 — Đăng ký Connect Webhook (`POST https://webhook.haravan.com/api/subscribe`):**
```json
// Headers: Authorization: Bearer <OAUTH2_ACCESS_TOKEN_WITH_WH_API>
// Content-Type: application/json
{}
// Response 200 OK:
{
  "message": "Subscribe webhook successfully"
}
```

**Ví dụ 2 — Challenge Verification (`GET` từ Haravan gửi tới Endpoint của bạn):**
```http
GET https://api.yourstore.vn/webhooks/haravan?hub.mode=subscribe&hub.challenge=1158201444&hub.verify_token=<YOUR_VERIFY_TOKEN>
```
→ Server của bạn phải kiểm tra `hub.verify_token` khớp ENV và trả về plain text `1158201444` với HTTP `200`.

**Ví dụ 3 — Payload thực tế sự kiện `orders/create` & xác thực HMAC bằng `scripts/hrv_client.py`:**
```json
// Headers:
// X-Haravan-Topic: orders/create
// X-Haravan-Org-Id: 200000123456
// X-Haravan-Hmacsha256: <base64_hmac_sha256_signature>
{
  "id": 1489023411,
  "order_number": "#104582",
  "financial_status": "pending",
  "fulfillment_status": "notfulfilled",
  "total_price": 685000.0,
  "gateway": "Thanh toán khi giao hàng (COD)",
  "created_at": "2026-11-25T06:15:22Z",
  "line_items": [
    { "sku": "ATN-DEN-L", "quantity": 2, "price": 325000.0 }
  ]
}
```
```python
from scripts.hrv_client import verify_webhook_hmac
# raw_body phải là bytes nguyên bản chưa qua json.loads()
is_valid = verify_webhook_hmac(raw_body=request.body, hmac_header=request.headers["X-Haravan-Hmacsha256"], secret=os.environ["HARAVAN_WEBHOOK_SECRET"])
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `webhook_mode` | enum (`connect`, `private`) | Có | `connect` | Chọn Connect Webhook (`wh_api`) hay Private Webhook. |
| `callback_url` | string (HTTPS) | Có | — | Bắt buộc HTTPS có chứng chỉ SSL hợp lệ; không dùng `localhost` hay IP trần. |
| `topics` | array[string] | Có | `["orders/create", "orders/updated"]` | Danh sách topic cần lắng nghe (vd `products/update`, `inventorylocationbalances/update`, `refunds/create`). |
| `verify_token` | string (ENV) | Có (với Connect) | — | Đọc từ `HARAVAN_WEBHOOK_VERIFY_TOKEN`, không hardcode. |
| `webhook_secret` | string (ENV) | Có | — | Đọc từ `HARAVAN_WEBHOOK_SECRET` (hoặc Client Secret với Connect App). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức xác thực HMAC-SHA256
```text
expected_sig = Base64( HMAC_SHA256(key = UTF8(WEBHOOK_SECRET), message = RAW_HTTP_BODY_BYTES) )
is_authentic = constant_time_compare(expected_sig, header["X-Haravan-Hmacsha256"])
```
- **Lưu ý sống còn:** Phải dùng `hmac.compare_digest()` (constant-time) để chống timing attack và tính trên **raw request bytes** (nếu parse JSON rồi serialize lại sẽ lệch khoảng trắng/thứ tự key → luôn fail HMAC).

### Kiến trúc xử lý bất đồng bộ & Chống trùng (Idempotency)
1. **Verify chữ ký:** Nếu `is_authentic == False` → trả `401 Unauthorized` và ghi log cảnh báo bảo mật (không log secret).
2. **Tạo Idempotency Key:** `key = sha256(f"{org_id}:{topic}:{payload['id']}:{payload.get('updated_at', '')}")`.
3. **Kiểm tra Dedup Store (Redis/DB với TTL 24–72h):** Nếu `key` đã tồn tại → trả ngay `200 OK` (`{"status": "duplicate_ignored"}`), không xử lý lại.
4. **Đẩy vào Queue & Ack nhanh:** Push raw event vào Redis/SQS/RabbitMQ và trả `200 OK` trong **< 2 giây** (Haravan timeout khoảng 5–10 giây; nếu chậm sẽ coi là lỗi và retry nhiều lần).
5. **Đối soát bù (Reconciliation Cron):** Vì webhook chỉ đảm bảo *at-least-once* và có thể rơi khi downtime, luôn chạy job polling định kỳ mỗi 15–30 phút (`GET /com/orders.json?updated_at_min=...`) để vá sự kiện sót.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo kiểm tra cấu hình Webhook (Markdown)
| Tiêu chí kiểm tra | Kết quả | Chi tiết |
| --- | --- | --- |
| Endpoint HTTPS & TLS | ĐẠT | `https://api.saigonstreetwear.vn/webhooks/haravan` (TLS 1.3, 180ms) |
| Challenge `GET` Verification | ĐẠT | Trả đúng `hub.challenge` khi khớp `verify_token` |
| Xác thực `X-Haravan-Hmacsha256` | ĐẠT | Chấp nhận payload hợp lệ (`200`), chặn payload giả (`401`) |
| Thời gian phản hồi P95 | ĐẠT | `145 ms` (< ngưỡng `3000 ms`) |
| Idempotency & Reconciliation | ĐẠT | Redis TTL 48h + Cron bù mỗi 30 phút |

### JSON Output Schema
```json
{
  "skill": "haravan-webhook-manager",
  "mode": "connect",
  "callback_url": "https://api.saigonstreetwear.vn/webhooks/haravan",
  "subscribed_topics": ["orders/create", "orders/updated", "orders/cancelled", "inventorylocationbalances/update"],
  "checks": {
    "https_valid": true,
    "challenge_verified": true,
    "hmac_valid_accepted": true,
    "hmac_invalid_rejected": true,
    "p95_latency_ms": 145
  },
  "reconciliation_recommended": true
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Bảo vệ Secret:** Không bao giờ log `HARAVAN_WEBHOOK_SECRET`, `CLIENT_SECRET`, hoặc raw payload chứa PII khách hàng (số điện thoại, địa chỉ nhà) vào log hệ thống dạng plain text; chỉ log `order_id`, `topic`, `org_id`.
- **Chống Replay Attack:** Kết hợp kiểm tra Idempotency Key và giới hạn kích thước body (`<= 2MB`) để tránh tấn công DoS.
- **Xác nhận khi bật mới:** Trước khi gọi `POST https://webhook.haravan.com/api/subscribe` trên production, xác nhận đã test thành công trên môi trường staging.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| Lỗi / Triệu chứng | Nguyên nhân | Cách khắc phục |
| --- | --- | --- |
| HMAC luôn trả `False` | Dùng sai secret (nhầm App Secret vs Private Webhook Secret) hoặc tính HMAC trên JSON đã parse | Đọc raw bytes trực tiếp từ HTTP stream; kiểm tra lại secret theo đúng loại webhook. |
| Webhook bị gửi lặp 5–10 lần cho 1 đơn | Server xử lý đồng bộ quá lâu (> 5s) khiến Haravan timeout và retry | Tách xử lý sang background worker, trả `200 OK` ngay lập tức + bật Idempotency Key. |
| Không nhận được webhook sau khi cài App | Quên gọi `POST https://webhook.haravan.com/api/subscribe` với token có `wh_api` | Gọi endpoint subscribe ngay sau bước OAuth2 callback hoàn tất. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Bão sự kiện (`orders/updated`) khi cập nhật vận đơn hàng loạt:** Mỗi khi đối tác vận chuyển (GHN/GHTK) cập nhật trạng thái giao hàng, Haravan bắn `orders/updated` liên tục. Nếu worker gọi ngược lại `GET /com/orders/{id}.json` cho mỗi webhook, sẽ nhanh chóng cạn leaky bucket 80 req. Hãy đọc trực tiếp dữ liệu từ payload webhook và debounce theo `order_id`.
2. **Thứ tự sự kiện bị đảo (Out-of-order delivery):** Sự kiện `orders/updated` có thể tới trước `orders/create` vài mili-giây. Luôn dùng thao tác `UPSERT` dựa trên so sánh `payload.updated_at >= db.updated_at`.
3. **Header phân biệt chữ hoa/thường:** Tùy reverse proxy (Nginx, Cloudflare), header có thể là `x-haravan-hmacsha256` thay vì `X-Haravan-Hmacsha256`. Luôn đọc header theo dạng case-insensitive.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup` (đảm bảo có scope `wh_api` cho Connect App), `haravan-api-core`.
- **Chạy tiếp theo:** `order-triage-daily` (đối soát đơn hàng hàng ngày), `inventory-low-stock-watchdog` (kết hợp sự kiện biến động tồn kho).
