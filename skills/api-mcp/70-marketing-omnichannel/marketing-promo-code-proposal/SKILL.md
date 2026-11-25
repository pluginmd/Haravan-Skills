---
name: marketing-promo-code-proposal
description: "Thiết kế, kiểm tra biên an toàn và đề xuất tạo hoặc bật/tắt mã khuyến mãi trên Haravan (/com/promotions.json)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 70-marketing-omnichannel
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_discounts
    - com.write_discounts
  endpoints:
    - "GET https://apis.haravan.com/com/promotions.json"
    - "POST https://apis.haravan.com/com/promotions.json"
    - "PUT https://apis.haravan.com/com/discounts/{promotion_id}/enable.json"
    - "PUT https://apis.haravan.com/com/discounts/{promotion_id}/disable.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
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

# Haravan Promotion & Discount Code Creation Proposal

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Thiết kế, thẩm định biên độ an toàn tài chính và đề xuất tạo mới (`create`) hoặc bật/tắt (`enable`/`disable`) chương trình khuyến mãi trên Haravan, ngăn chặn tuyệt đối lỗi nhập sai mức giảm (ví dụ giảm 500.000đ thay vì 50.000đ, hoặc giảm % không giới hạn trần) và lỗi chồng mã khuyến mãi.
- **Ngữ cảnh Haravan:** Haravan quản lý khuyến mãi qua `/com/promotions.json` và thao tác bật/tắt trạng thái qua `/com/discounts/{promotion_id}/enable.json` và `disable.json`. Một chương trình không có `ends_at`, không có `usage_limit` hoặc không đặt giá trị đơn tối thiểu (`value_limit`) có thể bị cộng đồng săn mã chia sẻ rộng rãi gây lỗ biên lợi nhuận chỉ trong vài giờ.
- **Definition of Done (DoD):**
  1. Đọc danh sách khuyến mãi hiện hữu (`GET /com/promotions.json`) để kiểm tra trùng tên/trùng mã và xung đột thời gian.
  2. Kiểm tra đủ 5 guardrail biên an toàn (mức giảm, hạn kết thúc, giới hạn lượt dùng, đơn tối thiểu, rủi ro chồng mã).
  3. Sinh bản Preview + file Backup JSON/CSV qua `scripts/dry_run_report.py`; chỉ thực thi `POST`/`PUT` sau khi người dùng xác nhận và luôn gọi lại `GET` để xác minh hậu ghi.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_discounts`, `com.write_discounts` |
| **Endpoints** | `GET/POST /com/promotions.json`, `PUT /com/discounts/{promotion_id}/enable.json`, `PUT /com/discounts/{promotion_id}/disable.json` |

**Ví dụ gọi Dry-Run qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)  # Luôn chạy dry_run=True trước!
payload = {
    "promotion": {
        "name": "WINBACK_T11_GIAM10",
        "discount_type": "percentage",
        "value": 10,
        "applies_to_resource": "order",
        "minimum_order_amount": 500000,
        "usage_limit": 200,
        "starts_at": "2026-11-26T00:00:00+07:00",
        "ends_at": "2026-11-30T23:59:59+07:00",
        "is_promotion": False
    }
}
preview = client.request("POST", "com", "/promotions.json", payload=payload)
```

**Ví dụ Payload bật/tắt chương trình hiện có:**
```http
PUT https://apis.haravan.com/com/discounts/2049182/disable.json
Authorization: Bearer <HARAVAN_ACCESS_TOKEN>
Content-Type: application/json
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `action` | `string` | Bắt buộc | — | Enum: `create`, `enable`, `disable`. |
| `promotion_id` | `integer` | Khi `enable`/`disable` | `null` | ID chương trình khuyến mãi cần bật/tắt. |
| `promotion_spec` | `object` | Khi `create` | `{}` | Gồm `name`, `discount_type` (`percentage`/`fixed_amount`/`shipping`), `value`, `starts_at`, `ends_at`, `usage_limit`, `minimum_order_amount`. |
| `max_safe_discount_pct` | `number` | Không | `50` | Ngưỡng cảnh báo cứng nếu `discount_type == percentage` và `value > 50`. |
| `dry_run` | `boolean` | Bắt buộc | `true` | Bắt buộc chạy `true` trước khi thực thi ghi thật. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Kiểm tra hiện trạng (Pre-Flight Check):**
   - Gọi `GET /com/promotions.json` lấy toàn bộ chương trình đang hoạt động (`status == "enabled"`).
   - Nếu `action == "create"`: kiểm tra không trùng `name` (so sánh không phân biệt hoa thường) và liệt kê các chương trình tự động (`is_promotion: true`) đang chạy trùng khung giờ `[starts_at, ends_at]`.
   - Nếu `action in ("enable", "disable")`: kiểm tra tồn tại `promotion_id` và trạng thái hiện tại để đảm bảo tính idempotent (không bật mã đã bật).
2. **Thẩm định 5 Guardrails biên an toàn:**
   - **G1 — Hạn kết thúc bắt buộc:** `ends_at` không được `null` và `ends_at > starts_at` (tối đa 90 ngày với mã chiến dịch).
   - **G2 — Trần mức giảm:** Nếu `discount_type == "percentage"` và `value > 50`, hoặc `discount_type == "fixed_amount"` và `value > 0.5 * minimum_order_amount` -> **Gắn cờ HIGH RISK**, yêu cầu người dùng xác nhận đặc biệt.
   - **G3 — Giới hạn ngân sách tối đa (Max Budget Exposure):**
     $$\text{Max Exposure (VND)} = \begin{cases} \text{usage\_limit} \times \text{value} & \text{(fixed\_amount)} \\ \text{usage\_limit} \times \text{AOV}_{\text{est}} \times \frac{\text{value}}{100} & \text{(percentage)} \end{cases}$$
   - **G4 — Không để trống điều kiện đơn tối thiểu** khi tạo mã giảm tiền mặt cố định (tránh trường hợp mua hàng 50k dùng mã giảm 100k -> đơn 0đ).
   - **G5 — Cảnh báo chồng mã (Stacking Risk):** Nếu có khuyến mãi tự động toàn shop đang bật trùng thời gian, cảnh báo rõ tổng mức giảm cộng dồn ước tính.
3. **Sinh Preview & Backup Snapshot:** Lưu file `hrv-marketing-promo-code-proposal-<ts>.backup.json` và `.preview.csv`. Trình bày bảng tóm tắt và chờ người dùng xác nhận.
4. **Thực thi & Xác minh hậu ghi (Post-Write Verification):** Sau khi xác nhận, gọi `POST`/`PUT` với `dry_run=False`, `partial_failure_policy: stop`. Ngay lập tức gọi lại `GET /com/promotions.json` xác nhận `id`, `status`, `ends_at` đã lưu đúng trên Haravan.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Bản Xem Trước (Dry-Run) Tạo Mã Khuyến Mãi Haravan
- **Hành động:** `create` | **Môi trường:** `production` | **Trạng thái Guardrail:** ĐẠT (1 lưu ý)
- **Backup Artifact:** `artifacts/hrv-marketing-promo-code-proposal-20261125T064500Z.backup.json`

| Thuộc tính | Giá trị đề xuất | Kiểm tra an toàn |
| --- | --- | --- |
| Mã / Tên | `WINBACK_T11_GIAM10` | Không trùng mã hiện có |
| Mức giảm | `10%` (Đơn tối thiểu `500,000 VND`) | ≤ ngưỡng 50% |
| Thời gian | `26/11/2026 00:00` → `30/11/2026 23:59` (UTC+7) | Có hạn kết thúc (5 ngày) |
| Giới hạn lượt | `200` lượt | Max Exposure ước tính: ~16,000,000 VND (với AOV 800k) |
| Xung đột | 1 CT tự động "Freeship đơn > 499k" đang chạy cùng lúc | Lưu ý: khách có thể hưởng cả Freeship + giảm 10% |

> Vui lòng xác nhận **"Đồng ý tạo mã WINBACK_T11_GIAM10"** để tiến hành gọi API ghi.
```

```json
{
  "skill": "marketing-promo-code-proposal",
  "action": "create",
  "dry_run": true,
  "guardrail_status": "PASS_WITH_WARNING",
  "warnings": ["OVERLAP_WITH_AUTO_PROMO_ID_2049101"],
  "max_exposure_vnd_est": 16000000,
  "backup_json": "artifacts/hrv-marketing-promo-code-proposal-20261125T064500Z.backup.json",
  "result": { "promotion_id": null, "verified": false }
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Dry-Run & Xác nhận (L2):** Luôn chạy `dry_run: true` trước, `confirmation_required: true`, `max_records <= 50`. Nếu mức giảm > 50% hoặc thao tác bật/tắt hàng loạt > 10 mã, nâng mức cảnh báo lên xác nhận tường minh.
- **Rollback tức thì:** Nếu mã vừa tạo hoặc vừa bật có sai sót, có thể đảo ngược ngay bằng `PUT /com/discounts/{promotion_id}/disable.json` (với mã mới tạo/bật) hoặc `enable.json` (với mã vừa tắt) dựa trên file `*.backup.json`.
- **Financial Disclaimer:** Con số `max_exposure_vnd_est` là ước tính vận hành dựa trên AOV trung bình, không phải cam kết ngân sách kế toán.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn hoặc bị thu hồi | Dừng ngay, báo người dùng kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.write_discounts` | Chỉ có quyền đọc — đề xuất người dùng bổ sung scope hoặc tạo tay qua Browser UI. |
| `404 Not Found` | `promotion_id` không tồn tại hoặc đã bị xóa | Dừng batch (`partial_failure_policy: stop`), báo ID không hợp lệ. |
| `422 Unprocessable` | Trùng tên mã, `ends_at <= starts_at`, hoặc `value <= 0` | Trích xuất thông báo lỗi từ Haravan response, sửa spec và chạy lại dry-run. |
| `429 Too Many Requests` | Bật/tắt hàng loạt nhiều mã vượt rate limit | `HaravanClient` tự backoff `1s -> 2s -> 4s`; không retry mù nếu đã tạo mã (`POST`). |

- **Edge Case 1 — Lệch múi giờ UTC vs UTC+7 (`Asia/Ho_Chi_Minh`):** Nếu truyền `starts_at` theo UTC mà quên cộng `+07:00`, mã Flash Sale 00:00 sẽ kích hoạt muộn 7 tiếng (07:00 sáng). Bắt buộc chuẩn hóa chuỗi ISO kèm offset `+07:00`.
- **Edge Case 2 — Bật lại mã đã quá hạn `ends_at`:** Gọi `PUT .../enable.json` lên một mã có `ends_at` trong quá khứ sẽ không cho phép khách sử dụng được dù trạng thái trả về 200. Agent phải kiểm tra `ends_at > now` trước khi đề xuất `enable`.
- **Edge Case 3 — Tạo trùng do lỗi timeout mạng:** Trước khi retry `POST /com/promotions.json` sau lỗi 5xx/timeout, bắt buộc gọi `GET /com/promotions.json` kiểm tra xem mã `name` đã được tạo hay chưa (đảm bảo `idempotency_required: true`).

## 8. Liên kết Workflow & Skill kế tiếp

- **Kiểm tra vệ sinh toàn bộ mã đang chạy trước khi tạo mới:** Chạy `marketing-promotion-hygiene-audit` (L1).
- **Gắn mã mới tạo vào chiến dịch kéo khách:** Kết hợp `marketing-winback-campaign` (L2) hoặc `marketing-cart-recovery-zns` (L2).
- **Hoàn tác khẩn cấp nếu phát hiện sai sót sau khi chạy:** Kích hoạt `governance-rollback-executor` (L3) hoặc `ops-incident-runbook-escalation` (L0).
