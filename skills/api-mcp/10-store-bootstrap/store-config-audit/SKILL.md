---
name: store-config-audit
description: "Kiểm toán cấu hình chung cửa hàng, chi nhánh/kho hàng, đơn vị tiền tệ, thuế và khu vực hành chính Việt Nam."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 10-store-bootstrap
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/shop.json"
    - "GET https://apis.haravan.com/com/locations.json"
    - "GET https://apis.haravan.com/com/countries/{country_id}/provinces.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 200
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
# Store Config Audit — Kiểm Toán Cấu Hình Cửa Hàng, Chi Nhánh, Thuế & Hành Chính VN

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

Skill `L1 / read` kiểm toán chuyên sâu cấu hình cốt lõi của cửa hàng Haravan (`shop.json`), hệ thống kho/chi nhánh (`locations.json`), cấu hình tiền tệ/thuế GTGT (`taxes_included`) và ánh xạ đơn vị hành chính Việt Nam (`countries/{country_id}/provinces.json`). Cấu hình sai ở tầng này sẽ làm hỏng phí vận chuyển toàn quốc, sai thuế xuất hóa đơn điện tử (e-invoice), hoặc lỗi đồng bộ đơn về đúng kho HaraRetail POS.

- **Khi nào sử dụng:** Khi thiết lập cửa hàng mới, mở thêm chi nhánh/kho hàng mới, thay đổi chính sách thuế VAT (8%/10%), hoặc khi phát hiện đơn hàng bị tính sai phí ship / sai múi giờ báo cáo.
- **Khi nào KHÔNG sử dụng:** Khi muốn kiểm tra tồn kho từng SKU tại các kho (dùng `inventory-multi-location-audit`) hoặc phân quyền nhân sự (dùng `store-staff-permission-audit`).
- **Definition of Done (DoD):**
  1. Đọc đủ `shop.json`, `locations.json`, và danh sách tỉnh/thành Việt Nam (`country_id` của VN, thường là `241` trên Haravan).
  2. Kiểm tra đầy đủ 5 nhóm cấu hình: Định danh & Múi giờ, Tiền tệ & Thuế VAT, Chuẩn hóa địa chỉ chi nhánh 3 cấp, Trạng thái kho chính (`is_primary`), và Tính đồng nhất dữ liệu tỉnh/thành.
  3. Xuất bảng cảnh báo theo mức độ `HIGH / MEDIUM / LOW` kèm hướng dẫn chỉnh sửa chính xác.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Dữ liệu | Scope | Endpoint Haravan |
| --- | --- | --- |
| Cấu hình chung cửa hàng | `com.read_shop` | `GET https://apis.haravan.com/com/shop.json` |
| Danh sách kho & chi nhánh POS | `com.read_shop` | `GET https://apis.haravan.com/com/locations.json` |
| Danh mục tỉnh/thành (VN) | `com.read_shop` | `GET https://apis.haravan.com/com/countries/{country_id}/provinces.json` |

**Chạy thu thập dữ liệu qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
c = HaravanClient(dry_run=True)
shop = c.get("com", "/shop.json")["shop"]
locations = c.get("com", "/locations.json").get("locations") or []
# Vietnam country_id trên Haravan thường là 241 (xác nhận từ shop hoặc /com/countries.json)
provinces = c.get("com", "/countries/241/provinces.json").get("provinces") or []
```

**Sample Response (`GET /com/locations.json`):**
```json
{
  "locations": [
    {
      "id": 1001234,
      "name": "Kho Tổng Thủ Đức",
      "loc_type": "warehouse",
      "address1": "128 Kha Vạn Cân",
      "ward": "Phường Linh Đông",
      "district": "Thành phố Thủ Đức",
      "province": "Hồ Chí Minh",
      "country_code": "VN",
      "phone": "02838991234",
      "is_primary": true,
      "is_unavailable_quantity": false,
      "status": "active"
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `expected_currency` | string | Không | `"VND"` | Mã tiền tệ chuẩn; cảnh báo `HIGH` nếu khác `VND` ở shop nội địa. |
| `expected_timezone_offset` | string | Không | `"+07:00"` | Múi giờ chuẩn Việt Nam (`Asia/Ho_Chi_Minh`). |
| `vietnam_country_id` | integer | Không | `241` | Mã quốc gia Việt Nam trên Haravan để tra cứu `provinces.json`. |
| `require_ward_district` | boolean | Không | `true` | Bắt buộc chi nhánh có đủ Phường/Xã & Quận/Huyện cho API vận chuyển VN. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

### Bộ luật kiểm toán 6 tiêu chí (Config Audit Rules)
1. **Rule C1 — Tiền tệ & Định dạng giá (`HIGH`):** `shop.currency == expected_currency`. Nếu `taxes_included` là `false` ở mô hình bán lẻ B2C Việt Nam, cảnh báo `MEDIUM` vì giá giỏ hàng sẽ cộng thêm thuế ở bước checkout gây rớt đơn.
2. **Rule C2 — Múi giờ (`HIGH`):** `shop.timezone` phải chứa `+07:00`. Sai múi giờ làm lệch doanh thu ngày/tháng và sai khung giờ chạy Flash Sale.
3. **Rule C3 — Kho mặc định (`HIGH`):** Trong `locations`, phải có **đúng 1** địa điểm `is_primary == true` và `status == "active"`. Nếu kho chính bị `inactive` hoặc bị đánh dấu `is_unavailable_quantity == true` (không cho bán online) → báo động `HIGH`.
4. **Rule C4 — Chuẩn địa chỉ lấy hàng 3 cấp (`MEDIUM`):** Mỗi kho `active` phải có đủ `address1`, `province`, `district`, `ward`, `phone`. Thiếu 1 trường khiến GHN/GHTK/Viettel Post từ chối tạo vận đơn tự động.
5. **Rule C5 — Khớp mã tỉnh/thành (`MEDIUM`):** Đối chiếu tên `location.province` với danh sách trả về từ `GET /com/countries/{country_id}/provinces.json` (63 tỉnh/thành). Phát hiện lỗi chính tả hoặc nhập tay không chuẩn (vd `"TPHCM"` thay vì `"Hồ Chí Minh"`).
6. **Rule C6 — Kho rác / chi nhánh đóng cửa (`LOW`):** Liệt kê các kho có `status != "active"` hoặc tên chứa `test`, `demo`, `nháp` để đề xuất dọn dẹp.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

### Báo cáo Kiểm toán Cấu hình Cửa hàng (Markdown)
| Mã Rule | Mức độ | Hạng mục | Giá trị hiện tại | Khuyến nghị xử lý |
| --- | --- | --- | --- | --- |
| `C1` | PASS | Tiền tệ & Thuế | `VND`, `taxes_included: true` | Chuẩn bán lẻ VN |
| `C2` | PASS | Múi giờ | `(GMT+07:00) Bangkok, Hanoi, Jakarta` | Đạt |
| `C3` | PASS | Kho chính | `Kho Tổng Thủ Đức` (`id: 1001234`, active) | Đạt |
| `C4` | MEDIUM | Địa chỉ chi nhánh | `Cửa hàng Quận 1` thiếu `ward` (Phường) | Bổ sung Phường trong `/admin/settings/locations` để đẩy đơn GHN |
| `C5` | PASS | Hành chính VN | 63/63 tỉnh thành hợp lệ, 100% kho khớp mã | Đạt |

### JSON Output Schema
```json
{
  "skill": "store-config-audit",
  "shop_domain": "saigonstreetwear.myharavan.com",
  "summary": { "high": 0, "medium": 1, "low": 0, "active_locations": 2, "inactive_locations": 1 },
  "findings": [
    {
      "rule_id": "C4",
      "severity": "MEDIUM",
      "resource": "location:1001235",
      "message": "Chi nhánh 'Cửa hàng Quận 1' thiếu thông tin Phường/Xã (ward)",
      "remediation": "Cập nhật địa chỉ đầy đủ tại Haravan Admin -> Cấu hình -> Địa chỉ & Kho hàng"
    }
  ],
  "provinces_checked": 63
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only (`L1`):** Chỉ gọi `GET`, không thay đổi bất kỳ cấu hình cửa hàng hay kho nào.
- **PII:** Che số điện thoại cá nhân của chủ shop/quản lý kho (`090****678`), chỉ giữ số hotline công ty nếu cần.
- **Tuyên bố thuế/tài chính:** Kiểm tra cờ `taxes_included` chỉ mang tính kỹ thuật vận hành (Operational Aid), không thay thế tư vấn kế toán thuế chính thức.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `404 Not Found` tại `/countries/241/provinces.json` | `country_id` khác `241` trên môi trường shop đó | Gọi `GET /com/countries.json`, tìm phần tử có `code == "VN"` để lấy `id` động. |
| `403 Forbidden` | Token thiếu `com.read_shop` | Yêu cầu cấp tối thiểu `com.read_shop` trong Private App. |
| `429 Too Many Requests` | Gọi lặp nhiều lần | Dùng `HaravanClient` với backoff tự động. |

**Tình huống biên (Edge Cases) đặc thù Haravan:**
1. **Kho bán hàng POS bị tắt bán online (`is_unavailable_quantity: true`):** Nhiều shop có 5 chi nhánh POS nhưng chỉ muốn kho tổng bán online; nếu tất cả kho đều bật `is_unavailable_quantity: true`, toàn bộ sản phẩm trên web sẽ hiện "Hết hàng" dù tổng tồn > 0.
2. **Tên tỉnh/thành cũ sau sáp nhập địa giới hành chính:** Một số đơn vị vận chuyển phân biệt `TP. Thủ Đức` vs `Quận 2/Quận 9/Thủ Đức` cũ; cần đối chiếu chuẩn danh mục của Haravan trước khi map sang ERP.
3. **Shop bán đa thị trường (VN + quốc tế):** Nếu cửa hàng bán xuất khẩu dùng `USD`, phải truyền `expected_currency="USD"` để tránh báo lỗi giả ở Rule `C1`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Chạy trước:** `haravan-auth-setup`, `store-bootstrap-checklist`.
- **Chạy tiếp theo:** `inventory-multi-location-audit` (kiểm toán tồn kho chi tiết theo từng `location_id` vừa phát hiện), `store-health-check`.
