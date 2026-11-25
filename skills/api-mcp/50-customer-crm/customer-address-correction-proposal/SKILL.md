---
name: customer-address-correction-proposal
description: "Kiểm tra và đề xuất chuẩn hóa địa chỉ giao hàng Việt Nam (Tỉnh/Thành, Quận/Huyện, Phường/Xã) để giảm lỗi đẩy đơn NVC."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 50-customer-crm
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: com
  scopes:
    - com.read_customers
    - com.write_customers
    - com.read_shop
  endpoints:
    - "GET https://apis.haravan.com/com/customers/{customer_id}/addresses.json"
    - "PUT https://apis.haravan.com/com/customers/{customer_id}/addresses/{address_id}.json"
    - "GET https://apis.haravan.com/com/countries/{country_id}/provinces.json"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Vietnam Shipping Address Normalization Proposal

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Lỗi đẩy vận đơn sang GHN, GHTK, Viettel Post và J&T tại Việt Nam phần lớn xuất phát từ **sai lệch danh mục địa giới hành chính 3 cấp** trên hồ sơ khách hàng Haravan (ghi tắt `TPHCM`/`SG`/`HN`, nhập lẫn Phường/Xã vào `address1`, chọn sai mã `province_code`/`district_code`, hoặc dùng tên quận/huyện cũ trước sáp nhập như `Quận 2` / `Quận 9` thay vì `TP. Thủ Đức`). Skill này đối chiếu địa chỉ khách hàng với danh mục chuẩn Haravan, đề xuất bản sửa chuẩn hóa (`dry_run: true`) và chỉ cập nhật sau khi được duyệt.

**Tiêu chí hoàn thành (Definition of Done):**
- Tải danh mục 63 Tỉnh/Thành chuẩn Việt Nam từ `GET /com/countries/{country_id}/provinces.json` và đối chiếu từng địa chỉ của tối đa `50` khách hàng.
- Tách bạch 2 loại lỗi: `AUTO_FIXABLE` (chuẩn hóa chính tả/mã cấp Tỉnh–Quận–Phường với độ tin cậy 100%) và `NEEDS_CSKH_CALL` (thiếu số nhà, thiếu phường/xã không suy đoán được).
- Sinh Backup JSON nguyên trạng + Preview Diff (che số nhà trong báo cáo tổng hợp), chờ xác nhận trước khi gọi `PUT`, và kiểm tra lại bằng `GET`.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_customers`, `com.write_customers`, `com.read_shop` |
| **Endpoints** | `GET /com/countries/{country_id}/provinces.json`, `GET /com/customers/{customer_id}/addresses.json`, `PUT /com/customers/{customer_id}/addresses/{address_id}.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=False)  # Chỉ False sau khi duyệt preview
provinces = client.get("/com/countries/241/provinces.json")["provinces"]  # 241 = Vietnam
addrs = client.get(f"/com/customers/{customer_id}/addresses.json")["addresses"]
client.put(f"/com/customers/{customer_id}/addresses/{address_id}.json", json_body=payload)
```

**JSON Request Payload (`PUT /com/customers/70122/addresses/9120441.json`):**
```json
{
  "address": {
    "id": 9120441,
    "address1": "123 Lê Lợi",
    "ward": "Phường Bến Nghé",
    "ward_code": "26740",
    "district": "Quận 1",
    "district_code": "HC466",
    "province": "Hồ Chí Minh",
    "province_code": "HC",
    "country_code": "VN"
  }
}
```

**JSON Response Payload (HTTP 200 OK):**
```json
{
  "customer_address": {
    "id": 9120441,
    "customer_id": 70122,
    "province": "Hồ Chí Minh",
    "province_code": "HC",
    "district": "Quận 1",
    "ward": "Phường Bến Nghé",
    "default": true
  }
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `customer_ids` | array[integer] | Yes | — | Danh sách `customer_id` cần rà soát; giới hạn cứng ≤ `50` khách/lần. |
| `country_id` | integer | No | `241` | Mã quốc gia Việt Nam trên Haravan (`VN`). |
| `only_default_address` | boolean | No | `true` | Chỉ kiểm tra địa chỉ mặc định (`default: true`) hay toàn bộ sổ địa chỉ. |
| `dry_run` | boolean | Yes | `true` | Mặc định `true`; bắt buộc tạo preview + backup trước khi ghi. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Từ điển ánh xạ chuẩn Việt Nam (Normalization Dictionary):**
   - Tỉnh/Thành viết tắt phổ biến: `{"TPHCM", "TP.HCM", "HCM", "Sai Gon", "Sài Gòn"} → "Hồ Chí Minh" (HC)`; `{"HN", "Ha Noi"} → "Hà Nội" (HI)`; `{"DN", "Da Nang"} → "Đà Nẵng" (DA)`.
   - Sáp nhập hành chính tiêu biểu: `Quận 2`, `Quận 9`, `Quận Thủ Đức` → `Thành phố Thủ Đức` (kiểm tra khớp mã danh mục hiện hành trên Haravan).
2. **Phân tách chuỗi địa chỉ bị dồn vào `address1`:**
   - Nếu `ward` hoặc `district` trống nhưng `address1` có cấu trúc `Số nhà Đường, P. Bến Nghé, Q.1, TPHCM`, dùng regex tách phần Phường/Quận/Tỉnh khớp chính xác với danh mục Haravan, giữ nguyên tuyệt đối phần số nhà/tên đường.
3. **Phân loại kết quả kiểm tra (3 Trạng thái):**
   - `VALID`: Đủ 3 cấp hành chính khớp mã Haravan và `address1` có thông tin cụ thể.
   - `AUTO_FIXABLE`: Có thể ánh xạ chính xác 1-1 sang mã Tỉnh/Quận/Phường của Haravan mà **không phải đoán**.
   - `NEEDS_CSKH_CALL`: Thiếu hẳn phường/xã không có trong `address1`, trùng tên xã ở nhiều huyện khác nhau, hoặc `address1` chỉ ghi "gần ủy ban / chợ".
4. **Backup & Apply:** Lưu toàn bộ JSON địa chỉ gốc vào `backup_<ts>.json` qua `scripts/dry_run_report.py`, hiển thị diff (đã ẩn số nhà trong bảng tóm tắt) và chỉ `PUT` các bản ghi `AUTO_FIXABLE` sau khi người dùng duyệt.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Bảng Preview Chuẩn hóa Địa chỉ (Dry-Run — 20 khách hàng):**
| Customer ID | Address ID | Địa giới trước (Redacted) | Địa giới đề xuất chuẩn hóa | Phân loại | Hành động |
| --- | --- | --- | --- | --- | --- |
| `70122` | `9120441` | `TPHCM / Q1 / (trống)` | `Hồ Chí Minh (HC) / Quận 1 / Phường Bến Nghé` | `AUTO_FIXABLE` | `PUT_ADDRESS` |
| `70145` | `9120810` | `HN / Cầu Giấy / Dịch Vọng` | `Hà Nội (HI) / Quận Cầu Giấy / Phường Dịch Vọng` | `AUTO_FIXABLE` | `PUT_ADDRESS` |
| `70199` | `9120999` | `Hồ Chí Minh / Bình Chánh / (trống)` | *(Không đủ dữ liệu suy ra xã)* | `NEEDS_CSKH_CALL` | `SKIP_FLAG_CSKH` |

```json
{
  "skill": "customer-address-correction-proposal",
  "mode": "dry_run",
  "summary": { "scanned": 20, "valid": 11, "auto_fixable": 6, "needs_cskh_call": 3 },
  "backup_artifact": "artifacts/customer-address-correction-proposal_20260410_backup.json",
  "proposals": [
    {
      "customer_id": 70122,
      "address_id": 9120441,
      "classification": "AUTO_FIXABLE",
      "before_admin_area": "TPHCM / Q1 / (empty)",
      "after_admin_area": "Hồ Chí Minh / Quận 1 / Phường Bến Nghé",
      "confidence": 1.0
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Không bao giờ suy đoán địa chỉ chi tiết:** Tuyệt đối không tự bịa số nhà, tên đường hoặc chọn đại 1 phường/xã khi khách ghi thiếu; những trường hợp đó bắt buộc gắn `NEEDS_CSKH_CALL`.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Trong báo cáo tổng hợp chỉ hiển thị cấp Tỉnh/Quận/Phường và `customer_id`, ẩn họ tên, SĐT và số nhà.
- **Rollback (`supported: true`):** Dùng `backup_<ts>.json` gọi lại `PUT /com/customers/{customer_id}/addresses/{address_id}.json` với payload gốc để khôi phục ngay nếu cần.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `com.write_customers` hoặc `com.read_shop` | Dừng, báo chính xác scope bị thiếu. |
| `404 Not Found` | `customer_id` hoặc `address_id` không tồn tại | Dừng theo `partial_failure_policy: stop`, kiểm tra lại ID. |
| `422 Unprocessable` | `province_code` hoặc `district_code` không khớp bảng mã Haravan | Đối chiếu lại mã từ `GET /com/countries/241/provinces.json` trước khi gửi. |
| `429 Too Many Requests` | Cập nhật liên tiếp 50 địa chỉ | Throttle tự động qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Cập nhật sổ địa chỉ khách hàng KHÔNG tự cập nhật địa chỉ của đơn hàng đã tạo trước đó:** `PUT /customers/{id}/addresses/{addr_id}.json` chỉ sửa hồ sơ khách cho các đơn tương lai; nếu cần sửa cho một đơn đang chờ giao, phải thông báo rõ để vận hành sửa `shipping_address` trên đơn hàng đó.
2. **Địa chỉ sáp nhập phường/xã theo Nghị quyết mới (2024–2025):** Một số phường cũ đã gộp tên nhưng danh mục NVC (GHN/GHTK) và Haravan có thể cập nhật lệch nhịp nhau vài tuần; luôn ưu tiên đúng `ward_code`/`district_code` trả về từ API Haravan hiện tại của cửa hàng.
3. **Khách hàng mua qua Harasocial để trống hoàn toàn tên đường, chỉ ghi tên tòa nhà/chung cư (vd: "Vinhomes Central Park, Bình Thạnh"):** Vẫn hợp lệ cho shipper nội thành, không nên gắn lỗi thiếu số nhà nếu có tên tòa nhà + đủ Phường/Quận.

## 8. Liên kết Workflow & Skill kế tiếp
- **Đầu vào:** Nhận danh sách khách dính cờ `INCOMPLETE_ADDRESS` từ `order-risk-cod-boom-signals`.
- **Sau khi chuẩn hóa:** Quay lại `fulfillment-bulk-create-critical` để đẩy vận đơn sạch lỗi sang NVC.
