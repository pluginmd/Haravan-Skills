---
name: ops-incident-runbook-escalation
description: "Sổ tay ứng cứu sự cố khẩn cấp Haravan: bão đơn 429 Mega Sale, đẩy nhầm giá/tồn kho, đứt đồng bộ sàn TMĐT, lỗi cổng thanh toán hoặc sập domain/SSL."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 90-control-tower-governance
layer: L0
wave: 1
mode: reference
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/shop.json"
    - "UI /admin/settings/domains"
    - "UI /admin/settings/payments"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 25
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

# Haravan Operations Incident Runbook & Emergency Escalation

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Cung cấp sổ tay phản ứng sự cố theo từng phút (mục tiêu **MTTR < 15 phút**) cho 5 kịch bản khủng hoảng nghiêm trọng nhất trên hệ thống Haravan live (`wrong_bulk_price`, `oversell_sync_break`, `rate_limit_429_storm`, `payment_gateway_down`, `domain_ssl_down`), giúp đội vận hành khoanh vùng đúng lỗi, ngăn thiệt hại lan rộng và không hoảng loạn làm hỏng thêm dữ liệu.
- **Ngữ cảnh Haravan:** Trong các đợt Mega Sale (11.11, 12.12, Black Friday) hoặc sau khi chạy script cập nhật hàng loạt, sai lầm phổ biến nhất là tiếp tục chạy thêm nhiều job song song (làm bão `429` nặng hơn) hoặc tự sửa tay đè lên dữ liệu mà chưa chụp bằng chứng/backup. Sổ tay này chuẩn hóa quy trình phân loại `SEV-1 / SEV-2 / SEV-3`, kênh leo thang hỗ trợ kỹ thuật Haravan (**Hotline 1900.636.099** / `support@haravan.com`) và mẫu biên bản Post-Mortem.
- **Definition of Done (DoD):**
  1. Xác nhận nhanh kết nối API cửa hàng (`GET /com/shop.json`) để phân biệt lỗi từ phía Haravan hay phía tích hợp/cấu hình nội bộ.
  2. Phân loại chính xác mức độ `SEV-1` / `SEV-2` / `SEV-3` và xuất Checklist hành động theo từng mốc phút (`T+0` → `T+5` → `T+15` → `T+60`).
  3. Cung cấp sẵn thông tin leo thang (Escalation Matrix) và khung biên bản Post-Mortem không đổ lỗi (Blameless Post-Mortem).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) + đối chiếu UI Admin |
| **Scopes tối thiểu** | `com.read_shop` |
| **Endpoints** | `GET /com/shop.json`, `UI /admin/settings/domains`, `UI /admin/settings/payments` |

**Ví dụ kiểm tra nhanh sức khỏe kết nối cửa hàng (`scripts/hrv_ops.py probe`):**
```bash
# Kiểm tra nhanh API Haravan & xác định đúng store_domain đang gặp sự cố
python3 scripts/hrv_ops.py probe
```

**Ví dụ JSON Response bình thường từ `GET /com/shop.json`:**
```json
{
  "shop": {
    "id": 1000123456,
    "name": "LocalBrand VN Official",
    "myharavan_domain": "localbrandvn.myharavan.com",
    "domain": "localbrand.vn",
    "timezone": "(GMT+07:00) Bangkok, Hanoi, Jakarta",
    "currency": "VND"
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `incident_type` | `string` | Bắt buộc | — | Enum: `wrong_bulk_price`, `oversell_sync_break`, `rate_limit_429_storm`, `payment_gateway_down`, `domain_ssl_down`. |
| `detected_at` | `string` | Không | Hiện tại (`UTC+7`) | Thời điểm phát hiện sự cố (`YYYY-MM-DD HH:MM`). |
| `backup_json_path` | `string` | Khi `wrong_bulk_price` | `""` | Đường dẫn tệp `*.backup.json` gần nhất để bàn giao sang `governance-rollback-executor`. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Bảng Phân loại Mức độ Nghiêm trọng (Severity Matrix)
| Mức độ | Định nghĩa | SLA Phản ứng | Ví dụ điển hình |
| --- | --- | --- | --- |
| **SEV-1 (Khẩn cấp)** | Dừng toàn bộ luồng đặt hàng, sập web hoặc thất thoát tài chính trực tiếp mỗi phút | Phản ứng ngay (`< 5 phút`), MTTR `< 15 phút` | `wrong_bulk_price`, `domain_ssl_down`, `payment_gateway_down` toàn hệ thống |
| **SEV-2 (Nghiêm trọng)** | Đứt đồng bộ 1 sàn TMĐT, bán vượt tồn diện rộng, bão `429` làm chậm đơn | `< 15 phút`, MTTR `< 60 phút` | `oversell_sync_break`, `rate_limit_429_storm` |
| **SEV-3 (Trung bình)** | Lỗi báo cáo, lệch số liệu hiển thị không ảnh hưởng đặt hàng | Trong ca làm việc (`< 4 giờ`) | Chậm đồng bộ lịch sử khách hàng, lỗi xuất báo cáo |

### Quy trình Ứng cứu Theo Từng Phút (Minute-by-Minute Playbook)
1. **Phút `T+0 → T+2` (Đóng băng & Chụp bằng chứng — Contain First):**
   - **Dừng ngay** mọi cronjob, script sync, hoặc chiến dịch quảng cáo đang đổ traffic vào sản phẩm lỗi.
   - Chạy `python3 scripts/hrv_ops.py probe` xác minh `store_domain` và chụp ảnh màn hình lỗi / lưu HTTP status code + timestamp.
2. **Phút `T+2 → T+10` (Xử lý đặc thù theo `incident_type`):**
   - **`wrong_bulk_price` (SEV-1):** Xác định file `*.backup.json` gần nhất → kích hoạt `governance-rollback-executor` (L3, `dry_run: true` rồi xác nhận lượt riêng) để khôi phục từng lô ≤ 25 bản ghi. Nếu lỗi > 100 SKU, cân nhắc tạm ẩn bộ sưu tập bị lỗi trên Online Store trong lúc rollback.
   - **`rate_limit_429_storm` (SEV-2):** Tắt toàn bộ job audit/reporting/sync tồn kho định kỳ; hạ `leak_rate` của `HaravanClient` xuống `1.0 req/s`; giữ ưu tiên băng thông API cho webhook đơn hàng & HaraRetail POS.
   - **`oversell_sync_break` (SEV-2):** Chạy `omnichannel-marketplace-sync-audit` xác định kênh bị đứt; vào Haravan Admin > Kênh bán hàng kết nối lại OAuth token sàn; tạm tăng tồn đệm an toàn (buffer) trên Seller Center.
   - **`payment_gateway_down` (SEV-1):** Kiểm tra `/admin/settings/payments` và trạng thái hệ thống VNPay/MoMo/Ngân hàng; tạm thông báo banner khuyến khích chuyển sang COD/VietQR thủ công (chỉ quản trị viên tự thao tác trên UI, **Agent không tự sửa cấu hình thanh toán**).
   - **`domain_ssl_down` (SEV-1):** Kiểm tra bản ghi DNS (`A` / `CNAME`) và chứng chỉ SSL tại `/admin/settings/domains` bằng `dig`/`curl -I`; nếu lỗi phía hạ tầng Haravan, gọi ngay **Hotline kỹ thuật Haravan: 1900.636.099** (kèm `myharavan_domain`, thời điểm lỗi và ảnh chụp).
3. **Phút `T+10 → T+15` (Xác minh phục hồi):** Đặt 1 đơn test nội bộ (hoặc kiểm tra `GET` sản phẩm/đơn hàng) xác nhận hệ thống đã hoạt động bình thường.
4. **Trong vòng `24h` (Post-Mortem):** Hoàn tất biên bản Root Cause Analysis (5 Whys) và cập nhật guardrail để không tái diễn.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### [SEV-1 RUNBOOK] Ứng cứu Sự cố: `wrong_bulk_price`
- **Cửa hàng:** `localbrandvn.myharavan.com` | **Phát hiện lúc:** `2026-11-25 10:12 UTC+7` | **Mục tiêu MTTR:** `< 15 phút`

| Mốc thời gian | Bước hành động | Người phụ trách | Trạng thái |
| --- | --- | --- | --- |
| `T+0 → T+2` | Dừng toàn bộ job cập nhật giá & tạm dừng Ads sản phẩm lỗi | Ops Lead | [ ] |
| `T+2 → T+5` | Kiểm tra `*.backup.json` & chạy `governance-rollback-executor` (`dry_run: true`) | AI Agent + Tech | [ ] |
| `T+5 → T+10` | Xác nhận lượt riêng & khôi phục giá theo lô ≤ 25 SKU | Tech Lead | [ ] |
| `T+10 → T+15` | Gọi `GET` xác minh giá live & rà soát các đơn đã phát sinh ở giá sai | CSKH + Ops | [ ] |

**Khung Biên bản Post-Mortem:** Tóm tắt sự cố → Dòng thời gian → Nguyên nhân gốc (5 Whys) → Thiệt hại ước tính → 3 Hành động phòng ngừa (Action Items có người chịu trách nhiệm & deadline).
```

```json
{
  "skill": "ops-incident-runbook-escalation",
  "incident_type": "wrong_bulk_price",
  "severity": "SEV-1",
  "store_domain": "localbrandvn.myharavan.com",
  "target_mttr_minutes": 15,
  "escalation_contacts": { "haravan_hotline": "1900.636.099", "haravan_email": "support@haravan.com" },
  "next_skill": "governance-rollback-executor"
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ Reference / Read-Only (L0):** Skill chỉ cung cấp hướng dẫn ứng cứu và kiểm tra kết nối `GET /com/shop.json`. Mọi thao tác ghi dữ liệu khẩn cấp (rollback) vẫn phải đi qua `governance-rollback-executor` (L3) với đầy đủ `dry_run: true`, kiểm tra `store_domain` và `separate_turn: true`.
- **Không tự ý sửa cài đặt nhạy cảm:** Tuyệt đối không để Agent tự sửa `/admin/settings/payments` hay `/admin/settings/domains`.
- **Bảo toàn bằng chứng:** Luôn yêu cầu lưu log/ảnh chụp trước khi thực hiện bất kỳ thao tác khắc phục nào.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token bị thu hồi trong lúc sự cố bảo mật | Dùng ngay Haravan Admin UI để kiểm tra và tạo token mới có quyền tối thiểu. |
| `403 Forbidden` | Thiếu `com.read_shop` | Vẫn xuất đầy đủ Runbook offline theo `incident_type`, ghi chú chưa verify được `store_domain` qua API. |
| `404 Not Found` | Endpoint sai | Dùng `GET https://apis.haravan.com/com/shop.json`. |
| `429 Too Many Requests` | Chính lệnh `probe` cũng dính bão 429 | Xác nhận ngay đang có bão API; ưu tiên dừng tất cả worker đang chạy trên server. |
| `502 / 503 / 504` | Sự cố hạ tầng phía Haravan | Không retry dồn dập; gọi ngay Hotline Haravan `1900.636.099` xác minh trạng thái hệ thống. |

- **Edge Case 1 — Sự cố xảy ra nhưng KHÔNG có file `*.backup.json`:** Hướng dẫn chuyển sang phương án dự phòng: xuất lịch sử giá từ báo cáo đơn hàng gần nhất (`GET /com/orders.json` đọc `line_items[].price`) hoặc file Excel bảng giá gốc của kế toán để dựng lại file khôi phục.
- **Edge Case 2 — Sự cố đồng thời (`rate_limit_429_storm` + `wrong_bulk_price`):** Phải dừng toàn bộ các job khác **trước** (giải phóng leaky bucket) rồi mới chạy `governance-rollback-executor` ở tốc độ `1 req/s`.
- **Edge Case 3 — Sự cố vào ban đêm / cuối tuần không có người duyệt L3:** Cho phép đội trực ca tạm thời ẩn sản phẩm/tắt quảng cáo trên giao diện Admin để cắt lỗ trước, sau đó đợi Tech Lead duyệt rollback vào sáng hôm sau.

## 8. Liên kết Workflow & Skill kế tiếp

- **Thực thi đảo ngược dữ liệu sau khi khoanh vùng sự cố:** Chuyển ngay sang `governance-rollback-executor` (L3).
- **Chẩn đoán đứt đồng bộ sàn TMĐT trong sự cố SEV-2:** Chạy `omnichannel-marketplace-sync-audit` (L1).
- **Rà soát lại tác động tài chính của sự cố vào cuối tuần:** Báo cáo trong `ops-weekly-business-review` (L1).
