---
name: catalog-product-lifecycle-proposal
description: "Đề xuất ẩn/hiện sản phẩm hoặc gắn tag vòng đời (new-arrival, clearance, out-of-season) theo quy tắc tồn kho & doanh số."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 20-catalog-merchandising
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_products
    - com.write_products
  endpoints:
    - "GET https://apis.haravan.com/com/products.json"
    - "PUT https://apis.haravan.com/com/products/{product_id}.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 100
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---
# Catalog Product Lifecycle Proposal — Quản Lý Vòng Đời Sản Phẩm (Ẩn/Hiện & Tag)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` tự động phân tích vòng đời sản phẩm dựa trên ngày ra mắt (`created_at`), tồn kho và trạng thái bán để đề xuất cập nhật trạng thái hiển thị (`published: true/false`) và bộ **Lifecycle Tags** chuẩn hóa (`new-arrival`, `best-seller`, `clearance`, `out-of-season`, `sold-out-archive`). Tại Việt Nam (đặc biệt ngành Thời trang, Giày dép, Đồ theo mùa), việc giữ hàng trăm mẫu đã hết hàng 6 tháng trên trang đầu danh mục làm giảm mạnh tỷ lệ chuyển đổi và lãng phí ngân sách quảng cáo.

- **Khi nào sử dụng:** Chuyển mùa bộ sưu tập (Xuân-Hè → Thu-Đông), dọn dẹp sản phẩm hết hàng lâu ngày sau Mega Sale, hoặc tự động đẩy hàng mới vào Smart Collection `"Hàng Mới Về"` bằng tag `new-arrival`.
- **Khi nào KHÔNG sử dụng:** Khi muốn xóa vĩnh viễn sản phẩm (tuyệt đối ưu tiên **ẩn** `published: false` thay vì `DELETE` để bảo toàn lịch sử đơn hàng & báo cáo kế toán).
- **Definition of Done (DoD):**
  1. Đọc danh mục sản phẩm qua `GET /com/products.json` và đối chiếu tồn kho/ngày tạo theo quy tắc vòng đời đã cấu hình.
  2. Tính toán tập tag mới theo nguyên tắc **Merge an toàn** (chỉ thêm/bớt các tag thuộc nhóm vòng đời, giữ nguyên 100% tag khác của shop như tag màu sắc, chất liệu, app khuyến mãi).
  3. Xuất Dry-Run Preview (`.backup.json` + `.preview.csv`) và kiểm tra conflict `updated_at` trước khi gọi `PUT /com/products/{product_id}.json`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đọc danh sách sản phẩm, tags & ngày tạo | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50` |
| Cập nhật trạng thái hiển thị & tags | `com.write_products` | `PUT https://apis.haravan.com/com/products/{product_id}.json` |

**JSON Request Payload (`PUT https://apis.haravan.com/com/products/1041120088.json`):**
```json
{
  "product": {
    "id": 1041120088,
    "published": false,
    "tags": "ao-khoac, cotton, out-of-season, sold-out-archive"
  }
}
```

**Sample Response (`200 OK`):**
```json
{
  "product": {
    "id": 1041120088,
    "title": "Áo Khoác Phao Đông 2024",
    "published_at": null,
    "tags": "ao-khoac, cotton, out-of-season, sold-out-archive",
    "updated_at": "2026-11-25T07:15:40Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `new_arrival_days` | integer | Không | `30` | Sản phẩm tạo trong vòng `<= 30` ngày được gắn tag `new-arrival`. |
| `hide_zero_stock_days` | integer | Không | `60` | Đề xuất ẩn (`published: false`) nếu hết tồn (`total_qty <= 0`) và không cập nhật quá `60` ngày. |
| `managed_lifecycle_tags` | array[string] | Không | `["new-arrival", "clearance", "out-of-season", "sold-out-archive"]` | Chỉ các tag nằm trong danh sách này mới được thêm/gỡ tự động. |
| `preserve_seo_urls` | boolean | Không | `true` | Nếu `true`, cảnh báo danh sách URL cần tạo Redirect 301 trước khi ẩn sản phẩm có traffic SEO. |
| `max_records` | integer | Không | `100` | Giới hạn số sản phẩm cập nhật mỗi batch. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Ma trận Luật Vòng Đời (Lifecycle State Machine)
Với mỗi sản phẩm `p`, tính `age_days = (now - p.created_at).days` và `total_stock = sum(v.inventory_quantity for v in p.variants if v.inventory_management)`:
1. **Giai đoạn Mới (`new-arrival`):** `age_days <= new_arrival_days` AND `total_stock > 0` → thêm tag `new-arrival`, gỡ `out-of-season`.
2. **Hết thời gian Hàng Mới:** `age_days > new_arrival_days` AND `"new-arrival" in p.tags` → gỡ tag `new-arrival`.
3. **Lưu trữ Hết hàng (`sold-out-archive`):** `total_stock <= 0` AND `(now - p.updated_at).days >= hide_zero_stock_days` → đề xuất `published: false` + gắn tag `sold-out-archive`.
4. **Quy tắc Merge Tag An toàn (bắt buộc):**
   ```text
   existing_tags = [t.strip() for t in p.tags.split(",") if t.strip()]
   preserved_tags = [t for t in existing_tags if t not in managed_lifecycle_tags]
   final_tags = ", ".join(preserved_tags + computed_lifecycle_tags)
   ```
   *(Tuyệt đối không gửi chuỗi chỉ có tag mới vì `PUT /products/{id}.json` trên Haravan sẽ **ghi đè toàn bộ** trường `tags`!)*

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Cập nhật Vòng đời Sản phẩm (Dry-Run Preview)
- **Tổng sản phẩm đề xuất thay đổi:** `24` (`9` gỡ `new-arrival`, `8` gắn `new-arrival`, `7` ẩn `sold-out-archive`)

| Product ID | Tên sản phẩm | Trạng thái (`Before → After`) | Tags (`Before → After`) | Ghi chú rủi ro |
| --- | --- | --- | --- | --- |
| `1058923401` | Áo Thun 250GSM - Đen | `published → published` | `cotton` → `cotton, new-arrival` | Mới tạo 4 ngày, tồn 85 |
| `1041120088` | Áo Khoác Phao 2024 | `published → hidden` | `ao-khoac` → `ao-khoac, sold-out-archive` | Tồn 0 quá 75 ngày (cân nhắc Redirect 301) |

### JSON Output Schema
```json
{
  "skill": "catalog-product-lifecycle-proposal",
  "dry_run": true,
  "summary": { "total_changes": 24, "add_new_arrival": 8, "remove_new_arrival": 9, "archive_hidden": 7 },
  "seo_redirect_candidates": ["/products/ao-khoac-phao-dong-2024"],
  "artifacts": {
    "backup_json": "artifacts/hrv-catalog-product-lifecycle-proposal-20261125T071500Z.backup.json",
    "preview_csv": "artifacts/hrv-catalog-product-lifecycle-proposal-20261125T071500Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Optimistic Concurrency Check (`updated_at`):** Trước khi gọi `PUT`, nếu `updated_at` hiện tại khác bản snapshot lúc dry-run → dừng bản ghi đó và cảnh báo xung đột (nhân viên vừa sửa sản phẩm).
- **Post-Write Verification:** Gọi `GET /com/products/{id}.json` xác nhận `published_at` và `tags` khớp hoàn toàn.
- **Rollback:** Dùng `.backup.json` chứa nguyên văn `published` và `tags` gốc để gọi lại `PUT /com/products/{id}.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | Chuỗi `tags` quá dài hoặc chứa ký tự điều khiển | Lọc trùng tag và kiểm tra độ dài từng tag `< 255` ký tự. |
| `404 Not Found` | Sản phẩm đã bị xóa thủ công sau khi chạy dry-run | Ghi log `skipped_not_found`, dừng nếu vượt ngưỡng lỗi. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Ẩn sản phẩm đang chạy Quảng cáo Facebook/TikTok/Google Shopping:** Nếu ẩn sản phẩm đang là đích của quảng cáo, trang sẽ báo 404 làm rớt tiền ads ngay lập tức. Luôn kiểm tra và yêu cầu team Marketing xác nhận danh sách `archive_hidden` trước khi bấm duyệt.
2. **Sản phẩm có `inventory_policy == "continue"` (cho phép đặt trước / Pre-order):** Dù `total_stock <= 0` nhưng shop vẫn đang nhận đơn đặt trước; phải loại trừ nhóm `inventory_policy == "continue"` khỏi luật tự động ẩn!
3. **Ghi đè mất tag kích hoạt Smart Collection hoặc app khuyến mãi:** Vì Haravan `PUT` thay thế toàn bộ chuỗi `tags`, luôn sử dụng thuật toán `preserved_tags + computed_lifecycle_tags`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `inventory-aging-dead-stock` (xác định hàng tồn chậm cần gắn tag `clearance`).
- **Chạy tiếp theo:** `store-redirect-audit` (nếu có sản phẩm bị ẩn cần tạo chuyển hướng 301), `catalog-collection-reorg-proposal`.
