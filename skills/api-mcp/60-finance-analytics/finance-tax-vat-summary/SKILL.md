---
name: finance-tax-vat-summary
description: "Tổng hợp ước tính doanh thu chịu thuế GTGT (VAT) và danh sách đơn có yêu cầu xuất hóa đơn điện tử để bàn giao kế toán."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 60-finance-analytics
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
  idempotency_required: false
  partial_failure_policy: stop
privacy:
  pii_level: financial
  redact_output: true
  export_allowed: false
rollback:
  supported: false
  backup_required: false
---

# Haravan Vietnam VAT / E-Invoice Operational Summary

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)
Cuối mỗi tháng hoặc quý, kế toán doanh nghiệp Việt Nam vận hành Haravan phải đối chiếu tổng doanh thu hoàn thành để chuẩn bị kê khai thuế GTGT (VAT 8% / 10% theo chính sách giảm thuế GTGT hiện hành và Nghị định 123/2020/NĐ-CP) đồng thời rà soát **toàn bộ các đơn hàng khách có yêu cầu xuất Hóa đơn điện tử (HĐĐT)** trên MISA meInvoice, VNPT Invoice hoặc Viettel S-Invoice để tránh bỏ sót hoặc xuất trễ thời điểm lập hóa đơn. Skill này tự động tổng hợp bảng ước tính doanh thu chịu thuế và lọc danh sách đơn yêu cầu HĐĐT kèm kiểm tra độ đầy đủ thông tin (MST, Tên công ty, Email nhận HĐĐT).

**Tiêu chí hoàn thành (Definition of Done):**
- Lọc toàn bộ đơn hoàn thành / đã thanh toán trong `month` (`YYYY-MM`, chuẩn múi giờ `Asia/Ho_Chi_Minh`, loại trừ đơn hủy/hoàn toàn phần).
- Tách bạch 2 cấu phần: (1) Tổng hợp ước tính doanh thu trước thuế, thuế GTGT ghi nhận (`total_tax`) và ước tính quy đổi VAT theo cấu hình giá đã gồm thuế (`taxes_included`), và (2) Danh sách đơn có yêu cầu xuất HĐĐT kèm trạng thái kiểm tra Mã số thuế (10 hoặc 13 chữ số).
- Đính kèm **Cảnh báo pháp lý & Financial Disclaimer bắt buộc** (tuyệt đối không thay thế tờ khai thuế chính thức).

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com/`) |
| **Scopes tối thiểu** | `com.read_orders` |
| **Endpoints** | `GET /com/orders.json` (filter `status=any`, `created_at_min`, `created_at_max`, `limit=50`) |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient
client = HaravanClient(dry_run=True)
orders = client.paginate(
    "/com/orders.json",
    params={"status": "any", "created_at_min": "2026-03-01T00:00:00+07:00", "created_at_max": "2026-03-31T23:59:59+07:00", "limit": 50},
    data_key="orders",
    max_records=5000,
)
```

**JSON Response trích xuất thông tin thuế & yêu cầu HĐĐT (`GET /com/orders.json`):**
```json
{
  "orders": [
    {
      "id": 1482065110,
      "name": "#109142",
      "created_at": "2026-03-18T03:45:00Z",
      "financial_status": "paid",
      "taxes_included": true,
      "subtotal_price": 4320000.0,
      "total_discounts": 200000.0,
      "total_tax": 320000.0,
      "total_price": 4320000.0,
      "tags": "xuat-vat, don-si",
      "note": "Xuất HĐĐT Công ty TNHH Minh An - MST: 0312345678 - Email: ketoan@minhan.vn",
      "note_attributes": [
        { "name": "company_tax_code", "value": "0312345678" },
        { "name": "company_name", "value": "Công ty TNHH Minh An" }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `month` | string | Yes | — | Tháng báo cáo theo định dạng `YYYY-MM` (múi giờ `Asia/Ho_Chi_Minh`). |
| `vat_invoice_tag` | string | No | `"xuat-vat"` | Tag nhận diện đơn yêu cầu xuất hóa đơn điện tử. |
| `vat_note_keywords` | array[string] | No | `["hóa đơn","hoa don","mst","mã số thuế","vat","hdgtgt"]` | Từ khóa quét bổ sung trong `order.note` và `note_attributes` để không sót đơn quên gắn tag. |
| `default_vat_rate_pct` | number | No | `8.0` | Thuế suất ước tính tham khảo (8% hoặc 10% tùy nhóm ngành hàng) khi shop chưa bật cấu hình tính thuế tự động trên Haravan (`total_tax = 0`). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết
1. **Lọc đơn trong kỳ báo cáo:** Lấy đơn trong `[YYYY-MM-01T00:00:00+07:00, YYYY-MM-DDT23:59:59+07:00]`, loại bỏ `cancelled_at != null` và `financial_status == "refunded"`. Tách riêng 2 nhóm: `PAID_COMPLETED` (đã thu tiền) và `DELIVERED_COD_PENDING` (đã giao hàng nhưng COD chưa bấm xác nhận `paid` — vẫn phải ghi nhận doanh thu xuất hóa đơn theo thời điểm chuyển giao quyền sở hữu hàng hóa!).
2. **Công thức Ước tính Doanh thu & Thuế GTGT:**
   - Nếu `taxes_included == true` (mặc định đa số shop bán lẻ VN — giá niêm yết đã gồm VAT):
     - Trường hợp Haravan có cấu hình thuế (`total_tax > 0`): dùng trực tiếp `total_tax` và $\text{PreTaxRev} = \text{NetTotal} - \text{total\_tax}$.
     - Trường hợp shop chưa bật cấu hình thuế trên Haravan (`total_tax == 0`): ước tính tham khảo theo `default_vat_rate_pct` ($r$):
       $$\text{EstPreTaxRev} = \frac{\text{NetTotal}}{1 + r/100}, \quad \text{EstVAT} = \text{NetTotal} - \text{EstPreTaxRev}$$
3. **Rà soát Đơn Yêu cầu Xuất HĐĐT:**
   - Quét cả `tags`, `note`, và `note_attributes`.
   - Trích xuất MST bằng regex `\b\d{10}(-\d{3})?\b`. Gắn cờ `READY_FOR_EINVOICE` (đủ MST + Tên đơn vị), `MISSING_TAX_INFO` (có yêu cầu nhưng thiếu MST/email → CSKH cần hỏi bổ sung ngay).

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

**Bảng Tổng hợp Ước tính Doanh thu & Thuế GTGT — Tháng `2026-03` (Múi giờ `UTC+7`):**
| Nhóm đơn hàng | Số đơn | Tổng tiền hàng thuần (VND) | Phí ship thu khách | Thuế GTGT Haravan (`total_tax`) | Ước tính VAT quy đổi (8%) |
| --- | --- | --- | --- | --- | --- |
| Đã thanh toán (`paid`) | 1.480 | 892.000.000 | 18.400.000 | 42.100.000 | 66.074.000 |
| Đã giao — COD chưa đối soát (`delivered/pending`) | 112 | 76.500.000 | 2.100.000 | 3.200.000 | 5.667.000 |
| **Tổng cộng kỳ `2026-03`** | **1.592** | **968.500.000** | **20.500.000** | **45.300.000** | **71.741.000** |

**Danh sách Đơn yêu cầu Xuất Hóa đơn Điện tử (18 đơn — 15 Đủ thông tin, 3 Thiếu MST/Email):**
| Mã đơn | Ngày đặt | Tổng tiền (VND) | MST trích xuất | Email nhận HĐĐT (Redacted) | Trạng thái hồ sơ HĐĐT |
| --- | --- | --- | --- | --- | --- |
| `#109142` | 18/03/2026 | 4.320.000 | `0312345678` | `ke***@minhan.vn` | `READY_FOR_EINVOICE` |
| `#109168` | 24/03/2026 | 2.850.000 | *(Không tìm thấy)* | *(Trống)* | `MISSING_TAX_INFO` (CSKH gọi hỏi) |

```json
{
  "skill": "finance-tax-vat-summary",
  "legal_disclaimer": "CẢNH BÁO PHÁP LÝ: Đây là Operational Estimate / Reconciliation Aid, TUYỆT ĐỐI KHÔNG dùng làm tờ khai thuế GTGT chính thức. Kế toán phải đối chiếu sổ cái, hóa đơn điện tử thực xuất và quy định thuế suất từng mặt hàng (8% vs 10% vs không chịu thuế).",
  "month": "2026-03",
  "timezone": "Asia/Ho_Chi_Minh",
  "summary": {
    "eligible_orders": 1592,
    "net_merchandise_vnd": 968500000,
    "shipping_collected_vnd": 20500000,
    "haravan_recorded_tax_vnd": 45300000,
    "estimated_vat_at_default_rate_vnd": 71741000
  },
  "einvoice_requests": [
    { "order_id": 1482065110, "order_name": "#109142", "total_price_vnd": 4320000, "tax_code": "0312345678", "status": "READY_FOR_EINVOICE" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback
- **Cảnh báo Pháp lý & Financial Disclaimer Bắt buộc:**
  > *⚠️ Cảnh báo pháp lý: Báo cáo này là **Operational Estimate / Reconciliation Aid**, tuyệt đối không dùng làm tờ khai thuế GTGT chính thức. Kế toán phải đối chiếu thuế suất chính xác theo mã HS/nhóm ngành hàng (0%, 5%, 8%, 10%), chứng từ ngân hàng và dữ liệu thực xuất trên phần mềm HĐĐT (MISA, VNPT, Viettel S-Invoice).*
- **Chế độ Read-Only (L1):** Chỉ đọc đơn hàng; không tự phát hành HĐĐT và không xuất dữ liệu cá nhân thô của khách lẻ (`export_allowed: false`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Hành động xử lý chuẩn |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_orders` | Dừng, báo thiếu quyền đọc đơn hàng. |
| `404 Not Found` | Endpoint sai | Kiểm tra base URL `/com/orders.json`. |
| `422 Unprocessable` | Tham số `month` không đúng định dạng `YYYY-MM` | Báo lỗi định dạng và yêu cầu nhập lại (vd `2026-03`). |
| `429 Too Many Requests` | Tháng cao điểm có > 5.000 đơn | Tự động chia nhỏ theo từng tuần trong tháng và backoff qua `hrv_client.py`. |

**Tình huống biên thực tế tại Việt Nam:**
1. **Cửa hàng bán hỗn hợp mặt hàng VAT 8% và 10% (hoặc không chịu thuế):** Một số nhóm hàng (rượu bia, viễn thông, tài chính, kim loại...) không thuộc diện giảm thuế 8%. Nếu shop không cấu hình thuế theo từng sản phẩm trên Haravan (`total_tax = 0`), phép quy đổi bằng 1 mức `default_vat_rate_pct` chỉ là ước tính tham khảo — báo cáo phải cảnh báo rõ điều này.
2. **Đơn giao thành công cuối tháng nhưng tiền COD về đầu tháng sau:** Theo Nghị định 123/2020/NĐ-CP, thời điểm lập HĐĐT bán hàng là thời điểm chuyển giao quyền sở hữu/sử dụng hàng hóa, **không phân biệt đã thu tiền hay chưa**. Do đó bắt buộc đưa cả nhóm `DELIVERED_COD_PENDING` vào bảng tổng hợp tháng.
3. **Khách lẻ không lấy hóa đơn (B2C):** Theo quy định HĐĐT hiện hành, cuối kỳ kế toán vẫn phải xuất hóa đơn cho khách lẻ không lấy hóa đơn (hoặc xuất theo từng lần bán hàng từ máy tính tiền POS); phần `net_merchandise_vnd` trừ đi các đơn `einvoice_requests` giúp kế toán đối chiếu nhanh phần doanh thu khách lẻ.

## 8. Liên kết Workflow & Skill kế tiếp
- **Tự động gắn tag `xuat-vat` hàng ngày để không sót đơn cuối tháng:** Chạy `order-triage-tagging-proposal`.
- **Đối chiếu tiền thực nhận COD cho nhóm `DELIVERED_COD_PENDING`:** Chạy `finance-cod-reconciliation`.
- **Xem phân bổ doanh thu theo từng kênh Omni:** Chạy `finance-sales-by-channel-omni`.
