---
name: store-redirect-audit
description: "Kiểm toán toàn bộ luật chuyển hướng URL (/web/redirects.json) để phát hiện redirect loop, chain dài và đường dẫn xung đột SEO."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 10-store-bootstrap
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: web
  scopes:
    - com.read_contents
  endpoints:
    - "GET https://apis.haravan.com/web/redirects/count.json"
    - "GET https://apis.haravan.com/web/redirects.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 2000
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
# Store Redirect Audit — Kiểm Toán Chuyển Hướng URL & Phát Hiện Redirect Loop/Chain

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` kiểm toán toàn bộ bảng chuyển hướng URL 301 trên Haravan Online Store (`/web/redirects.json`) nhằm phát hiện **Redirect Loop** (vòng lặp vô hạn `A → B → A`), **Redirect Chain** (chuỗi nhảy nhiều bước `A → B → C` làm mất PageRank và chậm TTFB), **Self-Redirect** (`A → A`), và **Xung đột đường dẫn hệ thống** (`/cart`, `/checkout`, `/collections/all`). Tại Việt Nam, lỗi này rất hay phát sinh sau khi shop đổi cấu trúc URL SEO, xóa sản phẩm cũ hoặc migrate từ WordPress/Sapo sang Haravan.

- **Khi nào sử dụng:** Sau khi migrate website, sau đợt dọn dẹp/ẩn sản phẩm cũ hàng loạt, khi Google Search Console báo lỗi *"Trang có lệnh chuyển hướng"* hoặc *"Quá nhiều lần chuyển hướng"*.
- **Khi nào KHÔNG sử dụng:** Khi muốn tự động xóa hoặc ghi đè redirect ngay lập tức (skill này chỉ đọc và đề xuất danh sách sửa; thao tác ghi cần lập proposal riêng).
- **Definition of Done (DoD):**
  1. Lấy tổng số redirect qua `GET /web/redirects/count.json` và tải toàn bộ danh sách (tối đa `max_records=2000`).
  2. Chạy thuật toán đồ thị có hướng (Directed Graph) để phát hiện 100% Loop, Chain (`hop >= 2`), Self-redirect, Duplicate path, và đích chứa domain lạ/HTTP không bảo mật.
  3. Xuất báo cáo phân loại mức độ nghiêm trọng (`CRITICAL / HIGH / MEDIUM`) kèm bảng đích tối ưu (`flatten target`) cho từng chuỗi.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đếm tổng số redirect | `com.read_contents` | `GET https://apis.haravan.com/web/redirects/count.json` |
| Danh sách quy tắc chuyển hướng | `com.read_contents` | `GET https://apis.haravan.com/web/redirects.json?limit=50&page=1` |

**Chạy trực tiếp qua CLI của repo (`scripts/hrv_ops.py`):**
```bash
python3 scripts/hrv_ops.py redirect-audit
# Chạy thử offline với bộ dữ liệu demo:
python3 scripts/hrv_ops.py --demo redirect-audit
```

**Sample Response (`GET https://apis.haravan.com/web/redirects.json?limit=50`):**
```json
{
  "redirects": [
    { "id": 90101, "path": "/products/ao-thun-cu", "target": "/products/ao-thun-v2" },
    { "id": 90102, "path": "/products/ao-thun-v2", "target": "/products/ao-thun-v3" },
    { "id": 90103, "path": "/collections/sale-2024", "target": "/collections/sale-2025" },
    { "id": 90104, "path": "/collections/sale-2025", "target": "/collections/sale-2024" }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `max_chain_hops` | integer | Không | `1` | Số bước nhảy tối đa chấp nhận được; chuỗi `>= 2` hop bị gắn cờ `HIGH`. |
| `protected_paths` | array[string] | Không | `["/", "/cart", "/checkout", "/account", "/search"]` | Đường dẫn hệ thống không được phép bị redirect đè. |
| `max_records` | integer | Không | `2000` | Giới hạn bản ghi quét; cảnh báo nếu `count > max_records`. |
| `normalize_case` | boolean | Không | `true` | Chuẩn hóa chữ thường và bỏ dấu `/` cuối khi so khớp đồ thị. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Chuẩn hóa URL & Xây dựng Đồ thị Chuyển hướng
Với mỗi bản ghi `r` trong `redirects`:
- `src = normalize(r.path)` (lowercase, bỏ trailing slash trừ `"/"`, giữ nguyên query string nếu có).
- `dst = normalize(r.target)` (nếu là URL tuyệt đối cùng domain cửa hàng thì cắt về relative path).
- Tạo ánh xạ `edge[src] = (dst, r.id)`.

### Thuật toán phát hiện 5 nhóm lỗi
1. **Self-Redirect (`CRITICAL`):** `src == dst`.
2. **Redirect Loop (`CRITICAL`):** Duyệt chuỗi `u -> edge[u]` bằng tập `visited` (DFS/cycle detection). Nếu quay lại một node đã nằm trong `visited` → ghi nhận vòng lặp kèm danh sách `redirect_id` tham gia.
3. **Redirect Chain (`HIGH`):** Độ dài chuỗi `hops >= 2` (ví dụ `A → B → C`). Tính sẵn đích cuối `final_target = C` để đề xuất làm phẳng (`A → C`).
4. **System Path Collision (`CRITICAL`):** `src` trùng với `protected_paths` (`/cart`, `/checkout`, `/`).
5. **Insecure / External Target (`MEDIUM`):** `target` bắt đầu bằng `http://` (không phải `https://`) hoặc trỏ ra domain ngoài không nằm trong whitelist (nguy cơ open redirect / phishing).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Kiểm toán Redirect SEO (Markdown)
- **Tổng số redirect đã quét:** `342 / 342` (`partial_sample: false`)
- **Tóm tắt lỗi:** `2 CRITICAL (Loop)` | `7 HIGH (Chain >= 2 hops)` | `3 MEDIUM (HTTP target)`

| Mức độ | Loại lỗi | Redirect ID(s) | Chuỗi hiện tại | Đề xuất khắc phục |
| --- | --- | --- | --- | --- |
| CRITICAL | Loop | `90103, 90104` | `/collections/sale-2024 → /collections/sale-2025 → /collections/sale-2024` | Xóa `90104`, trỏ `90103` về `/collections/flash-sale` |
| HIGH | Chain (2 hops) | `90101, 90102` | `/products/ao-thun-cu → /products/ao-thun-v2 → /products/ao-thun-v3` | Cập nhật `90101` trỏ thẳng sang `/products/ao-thun-v3` |
| MEDIUM | Insecure HTTP | `90215` | `/pages/huong-dan → http://saigonstreetwear.vn/pages/size-guide` | Đổi sang relative path `/pages/size-guide` |

### JSON Output Schema
```json
{
  "skill": "store-redirect-audit",
  "total_redirects": 342,
  "partial_sample": false,
  "summary": { "loops": 1, "self_redirects": 0, "chains": 7, "protected_collisions": 0, "insecure_targets": 3 },
  "loops": [{ "ids": [90103, 90104], "cycle": ["/collections/sale-2024", "/collections/sale-2025", "/collections/sale-2024"] }],
  "chains": [{ "ids": [90101, 90102], "hops": 2, "path": "/products/ao-thun-cu", "recommended_target": "/products/ao-thun-v3" }]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ Read-Only (`L1`):** Tuyệt đối không tự gọi `PUT` hoặc `DELETE /web/redirects/{id}.json`.
- **Cảnh báo Partial Sample:** Nếu `count > 2000`, phân tích đồ thị có thể bỏ sót chuỗi nối sang trang chưa tải — bắt buộc gắn cờ `partial_sample: true` và khuyến nghị tăng giới hạn hoặc xuất theo từng đợt.
- **PII:** Không có PII (`pii_level: none`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` | Thiếu scope `com.read_contents` (lưu ý: dù endpoint là `/web/redirects.json` nhưng scope trên Haravan là `com.read_contents`) | Cấp lại `com.read_contents` trong Private App. |
| `404 Not Found` | Gọi nhầm sang `https://apis.haravan.com/com/redirects.json` | Đổi sang surface `web` (`https://apis.haravan.com/web/redirects.json`). |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Haravan chỉ kích hoạt Redirect khi URL gốc trả 404:** Nếu một sản phẩm `/products/ao-thun-cu` vẫn đang ở trạng thái hiển thị (200 OK), quy tắc redirect cho đường dẫn đó sẽ **không chạy** trên storefront. Cần nhắc người dùng kiểm tra chéo với danh sách sản phẩm đang active nếu thấy redirect "không ăn".
2. **Đường dẫn có ký tự tiếng Việt hoặc URL-encoded (`%20`, `%C3%A1`):** Một số bản ghi nhập từ WordPress cũ chứa ký tự có dấu hoặc khoảng trắng; cần `urllib.parse.unquote()` khi đối chiếu tránh bỏ sót vòng lặp.
3. **Target trỏ tới trang đích đã bị xóa (404 Soft-dead target):** API `/web/redirects.json` chỉ cho biết quy tắc redirect, không tự biết trang đích còn tồn tại hay không; khuyến nghị kiểm tra HTTP status (HEAD) trên top 50 đích quan trọng.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `store-bootstrap-checklist` (khi migrate website).
- **Chạy tiếp theo:** `seo-technical-audit` (kiểm toán tổng thể SEO kỹ thuật), `catalog-product-lifecycle-proposal` (trước khi ẩn sản phẩm cũ cần lập redirect 301).
