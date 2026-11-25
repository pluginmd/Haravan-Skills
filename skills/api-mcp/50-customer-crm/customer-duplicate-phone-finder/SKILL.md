---
name: customer-duplicate-phone-finder
description: "Chuẩn hóa đầu số điện thoại Việt Nam (+84 / 84 / 0) để phát hiện hồ sơ khách hàng bị trùng giữa Website, Harasocial và POS."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 50-customer-crm
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_customers
  endpoints:
    - "GET https://apis.haravan.com/com/customers.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---

# Haravan Duplicate Customer Finder (Vietnam Phone-First)

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Trong hệ sinh thái Haravan Omnichannel tại Việt Nam, cùng một khách hàng rất dễ bị tách thành 2–4 hồ sơ khác nhau: mua trên Website nhập `0901234567`, chốt đơn trên Harasocial lưu `+84901234567`, mua tại cửa hàng POS nhân viên gõ `0901 234 567` không có email, hoặc còn tồn tại đầu số cũ 11 số (`016x`, `012x`). Hệ quả là điểm tích lũy **Haraloyalty** bị phân mảnh và báo cáo RFM/Cohort bị sai lệch. Skill này quét, chuẩn hóa SĐT chuẩn Việt Nam và chỉ mặt từng cụm hồ sơ trùng kèm đề xuất **Hồ sơ chính (Primary)** để đội CRM rà soát gộp thủ công.

**Tiêu chí hoàn thành (Definition of Done):**
- Quét tối đa `5.000` hồ sơ khách hàng từ `GET /com/customers.json` và chuẩn hóa toàn bộ SĐT (kể cả `phone` ở gốc và `default_address.phone`).
- Gom nhóm chính xác mọi cụm trùng theo **SĐT chuẩn hóa (`0xxxxxxxxx`)** và tùy chọn theo **Email hợp lệ** (loại trừ email giả/hệ thống).
- Chấm điểm đề xuất `primary_customer_id` (ưu tiên nhiều đơn thành công hơn, tổng chi tiêu cao hơn, có gắn tag Haraloyalty) và che PII (`090****567`, `ng***@gmail.com`).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_customers` |
| **Endpoints** | `GET /com/customers.json` (`limit=50`, `page=1..N`) |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
customers = client.paginate(
    "/com/customers.json",
    params={"limit": 50},
    data_key="customers",
    max_records=5000,
)
```

**JSON Response trích xuất từ `GET /com/customers.json`:**
```json
{
  "customers": [
    {
      "id": 70122,
      "phone": "0901234567",
      "email": "nguyen.an@gmail.com",
      "orders_count": 6,
      "total_spent": 4850000.0,
      "tags": "VIP, haraloyalty-gold",
      "default_address": { "phone": "0901234567", "province": "Hồ Chí Minh" }
    },
    {
      "id": 78941,
      "phone": "+84 901 234 567",
      "email": null,
      "orders_count": 1,
      "total_spent": 420000.0,
      "tags": "harasocial",
      "default_address": { "phone": "84901234567", "province": "Hồ Chí Minh" }
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `max_customers` | integer | No | `5000` | Giới hạn số hồ sơ khách hàng quét (`100`–`5000`). |
| `match_by_email` | boolean | No | `true` | Quét thêm cụm trùng theo Email sau khi chuẩn hóa lowercase (loại email trống/hệ thống). |
| `convert_legacy_11digit` | boolean | No | `true` | Tự động chuyển đầu số 11 số cũ VN sang 10 số (vd `0168→038`, `0120→070`, `0123→083`) theo quy định Bộ TT&TT. |
| `min_cluster_size` | integer | No | `2` | Số hồ sơ tối thiểu trong một cụm để báo cáo trùng lặp. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Hàm chuẩn hóa Số điện thoại Việt Nam (`normalize_vn_phone`):**
   - Bước 1: Loại bỏ mọi ký tự không phải số (`\D`).
   - Bước 2: Nếu bắt đầu bằng `0084` → thay bằng `0`; nếu bắt đầu bằng `84` và độ dài $\ge 10$ → thay `84` bằng `0`.
   - Bước 3 (nếu `convert_legacy_11digit=true`): Chuyển đổi bảng mã 11 số sang 10 số (`0162–0169 → 032–039`, `0120/0121/0122/0126/0128 → 070/079/077/076/078`, `0123/0124/0125/0127/0129 → 083/084/085/081/082`, `0186/0188 → 056/058`, `0199 → 059`).
   - Bước 4: Chỉ coi là SĐT di động VN hợp lệ khi dài đúng `10` chữ số và thuộc đầu số `03|05|07|08|09`.
2. **Thuật toán Gom cụm (Clustering):**
   - Trích xuất SĐT từ `customer.phone` (nếu rỗng thì fallback `default_address.phone`).
   - Gom tất cả `customer_id` có cùng `normalized_phone` vào 1 cụm. Nếu `match_by_email=true`, gom thêm các hồ sơ trùng email hợp lệ (bỏ qua các email placeholder như `noemail@`, `pos@`, `guest@`).
3. **Chọn Hồ sơ Chính (Primary Record Scoring):**
   - Xếp hạng trong từng cụm theo thứ tự ưu tiên: `(1) Có tag Haraloyalty / Hạng thành viên` > `(2) orders_count cao nhất` > `(3) total_spent cao nhất` > `(4) Có email hợp lệ` > `(5) id nhỏ hơn (tạo sớm hơn)`.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Tổng hợp Cụm Hồ sơ Khách hàng Trùng lặp (Quét 4.280 hồ sơ — Phát hiện 68 cụm / 147 hồ sơ):**
| Cụm | Khóa trùng (Redacted) | Hồ sơ Chính (`Primary`) | Hồ sơ Phụ (`Duplicate`) | Tổng đơn gộp | Tổng chi tiêu gộp (VND) | Lưu ý CRM |
| --- | --- | --- | --- | --- | --- | --- |
| `#01` | SĐT `090****567` | `70122` (6 đơn, 4.850.000đ) | `78941` (1 đơn, 420.000đ) | 7 | 5.270.000 | Giữ `70122` (có Haraloyalty) |
| `#02` | SĐT `038****219` | `71405` (4 đơn, 3.100.000đ) | `62011` (`0168****219`, 2 đơn) | 6 | 4.350.000 | Đầu số cũ 11 số → 10 số |
| `#03` | Email `th***@gmail.com` | `73210` (3 đơn, 2.400.000đ) | `79102` (0 đơn, SĐT khác) | 3 | 2.400.000 | Kiểm tra lại SĐT trước khi gộp |

```json
{
  "skill": "customer-duplicate-phone-finder",
  "scanned_customers": 4280,
  "duplicate_clusters_count": 68,
  "affected_customer_records": 147,
  "clusters": [
    {
      "cluster_id": 1,
      "match_type": "phone_normalized",
      "match_key_redacted": "090****567",
      "primary_customer_id": 70122,
      "duplicate_customer_ids": [78941],
      "combined_orders_count": 7,
      "combined_total_spent_vnd": 5270000,
      "loyalty_conflict_warning": false
    }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Chế độ Read-Only (L1):** Tuyệt đối **không tự động xóa hoặc gộp hồ sơ khách hàng** qua API, vì thao tác merge không thể đảo ngược và có thể làm mất lịch sử tích điểm Haraloyalty hoặc mã hóa đơn đã liên kết.
- **Bảo vệ PII (`pii_level: customer`, `redact_output: true`, `export_allowed: false`):** Che toàn bộ SĐT (`090****567`), email (`th***@gmail.com`) và không in họ tên khách hàng trong báo cáo.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_customers` | Dừng, báo thiếu quyền đọc khách hàng. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `/com/customers.json`. |
| `422 Unprocessable` | Tham số `page`/`limit` vượt giới hạn | Giới hạn `limit <= 50` theo chuẩn Haravan. |
| `429 Too Many Requests` | Quét 100 trang khách hàng liên tiếp | `hrv_client.py` tự throttle ≤ 4 req/s và backoff khi gặp 429. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Số điện thoại dùng chung của nhân viên sale / cộng tác viên đặt hộ (Dropship/CTV):** Một SĐT trùng tới 15–30 hồ sơ tên khác nhau không phải khách trùng mà là CTV/Sale nhập SĐT cá nhân khi tạo đơn hộ. Gắn cờ `POSSIBLE_STAFF_OR_CTV` cho cụm có kích thước $\ge 5$ hồ sơ.
2. **SĐT rỗng hoặc số giả lập (`0000000000`, `0999999999`, `1234567890`):** Thu ngân POS thường nhập số mặc định cho khách không muốn cung cấp SĐT; phải loại bỏ danh sách số rác (denylist) trước khi gom cụm để tránh gom nhầm hàng trăm khách vãng lai vào 1 cụm.
3. **Khách có cả 2 hồ sơ đều đang tích điểm Haraloyalty:** Gắn cờ `loyalty_conflict_warning: true` để nhân viên CRM kiểm tra cộng bù điểm thủ công trước khi vô hiệu hóa hồ sơ phụ.

## 8. Liên kết Workflow & Skill kế tiếp
- **Gắn tag đánh dấu hồ sơ phụ chờ xử lý:** Chuyển `duplicate_customer_ids` sang `customer-tag-note-proposal` (vd tag `dup-review`).
- **Chạy phân tích sạch sau khi nhận diện trùng:** Chạy `customer-rfm-segmentation` và `customer-cohort-retention`.
