---
name: catalog-collection-reorg-proposal
description: "Kiểm toán sản phẩm mồ côi (không thuộc nhóm nào) và đề xuất sắp xếp lại sản phẩm vào Custom Collections (/com/collects.json)."
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
    - "GET https://apis.haravan.com/com/custom_collections.json"
    - "GET https://apis.haravan.com/com/smart_collections.json"
    - "GET https://apis.haravan.com/com/collects.json"
    - "POST https://apis.haravan.com/com/collects.json"
    - "DELETE https://apis.haravan.com/com/collects/{collect_id}.json"
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
# Catalog Collection Reorg Proposal — Xử Lý Sản Phẩm Mồ Côi & Sắp Xếp Danh Mục

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` kiểm toán toàn bộ mối liên kết giữa Sản phẩm và Nhóm sản phẩm (`custom_collections`, `smart_collections`, `collects`) trên Haravan để phát hiện **Sản phẩm mồ côi (Orphan Products)** — đang ở trạng thái hiển thị nhưng không nằm trong bất kỳ danh mục nào khiến khách hàng không thể tìm thấy trên menu, và đề xuất gắn/gỡ sản phẩm vào Custom Collections một cách có hệ thống.

- **Khi nào sử dụng:** Sau khi import hàng loạt sản phẩm mới, trước chiến dịch lớn (Sale 11.11, Tết, BST Thu-Đông) cần gom hàng vào nhóm khuyến mãi, hoặc khi tái cấu trúc cây menu danh mục website.
- **Khi nào KHÔNG sử dụng:** Khi muốn chỉnh điều kiện tự động của Smart Collection (hãy dùng tag sản phẩm qua `catalog-product-lifecycle-proposal` thay vì gọi `/com/collects.json` vì `collects` chỉ áp dụng cho Custom Collection).
- **Definition of Done (DoD):**
  1. Quét đủ `products`, `custom_collections`, `smart_collections`, và `collects` để xác định chính xác tập sản phẩm mồ côi và sản phẩm nằm sai nhóm.
  2. Lập bảng đề xuất `ADD` (`POST /com/collects.json`) và `REMOVE` (`DELETE /com/collects/{collect_id}.json`) dựa trên rule từ `product_type`, `tags`, `vendor`, giới hạn `<= 100` thao tác/lô.
  3. Xuất bản xem trước Dry-Run (`.backup.json` + `.preview.csv`) và chỉ thực thi sau khi có xác nhận của người dùng.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đọc nhóm thủ công & nhóm tự động | `com.read_products` | `GET /com/custom_collections.json`, `GET /com/smart_collections.json` |
| Đọc danh sách liên kết hiện có | `com.read_products` | `GET https://apis.haravan.com/com/collects.json?limit=50` |
| Gắn sản phẩm vào Custom Collection | `com.write_products` | `POST https://apis.haravan.com/com/collects.json` |
| Gỡ sản phẩm khỏi Custom Collection | `com.write_products` | `DELETE https://apis.haravan.com/com/collects/{collect_id}.json` |

**JSON Request Payload (`POST https://apis.haravan.com/com/collects.json`):**
```json
{
  "collect": {
    "product_id": 1058923401,
    "collection_id": 1003421908
  }
}
```

**Sample Response (`201 Created`):**
```json
{
  "collect": {
    "id": 9881234501,
    "collection_id": 1003421908,
    "product_id": 1058923401,
    "position": 1,
    "created_at": "2026-11-25T06:40:11Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `mapping_rules` | array[object] | Không | Suy luận từ `product_type` & `tags` | Danh sách luật ánh xạ (vd `{"if_product_type": "Áo thun", "target_collection_id": 1003421908}`). |
| `include_unpublished` | boolean | Không | `false` | Chỉ kiểm tra sản phẩm đang hiển thị (`published_at != null`) để tránh rác. |
| `allow_remove` | boolean | Không | `false` | Chỉ đề xuất `DELETE /collects/{id}` khi người dùng yêu cầu rõ việc gỡ khỏi nhóm cũ. |
| `max_records` | integer | Không | `100` | Số thao tác `POST/DELETE` tối đa trong 1 batch proposal. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Thuật toán phát hiện Sản phẩm Mồ côi & Lập Proposal
1. **Tải bản đồ liên kết:**
   - Lấy toàn bộ `custom_collections` (chỉ nhóm có thể thao tác bằng `collects`) và `smart_collections` (để biết sản phẩm đã thuộc nhóm tự động hay chưa).
   - Lấy toàn bộ `collects` → tạo tập `assigned_custom[product_id] = set(collection_ids)` và ánh xạ ngược `collect_id_map[(product_id, collection_id)] = collect_id`.
2. **Đánh giá độ phủ Smart Collection (ước lượng):** Với mỗi `smart_collection`, kiểm tra sơ bộ `products_count` hoặc gọi `GET /com/products.json?collection_id={id}&fields=id` để tránh đánh nhầm sản phẩm đã nằm trong Smart Collection là "mồ côi".
3. **Xác định Orphan Products:** `orphan = {p | p.published_at != null AND p.id not in assigned_custom AND p.id not in assigned_smart}`.
4. **Áp dụng luật phân nhóm (Mapping Engine):** So khớp `product_type`, `tags`, `vendor` theo thứ tự ưu tiên; loại bỏ các cặp `(product_id, collection_id)` đã tồn tại (Idempotency).
5. **Sinh Dry-Run Proposal:** Xuất bảng diff `ADD / REMOVE` qua `dry_run_report.py` và dừng chờ xác nhận.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Sắp xếp Danh mục (Dry-Run Preview)
- **Tổng sản phẩm đang bán:** `215` | **Sản phẩm mồ côi phát hiện:** `18` | **Thao tác đề xuất:** `22` (`18 ADD`, `4 REMOVE`)

| Hành động | Product ID | Tên sản phẩm | Custom Collection Đích | Lý do / Rule khớp |
| --- | --- | --- | --- | --- |
| `ADD` | `1058923401` | Áo Thun Cotton 250GSM - Đen | `Áo Thun Nam` (`1003421908`) | `product_type == "Áo thun"` (Orphan) |
| `ADD` | `1058923405` | Quần Short Kaki Basic | `Quần Nam` (`1003421912`) | `tags` chứa `quan-short` (Orphan) |
| `REMOVE` | `1041120088` | Áo Khoác Phao Đông 2024 | `Hàng Mới Về` (`1003421901`) | `created_at > 180 ngày` (`collect_id: 9771122`) |

### JSON Output Schema
```json
{
  "skill": "catalog-collection-reorg-proposal",
  "dry_run": true,
  "summary": { "active_products": 215, "orphan_products": 18, "proposed_adds": 18, "proposed_removes": 4 },
  "artifacts": {
    "backup_json": "artifacts/hrv-catalog-collection-reorg-proposal-20261125T064500Z.backup.json",
    "preview_csv": "artifacts/hrv-catalog-collection-reorg-proposal-20261125T064500Z.preview.csv"
  },
  "operations": [
    { "op": "ADD", "product_id": 1058923401, "collection_id": 1003421908, "reason": "orphan_match_product_type" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run & Backup:** Lưu toàn bộ trạng thái `collects` gốc (bao gồm `collect_id`, `product_id`, `collection_id`) vào `.backup.json` trước khi chạy.
- **Post-Write Verification:** Gọi `GET /com/collects.json?collection_id={id}` sau khi ghi để xác nhận số lượng sản phẩm trong nhóm đã tăng/giảm đúng như proposal.
- **Rollback:**
  - Với thao tác `ADD`: gọi `DELETE /com/collects/{created_collect_id}.json`.
  - Với thao tác `REMOVE`: gọi lại `POST /com/collects.json` với cặp `(product_id, collection_id)` lưu trong `.backup.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | Cố gắn sản phẩm vào **Smart Collection** bằng `/com/collects.json`, hoặc cặp `(product_id, collection_id)` đã tồn tại | Lọc chặt chỉ cho phép `collection_id` thuộc `custom_collections`; kiểm tra `collect_id_map` trước khi POST. |
| `404 Not Found` | `collect_id` đã bị nhân viên khác gỡ trước đó | Ghi nhận `already_removed`, tiếp tục kiểm tra đối chiếu thay vì làm hỏng báo cáo. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Nhóm mặc định `Tất cả sản phẩm` (`handle: all` / `onsale`):** Một số nhóm hệ thống không xuất hiện trong `custom_collections.json`; sản phẩm chỉ nằm trong nhóm `all` vẫn bị coi là **mồ côi** về mặt điều hướng danh mục.
2. **Xung đột thứ tự hiển thị (`sort_order: manual`):** Khi thêm hàng loạt vào Custom Collection có sắp xếp thủ công, sản phẩm mới có thể bị đẩy xuống cuối trang 5. Cần thông báo người dùng kiểm tra lại vị trí ưu tiên cho BST mới.
3. **Smart Collection bị rỗng do sai chính tả Tag:** Nếu phát hiện Smart Collection có `products_count == 0`, cảnh báo ngay trong báo cáo vì có thể shop đổi quy ước đặt tag nhưng quên cập nhật luật Smart Collection.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-bulk-import-proposal`, `catalog-data-completeness-audit`.
- **Chạy tiếp theo:** `catalog-product-lifecycle-proposal` (gắn tag cho Smart Collection), `seo-collection-audit`.
