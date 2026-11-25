---
name: pricing-compare-at-cleanup
description: "Phát hiện và đề xuất dọn dẹp giá so sánh (compare_at_price) bất hợp lệ (nhỏ hơn hoặc bằng giá bán, giảm ảo > 80%) sau đợt sale."
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
    - "PUT https://apis.haravan.com/com/variants/{variant_id}.json"
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
# Pricing Compare-At Cleanup — Dọn Dẹp Giá So Sánh Bất Hợp Lệ Sau Đợt Sale

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` phát hiện và đề xuất dọn dẹp các trường hợp `compare_at_price` (giá so sánh / giá gạch ngang) bất hợp lệ trên Haravan (`/com/products.json` → `PUT /com/variants/{variant_id}.json`). Sau mỗi chiến dịch Mega Sale (11.11, 12.12, Tết) hoặc khi tăng giá bán mới, rất nhiều sản phẩm bị rơi vào 3 lỗi kinh điển: (1) `compare_at_price <= price` (giá gạch ngang nhỏ hơn hoặc bằng giá bán gây lỗi giao diện `-0%` hoặc `+15%`), (2) Giảm giá ảo quá `80%` dễ bị Google Merchant Center / Facebook Catalog khóa tài khoản vì vi phạm chính sách giá, và (3) Quên xóa `compare_at_price` sau khi kết thúc sale.

- **Khi nào sử dụng:** Ngay sau khi kết thúc đợt Sale lớn, sau khi tăng giá bán hàng loạt, hoặc khi Google Merchant Center báo lỗi *"Mismatched value (price/sale_price)"*.
- **Khi nào KHÔNG sử dụng:** Khi muốn thay đổi giá bán thực tế `price` (dùng `pricing-bulk-adjustment-proposal`; skill này **tuyệt đối không đụng vào `price`**, chỉ làm sạch `compare_at_price`).
- **Definition of Done (DoD):**
  1. Quét toàn bộ biến thể sản phẩm, phân loại chính xác 3 nhóm lỗi `compare_at_price`: `LESS_OR_EQUAL_PRICE`, `SUSPICIOUS_DISCOUNT_GT_80PCT`, `MICRO_DISCOUNT_LT_3PCT`.
  2. Lập bản Dry-Run Proposal đưa `compare_at_price` lỗi về `0` (hoặc `null` theo chuẩn Haravan) trong giới hạn `<= 100` variants/batch, giữ nguyên 100% `price`.
  3. Xuất `.backup.json` & `.preview.csv`, chờ xác nhận, thực thi `PUT` và xác minh lại bằng `GET`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Quét sản phẩm & giá các biến thể | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50&fields=id,title,variants` |
| Xóa/đặt lại `compare_at_price` về `0` | `com.write_products` | `PUT https://apis.haravan.com/com/variants/{variant_id}.json` |

**JSON Request Payload (`PUT https://apis.haravan.com/com/variants/1129045588.json`):**
```json
{
  "variant": {
    "id": 1129045588,
    "compare_at_price": 0
  }
}
```

**Sample Response (`200 OK`):**
```json
{
  "variant": {
    "id": 1129045588,
    "sku": "QJG-DEN-XL",
    "price": 450000.0,
    "compare_at_price": 0.0,
    "updated_at": "2026-11-25T07:35:00Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `max_discount_pct` | float | Không | `80.0` | Ngưỡng `%` giảm giá tối đa hợp lệ; cao hơn bị gắn cờ giảm ảo / sai số 0. |
| `min_meaningful_discount_pct` | float | Không | `3.0` | Giảm dưới `3%` (vd `399k` vs `400k`) chỉ làm rối giao diện — gắn cảnh báo nhẹ. |
| `auto_fix_suspicious_gt_80` | boolean | Không | `false` | Mặc định chỉ báo cáo nhóm `> 80%` để người dùng xác nhận (tránh xóa nhầm hàng xả kho thật 85%). |
| `max_records` | integer | Không | `100` | Số variants cập nhật tối đa trong 1 batch proposal. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức kiểm toán `compare_at_price`
Với mỗi biến thể có `compare_at_price > 0` và `price > 0`:
```text
discount_pct = ((compare_at_price - price) / compare_at_price) * 100
```
Phân loại xử lý:
1. **Nhóm 1 — Bất hợp lệ toán học (`INVALID_LE_PRICE`, tự động đưa vào proposal dọn về `0`):** `compare_at_price <= price` (`discount_pct <= 0%`).
2. **Nhóm 2 — Giảm ảo / nghi sai số 0 (`SUSPICIOUS_GT_80PCT`, cần review thủ công):** `discount_pct > max_discount_pct` (ví dụ `compare_at_price = 3.500.000₫`, `price = 350.000₫` do gõ dư 1 số 0).
3. **Nhóm 3 — Giảm không đáng kể (`MICRO_DISCOUNT`, tùy chọn dọn):** `0 < discount_pct < min_meaningful_discount_pct`.

**Cam kết bất biến (Invariant):** Payload `PUT` **chỉ chứa** `id` và `compare_at_price: 0`, không truyền trường `price` để đảm bảo tuyệt đối không làm biến động giá bán đang chạy.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Dọn dẹp `compare_at_price` (Dry-Run Preview)
- **Tổng variants đã quét:** `712` | **Phát hiện lỗi:** `23` (`18` giá so sánh `<=` giá bán, `3` giảm ảo `> 80%`, `2` giảm `< 3%`)
- **Đề xuất tự động đưa về `0`:** `18` variants (nhóm `INVALID_LE_PRICE`)

| Variant ID | SKU | Giá bán (`price`) | `compare_at_price` cũ | % Giảm hiện tại | Phân loại | Đề xuất |
| --- | --- | --- | --- | --- | --- | --- |
| `1129045588` | `QJG-DEN-XL` | 450.000 | 420.000 | `-7.1%` (Lỗi) | `INVALID_LE_PRICE` | Đặt về `0` |
| `1129045601` | `ASM-TRG-M` | 350.000 | 350.000 | `0.0%` (Lỗi) | `INVALID_LE_PRICE` | Đặt về `0` |
| `1129045712` | `ATN-XAM-S` | 290.000 | 2.900.000 | `90.0%` (Nghi dư số 0) | `SUSPICIOUS_GT_80PCT` | Chờ review |

### JSON Output Schema
```json
{
  "skill": "pricing-compare-at-cleanup",
  "dry_run": true,
  "summary": { "invalid_le_price": 18, "suspicious_gt_80pct": 3, "micro_discount": 2, "proposed_cleanup_count": 18 },
  "artifacts": {
    "backup_json": "artifacts/hrv-pricing-compare-at-cleanup-20261125T073500Z.backup.json",
    "preview_csv": "artifacts/hrv-pricing-compare-at-cleanup-20261125T073500Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run & Xác nhận:** Luôn sinh `.backup.json` lưu toàn bộ giá trị `compare_at_price` cũ trước khi đặt về `0`.
- **Post-Write Verification:** Gọi `GET /com/variants/{id}.json` xác nhận `compare_at_price == 0` và `price` hoàn toàn không đổi.
- **Rollback:** Chạy ngược `PUT /com/variants/{id}.json` với giá trị `compare_at_price` lưu trong `.backup.json`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | Truyền `compare_at_price: null` trên một số phiên bản API yêu cầu số `0` | Luôn chuẩn hóa gửi số `0` (`0.0`) thay vì `null` trên Haravan Commerce API. |
| `429 Too Many Requests` | Dọn dẹp gần 100 variants liên tiếp | Chạy tuần tự `<= 2.0 req/s` qua `HaravanClient`. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Haravan Liquid hiển thị badge `-0%` hoặc `Tiết kiệm -30.000₫`:** Khi `compare_at_price <= price`, nhiều theme Việt Nam không kiểm tra điều kiện `if compare_at_price > price` nên render badge lỗi ngay trên trang chủ — dọn sạch nhóm này khắc phục tức thì lỗi UI.
2. **Sản phẩm có 5 size nhưng chỉ 1 size bị sót `compare_at_price`:** Giao diện danh mục vẫn hiện nhãn "SALE" cho cả sản phẩm dù 4 size còn lại không giảm giá. Cần kiểm tra đồng bộ trên toàn bộ variants của cùng `product_id`.
3. **Hàng xả kho lẻ size giảm thật 85%:** Không tự động xóa nhóm `> 80%` nếu `tags` chứa `clearance` hoặc `xa-kho`; luôn tách riêng cho người dùng duyệt.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `catalog-data-completeness-audit`.
- **Chạy tiếp theo:** `pricing-bulk-adjustment-proposal` (nếu cần thiết lập lại bảng giá mới), `promo-audit-overlap`.
