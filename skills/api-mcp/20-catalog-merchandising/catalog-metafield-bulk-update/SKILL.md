---
name: catalog-metafield-bulk-update
description: "Đọc, kiểm chuẩn và đề xuất cập nhật hàng loạt Metafields cho sản phẩm/variant (thông số kỹ thuật, xuất xứ, hướng dẫn bảo quản)."
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
    - "GET https://apis.haravan.com/com/products/{product_id}/metafields.json"
    - "POST https://apis.haravan.com/com/products/{product_id}/metafields.json"
    - "GET https://apis.haravan.com/com/variants/{variant_id}/metafields.json"
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
# Catalog Metafield Bulk Update — Chuẩn Hóa & Cập Nhật Hàng Loạt Metafields

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` đọc, kiểm tra tính nhất quán và đề xuất cập nhật hàng loạt **Metafields** cho Sản phẩm (`/com/products/{product_id}/metafields.json`) hoặc Biến thể (`/com/variants/{variant_id}/metafields.json`). Tại Việt Nam, Metafields trên Haravan được dùng rộng rãi để lưu thông số kỹ thuật (bảng size, chất liệu vải, xuất xứ, số công bố mỹ phẩm, thời hạn bảo hành, hướng dẫn bảo quản) nhằm hiển thị tab thông số trên theme Liquid hoặc lọc nâng cao.

- **Khi nào sử dụng:** Khi bổ sung thông số kỹ thuật chuẩn hóa cho 10–100 sản phẩm, chuẩn bị dữ liệu cho bộ lọc mới trên giao diện, hoặc đồng bộ thông số từ ERP/Excel lên Haravan.
- **Khi nào KHÔNG sử dụng:** Khi chỉ cần gắn nhãn phân loại đơn giản (dùng `tags` nhanh và tiết kiệm API call hơn rất nhiều), hoặc cập nhật > 100 bản ghi cùng lúc (phải chia nhiều batch).
- **Definition of Done (DoD):**
  1. Đọc metafields hiện có của từng `product_id`/`variant_id` trong phạm vi batch (`<= 100`) để phát hiện xung đột `namespace.key` và lưu giá trị cũ làm backup.
  2. Kiểm tra chuẩn `namespace`, `key`, `value_type` (`string`, `integer`, `json_string`), độ dài và cấu trúc JSON (nếu có).
  3. Sinh bản xem trước Dry-Run (`.backup.json` + `.preview.csv`) và chỉ thực thi `POST/PUT` sau khi người dùng xác nhận, kèm xác minh sau ghi (`GET`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đọc Metafields của sản phẩm | `com.read_products` | `GET https://apis.haravan.com/com/products/{product_id}/metafields.json` |
| Đọc Metafields của biến thể | `com.read_products` | `GET https://apis.haravan.com/com/variants/{variant_id}/metafields.json` |
| Tạo/Cập nhật Metafield sản phẩm | `com.write_products` | `POST https://apis.haravan.com/com/products/{product_id}/metafields.json` |

**JSON Request Payload (`POST https://apis.haravan.com/com/products/1051120045/metafields.json`):**
```json
{
  "metafield": {
    "namespace": "specs",
    "key": "chat_lieu",
    "value": "100% Cotton 2 chiều 250GSM",
    "value_type": "string",
    "description": "Chất liệu vải hiển thị ở tab Thông số sản phẩm"
  }
}
```

**Sample Response (`201 Created`):**
```json
{
  "metafield": {
    "id": 778123409,
    "namespace": "specs",
    "key": "chat_lieu",
    "value": "100% Cotton 2 chiều 250GSM",
    "value_type": "string",
    "owner_id": 1051120045,
    "owner_resource": "product",
    "updated_at": "2026-11-25T07:00:12Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `owner_resource` | enum (`product`, `variant`) | Có | `product` | Chọn cấp độ gắn metafield. |
| `namespace` | string | Có | — | Chỉ gồm `a-z0-9_`, độ dài `2..20` ký tự (vd `specs`, `warranty`, `seo_extra`). |
| `updates_file` | string (path) | Có | — | Tệp CSV/JSON gồm cột `owner_id, key, value, value_type`. |
| `overwrite_existing` | boolean | Không | `false` | `false`: chỉ tạo mới nếu key chưa có; `true`: cho phép ghi đè giá trị cũ (có backup). |
| `max_records` | integer | Không | `100` | Giới hạn tối đa 100 bản ghi mỗi batch để tránh cạn leaky bucket. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Quy trình kiểm chuẩn & Diff Metafield (5 bước)
1. **Validate Schema đầu vào:** Kiểm tra `namespace` và `key` tuân thủ `^[a-z0-9_]{2,30}$`; `value_type` thuộc `{"string", "integer", "json_string"}`. Nếu `value_type == "integer"`, ép kiểm `int(value)`; nếu `json_string`, kiểm tra `json.loads(value)` hợp lệ.
2. **Đọc trạng thái hiện tại (Pre-fetch Snapshot):** Với mỗi `owner_id` duy nhất (giới hạn `<= 100` calls, chạy `<= 2.0 req/s`), gọi `GET .../metafields.json` và lập bản đồ `(owner_id, namespace, key) -> {id, value, value_type}`.
3. **Phân loại thao tác (Idempotency Check):**
   - `NO_CHANGE`: `old_value == new_value` → bỏ qua, không gọi API ghi.
   - `CREATE`: chưa tồn tại `(namespace, key)`.
   - `UPDATE`: đã tồn tại và `old_value != new_value` (chỉ đưa vào proposal nếu `overwrite_existing == true`, ngược lại gắn `SKIP_CONFLICT`).
4. **Xuất Dry-Run Preview & Backup:** Gọi `write_dry_run_artifact()` lưu toàn bộ giá trị `before` (kèm `metafield_id` cũ) vào `.backup.json` và bảng diff vào `.preview.csv`.
5. **Thực thi sau xác nhận (`partial_failure_policy: stop`):** Chạy tuần tự `<= 2 req/s`; gặp lỗi HTTP `422/5xx` dừng ngay và báo cáo checkpoint.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Cập nhật Metafields (Dry-Run Preview)
- **Namespace:** `specs` | **Tổng dòng đầu vào:** `30` | **Tạo mới:** `18` | **Ghi đè:** `7` | **Không đổi (bỏ qua):** `5`

| Owner ID | Key | Giá trị cũ (Before) | Giá trị mới (After) | Thao tác |
| --- | --- | --- | --- | --- |
| `1051120045` | `chat_lieu` | `(chưa có)` | `100% Cotton 2 chiều 250GSM` | `CREATE` |
| `1051120045` | `xuat_xu` | `VN` | `Việt Nam` | `UPDATE` |
| `1051120048` | `bao_hanh_thang` | `12` | `12` | `NO_CHANGE` |

### JSON Output Schema
```json
{
  "skill": "catalog-metafield-bulk-update",
  "dry_run": true,
  "namespace": "specs",
  "summary": { "create": 18, "update": 7, "no_change": 5, "errors": 0 },
  "artifacts": {
    "backup_json": "artifacts/hrv-catalog-metafield-bulk-update-20261125T070500Z.backup.json",
    "preview_csv": "artifacts/hrv-catalog-metafield-bulk-update-20261125T070500Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Cấm đụng vào namespace hệ thống:** Chặn tuyệt đối các namespace dành riêng cho app/hệ thống (như `global`, `haravan`, `app_*`, `egany_*`) trừ khi người dùng chỉ định rõ để tránh hỏng tính năng của app bên thứ ba.
- **Post-Write Verification:** Sau khi apply, gọi lại `GET` trên mẫu kiểm tra (tối thiểu 100% bản ghi đã ghi nếu `<= 20`, hoặc 20% ngẫu nhiên + bản ghi đầu/cuối nếu `> 20`) để xác nhận `value` khớp.
- **Rollback:**
  - Bản ghi `UPDATE`: gửi lại `POST/PUT` với giá trị `before` từ `.backup.json`.
  - Bản ghi `CREATE`: gọi `DELETE /com/products/{product_id}/metafields/{created_id}.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | `value_type` không khớp kiểu dữ liệu thực tế hoặc `key` chứa ký tự tiếng Việt có dấu | Chuẩn hóa `key` sang ASCII `snake_case`, kiểm tra kiểu dữ liệu trước khi gửi. |
| `429 Too Many Requests` | Quét metafield tốn 1 request cho mỗi sản phẩm (N+1) | Bắt buộc giữ `batch_size <= 100` và tốc độ `<= 2.0 req/s`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Khác biệt `POST` upsert vs `PUT` theo `metafield_id`:** Trên Haravan, gọi `POST` với `(namespace, key)` đã tồn tại có thể tự cập nhật (upsert) hoặc trả lỗi tùy phiên bản; an toàn nhất là kiểm tra trước từ bước Pre-fetch và ghi rõ `metafield_id` khi cập nhật.
2. **Theme Liquid đọc sai tên `namespace` hoặc `key`:** Một ký tự viết hoa khác biệt (`Chat_Lieu` vs `chat_lieu`) sẽ khiến `{{ product.metafields.specs.chat_lieu }}` trên Liquid trả về rỗng. Luôn ép lowercase toàn bộ `namespace` và `key`.
3. **Giá trị rỗng `""` không được chấp nhận:** Haravan thường trả `422` khi truyền `"value": ""`. Nếu muốn xóa giá trị metafield, phải đề xuất thao tác `DELETE` rõ ràng thay vì gán chuỗi rỗng.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-data-completeness-audit`.
- **Chạy tiếp theo:** `haravan-cli-theme-ops` (nếu cần cập nhật code Liquid hiển thị metafields mới trên Staging Theme).
