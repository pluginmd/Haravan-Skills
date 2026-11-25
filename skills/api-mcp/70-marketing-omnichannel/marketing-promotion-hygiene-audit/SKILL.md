---
name: marketing-promotion-hygiene-audit
description: "Kiểm toán toàn bộ chương trình khuyến mãi (/com/promotions.json), phát hiện mã hết hạn chưa tắt, rủi ro chồng mã (stacking) hoặc giảm quá sâu."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 70-marketing-omnichannel
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_discounts
  endpoints:
    - "GET https://apis.haravan.com/com/promotions.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
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

# Haravan Promotions & Discounts Hygiene Audit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Rà soát toàn diện các chương trình khuyến mãi và mã giảm giá trên Haravan để ngăn chặn thất thoát biên lợi nhuận do quên tắt mã cũ, để mã chạy vô thời hạn (`ends_at == null`), giảm giá quá sâu (> `max_safe_discount_pct`) hoặc chồng nhiều khuyến mãi cùng lúc (stacking) trong các đợt Mega Sale (11.11, 12.12, Tết).
- **Ngữ cảnh Haravan:** Các shop vận hành lâu năm trên Haravan thường tích lũy hàng chục đến hàng trăm chương trình tại `/com/promotions.json`. Nhiều mã KOL/livestream cũ không đặt ngày kết thúc hoặc đã đạt gần ngưỡng lạm dụng vẫn ở trạng thái `enabled`, tạo lỗ hổng doanh thu âm thầm mỗi tháng.
- **Definition of Done (DoD):**
  1. Tải toàn bộ danh sách khuyến mãi (`<= 500` bản ghi) qua `GET /com/promotions.json` hoặc `scripts/hrv_ops.py promo-audit`.
  2. Phân loại rõ 5 nhóm trạng thái: Đang hoạt động an toàn, Đang hoạt động có rủi ro (`P0`/`P1`), Sắp chạy, Đã hết hạn nhưng chưa tắt (`Zombie Promo`), Đã tắt.
  3. Xuất danh sách `promotion_id` cụ thể kèm lý do và đề xuất hành động tắt (chuyển sang skill L2 `marketing-promo-code-proposal`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_discounts` |
| **Endpoints** | `GET /com/promotions.json` |

**Ví dụ gọi nhanh bằng CLI có sẵn trong repo (`scripts/hrv_ops.py`):**
```bash
# Chạy kiểm toán thực tế (yêu cầu ENV HARAVAN_ACCESS_TOKEN)
python3 scripts/hrv_ops.py promo-audit

# Chạy chế độ demo offline để kiểm thử định dạng đầu ra
python3 scripts/hrv_ops.py --demo promo-audit
```

**Ví dụ JSON Response thực tế từ `GET /com/promotions.json`:**
```json
{
  "promotions": [
    {
      "id": 2049101,
      "name": "MEGA11_GIAM45",
      "status": "enabled",
      "discount_type": "percentage",
      "value": 45.0,
      "minimum_order_amount": 0,
      "usage_limit": null,
      "times_used": 312,
      "starts_at": "2026-11-10T00:00:00+07:00",
      "ends_at": null,
      "is_promotion": false
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `max_safe_discount_pct` | `number` | Không | `40` | Ngưỡng cảnh báo % giảm giá (`1..100`). Vượt ngưỡng bị gắn cờ `P0: DEEP_DISCOUNT`. |
| `max_safe_fixed_vnd` | `integer` | Không | `500000` | Ngưỡng cảnh báo giảm tiền mặt cố định (VND). |
| `include_disabled` | `boolean` | Không | `false` | Có liệt kê chi tiết cả mã đã tắt hay chỉ thống kê tổng số lượng. |
| `upcoming_window_days` | `integer` | Không | `7` | Số ngày kiểm tra các chương trình sắp chạy để phát hiện sớm xung đột chồng mã. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Thu thập dữ liệu:** Dùng `client.paginate("com", "/promotions.json", "promotions", limit=50, max_pages=10)`.
2. **Đánh giá 6 luật kiểm toán trên từng chương trình `status == "enabled"`:**
   - **Rule 1 (`P0 - DEEP_DISCOUNT`):** `discount_type == "percentage"` và `value > max_safe_discount_pct`, hoặc `discount_type == "fixed_amount"` và `value > max_safe_fixed_vnd`.
   - **Rule 2 (`P0 - UNBOUNDED_PROMO`):** `ends_at == null` VÀ `usage_limit == null` (chạy vô thời hạn không trần lượt dùng).
   - **Rule 3 (`P1 - NO_MIN_ORDER_FIXED`):** `discount_type == "fixed_amount"` và `(minimum_order_amount == null || minimum_order_amount < value * 2)` -> nguy cơ tạo đơn 0đ hoặc lỗ phí ship.
   - **Rule 4 (`P1 - ZOMBIE_EXPIRED`):** `ends_at != null` và `ends_at < now_utc` nhưng `status` vẫn là `enabled`.
   - **Rule 5 (`P1 - STACKING_OVERLAP`):** Tồn tại ≥ 2 chương trình tự động (`is_promotion == true`) hoặc 1 CT tự động + 1 mã giảm giá áp dụng cùng phạm vi (`applies_to_resource == "order"`) có khoảng thời gian `[starts_at, ends_at]` giao nhau.
   - **Rule 6 (`P2 - HIGH_USAGE_VELOCITY`):** `usage_limit != null` và `times_used / usage_limit >= 0.85` (sắp hết ngân sách mã).
3. **Tính Chỉ số Rủi ro Khuyến mãi (Promo Hygiene Score):**
   $$\text{Hygiene Score} = 100 - \min(100,\; 20 \cdot N_{P0} + 8 \cdot N_{P1} + 2 \cdot N_{P2})$$
4. **Tổng hợp khuyến nghị:** Nhóm danh sách `promotion_id` cần tắt ngay (`disable`) hoặc cần bổ sung `ends_at` để bàn giao cho bước L2.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Kiểm toán Vệ sinh Khuyến mãi Haravan
- **Tổng chương trình quét:** 64 | **Đang bật (`enabled`):** 14 | **Hygiene Score:** 52 / 100
- **Phát hiện rủi ro:** 2 lỗi P0 (nghiêm trọng) | 3 lỗi P1 | 1 cảnh báo P2

| Mức độ | Promotion ID | Tên chương trình | Giá trị | Phát hiện lỗi | Đề xuất |
| --- | --- | --- | --- | --- | --- |
| P0 | `2049101` | `MEGA11_GIAM45` | `45%` | `DEEP_DISCOUNT` + `UNBOUNDED_PROMO` (`ends_at=null`, đã dùng 312 lượt) | Tắt ngay qua L2 |
| P1 | `2048820` | `KOL_LINH_100K` | `100,000đ` | `NO_MIN_ORDER_FIXED` (`min_order=0`) | Đặt `min_order >= 300,000đ` hoặc tắt |
| P1 | `2047112` | `FLASH_T10` | `15%` | `ZOMBIE_EXPIRED` (hết hạn 31/10 vẫn bật) | Tắt để dọn sạch danh sách |

> *Lưu ý tài chính:* Đây là kiểm toán vận hành nhằm phát hiện rủi ro thất thoát; cần đối chiếu báo cáo doanh thu thực tế để xác định tổng giá trị chiết khấu đã phát sinh.
```

```json
{
  "skill": "marketing-promotion-hygiene-audit",
  "summary": { "total_scanned": 64, "active_count": 14, "p0_count": 2, "p1_count": 3, "p2_count": 1, "hygiene_score": 52 },
  "findings": [
    { "severity": "P0", "promotion_id": 2049101, "name": "MEGA11_GIAM45", "flags": ["DEEP_DISCOUNT", "UNBOUNDED_PROMO"], "times_used": 312, "recommended_action": "disable" }
  ],
  "recommended_disable_ids": [2049101, 2047112]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ gọi `GET /com/promotions.json`. Không tự ý gọi `PUT /com/discounts/{id}/disable.json` trong skill này.
- **Bảo mật:** `pii_level: none`. Không xuất token hoặc thông tin cấu hình nội bộ.
- **Rollback:** Không cần rollback vì không ghi dữ liệu. Việc tắt các mã rủi ro phải chuyển sang `marketing-promo-code-proposal` (L2) có dry-run và backup snapshot.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | `HARAVAN_ACCESS_TOKEN` hết hạn | Dừng audit, thông báo làm mới token. |
| `403 Forbidden` | App chưa được cấp scope `com.read_discounts` | Báo rõ thiếu scope `com.read_discounts`. |
| `404 Not Found` | Endpoint sai hoặc shop chưa kích hoạt module khuyến mãi | Kiểm tra đường dẫn `/com/promotions.json`. |
| `422 Unprocessable` | Tham số phân trang vượt giới hạn | Giới hạn `limit <= 250`. |
| `429 Too Many Requests` | Vượt leaky bucket `80` req / `4` req/s | Sử dụng `HaravanClient` tự backoff `1s -> 2s -> 4s`. |

- **Edge Case 1 — Chương trình ưu đãi nội bộ nhân viên (`NV_50%`):** Một số shop cố tình tạo mã giảm 50% không hạn cho nhân viên. Agent vẫn phải gắn cờ `P0`, nhưng nếu tên mã chứa `NOIBO`/`STAFF`/`VIP` thì ghi chú rõ *"Cần xác nhận có phải mã nội bộ đã giới hạn nhóm khách hàng hay không"*.
- **Edge Case 2 — Khuyến mãi đồng giá / Mua X tặng Y:** Các cấu trúc combo/mua kèm trên Haravan có thể có `value == 0` ở cấp root. Không báo lỗi `value == 0` mà kiểm tra sâu vào chi tiết điều kiện khuyến mãi.
- **Edge Case 3 — Danh sách > 500 khuyến mãi lịch sử:** Nếu cửa hàng có hơn 500 bản ghi cũ, ưu tiên lọc hoặc dừng ở `max_records: 500` và ghi chú rõ trong báo cáo rằng vẫn còn các trang lịch sử chưa quét hết.

## 8. Liên kết Workflow & Skill kế tiếp

- **Tắt các mã vi phạm ngay sau khi duyệt:** Chuyển danh sách `recommended_disable_ids` sang `marketing-promo-code-proposal` (L2, `action: disable`).
- **Đánh giá tác động chiết khấu lên doanh thu cuối tháng:** Kết hợp `ops-monthly-financial-close` (L1) để xem tỷ lệ Discount / Gross Revenue.
- **Kiểm tra đột biến giảm giá bất thường trong ngày:** Xem thêm `ops-daily-morning-briefing` (L1).
