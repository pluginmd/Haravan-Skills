---
name: catalog-bulk-import-proposal
description: "Chuẩn hóa dữ liệu đầu vào (CSV/JSON), kiểm tra trùng SKU và tạo proposal nhập sản phẩm mới lên Haravan (dry-run trước)."
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
    - "POST https://apis.haravan.com/com/products.json"
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
# Catalog Bulk Import Proposal — Chuẩn Hóa & Nhập Hàng Loạt Sản Phẩm Lên Haravan

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` chuẩn hóa tệp sản phẩm đầu vào (CSV/Excel/JSON từ nhà cung cấp, ERP hoặc xuất từ Shopee/Sapo), kiểm tra trùng lặp SKU/Barcode/Handle với danh mục hiện có trên Haravan, và lập bản **Dry-Run Proposal** trước khi tạo mới qua `POST /com/products.json`. Tại Việt Nam, import thô không qua bước kiểm chuẩn thường dẫn đến tạo trùng sản phẩm, giá nhập sai đơn vị nghìn đồng (`350` thay vì `350000`), thiếu trọng lượng (`grams`) làm hỏng tính cước GHN/GHTK, hoặc vượt giới hạn 100 variants/sản phẩm.

- **Khi nào sử dụng:** Khi nhập bộ sưu tập mới (20–100 sản phẩm), đưa danh mục từ nhà cung cấp lên Haravan, hoặc migrate sản phẩm mới theo từng lô an toàn.
- **Khi nào KHÔNG sử dụng:** Khi cập nhật giá hoặc thông số cho sản phẩm đã tồn tại (dùng `pricing-bulk-adjustment-proposal` hoặc `catalog-metafield-bulk-update`), hoặc khi import > 100 sản phẩm trong 1 lần (phải chia thành nhiều batch `<= 100`).
- **Definition of Done (DoD):**
  1. Đối chiếu toàn bộ SKU/Barcode/Handle đầu vào với danh mục Haravan hiện tại (`GET /com/products.json`), tách rõ: `VALID_NEW`, `DUPLICATE_SKIP`, `INVALID_SCHEMA`.
  2. Sinh bản xem trước `dry_run` + tệp `.backup.json` & `.preview.csv` bằng `scripts/dry_run_report.py` với đầy đủ payload chuẩn bị tạo.
  3. Chỉ thực thi `POST /com/products.json` (mặc định tạo ở trạng thái ẩn `published: false` nếu chưa duyệt ảnh) sau khi người dùng xác nhận tường minh, kèm xác minh sau ghi (`GET`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Quét danh mục hiện có (chống trùng SKU/Handle) | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,handle,title,variants` |
| Tạo sản phẩm mới (sau khi duyệt Dry-Run) | `com.write_products` | `POST https://apis.haravan.com/com/products.json` |

**JSON Request Payload chuẩn (`POST https://apis.haravan.com/com/products.json`):**
```json
{
  "product": {
    "title": "Áo Thun Cotton 250GSM Local Brand - Đen",
    "body_html": "<p>Chất liệu 100% Cotton 2 chiều 250GSM thoáng mát, form boxy chuẩn streetwear.</p>",
    "vendor": "Saigon Streetwear",
    "product_type": "Áo thun",
    "tags": "new-arrival, cotton-250gsm, boxy",
    "published": false,
    "options": [{ "name": "Kích thước" }, { "name": "Màu sắc" }],
    "variants": [
      {
        "option1": "M",
        "option2": "Đen",
        "sku": "ATN-250-DEN-M",
        "barcode": "8938501234011",
        "price": 329000,
        "compare_at_price": 399000,
        "grams": 320,
        "inventory_management": "haravan",
        "inventory_policy": "deny",
        "requires_shipping": true
      }
    ],
    "images": [
      { "src": "https://cdn.saigonstreetwear.vn/img/atn-250-den-1.jpg", "alt": "Áo thun cotton 250GSM màu đen mặt trước" }
    ]
  }
}
```

**Sample Response (`201 Created`):**
```json
{
  "product": {
    "id": 1058923401,
    "handle": "ao-thun-cotton-250gsm-local-brand-den",
    "title": "Áo Thun Cotton 250GSM Local Brand - Đen",
    "published_at": null,
    "variants": [{ "id": 1129045512, "sku": "ATN-250-DEN-M", "price": 329000.0 }]
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `source_file` | string (path) | Có | — | Đường dẫn tệp CSV/JSON chứa danh sách sản phẩm cần nhập. |
| `default_published` | boolean | Không | `false` | Khuyến nghị `false` (tạo dạng nháp/ẩn) để kiểm tra hiển thị trước khi bật bán. |
| `batch_size` | integer | Không | `100` | Không vượt quá `max_records: 100` mỗi phiên xác nhận. |
| `duplicate_policy` | enum (`skip`, `block`) | Không | `skip` | `skip`: bỏ qua dòng trùng SKU; `block`: dừng toàn bộ batch nếu có trùng. |
| `min_price_vnd` | integer | Không | `1000` | Chặn lỗi gõ thiếu 3 số 0 (vd `329` thay vì `329000` VND). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Quy trình chuẩn hóa & kiểm tra 6 bước (Validation Pipeline)
1. **Tải chỉ mục hiện tại:** Phân trang `GET /com/products.json?limit=50&fields=id,handle,variants` qua `HaravanClient` để lập 3 tập khóa tra cứu: `existing_skus`, `existing_barcodes`, `existing_handles`.
2. **Gom nhóm dòng CSV thành Product + Variants:** Gom các dòng có cùng `handle` hoặc `product_code` thành 1 object `product` chứa mảng `variants`. Kiểm tra giới hạn Haravan: `len(options) <= 3` và `len(variants) <= 100`.
3. **Chuẩn hóa dữ liệu Việt Nam:**
   - Giá bán `price` & `compare_at_price`: loại bỏ dấu `.`/`,`/`đ`, ép kiểu số nguyên VND; kiểm tra `price >= min_price_vnd` và `(compare_at_price == 0 or compare_at_price > price)`.
   - Trọng lượng `grams`: bắt buộc `> 0` với hàng vật lý (`requires_shipping: true`), mặc định cảnh báo nếu `grams == 0` (sẽ sai phí vận chuyển GHN/GHTK).
   - Ảnh `images[].src`: phải là URL `https://` hợp lệ, không chứa khoảng trắng chưa encode.
4. **Kiểm tra trùng lặp nội bộ & hệ thống:** Phát hiện SKU trùng trong chính file nguồn hoặc đã có trong `existing_skus`.
5. **Sinh Dry-Run Proposal:** Gọi `write_dry_run_artifact()` xuất `.backup.json` và `.preview.csv`; trình bày tóm tắt trước khi hỏi xác nhận.
6. **Thực thi có Idempotency (`partial_failure_policy: stop`):** Khi được duyệt, gọi `POST /com/products.json` tuần tự (`<= 2 req/s`), lưu ánh xạ `input_sku -> created_product_id` để có thể rollback hoặc tránh tạo trùng nếu chạy lại.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Nhập Sản Phẩm (Dry-Run Preview)
- **Tổng số sản phẩm đọc từ nguồn:** `45` (`132` variants)
- **Hợp lệ sẵn sàng tạo:** `41` sản phẩm (`120` variants) | **Bỏ qua (trùng SKU):** `2` | **Lỗi dữ liệu:** `2`

| Dòng/Mã | Tiêu đề sản phẩm | Số Variant | Giá (VND) | Trạng thái kiểm tra | Ghi chú |
| --- | --- | --- | --- | --- | --- |
| `SP-01` | Áo Thun Cotton 250GSM - Đen | 4 | 329.000 | READY (`published: false`) | Hợp lệ |
| `SP-14` | Quần Cargo Túi Hộp - Rêu | 3 | 490.000 | SKIP | SKU `QCG-REU-M` đã tồn tại (`product_id: 1044210`) |
| `SP-29` | Mũ Lưỡi Trai Basic | 1 | `150` | ERROR | Giá < 1.000 VND (nghi thiếu 3 số 0) |

### JSON Output Schema
```json
{
  "skill": "catalog-bulk-import-proposal",
  "dry_run": true,
  "summary": { "total_products": 45, "ready": 41, "skipped_duplicate": 2, "invalid": 2 },
  "artifacts": {
    "backup_json": "artifacts/hrv-catalog-bulk-import-proposal-20261125T063000Z.backup.json",
    "preview_csv": "artifacts/hrv-catalog-bulk-import-proposal-20261125T063000Z.preview.csv"
  },
  "errors": [{ "row": 29, "field": "price", "value": 150, "reason": "below_min_price_vnd" }]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run bắt buộc (`dry_run: true`, `confirmation_required: true`):** Luôn sinh `.backup.json` & `.preview.csv` trước; chỉ gọi `POST` sau khi người dùng xác nhận rõ ràng.
- **Post-Write Verification:** Sau khi tạo xong lô sản phẩm, gọi `GET /com/products.json?since_id=<first_id_minus_1>` xác nhận đủ số lượng `product_id` và SKU khớp 100%.
- **Rollback cụ thể:** Sử dụng danh sách `created_product_ids` đã ghi trong log kết quả để gọi `DELETE /com/products/{product_id}.json` (chỉ rollback được khi sản phẩm chưa phát sinh đơn hàng; nếu đã có đơn thì ẩn `published: false`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | Vượt 100 variants, thiếu `title`, trùng tổ hợp `option1/option2/option3`, hoặc URL ảnh tải thất bại | Dừng batch ngay (`partial_failure_policy: stop`), báo dòng lỗi và danh sách `created_product_ids` đã tạo thành công trước đó. |
| `429 Too Many Requests` | Đẩy sản phẩm kèm nhiều ảnh lớn khiến Haravan xử lý chậm | Giảm tốc độ xuống `1.0–1.5 req/s` và bật backoff. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Haravan không chặn trùng SKU ở tầng API:** Khác với nhiều hệ thống ERP, `POST /com/products.json` vẫn cho phép tạo sản phẩm mới có SKU trùng hệt SKU cũ mà không báo lỗi 422 — vì vậy bước quét `existing_skus` trước khi import là bắt buộc tuyệt đối.
2. **Tạo sản phẩm kèm tồn kho ban đầu trên cửa hàng đa kho:** Trường `inventory_quantity` trên `variant` khi `POST /com/products.json` chỉ ghi nhận vào kho mặc định (hoặc bị bỏ qua trên mô hình multi-location mới). Để phân bổ tồn theo nhiều kho, phải chạy tiếp `inventory-adjustment-proposal` sau khi tạo sản phẩm.
3. **URL ảnh Google Drive / Facebook CDN hết hạn:** Haravan tải ảnh về CDN của họ khi tạo sản phẩm; nếu link ảnh là Google Drive chưa mở công khai hoặc link Facebook CDN hết hạn token, ảnh sẽ bị lỗi trắng. Phải xác nhận URL ảnh trả HTTP `200` và `Content-Type: image/*`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-duplicate-sku-barcode` (đảm bảo danh mục hiện tại sạch trùng lặp).
- **Chạy tiếp theo:** `catalog-collection-reorg-proposal` (gắn sản phẩm mới vào danh mục), `inventory-adjustment-proposal` (nạp tồn kho ban đầu theo từng kho), `catalog-image-alt-audit`.
