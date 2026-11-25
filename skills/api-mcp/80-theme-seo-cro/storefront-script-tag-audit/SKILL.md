---
name: storefront-script-tag-audit
description: "Kiểm toán toàn bộ mã nhúng JavaScript bên thứ ba (/web/script_tags.json) để phát hiện script thừa, trùng pixel tracking hoặc làm chậm website."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 80-theme-seo-cro
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: web
  scopes:
    - web.read_script_tags
  endpoints:
    - "GET https://apis.haravan.com/web/script_tags/count.json"
    - "GET https://apis.haravan.com/web/script_tags.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 200
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

# Haravan Script Tags & Third-Party Overhead Audit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Kiểm kê toàn bộ mã JavaScript bên thứ ba đang được tự động tiêm vào storefront Haraweb và trang hoàn tất đơn hàng (`order_status` / Thank You) thông qua `/web/script_tags.json`, phát hiện script mồ côi từ app đã gỡ, trùng lặp Pixel quảng cáo (gây đo sai ROAS) và script dùng `http://` hoặc chặn luồng chính làm giảm Core Web Vitals (INP/LCP).
- **Ngữ cảnh Haravan:** Khi cài ứng dụng trên Haravan App Store (popup khuyến mãi, vòng quay may mắn, livechat, đánh giá sản phẩm, tracking pixel), app sẽ đăng ký `script_tag` chạy tự động trên mọi trang. Ngay cả khi cửa hàng đã ngừng dùng app hoặc đổi công cụ mới, nhiều `script_tag` vẫn còn tồn tại âm thầm tải hàng trăm KB JavaScript mỗi lần khách mở web trên 4G.
- **Definition of Done (DoD):**
  1. Lấy tổng số lượng (`GET /web/script_tags/count.json`) và toàn bộ danh sách chi tiết (`GET /web/script_tags.json`).
  2. Phân loại từng script theo 5 nhóm chức năng (`Analytics/Pixel`, `Livechat/Harasocial`, `CRO/Popup/Review`, `Shipping/Utility`, `Unknown/Orphan`) và phát hiện trùng tên miền/nhà cung cấp.
  3. Chấm điểm Third-Party Overhead Risk và xuất danh sách `script_tag.id` đề xuất rà soát gỡ bỏ (không tự ý xóa).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `web` (`https://apis.haravan.com/web`) |
| **Scopes tối thiểu** | `web.read_script_tags` |
| **Endpoints** | `GET /web/script_tags/count.json`, `GET /web/script_tags.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
count_resp = client.request("GET", "web", "/script_tags/count.json")
script_tags = client.paginate("web", "/script_tags.json", "script_tags", limit=50, max_pages=4)
print(f"Total script_tags: {count_resp.get('count', len(script_tags))}")
```

**Ví dụ JSON Response thực tế từ `GET /web/script_tags.json`:**
```json
{
  "script_tags": [
    {
      "id": 910248,
      "src": "https://cdn.example-popup-app.vn/widget.min.js?shop=demo.myharavan.com",
      "event": "onload",
      "display_scope": "online_store",
      "created_at": "2024-03-12T08:20:00+07:00",
      "updated_at": "2024-03-12T08:20:00+07:00"
    },
    {
      "id": 910305,
      "src": "http://legacy-tracker.oldapp.io/pixel.js",
      "event": "onload",
      "display_scope": "all",
      "created_at": "2023-08-05T14:11:00+07:00",
      "updated_at": "2023-08-05T14:11:00+07:00"
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `check_duplicate_domains` | `boolean` | Không | `true` | Phát hiện ≥ 2 script cùng hostname hoặc cùng chức năng tracking (ví dụ 2 script Meta/TikTok/GA4). |
| `stale_days_threshold` | `integer` | Không | `365` | Gắn cờ xem xét lại (`P2: STALE_SCRIPT`) nếu `updated_at` cũ hơn `365` ngày. |
| `max_safe_scripts` | `integer` | Không | `6` | Ngưỡng số lượng script bên thứ ba khuyến nghị trên mobile storefront (`> 6` cảnh báo nặng tải). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Thu thập & Kiểm đếm:** Gọi `GET /web/script_tags/count.json` rồi `paginate` `/web/script_tags.json` (tối đa `max_records: 200`).
2. **Phân tích từng `script_tag` theo 5 quy tắc rủi ro:**
   - **`P0 — INSECURE_HTTP`:** `src` bắt đầu bằng `http://` (gây lỗi Mixed Content trên HTTPS và rủi ro bảo mật chèn mã độc).
   - **`P0 — UNKNOWN_SUSPICIOUS_ORIGIN`:** Domain lạ không thuộc danh sách vendor phổ biến (Google, Meta, TikTok, Haravan/Hstatic, Zalo, Subiz, Crisp, Hotjar, Clarity, Antsomi...) và không có chủ sở hữu rõ ràng.
   - **`P1 — DUPLICATE_TRACKING_OR_DOMAIN`:** Có từ `2` script trở lên cùng domain hoặc cùng nhóm `Analytics/Pixel` (ví dụ vừa cài Pixel qua app vừa cài qua script tag -> nhân đôi sự kiện `Purchase` làm sai lệch ROAS).
   - **`P1 — EXCESSIVE_DISPLAY_SCOPE`:** Script popup/chat/banner không liên quan thanh toán nhưng đặt `display_scope == "all"` (tải cả trên trang Thank You / Order Status).
   - **`P2 — STALE_OR_BLOAT`:** Tổng số `script_tags > max_safe_scripts` hoặc script tạo từ > `stale_days_threshold` ngày không cập nhật.
3. **Ước tính Overhead Score:**
   $$\text{Overhead Risk} = \min(100,\; 25 \cdot N_{P0} + 12 \cdot N_{P1} + 4 \cdot N_{\text{total}})$$
   - `0–25`: Gọn nhẹ | `26–60`: Cần tối ưu | `> 60`: Quá tải JS, ảnh hưởng trực tiếp INP/TBT trên mobile.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Kiểm toán Script Tags & Mã Nhúng Bên Thứ Ba
- **Tổng Script Tags:** 9 (vượt ngưỡng khuyến nghị ≤ 6) | **Overhead Risk:** `68 / 100` (Cao)
- **Phát hiện:** 1 lỗi P0 (`http://`) | 2 lỗi P1 (trùng domain / thừa scope) | 2 cảnh báo P2 (script cũ > 1 năm)

| Mức độ | Script ID | Domain / Nguồn | Nhóm | Scope | Vấn đề phát hiện | Hành động đề xuất |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | `910305` | `legacy-tracker.oldapp.io` | Unknown | `all` | Dùng `http://` không an toàn, tạo từ 2023 | Xác nhận app đã gỡ & xóa thủ công |
| P1 | `910248` | `cdn.example-popup-app.vn` | CRO/Popup | `online_store` | Trùng với script `#910290` cùng domain | Giữ 1 bản mới nhất |
| P1 | `910412` | `widget.chat-vendor.com` | Livechat | `all` | Tải thừa trên trang `order_status` | Giới hạn chỉ `online_store` |
```

```json
{
  "skill": "storefront-script-tag-audit",
  "summary": { "total_scripts": 9, "p0_count": 1, "p1_count": 2, "p2_count": 2, "overhead_risk_score": 68 },
  "findings": [
    { "severity": "P0", "script_tag_id": 910305, "src": "http://legacy-tracker.oldapp.io/pixel.js", "category": "unknown", "display_scope": "all", "flags": ["INSECURE_HTTP", "STALE_SCRIPT"] }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ gọi `GET /web/script_tags*.json`. **Không tự ý gọi `DELETE /web/script_tags/{id}.json`** vì xóa nhầm script của app đang chạy hoặc pixel tracking sẽ làm đứt dữ liệu chuyển đổi quảng cáo (Facebook CAPI/Pixel, TikTok, GA4).
- **Quy trình dọn dẹp an toàn:** Báo cáo kết quả cho đội Marketing/Dev xác nhận từng `script_tag_id` trước khi gỡ app tương ứng trong Haravan Admin (`/admin/apps`) hoặc gọi xóa có kiểm soát.
- **Rollback:** Không áp dụng trong skill đọc này (`rollback.supported: false`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng audit, thông báo làm mới `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `web.read_script_tags` | Yêu cầu cấp đúng scope `web.read_script_tags` (không yêu cầu `write`). |
| `404 Not Found` | Gọi nhầm surface `/com/script_tags.json` | Chuyển sang surface `web` (`/web/script_tags.json`). |
| `422 Unprocessable` | Tham số `limit` không hợp lệ | Đặt `limit <= 250`. |
| `429 Too Many Requests` | Quét song song cùng nhiều skill khác | Dùng `HaravanClient` tự backoff `1s -> 2s -> 4s`. |

- **Edge Case 1 — Script nhúng cứng trong `layout/theme.liquid` thay vì `/web/script_tags.json`:** API `script_tags` chỉ trả về script đăng ký qua API của App. Nếu `/web/script_tags.json` trả về `[]` nhưng web vẫn chậm, bắt buộc kiểm tra thêm thẻ `<script>` nhúng trực tiếp trong `theme.liquid` bằng skill `theme-liquid-code-review`.
- **Edge Case 2 — Script tag thuộc sở hữu App khác:** Trên Haravan, một API token của App A thường chỉ thấy hoặc chỉ xóa được `script_tags` do chính App A tạo hoặc theo phân quyền của shop. Nếu số lượng thấy ít hơn thực tế trên DevTools trình duyệt, ghi chú rõ giới hạn phạm vi hiển thị API.
- **Edge Case 3 — Google Tag Manager (GTM) chứa hàng chục tag con bên trong:** API chỉ thấy 1 đường dẫn `gtm.js`, nhưng thực tế bên trong GTM có thể tải 15 script nặng. Agent cần nhắc kiểm tra thêm container GTM nếu phát hiện `googletagmanager.com`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Kiểm tra các thẻ `<script>` nhúng cứng trong mã nguồn theme:** Chạy ngay `theme-liquid-code-review` (L1).
- **Đánh giá tác động tốc độ lên trải nghiệm mua hàng trên mobile:** Kết hợp `theme-performance-cro-audit` (L1).
- **Kiểm tra xem pixel có bị trùng với cấu hình Google/TikTok Ads không:** Đối chiếu `marketing-ads-feed-google-tiktok-audit` (L1).
