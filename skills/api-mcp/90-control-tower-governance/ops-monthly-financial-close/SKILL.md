---
name: ops-monthly-financial-close
description: "Gói tổng hợp đóng sổ vận hành cuối tháng: doanh thu thuần đa kênh, hoàn hủy, chi phí khuyến mãi, đối soát COD, tồn kho và ước tính VAT."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 90-control-tower-governance
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: com
  scopes:
    - com.read_orders
    - com.read_inventories
    - com.read_discounts
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/orders.json"
    - "GET https://apis.haravan.com/com/inventory_locations.json"
    - "GET https://apis.haravan.com/com/promotions.json"
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

# Haravan Monthly Financial & Operations Close Pack

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Tự động tổng hợp **Gói Đóng Sổ Vận Hành Cuối Tháng (Monthly Close Pack)** phục vụ ban giám đốc và bộ phận kế toán đối chiếu cuối kỳ: Cầu nối doanh thu (Gross → Chiết khấu → Hủy/Hoàn → Doanh thu thuần ước tính), hiệu suất khuyến mãi, trạng thái đối soát COD treo tại ĐVVC, ảnh chụp tồn kho cuối kỳ (kèm hàng tồn chậm > 90 ngày) và bảng ước tính VAT / danh sách đơn yêu cầu xuất hóa đơn điện tử (e-Invoice).
- **Ngữ cảnh Haravan:** Vào ngày 01–05 đầu tháng mới, đội vận hành và kế toán thường mất 2–3 ngày để ghép số liệu giữa đơn hàng Haravan (`/com/orders.json`), chương trình khuyến mãi (`/com/promotions.json`) và tồn kho đa kho (`/com/inventory_locations.json`). Đặc biệt với đơn giao cuối tháng (đặt ngày 29–30 nhưng sang tháng sau khách mới nhận hàng và NVC mới đối soát COD), việc tách rõ *Đã thanh toán (`paid`)* vs *COD đang luân chuyển (`pending`)* là bắt buộc để tránh lệch dòng tiền.
- **Definition of Done (DoD):**
  1. Quét toàn bộ đơn hàng của tháng `month` (`YYYY-MM`, từ `01 00:00:00+07:00` đến ngày cuối tháng `23:59:59+07:00`), tồn kho cuối kỳ và khuyến mãi đang dùng trong tháng.
  2. Lập đầy đủ 4 bảng chuẩn: (1) Cầu nối Doanh thu theo kênh & MoM, (2) Tình trạng đối soát COD cuối tháng, (3) Ảnh chụp Tồn kho & Deadstock > 90 ngày, (4) Ước tính VAT & danh sách đơn có yêu cầu xuất hóa đơn VAT.
  3. Đính kèm **Financial Disclaimer** bắt buộc và che toàn bộ PII cá nhân.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) |
| **Scopes tối thiểu** | `com.read_orders`, `com.read_inventories`, `com.read_discounts`, `com.read_products` |
| **Endpoints** | `GET /com/orders.json`, `GET /com/inventory_locations.json`, `GET /com/promotions.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
orders = client.paginate(
    surface="com",
    path="/orders.json",
    resource_key="orders",
    params={
        "created_at_min": "2026-11-01T00:00:00+07:00",
        "created_at_max": "2026-11-30T23:59:59+07:00",
        "status": "any",
    },
    limit=50,
    max_pages=100,
)
inv_locs = client.paginate("com", "/inventory_locations.json", "inventory_locations", limit=50, max_pages=60)
promos = client.paginate("com", "/promotions.json", "promotions", limit=50, max_pages=10)
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `month` | `string` | Bắt buộc | Tháng trước (`YYYY-MM`) | Định dạng chuẩn `YYYY-MM` (ví dụ `2026-11`). |
| `vat_rate_pct` | `number` | Không | `8` | Thuế suất GTGT ước tính (`8` hoặc `10` tùy ngành hàng theo Nghị định thuế hiện hành tại VN). |
| `compare_prev_month` | `boolean` | Không | `true` | Tính tăng trưởng MoM (Month-over-Month) so với tháng liền trước. |
| `deadstock_days` | `integer` | Không | `90` | Ngưỡng số ngày không phát sinh bán ra để xếp vào nhóm hàng tồn chậm. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Cầu nối Doanh thu (Revenue Waterfall — Operational Estimate):**
   $$\text{Gross Merchandise Value (GMV)} = \sum \text{subtotal\_price} + \sum \text{total\_discounts}$$
   $$\text{Net Sales (Est.)} = \text{GMV} - \text{Total Discounts} - \text{Cancelled Value} - \text{Refunded Value}$$
   $$\text{Discount Rate} = \frac{\text{Total Discounts}}{\text{GMV}} \times 100\%, \quad \text{MoM \%} = \frac{\text{Net}_{\text{this}} - \text{Net}_{\text{prev}}}{\text{Net}_{\text{prev}}} \times 100\%$$
2. **Phân rã Trạng thái Đối soát COD Cuối Tháng:**
   - **Đã thu tiền (`paid`):** Tổng giá trị đơn đã chuyển sang `financial_status == "paid"`.
   - **COD đang treo tại NVC (`in_transit_cod`):** Đơn COD đã `fulfilled`, chưa hủy, `financial_status == "pending"`.
   - **COD quá hạn đối soát (> 10 ngày):** Đơn đã giao thành công quá 10 ngày nhưng vẫn `pending` -> gắn cờ yêu cầu kế toán đối chiếu bảng kê GHTK/GHN/SPX/ViettelPost.
3. **Chụp mốc Tồn kho Cuối kỳ (Inventory Snapshot):**
   - Tính tổng `qty_onhand`, `qty_available`, `qty_committed` theo từng kho (`location_id`) và tổng giá trị ước tính theo giá bán lẻ (hoặc giá vốn nếu có trường `cost_price`).
   - Liệt kê nhóm SKU có `qty_available > 0` nhưng không có bất kỳ lượt bán nào trong `deadstock_days` ngày qua.
4. **Ước tính VAT & Hóa đơn Điện tử (e-Invoice):**
   - Với giá bán đã bao gồm VAT trên Haravan:
     $$\text{Doanh thu trước thuế (Est.)} = \frac{\text{Net Sales (Est.)}}{1 + \text{vat\_rate\_pct}/100}, \quad \text{VAT ước tính} = \text{Net Sales (Est.)} - \text{Doanh thu trước thuế}$$
   - Quét `note` và `tags` của đơn hàng chứa từ khóa `VAT`, `xuat hoa don`, `MST` để liệt kê danh sách `order_number` cần kế toán kiểm tra xuất e-Invoice.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### GÓI ĐÓNG SỔ VẬN HÀNH THÁNG 11/2026 (Monthly Close Pack)
> **Financial Disclaimer:** Báo cáo này là *Operational Estimate / Reconciliation Aid* tổng hợp từ Haravan API, **không thay thế** sổ cái kế toán, tờ khai thuế GTGT chính thức hay biên bản đối soát chứng từ gốc với ĐVVC/Cổng thanh toán.

#### 1. Cầu nối Doanh thu Tháng 11/2026 (So sánh MoM)
| Chỉ tiêu | Tháng 11/2026 (VND) | Tháng 10/2026 (VND) | MoM |
| --- | ---: | ---: | ---: |
| Tổng giá trị đơn gộp (GMV) | 1,620,000,000 | 1,410,000,000 | +14.9% |
| (-) Chiết khấu & Khuyến mãi | -145,800,000 (9.0%) | -112,800,000 (8.0%) | +29.3% |
| (-) Đơn hủy & Hoàn trả | -98,200,000 (6.1%) | -89,000,000 (6.3%) | +10.3% |
| **(=) Doanh thu thuần ước tính** | **1,376,000,000** | **1,208,200,000** | **+13.9%** |
| Ước tính VAT đầu ra (8%) | ~101,925,926 | ~89,496,296 | +13.9% |

#### 2. Đối soát COD, Tồn kho & Hóa đơn VAT
- **COD đã hoàn tất (`paid`):** 912,400,000 VND | **COD đang treo tại NVC:** 118,500,000 VND (có **14 đơn > 10 ngày** cần đối chiếu bảng kê NVC)
- **Tồn kho cuối kỳ (30/11):** 12,480 đơn vị tại 2 kho | **Tồn chậm > 90 ngày:** 42 SKU (1,120 đơn vị)
- **Đơn yêu cầu xuất e-Invoice (VAT):** 37 đơn (đã liệt kê `order_number` kèm trạng thái thanh toán trong file JSON)
```

```json
{
  "skill": "ops-monthly-financial-close",
  "month": "2026-11",
  "disclaimer": "Operational Estimate / Reconciliation Aid only; not an audited accounting ledger.",
  "revenue_waterfall_vnd": { "gmv": 1620000000, "discounts": 145800000, "cancellations_refunds": 98200000, "net_sales_est": 1376000000, "vat_est_8pct": 101925926 },
  "cod_reconciliation": { "paid_vnd": 912400000, "in_transit_vnd": 118500000, "overdue_over_10d_orders": 14 },
  "inventory_snapshot": { "total_units_onhand": 12480, "deadstock_90d_skus": 42 },
  "einvoice_requested_order_count": 37
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ gọi `GET`. Không tự đóng đơn, không tự xác nhận thanh toán hay điều chỉnh số liệu kế toán.
- **Financial Disclaimer bắt buộc:** Mọi báo cáo đầu ra đều phải có tuyên bố miễn trừ trách nhiệm tài chính/thuế theo `AGENTS.md`.
- **Bảo vệ PII (`pii_level: financial`):** Không xuất danh sách tên/SĐT/email cá nhân hoặc MST thô vào báo cáo Markdown chung (`export_allowed: false`).

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng đóng sổ, báo làm mới `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu 1 trong 4 scope đọc (`orders`/`inventories`/`discounts`/`products`) | Báo chính xác scope thiếu để không xuất báo cáo khuyết dữ liệu. |
| `404 Not Found` | Endpoint sai | Kiểm tra surface `com`. |
| `422 Unprocessable` | Tham số `month` sai định dạng (ví dụ `11-2026`) | Bắt buộc định dạng `YYYY-MM`. |
| `429 Too Many Requests` | Tháng cao điểm có > 3.000 đơn cần nhiều trang `paginate` | Dùng `HaravanClient` (2.5 req/s + backoff); chia nhỏ truy vấn theo từng tuần trong tháng nếu cần. |

- **Edge Case 1 — Tổng số đơn trong tháng vượt `max_records: 5000`:** Không được âm thầm cắt dữ liệu làm sai lệch tổng doanh thu! Phải chia nhỏ khoảng truy vấn thành 4 tuần (tuần 1..4) hoặc cảnh báo rõ `INCOMPLETE_DATASET_TRUNCATED` để kế toán biết.
- **Edge Case 2 — Đơn hàng giao cắt tháng (Đặt 30/11, hủy/hoàn ngày 02/12):** Ghi chú rõ nguyên tắc ghi nhận theo `created_at` (ngày phát sinh đơn) vs `updated_at`/`cancelled_at` để khớp quy ước đối chiếu với kế toán.
- **Edge Case 3 — Đơn sàn TMĐT có trợ giá sàn & phí sàn:** Doanh thu trên Haravan thường chưa trừ phí hoa hồng/phí thanh toán của Shopee/TikTok Shop; bắt buộc ghi chú nhắc kế toán trừ thêm chi phí sàn từ sao kê Seller Center.

## 8. Liên kết Workflow & Skill kế tiếp

- **Đối soát chi tiết chênh lệch COD theo từng đơn vị vận chuyển:** Chuyển sang `finance-cod-reconciliation` (L1).
- **Rà soát các chương trình khuyến mãi gây tăng tỷ lệ Discount Rate:** Chạy `marketing-promotion-hygiene-audit` (L1).
- **Lập kế hoạch xả hàng tồn chậm > 90 ngày:** Chuyển sang `inventory-aging-deadstock-audit` (L1) và `marketing-promo-code-proposal` (L2).
