---
name: governance-rollback-executor
description: "Khôi phục dữ liệu Haravan (giá bán, tags, trạng thái sản phẩm, redirects, tồn kho bù trừ) từ file backup JSON đã tạo bởi dry_run_report.py."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 90-control-tower-governance
layer: L3
wave: 3
mode: write
risk: critical
haravan:
  api_surface: com
  scopes:
    - com.read_products
    - com.write_products
    - com.read_inventories
    - com.write_inventories
    - com.write_contents
  endpoints:
    - "PUT https://apis.haravan.com/com/variants/{variant_id}.json"
    - "PUT https://apis.haravan.com/com/products/{product_id}.json"
    - "POST https://apis.haravan.com/com/inventories/adjustments.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: true
  max_records: 25
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: true
---

# Haravan Safe Rollback Executor (Critical L3)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Cung cấp cơ chế đảo ngược dữ liệu chuẩn xác, có kiểm soát (Critical L3) khi một đợt cập nhật hàng loạt trên Haravan (giá biến thể, `compare_at_price`, tags/trạng thái sản phẩm, điều chỉnh tồn kho) gây sai lệch nghiệp vụ. Skill đọc trực tiếp tệp `*.backup.json` sinh bởi `scripts/dry_run_report.py` để khôi phục từng bản ghi về đúng trạng thái `before`.
- **Ngữ cảnh Haravan:** Trong tình huống khẩn cấp (ví dụ đẩy nhầm giá 25.000đ thay vì 250.000đ), việc tự viết script sửa vội rất dễ gây lỗi dây chuyền hoặc ghi đè lên các thay đổi hợp lệ mới phát sinh sau đó (ví dụ đơn hàng vừa trừ tồn kho). Do đó, Rollback Executor bắt buộc kiểm tra đối chiếu (`drift detection`), xác nhận ở **lượt hội thoại riêng (`separate_turn: true`)**, giới hạn `<= 25` bản ghi/đợt và dừng ngay ở lỗi đầu tiên (`partial_failure_policy: stop`).
- **Definition of Done (DoD):**
  1. Xác thực tệp `*.backup.json` hợp lệ (`rollback_supported == true`, khớp `store_domain` với `GET /com/shop.json`).
  2. Gọi `GET` lấy trạng thái hiện tại trên Haravan của từng `record_id`, phát hiện xung đột thay đổi (`drift`) và trình bày bảng Preview `Current → Restored Before` ở chế độ `dry_run: true`.
  3. Chờ người dùng xác nhận tường minh ở **lượt riêng**, thực thi khôi phục tối đa `25` bản ghi, lưu audit log và gọi lại `GET` xác minh 100% bản ghi đã khớp giá trị `before`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_products`, `com.write_products`, `com.read_inventories`, `com.write_inventories`, `com.write_contents` |
| **Endpoints** | `PUT /com/variants/{variant_id}.json`, `PUT /com/products/{product_id}.json`, `POST /com/inventories/adjustments.json` |

**Ví dụ cấu trúc tệp `*.backup.json` sinh bởi `scripts/dry_run_report.py`:**
```json
{
  "run_id": "hrv-catalog-price-update-20261125T060000Z",
  "store_domain": "shopdemo.myharavan.com",
  "environment": "production",
  "rollback_supported": true,
  "total_records": 2,
  "changes": [
    { "record_id": "variant_1120334455", "field": "price", "before": 299000, "after": 29900, "risk_note": "Wrong 0 digit" },
    { "record_id": "product_1054218901", "field": "tags", "before": "polo, new", "after": "polo, flash-sale", "risk_note": "Campaign tag" }
  ]
}
```

**Ví dụ gọi khôi phục giá biến thể qua `scripts/hrv_client.py` (chỉ đặt `dry_run=False` sau khi đã xác nhận ở lượt riêng):**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=False)
resp = client.request(
    "PUT", "com", "/variants/1120334455.json",
    payload={"variant": {"id": 1120334455, "price": 299000}}
)
# Với tồn kho: tính delta bù trừ thay vì ghi đè tuyệt đối nếu có đơn phát sinh
# POST /com/inventories/adjustments.json với {"inventory_adjustment": {"location_id": ..., "type": "adjust", "reason": "rollback", "line_items": [{"variant_id": ..., "qty": delta}]}}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `backup_json_path` | `string` | Bắt buộc | — | Đường dẫn tuyệt đối tới file `*.backup.json` hợp lệ. |
| `record_ids_subset` | `array[string]` | Không | `[]` | Lọc chỉ khôi phục một số `record_id` nhất định (rỗng = lấy từ đầu file, tối đa `25` bản ghi). |
| `allow_drift_override` | `boolean` | Không | `false` | Nếu `false`, tự động bỏ qua bản ghi có giá trị hiện tại khác giá trị `after` trong backup (tránh ghi đè sửa tay mới hơn). |
| `dry_run` | `boolean` | Bắt buộc | `true` | Bắt buộc chạy `true` ở lượt 1; chỉ cho phép `false` ở lượt 2 sau khi người dùng xác nhận rõ ràng. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Bước 1 — Xác thực Tệp Backup & Môi trường (Abort-on-Mismatch):**
   - Đọc `backup_json_path`; kiểm tra bắt buộc `rollback_supported === true` và mảng `changes` không rỗng.
   - Gọi `GET /com/shop.json` lấy `myharavan_domain` hiện tại. Nếu `backup.store_domain != current_store_domain` -> **DỪNG NGAY LẬP TỨC** (ngăn khôi phục nhầm sang cửa hàng khác).
2. **Bước 2 — Kiểm tra Độ lệch (Live Drift Detection):**
   - Với tối đa `25` bản ghi đầu tiên (hoặc theo `record_ids_subset`), gọi `GET` lấy giá trị `current` trên Haravan.
   - Phân loại trạng thái từng bản ghi:
     - `CLEAN_MATCH`: `current == after` → An toàn khôi phục về `before`.
     - `ALREADY_RESTORED`: `current == before` → Bỏ qua (idempotent).
     - `DRIFT_DETECTED`: `current != after` và `current != before` → Cảnh báo vàng, không ghi đè trừ khi `allow_drift_override == true`.
   - Với tồn kho (`inventory`): áp dụng công thức bù trừ delta $\Delta_{\text{rollback}} = \text{before} - \text{after}$ để không làm mất lượng trừ tồn của các đơn hàng phát sinh giữa hai thời điểm.
3. **Bước 3 — Preview & Khóa Xác nhận Lượt Riêng (`separate_turn: true`):**
   - Chụp một pre-rollback snapshot mới (phòng trường hợp cần đối chiếu sau sự cố).
   - Trình bày bảng `Current → Restored Before` và **DỪNG LẠI**, yêu cầu người dùng xác nhận bằng cụm từ tường minh kèm `run_id` ở lượt hội thoại tiếp theo.
4. **Bước 4 — Thực thi Tuần tự & Dừng Khi Lỗi (`partial_failure_policy: stop`):**
   - Chạy từng bản ghi một qua `HaravanClient(dry_run=False)`. Gặp bất kỳ lỗi HTTP 4xx/5xx (sau retry 429) -> **DỪNG NGAY**, xuất danh sách `succeeded_ids`, `failed_id`, `pending_ids`.
5. **Bước 5 — Xác minh Hậu Ghi (Post-Write Verification):**
   - Gọi lại `GET` trên toàn bộ `succeeded_ids` để xác nhận trạng thái thực tế trên Haravan đã khớp `before`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### [LƯỢT 1 — DRY-RUN] Bản Xem Trước Khôi Phục Dữ Liệu Haravan (Critical L3)
- **Nguồn Backup:** `hrv-catalog-price-update-20261125T060000Z` | **Store:** `shopdemo.myharavan.com` (KHỚP)
- **Phạm vi đợt này:** `2 / 25` bản ghi | **Drift phát hiện:** `0`

| Record ID | Trường | Hiện tại (Current) | Sẽ khôi phục (Before) | Trạng thái Drift |
| --- | --- | ---: | ---: | --- |
| `variant_1120334455` | `price` | `29,900 VND` | `299,000 VND` | `CLEAN_MATCH` |
| `product_1054218901` | `tags` | `polo, flash-sale` | `polo, new` | `CLEAN_MATCH` |

> **Yêu cầu xác nhận (Separate-Turn):** Để thực thi ghi thật, vui lòng phản hồi ở lượt tiếp theo:
> `"XÁC NHẬN ROLLBACK hrv-catalog-price-update-20261125T060000Z"`
```

```json
{
  "skill": "governance-rollback-executor",
  "run_id": "hrv-catalog-price-update-20261125T060000Z",
  "dry_run": true,
  "store_domain_verified": true,
  "summary": { "total_selected": 2, "clean_match": 2, "already_restored": 0, "drift_detected": 0, "succeeded": 0, "failed": 0 },
  "records": [
    { "record_id": "variant_1120334455", "field": "price", "current": 29900, "target_before": 299000, "drift_status": "CLEAN_MATCH", "verified_after_write": false }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Bộ 5 khóa cứng Critical L3:** `dry_run: true` mặc định, `confirmation_required: true`, `separate_turn: true`, `max_records <= 25` (nếu file backup có 60 dòng phải chia 3 đợt riêng biệt), `partial_failure_policy: stop`.
- **Giới hạn bất khả nghịch:** Từ chối chạy và báo rõ nếu tệp backup chứa thao tác không thể đảo ngược trên Haravan (hủy đơn `cancel`, hoàn tiền `refund`, gửi thông báo ZNS/Email đã phát).
- **Khóa môi trường:** Luôn kiểm tra khớp `store_domain` trước mọi lệnh `PUT`/`POST`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn giữa chừng | Dừng ngay lập tức, xuất trạng thái các bản ghi đã chạy & chưa chạy. |
| `403 Forbidden` | Thiếu quyền ghi (`write_products`/`write_inventories`) | Không cố thử tiếp; báo chính xác scope còn thiếu. |
| `404 Not Found` | Sản phẩm/biến thể đã bị nhân sự xóa sau đợt chạy gốc | Dừng batch (`partial_failure_policy: stop`), báo bản ghi không còn tồn tại. |
| `422 Unprocessable` | Dữ liệu `before` vi phạm ràng buộc mới (ví dụ biến thể duy nhất) | Dừng batch, trả nguyên văn lỗi 422 từ Haravan để xử lý thủ công. |
| `429 Too Many Requests` | Vượt leaky bucket trong sự cố Mega Sale | `HaravanClient` backoff `1s -> 2s -> 4s`; giảm tốc xuống `1 req/s`. |

- **Edge Case 1 — File backup > 25 bản ghi:** Tự động chia lô (`batch 1: records 1..25`, `batch 2: 26..50`), yêu cầu xác nhận từng lô thay vì cố chạy một lần.
- **Edge Case 2 — Đơn hàng đã phát sinh mua ở mức giá sai trước khi rollback:** Rollback chỉ khôi phục giá niêm yết cho khách mới; không tự ý sửa hay hủy các đơn đã đặt (phải chuyển quy trình CSKH xử lý riêng).
- **Edge Case 3 — File backup bị thiếu trường `store_domain` hoặc hỏng JSON:** Từ chối thực thi 100%, tuyệt đối không đoán `store_domain`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Kích hoạt trong sự cố đẩy nhầm giá/tồn kho SEV-1:** Được điều phối trực tiếp bởi `ops-incident-runbook-escalation` (L0).
- **Xác minh lại sức khỏe danh mục sau khi rollback xong:** Chạy `catalog-health-audit` (L1) hoặc `python3 scripts/hrv_ops.py catalog-audit`.
- **Ghi nhận biên bản sự cố sau khi khôi phục thành công:** Hoàn tất mục Post-Mortem trong `ops-incident-runbook-escalation`.
