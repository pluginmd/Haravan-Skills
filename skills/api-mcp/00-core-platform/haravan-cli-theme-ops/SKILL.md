---
name: haravan-cli-theme-ops
description: "Quy trình cài đặt và sử dụng @haravan/cli (pull, watch, deploy) kết hợp staging theme để phát triển giao diện Haravan Liquid an toàn."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 00-core-platform
layer: L0
wave: 1
mode: reference
risk: low
haravan:
  api_surface: cli
  scopes:
    - web.read_themes
    - web.write_themes
  endpoints:
    - "GET https://apis.haravan.com/web/themes.json"
    - "GET https://apis.haravan.com/web/themes/{theme_id}/assets.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 20
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---
# Haravan CLI Theme Ops — Quy trình @haravan/cli & Staging Theme An Toàn

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L0 / reference` chuẩn hóa quy trình phát triển, sao lưu và triển khai giao diện Haravan Liquid (`.liquid`, `.css`, `.js`, `settings_data.json`) bằng `@haravan/cli` kết hợp với **Staging/Unpublished Theme**. Trên Haravan, sửa trực tiếp Live Theme (`role: "main"`) là nguyên nhân phổ biến gây vỡ giỏ hàng, hỏng nút "Mua ngay", mất sự kiện Facebook Pixel/TikTok Pixel giữa chiến dịch quảng cáo.

- **Khi nào sử dụng:** Trước khi chỉnh sửa giao diện, thêm mã tracking/JSON-LD, tối ưu tốc độ tải trang (Core Web Vitals), hoặc sao lưu theme trước đợt nâng cấp lớn (Tết, Mega Sale 11.11/12.12).
- **Khi nào KHÔNG sử dụng:** Khi chỉ đổi ảnh banner/chữ trong `settings_data.json` qua trình duyệt Haravan Admin (dùng nhóm `skills/browser-ui/`), hoặc khi sửa sản phẩm/giá (dùng `20-catalog-merchandising`).
- **Definition of Done (DoD):**
  1. Xác định được danh sách theme qua `GET /web/themes.json`, phân biệt rõ Live Theme (`role: "main"`) và Staging Theme (`role: "unpublished"`).
  2. Toàn bộ mã nguồn Live Theme được kéo về máy (`haravan pull`) và commit vào Git làm bản backup trước khi sửa.
  3. Mọi thay đổi được `deploy` lên **Staging Theme** trước, có link preview kiểm thử Desktop + Mobile (iOS/Android), tuyệt đối không ghi đè thẳng lên `role: "main"` khi chưa có xác nhận L3 ở lượt riêng.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Công cụ / Endpoint | Scope yêu cầu | Mục đích |
| --- | --- | --- |
| `GET https://apis.haravan.com/web/themes.json` | `web.read_themes` | Liệt kê tất cả theme, lấy `theme_id` và `role` (`main` / `unpublished`) |
| `GET https://apis.haravan.com/web/themes/{theme_id}/assets.json` | `web.read_themes` | Kiểm kê danh sách file asset & dung lượng/thời gian cập nhật |
| `@haravan/cli` (`haravan pull / watch / deploy`) | `web.read_themes`, `web.write_themes` | Đồng bộ file Liquid hai chiều với Staging Theme |

**Quy trình lệnh `@haravan/cli` chuẩn Production:**
```bash
# 1. Cài đặt và kiểm tra phiên bản
npm install -g @haravan/cli && haravan --version

# 2. Khởi tạo thư mục làm việc và backup Live Theme (read-only)
mkdir -p theme-workspace && cd theme-workspace
git init
haravan pull --store=saigonstreetwear.myharavan.com --theme-id=1000881122
git add . && git commit -m "backup: live theme before sprint-2026-11"

# 3. Chuyển sang Staging Theme (role: unpublished) để phát triển & xem trước
haravan watch --store=saigonstreetwear.myharavan.com --theme-id=1000889955
# Hoặc deploy 1 file cụ thể lên Staging Theme:
haravan deploy snippets/product-card.liquid --theme-id=1000889955
```

**Sample Response từ `GET https://apis.haravan.com/web/themes.json`:**
```json
{
  "themes": [
    {
      "id": 1000881122,
      "name": "F1Gen Fashion Live v3.4",
      "role": "main",
      "created_at": "2025-08-10T03:12:00Z",
      "updated_at": "2026-11-20T09:45:12Z",
      "previewable": true
    },
    {
      "id": 1000889955,
      "name": "STAGING - Sale 12.12 (Copy of v3.4)",
      "role": "unpublished",
      "created_at": "2026-11-24T04:00:00Z",
      "updated_at": "2026-11-25T05:10:00Z",
      "previewable": true
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `store_domain` | string | Có | — | Tên miền gốc `*.myharavan.com`. |
| `live_theme_id` | integer | Có | Auto-detect (`role == "main"`) | Chỉ dùng để `pull` backup, cấm `deploy` trực tiếp. |
| `staging_theme_id` | integer | Có | — | Bắt buộc có `role == "unpublished"` trước khi `watch`/`deploy`. |
| `ignore_files` | array[string] | Không | `["config/settings_data.json"]` | Tránh ghi đè cấu hình banner/section mà team Marketing vừa chỉnh trên Admin. |
| `asset_keys` | array[string] | Không | `[]` | Danh sách file cụ thể cần kiểm tra hoặc deploy (vd `layout/theme.liquid`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Quy tắc khóa an toàn Live Theme (Live-Theme Guardrail)
```text
IF target_theme.role == "main":
    BLOCK deploy / PUT asset
    REQUIRE: duplicate Live Theme -> get staging_theme_id (role == "unpublished")
```

### Quy trình 6 bước phát triển & triển khai Theme
1. **Kiểm kê Theme:** Gọi `GET /web/themes.json` → xác nhận có tối thiểu 1 bản `unpublished` mới nhân bản từ `main`. Nếu số lượng theme gần giới hạn gói (thường tối đa 10–20 theme), cảnh báo dọn theme cũ.
2. **Pull & Git Snapshot:** Chạy `haravan pull` từ `live_theme_id` vào nhánh `main` của Git để có điểm rollback tức thì.
3. **Bảo vệ `config/settings_data.json`:** Trước khi deploy lên staging hoặc merge, luôn thêm `config/settings_data.json` vào danh sách ignore (trừ khi cố ý sửa schema cài đặt) để không làm mất banner/menu mà nhân sự vận hành vừa chỉnh trên Admin UI.
4. **Kiểm tra Static Asset & Liquid Syntax:** Quét các lỗi thường gặp trước khi đẩy: thẻ `{% if %}` / `{% for %}` chưa đóng, script đồng bộ chặn render (thiếu `defer`/`async`), ảnh thiếu `loading="lazy"` hoặc không dùng bộ lọc resize `img_url: 'grande'`.
5. **Deploy lên Staging & QA Checklist:** Đẩy thay đổi lên `staging_theme_id`, mở link preview `https://<domain>/?preview_theme_id=<staging_theme_id>` kiểm thử 4 luồng cốt lõi: Trang chủ → Trang sản phẩm (chọn biến thể) → Thêm giỏ hàng (Ajax Cart) → Nút Thanh toán (`/checkout`).
6. **Publish có kiểm soát (L3):** Chỉ chuyển đổi Publish trên Haravan Admin sau khi người dùng xác nhận ở lượt riêng và chọn khung giờ thấp điểm (23:00–06:00 giờ VN).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bảng kiểm kê Theme & Trạng thái An toàn (Markdown)
| Theme ID | Tên Theme | Vai trò (`role`) | Cập nhật gần nhất (UTC+7) | Quyền thao tác |
| --- | --- | --- | --- | --- |
| `1000881122` | F1Gen Fashion Live v3.4 | `main` (LIVE) | 2026-11-20 16:45 | Chỉ `pull` / Backup |
| `1000889955` | STAGING - Sale 12.12 | `unpublished` | 2026-11-25 12:10 | Cho phép `watch` / `deploy` |

### JSON Output Schema
```json
{
  "skill": "haravan-cli-theme-ops",
  "store_domain": "saigonstreetwear.myharavan.com",
  "live_theme": { "id": 1000881122, "name": "F1Gen Fashion Live v3.4", "role": "main" },
  "staging_theme": { "id": 1000889955, "name": "STAGING - Sale 12.12", "role": "unpublished" },
  "preview_url": "https://saigonstreetwear.vn/?preview_theme_id=1000889955",
  "git_backup_commit": "a1b2c3d",
  "ignored_files": ["config/settings_data.json"],
  "ready_to_deploy_staging": true
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Cấm tuyệt đối:** Không chạy `haravan deploy` hoặc `PUT /web/themes/{id}/assets.json` vào `role: "main"` mà không qua Staging Theme và xác nhận L3 ở lượt riêng.
- **Backup bắt buộc:** Lưu bản snapshot toàn bộ thư mục theme trong Git hoặc file zip tại `artifacts/theme-backup-<theme_id>-<timestamp>.zip`.
- **Kịch bản Rollback:**
  - Nếu đã lỡ ghi đè file asset trên staging/live: `git checkout <backup_commit> -- <file_path>` và `haravan deploy <file_path> --theme-id=<theme_id>`.
  - Nếu đã publish theme lỗi lên Live: vào Haravan Admin → Website → Giao diện → nhấn **Xuất bản (Publish)** lại bản theme Live cũ đã giữ nguyên trước đó (thời gian khôi phục < 30 giây).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| Lỗi thường gặp | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `403 Forbidden` khi `pull/deploy` | Token thiếu `web.read_themes` hoặc `web.write_themes` | Bổ sung scope Web Theme cho Private App hoặc đăng nhập lại CLI. |
| `422 Unprocessable Entity` | Lỗi cú pháp Liquid (`Liquid syntax error`) hoặc kích thước file asset vượt giới hạn | Kiểm tra dòng báo lỗi Liquid, tách file JS/CSS lớn > 1MB hoặc nén ảnh trước khi upload. |
| `429 Too Many Requests` khi `deploy` toàn bộ theme | Đẩy hàng trăm file liên tiếp vượt leaky bucket | Chỉ deploy các file thay đổi (`git diff --name-only`) thay vì deploy toàn bộ thư mục. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Ghi đè mất dữ liệu `config/settings_data.json`:** Team Marketing thường sửa ảnh banner/popup trên Haravan Admin trực tiếp trên Live Theme. Nếu dev `pull` từ 3 ngày trước rồi `deploy` đè `settings_data.json`, toàn bộ banner mới sẽ biến mất. Luôn exclude file này hoặc `pull` mới nhất trước khi merge.
2. **Iframe cross-origin trong Haravan Admin (`web.haravan.app`):** Các màn hình Website trong Admin UI chạy trong iframe khác domain, khiến browser automation khó thao tác sửa code Liquid; luôn dùng `@haravan/cli` và Web API thay thế.
3. **Khác biệt Liquid của Haravan so với Shopify:** Haravan hỗ trợ cú pháp Liquid cổ điển, một số filter/object mới của Shopify OS 2.0 (`sections/*.json`, `image_tag`, `render` với tham số phức tạp) không tương thích hoàn toàn — luôn kiểm thử trên Staging Theme thực tế của Haravan.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup` (kiểm tra scope `web.read_themes`), `store-bootstrap-checklist`.
- **Chạy tiếp theo:** `storefront-theme-audit` (kiểm toán kỹ thuật theme), `seo-technical-audit` (tối ưu thẻ meta/schema trên Liquid).
