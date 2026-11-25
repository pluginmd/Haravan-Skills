---
name: haravan-api-core
description: "Chuẩn kỹ thuật gọi Haravan REST API (/com/ và /web/), pagination, rate-limit leaky bucket và xử lý lỗi."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 00-core-platform
layer: L0
wave: 1
mode: reference
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/shop.json"
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
# Haravan API Core — Chuẩn gọi REST API, Pagination & Rate-Limit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill tầng nền tảng (`L0 / reference`) quy định chuẩn kỹ thuật bắt buộc cho mọi AI Agent và script khi tương tác với Haravan REST API (`/com/` cho Commerce/Omni và `/web/` cho Online Store). Tại Việt Nam, một cửa hàng Haravan Omni thường đồng bộ song song Website + HaraRetail POS + Shopee/TikTok Shop/Lazada, dẫn đến lưu lượng API cao và dễ dính `HTTP 429` nếu Agent tự viết vòng lặp `curl` không kiểm soát.

- **Khi nào sử dụng:** Trước khi chạy bất kỳ skill API nào trong `skills/api-mcp/`, khi viết script mới dùng `scripts/hrv_client.py`, hoặc khi cần debug lỗi HTTP `401/403/422/429/5xx`, sai phân trang, lệch múi giờ `UTC+7`.
- **Khi nào KHÔNG sử dụng:** Khi thao tác trực tiếp trên giao diện Haravan Admin (`skills/browser-ui/`) hoặc khi cần thiết lập OAuth2 token ban đầu (dùng `haravan-auth-setup`).
- **Definition of Done (DoD):**
  1. Xác nhận kết nối thành công tới `GET /com/shop.json` trả về HTTP `200`, đúng `domain` và `currency` (`VND`).
  2. Mọi lệnh gọi API đều đi qua `scripts/hrv_client.py` với `rate_limit <= 2.5 req/s` và `dry_run=True` mặc định.
  3. Phân trang lấy đủ bản ghi (không bỏ sót sau trang 1 mặc định `limit=50`) và ghi nhận rõ giới hạn `max_records` nếu dữ liệu lớn.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Surface | Base URL | Scope tối thiểu | Endpoint chuẩn kiểm tra kết nối |
| --- | --- | --- | --- |
| Commerce / Omni | `https://apis.haravan.com/com` | `com.read_shop` | `GET /com/shop.json` |
| Online Store / Web | `https://apis.haravan.com/web` | `web.read_themes` / `com.read_contents` | `GET /web/themes.json` |
| Connect Webhook | `https://webhook.haravan.com/api` | `wh_api` | `POST /api/subscribe` |

**Chạy nhanh kiểm tra qua CLI chuẩn của repo:**
```bash
export HARAVAN_ACCESS_TOKEN="<token_tu_env>"
python3 scripts/hrv_ops.py probe
# Chạy offline với dữ liệu mẫu Việt Nam:
python3 scripts/hrv_ops.py --demo probe
```

**Gọi qua Python `scripts/hrv_client.py` (có Leaky Bucket + Backoff + Dry-Run):**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True, req_per_sec=2.5)
shop = client.get("com", "/shop.json")
products = client.paginate("com", "/products.json", key="products", params={"limit": 50}, max_records=500)
```

**Sample Request Headers & Response (`GET https://apis.haravan.com/com/shop.json`):**
```json
// Headers: Authorization: Bearer <HARAVAN_ACCESS_TOKEN> | Content-Type: application/json
{
  "shop": {
    "id": 200000123456,
    "name": "Saigon Streetwear Official",
    "domain": "saigonstreetwear.vn",
    "myharavan_domain": "saigonstreetwear.myharavan.com",
    "currency": "VND",
    "timezone": "(GMT+07:00) Bangkok, Hanoi, Jakarta",
    "country_code": "VN",
    "province": "Hồ Chí Minh",
    "plan_name": "Omni Pro",
    "taxes_included": true
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `surface` | enum (`com`, `web`, `webhook`) | Có | `com` | Chọn đúng base URL; không gọi `/themes.json` trên `/com/`. |
| `path` | string | Có | `"/shop.json"` | Bắt đầu bằng `/`, kết thúc bằng `.json`. |
| `limit` | integer | Không | `50` | Trong khoảng `1..50` (nhiều endpoint Haravan giới hạn tối đa `50` hoặc `100`). |
| `page` / `since_id` | integer | Không | `1` / `0` | Ưu tiên `since_id` khi quét > 1.000 bản ghi để tránh trôi dữ liệu. |
| `req_per_sec` | float | Không | `2.5` | Giới hạn an toàn dưới mức leak rate `4.0 req/s` của Haravan. |
| `dry_run` | boolean | Không | `true` | Chặn mọi HTTP `POST/PUT/PATCH/DELETE` trong `HaravanClient`. |
| `max_records` | integer | Không | `5000` | Trần bảo vệ chống quét vô hạn trên cửa hàng > 50.000 SKU/đơn. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Mô hình Leaky Bucket của Haravan
- **Dung lượng xô (Bucket size):** `B = 80` requests.
- **Tốc độ rò (Leak rate):** `R = 4` requests/giây.
- **Công thức giãn cách an toàn:** `interval_sec = 1 / req_per_sec`. Mặc định `req_per_sec = 2.5` (`interval = 0.4s`) để chừa băng thông cho POS HaraRetail và đồng bộ sàn TMĐT chạy song song.
- **Backoff khi gặp HTTP `429` hoặc `5xx`:** `delay = min(16, 2^attempt)` giây (`1s → 2s → 4s → 8s → 16s`), tối đa `max_retries = 4`; sau lần `429` đầu tiên tự động hạ `req_per_sec` xuống `1.5`.

### Quy trình thực thi 5 bước chuẩn
1. **Xác thực môi trường:** Kiểm tra `os.getenv("HARAVAN_ACCESS_TOKEN")` tồn tại (tuyệt đối không in giá trị token ra log/stdout).
2. **Probe kết nối:** Gọi `GET /com/shop.json` để xác định `myharavan_domain`, `plan_name`, `currency`, `timezone`.
3. **Ước lượng khối lượng trước khi quét:** Gọi endpoint `/count.json` (ví dụ `/com/products/count.json`, `/com/orders/count.json`) để biết tổng `N`. Nếu `N > max_records`, thông báo chế độ lấy mẫu (`partial_sample: true`).
4. **Phân trang chuẩn:** Lặp `page = 1, 2, ...` với `limit=50` (hoặc `since_id = last_item["id"]` với orders/products lớn) cho đến khi mảng trả về rỗng hoặc `< limit` hoặc đạt `max_records`.
5. **Chuẩn hóa múi giờ & tiền tệ:** Chuyển timestamp ISO-8601 sang `Asia/Ho_Chi_Minh (UTC+7)` khi hiển thị báo cáo; giá VND giữ kiểu số nguyên (`int`), không làm tròn sai chữ số thập phân.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo tóm tắt kết nối API (Markdown)
| Hạng mục | Giá trị thực tế | Trạng thái |
| --- | --- | --- |
| Cửa hàng | Saigon Streetwear Official (`saigonstreetwear.myharavan.com`) | OK |
| Gói dịch vụ / Tiền tệ | Omni Pro / VND (`taxes_included: true`) | OK |
| Múi giờ hệ thống | `(GMT+07:00) Bangkok, Hanoi, Jakarta` | OK |
| Tốc độ gọi áp dụng | `2.5 req/s` (Leaky Bucket 80 / 4 req/s) | An toàn |
| Chế độ `dry_run` | `true` (Chặn toàn bộ mutation) | Bật |

### JSON Output Schema
```json
{
  "skill": "haravan-api-core",
  "status": "ok",
  "checked_at_utc": "2026-11-25T06:30:00Z",
  "shop": {
    "id": 200000123456,
    "domain": "saigonstreetwear.vn",
    "myharavan_domain": "saigonstreetwear.myharavan.com",
    "currency": "VND",
    "timezone": "(GMT+07:00) Bangkok, Hanoi, Jakarta"
  },
  "rate_limit_config": { "bucket": 80, "leak_per_sec": 4, "configured_req_per_sec": 2.5 },
  "dry_run": true
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ mặc định:** `L0 / reference`, chỉ cho phép `GET` khi kiểm tra kết nối.
- **Bảo vệ bí mật (Zero Secret Exposure):** Không bao giờ xuất `HARAVAN_ACCESS_TOKEN` vào log, traceback, file JSON hay phản hồi chat; chỉ hiển thị trạng thái `token_present: true`.
- **Chính sách PII:** Mọi helper trong `hrv_client.py` tích hợp sẵn `redact_phone()` (`090****567`) và `redact_email()` (`a***@domain.com`) cho các skill kế thừa.
- **Rollback:** Không áp dụng (chỉ đọc).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn, bị thu hồi hoặc sai định dạng `Bearer` | Dừng ngay, không retry; chuyển sang `haravan-auth-setup`. |
| `403 Forbidden` | Thiếu scope (vd gọi `/com/orders.json` khi chỉ có `com.read_shop`) hoặc gói cước chưa hỗ trợ endpoint | Ghi rõ endpoint + scope cần bổ sung trong `config/permissions.yaml`. |
| `404 Not Found` | Gọi sai surface (`/com/themes.json` thay vì `/web/themes.json`) hoặc ID không tồn tại | Kiểm tra lại bảng surface `com` vs `web` trước khi báo lỗi. |
| `422 Unprocessable Entity` | Payload sai kiểu dữ liệu, vượt giới hạn biến thể hoặc thiếu trường bắt buộc | Dừng mutation theo `partial_failure_policy: stop`, in chi tiết `errors`. |
| `429 Too Many Requests` | Vượt leaky bucket 80 req / 4 req/s (thường do POS/sàn đồng bộ cùng lúc) | Exponential backoff `1s→2s→4s→8s`, giảm `req_per_sec` xuống `1.5`. |
| `500 / 502 / 503 / 504` | Lỗi tạm thời từ gateway Haravan | Retry tối đa 4 lần với backoff; nếu vẫn lỗi thì lưu checkpoint `since_id`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Nhầm surface `/com/` và `/web/`:** Tài nguyên `themes`, `pages`, `redirects`, `blogs`, `script_tags` nằm ở `https://apis.haravan.com/web/`, còn `products`, `orders`, `customers`, `inventories` nằm ở `/com/`. Gọi sai surface sẽ trả `404` dù token đúng.
2. **Dữ liệu trả về có `null` thay vì mảng rỗng `[]`:** Một số endpoint cũ của Haravan trả `"variants": null` hoặc `"images": null`; code phải luôn dùng `(obj.get("variants") or [])`.
3. **Trôi bản ghi khi phân trang bằng `page=` trên đơn hàng đang phát sinh:** Trong giờ cao điểm livestream/flash sale (12.12, Tết), đơn mới liên tục đẩy vào đầu danh sách khiến `page=2` bị lặp bản ghi của `page=1`. Bắt buộc dùng `since_id` hoặc cố định `created_at_max` theo thời điểm bắt đầu quét.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup` (nếu chưa có `HARAVAN_ACCESS_TOKEN`).
- **Chạy tiếp theo:** `store-health-check` (khám sức khỏe 5 trụ cột), `store-config-audit` (kiểm toán cấu hình cửa hàng), hoặc `haravan-webhook-manager` (thiết lập nhận sự kiện real-time).
