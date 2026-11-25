---
name: pricing-bulk-adjustment-proposal
description: "Tính toán, kiểm tra biên an toàn và đề xuất điều chỉnh giá bán hàng loạt cho các variant trên Haravan với backup rollback đầy đủ."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 20-catalog-merchandising
layer: L2
wave: 2
mode: proposal
risk: high
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
  separate_turn: true
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
# Pricing Bulk Adjustment Proposal — Đề Xuất Điều Chỉnh Giá Bán Hàng Loạt An Toàn

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L2 / proposal` (**Risk: HIGH, Separate-Turn Confirmation bắt buộc**) tính toán, kiểm tra biên an toàn (guardrails) và lập bản đề xuất điều chỉnh giá bán (`price`) hoặc giá so sánh (`compare_at_price`) hàng loạt cho tối đa 100 biến thể trên Haravan (`/com/variants/{variant_id}.json`). Sai sót giá bán trên thương mại điện tử Việt Nam (như giảm nhầm 90% hoặc thiếu một số 0 VND) có thể gây lỗ hàng trăm triệu chỉ trong vài phút khi thợ săn sale phát hiện và lên đơn hàng loạt.

- **Khi nào sử dụng:** Tăng/giảm giá theo tỷ lệ phần trăm cho 1 danh mục/thương hiệu (vd điều chỉnh giá nhập nguyên liệu +5%, chạy đợt giảm giá -15%), hoặc áp bảng giá cố định từ CSV đã được Ban Giám đốc duyệt.
- **Khi nào KHÔNG sử dụng:** Khi chỉ cần dọn `compare_at_price` bị lỗi sau sale (dùng `pricing-compare-at-cleanup`), hoặc khi cần tạo mã giảm giá/chương trình khuyến mãi tạm thời (nên dùng Haravan Promotions thay vì sửa giá gốc).
- **Definition of Done (DoD):**
  1. Áp dụng đầy đủ **5 lớp khóa an toàn giá**: biên độ thay đổi `|pct| <= 30%`, làm tròn chuẩn VND (bội số `1.000₫`), sàn giá tối thiểu (`min_price_vnd`), bảo vệ biên lợi nhuận (`price >= cost_price` nếu có dữ liệu giá vốn), và giới hạn `<= 100` variants/batch.
  2. Xuất đầy đủ `.backup.json` & `.preview.csv` bằng `scripts/dry_run_report.py` và trình bày bảng Before → After chi tiết.
  3. **Dừng lại chờ xác nhận tường minh ở lượt hội thoại tiếp theo (`separate_turn: true`)** trước khi gọi bất kỳ lệnh `PUT` nào.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thao tác | Scope | Endpoint Haravan |
| --- | --- | --- |
| Đọc giá & biến thể hiện tại | `com.read_products` | `GET https://apis.haravan.com/com/products.json?limit=50` |
| Cập nhật giá từng biến thể (sau duyệt L2/L3) | `com.write_products` | `PUT https://apis.haravan.com/com/variants/{variant_id}.json` |

**Chạy Dry-Run trực tiếp bằng CLI của repo (`scripts/hrv_ops.py`):**
```bash
# Tạo bản preview tăng/giảm giá (mặc định dry-run, tự sinh backup JSON & preview CSV)
python3 scripts/hrv_ops.py price-dry-run --pct -10 --out artifacts
# Test offline với dữ liệu mẫu:
python3 scripts/hrv_ops.py --demo price-dry-run --pct -10 --out artifacts
```

**JSON Request Payload (`PUT https://apis.haravan.com/com/variants/1129045512.json`):**
```json
{
  "variant": {
    "id": 1129045512,
    "price": 299000,
    "compare_at_price": 329000
  }
}
```

**Sample Response (`200 OK`):**
```json
{
  "variant": {
    "id": 1129045512,
    "product_id": 1058923401,
    "sku": "ATN-250-DEN-M",
    "price": 299000.0,
    "compare_at_price": 329000.0,
    "updated_at": "2026-11-25T07:25:10Z"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `adjustment_mode` | enum (`percent`, `fixed_csv`) | Có | `percent` | Chế độ tăng/giảm theo `%` hoặc áp giá từ file CSV. |
| `pct` | float | Có (nếu `percent`) | — | Biên độ khóa cứng trong `[-30.0, +30.0]`; vượt ngưỡng phải chia phê duyệt riêng. |
| `rounding_unit_vnd` | integer | Không | `1000` | Làm tròn giá VND (vd `1000` → `296.000₫`, hoặc psychological pricing `9000` → `299.000₫`). |
| `filter_scope` | object | Không | `{}` | Lọc theo `collection_id`, `vendor`, `product_type`, hoặc danh sách `sku`. |
| `set_old_price_as_compare_at` | boolean | Không | `true` (khi giảm giá) | Khi giảm giá, tự động lưu giá cũ vào `compare_at_price` để hiển thị mức giảm. |
| `min_price_vnd` | integer | Không | `10000` | Sàn giá tối thiểu tuyệt đối, chặn lỗi chia nhầm về 0đ hoặc vài trăm đồng. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Công thức tính giá mới & Kiểm tra biên an toàn (Price Guardrails)
```text
raw_new_price = old_price * (1 + pct / 100.0)
new_price = round(raw_new_price / rounding_unit_vnd) * rounding_unit_vnd
```
Kiểm tra 5 điều kiện chặn cứng (Hard Guardrails — vi phạm 1 điều kiện sẽ gắn cờ `BLOCKED`):
1. `abs(pct) <= 30.0` (chặn giảm giá sốc bất thường).
2. `new_price >= min_price_vnd` (chặn giá gần 0đ).
3. Nếu có giá vốn `cost_price`: kiểm tra `new_price >= cost_price * 1.05` (cảnh báo bán dưới vốn).
4. Nếu `set_old_price_as_compare_at == true` và `pct < 0`: gán `new_compare_at = max(old_price, old_compare_at_price)` để đảm bảo `new_compare_at > new_price`.
5. Nếu `pct > 0` và `old_compare_at_price <= new_price`: tự động đưa `new_compare_at = 0` (tránh lỗi giá gốc nhỏ hơn giá bán).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Bản xem trước Điều chỉnh Giá Hàng loạt (DRY-RUN — Chờ Xác Nhận Ở Lượt Tiếp Theo)
- **Quy tắc áp dụng:** Giảm `-10%`, làm tròn `1.000₫`, phạm vi: `vendor = "Saigon Streetwear"`
- **Tổng biến thể ảnh hưởng:** `36` variants | **Bị chặn bởi guardrail:** `1` variant (`price < min_price_vnd`)
- **Tệp backup rollback:** `artifacts/hrv-pricing-bulk-adjustment-proposal-20261125T072500Z.backup.json`

| Variant ID | SKU | Giá cũ (VND) | Giá mới (VND) | Compare-at mới | Chênh lệch | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| `1129045512` | `ATN-250-DEN-M` | 329.000 | 296.000 | 329.000 | `-33.000 (-10.0%)` | READY |
| `1129045513` | `ATN-250-DEN-L` | 329.000 | 296.000 | 329.000 | `-33.000 (-10.0%)` | READY |
| `1129045900` | `TUI-GIAY-S` | 10.000 | 9.000 | 10.000 | `-1.000` | BLOCKED (`< 10.000₫`) |

> **Xác nhận bắt buộc (Separate-Turn):** Vui lòng kiểm tra file `.preview.csv` và trả lời xác nhận rõ ràng (ví dụ: *"Đồng ý áp dụng batch giá 35 variants trên staging/production"*) ở lượt tiếp theo để tôi thực thi.

### JSON Output Schema
```json
{
  "skill": "pricing-bulk-adjustment-proposal",
  "dry_run": true,
  "separate_turn_confirmation_required": true,
  "guardrails": { "max_pct_delta": 30, "min_price_vnd": 10000, "rounding_unit_vnd": 1000 },
  "summary": { "ready": 35, "blocked": 1, "unchanged": 0 },
  "artifacts": {
    "backup_json": "artifacts/hrv-pricing-bulk-adjustment-proposal-20261125T072500Z.backup.json",
    "preview_csv": "artifacts/hrv-pricing-bulk-adjustment-proposal-20261125T072500Z.preview.csv"
  }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Separate-Turn Confirmation (`separate_turn: true`, `risk: high`):** Tuyệt đối không bao giờ vừa sinh preview vừa gọi `PUT` trong cùng 1 lượt, kể cả khi người dùng giục "sửa luôn đi".
- **Partial Failure Policy (`stop`):** Gặp lỗi đầu tiên khi `PUT` lập tức dừng batch, xuất danh sách `applied_variant_ids` và `pending_variant_ids`.
- **Post-Write Verification:** Gọi `GET /com/variants/{id}.json` (hoặc `/com/products/{id}.json`) đối chiếu giá mới khớp 100%.
- **Rollback tức thì:** Đọc `.backup.json` và chạy ngược `PUT /com/variants/{id}.json` khôi phục đúng `price` và `compare_at_price` cũ cho các bản ghi đã ghi.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `422 Unprocessable Entity` | Giá âm hoặc vượt định dạng số | Chặn từ bước validation trước khi gửi. |
| `429 Too Many Requests` | Cập nhật 100 variants liên tục | Giữ tốc độ `<= 2.0 req/s` và exponential backoff. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Đồng bộ giá tự động sang Shopee / TikTok Shop / Lazada:** Nếu cửa hàng bật tính năng tự động đồng bộ giá từ Haravan sang sàn TMĐT, sửa giá trên Haravan có thể làm thay đổi giá sàn và vi phạm điều kiện tham gia Flash Sale đang đăng ký trên sàn (bị sàn phạt hủy deal). Luôn nhắc kiểm tra cấu hình đồng bộ giá đa kênh trước khi duyệt.
2. **Xung đột với chương trình Khuyến mãi đang chạy (`promotions`):** Giảm giá trực tiếp trên `variant.price` sẽ cộng dồn (stack) với mã giảm giá / khuyến mãi giảm `%` trên đơn hàng → gây lỗ kép. Khuyến nghị chạy `promo-audit-overlap` trước khi giảm giá gốc.
3. **Làm tròn dẫn đến `new_price == old_price`:** Với sản phẩm giá nhỏ (vd `15.000₫` giảm `-2%` làm tròn `1.000₫` vẫn ra `15.000₫`), loại khỏi danh sách `PUT` để tiết kiệm API call.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `promo-audit-overlap` (kiểm tra khuyến mãi chồng chéo), `pricing-compare-at-cleanup`.
- **Chạy tiếp theo:** `pricing-compare-at-cleanup` (sau khi kết thúc đợt sale), `store-health-check`.
