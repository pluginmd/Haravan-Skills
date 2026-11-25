---
name: marketing-ads-feed-google-tiktok-audit
description: "Kiểm toán chất lượng Product Feed đồng bộ sang Google Ads (/admin/googleshop) và TikTok Ads (/admin/marketings/tiktok_ads/products) để tránh bị từ chối sản phẩm."
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
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/com/products.json"
    - "UI /admin/googleshop"
    - "UI /admin/marketings/tiktok_ads/products"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 5000
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

# Haravan Google Shopping & TikTok Ads Product Feed Audit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Kiểm toán toàn bộ danh mục sản phẩm đang bật bán trên Haravan trước khi đồng bộ sang Google Merchant Center (GMC qua `/admin/googleshop`) và TikTok Ads Catalog (`/admin/marketings/tiktok_ads/products`), phát hiện sớm lỗi khiến sản phẩm bị từ chối (Disapproved) hoặc nguy cơ đình chỉ tài khoản (GMC Misrepresentation).
- **Ngữ cảnh Haravan:** Haravan tự động sinh feed từ trường `title`, `body_html`, `images`, `variants[].price`, `variants[].barcode`, `product_type`, `vendor`. Chỉ một tỷ lệ nhỏ SKU có giá = `0`, ảnh nhỏ hơn `800x800px`, tiêu đề viết HOA toàn bộ hoặc chứa chữ khuyến mãi (`FREESHIP`, `GIẢM 50%`) có thể làm giảm điểm chất lượng feed và tăng CPC quảng cáo Shopping/PMax/GMV Max.
- **Definition of Done (DoD):**
  1. Quét đầy đủ tối đa `max_records` (≤ 5.000) sản phẩm qua `GET /com/products.json` có phân trang an toàn.
  2. Chấm điểm Feed Health Score (0–100) riêng cho Google Shopping và TikTok Catalog theo bộ quy tắc chuẩn.
  3. Phân loại lỗi thành `P0` (nguy cơ khóa GMC/TikTok), `P1` (Disapproved item), `P2` (giảm hiệu suất hiển thị) kèm danh sách `product_id` / `variant_id` cần sửa.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `com` (`https://apis.haravan.com/com`) + đối chiếu UI Admin |
| **Scopes tối thiểu** | `com.read_products` |
| **Endpoints** | `GET /com/products.json`, `UI /admin/googleshop`, `UI /admin/marketings/tiktok_ads/products` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
products = client.paginate(
    surface="com",
    path="/products.json",
    resource_key="products",
    params={"published_status": "published"},
    limit=50,
    max_pages=100,
)
```

**Ví dụ JSON Response thực tế từ `GET /com/products.json?limit=1`:**
```json
{
  "products": [
    {
      "id": 1054218901,
      "title": "ÁO POLO NAM COTTON PIQUE FORM SLIM - SALE SỐC 50%",
      "handle": "ao-polo-nam-cotton-pique",
      "body_html": "<p>Chất liệu cotton 100% thấm hút mồ hôi.</p>",
      "vendor": "LocalBrandVN",
      "product_type": "Áo Polo Nam",
      "published_scope": "global",
      "images": [{ "id": 99012, "src": "https://product.hstatic.net/1000123456/product/polo_small.jpg" }],
      "variants": [
        { "id": 1120334455, "sku": "POLO-BLK-L", "price": "299000", "barcode": "", "inventory_quantity": 18 }
      ]
    }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `channels` | `string` | Không | `both` | Enum: `google_shopping`, `tiktok_ads`, `both`. Chọn bộ quy tắc kiểm toán áp dụng. |
| `published_only` | `boolean` | Không | `true` | Chỉ quét sản phẩm đang hiển thị trên Online Store (`published_status=published`). |
| `min_image_px` | `integer` | Không | `800` | Ngưỡng kích thước ảnh tối thiểu (px). GMC thời trang yêu cầu ≥ 250px, khuyến nghị ≥ 800x800px cho Zoom/TikTok. |
| `max_products` | `integer` | Không | `2000` | Phạm vi `1..5000` (khớp `max_records: 5000`). |
| `require_gtin` | `boolean` | Không | `false` | Bật `true` nếu bán hàng chính hãng có mã vạch EAN-13/UPC (bắt buộc `barcode` hợp lệ). |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Tải danh mục sản phẩm:** Gọi `client.paginate("com", "/products.json", "products", ...)` lấy toàn bộ sản phẩm đang publish.
2. **Kiểm tra bộ quy tắc GMC & TikTok Catalog trên từng SKU:**
   - **P0 (Nguy cơ đình chỉ tài khoản):** `price <= 0` hoặc `price == null`; đường dẫn ảnh lỗi `http://` hoặc không có ảnh (`images == []`); từ khóa bị cấm chính sách (y tế phóng đại, vũ khí, hàng giả/nhái thương hiệu).
   - **P1 (Bị từ chối từng sản phẩm - Disapproved):**
     - `title` dài > `150` ký tự (GMC) hoặc > `255` ký tự (TikTok); hoặc tỷ lệ chữ IN HOA > `60%` (trừ mã SKU/brand); hoặc chứa văn bản quảng cáo (`SALE`, `FREESHIP`, `GIẢM GIÁ`, `HOT`, `!!!`).
     - `body_html` sau khi lọc thẻ HTML có độ dài < `30` ký tự hoặc chứa mã script/style rác.
     - Toàn bộ biến thể đều `inventory_quantity <= 0` nhưng vẫn đẩy lên feed quảng cáo.
   - **P2 (Giảm hiển thị / Chất lượng kém):** Thiếu `product_type` (không map được `google_product_category`), thiếu `vendor` (brand), thiếu `barcode`/GTIN khi `require_gtin=true`, hoặc chỉ có 1 ảnh duy nhất.
3. **Công thức tính Feed Health Score:**
   $$\text{Feed Health Score} = 100 - \min\left(100, \frac{5 \cdot N_{P0} + 2 \cdot N_{P1} + 0.5 \cdot N_{P2}}{N_{\text{total}}} \times 100\right)$$
   - `>= 90`: Sẵn sàng chạy PMax / TikTok GMV Max.
   - `70–89`: Cần xử lý lỗi P0/P1 trước khi tăng ngân sách.
   - `< 70`: Cảnh báo đỏ — tạm dừng mở rộng ads, sửa feed ngay.
4. **Đối chiếu UI Admin (nếu cần xác minh trạng thái đồng bộ):** Kiểm tra tab lỗi tại `/admin/googleshop` và `/admin/marketings/tiktok_ads/products` để đối chiếu mã lỗi thực tế từ Google/TikTok trả về.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Kiểm toán Product Feed (Google Shopping & TikTok Ads)
- **Tổng sản phẩm quét:** 420 | **Feed Health Score:** 78.5 / 100 (Cần xử lý P0/P1)
- **Đạt chuẩn đồng bộ:** 318 SKU (75.7%) | **Lỗi P0:** 6 | **Lỗi P1:** 41 | **Lỗi P2:** 55

| Mức độ | Mã lỗi | Số SKU | Ví dụ Product ID / SKU | Hành động đề xuất |
| --- | --- | ---: | --- | --- |
| P0 | `MISSING_IMAGE` / `ZERO_PRICE` | 6 | `1054218909` (`AO-TEST-01`) | Ẩn sản phẩm test hoặc bổ sung giá & ảnh ≥ 800x800 |
| P1 | `PROMO_TEXT_IN_TITLE` | 24 | `1054218901` (`POLO-BLK-L`) | Bỏ cụm "SALE SỐC 50%" khỏi tiêu đề sản phẩm |
| P1 | `ALL_VARIANTS_OOS` | 17 | `1054218944` (`JEAN-29`) | Tắt đồng bộ ads hoặc nhập kho |
| P2 | `MISSING_PRODUCT_TYPE` | 55 | `1054219002` | Bổ sung `product_type` chuẩn để map danh mục GMC |
```

```json
{
  "skill": "marketing-ads-feed-google-tiktok-audit",
  "channels": "both",
  "summary": { "total_products": 420, "healthy_count": 318, "p0_count": 6, "p1_count": 41, "p2_count": 55, "feed_health_score": 78.5 },
  "issues": [
    { "severity": "P0", "code": "ZERO_PRICE", "product_id": 1054218909, "variant_ids": [1120334499], "channel_impact": ["google_shopping", "tiktok_ads"], "fix_hint": "Cập nhật giá > 0 hoặc chuyển sang ẩn trên Online Store" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Chế độ Read-Only tuyệt đối (L1):** Chỉ gọi `GET /com/products.json`. Không bao giờ tự ý sửa tiêu đề, giá sản phẩm, ẩn sản phẩm hay bật/tắt chiến dịch quảng cáo trên Google/TikTok.
- **Bảo mật & PII:** `pii_level: none`. Không in `HARAVAN_ACCESS_TOKEN` ra báo cáo.
- **Rollback:** Không áp dụng vì không thực hiện ghi dữ liệu (`rollback.supported: false`). Mọi chỉnh sửa dữ liệu sản phẩm phải đi qua skill L2/L3 có `dry_run: true` và backup snapshot.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn hoặc sai định dạng Bearer | Dừng ngay, báo người dùng kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu scope `com.read_products` | Yêu cầu cấp đúng scope `com.read_products` trong cấu hình app. |
| `404 Not Found` | Endpoint sai surface (dùng `/web/` thay vì `/com/`) | Kiểm tra `BASE_URLS["com"]` trong `hrv_client.py`. |
| `422 Unprocessable` | Tham số filter không hợp lệ | Xác thực lại `published_status` và `limit <= 250`. |
| `429 Too Many Requests` | Vượt leaky bucket (`80` req / `4` req/s) | Dùng `HaravanClient` tự backoff `1s -> 2s -> 4s` và giảm tốc xuống `2.5 req/s`. |

- **Edge Case 1 — Sản phẩm quà tặng 0đ (`Gift`):** Các shop Haravan thường tạo sản phẩm giá `0 VND` để làm quà tặng kèm đơn. Nếu vẫn để `published_scope: global`, feed GMC sẽ báo lỗi `P0`. Agent cần nhận diện từ khóa `[QUÀ TẶNG]`/`[GIFT]` và đề xuất loại trừ khỏi kênh Google/TikTok thay vì báo lỗi sửa giá.
- **Edge Case 2 — Ảnh biến thể khác ảnh đại diện:** Một số sản phẩm có ảnh chính đạt chuẩn nhưng ảnh của biến thể màu thứ 2 bị thiếu hoặc lỗi 404. Cần kiểm tra cả `product.images` lẫn `variant.image_id`.
- **Edge Case 3 — Tiêu đề tiếng Việt có dấu kết hợp mã SKU in hoa:** Mã như `SKU: POLO-VN-01` hay tên thương hiệu `ZARA`, `MLB` bị viết hoa hợp lệ; thuật toán kiểm tra ALL CAPS cần loại trừ token mã SKU/brand trước khi tính tỷ lệ chữ hoa.

## 8. Liên kết Workflow & Skill kế tiếp

- **Sửa lỗi catalog sau audit:** Chuyển sang `catalog-seo-metadata-proposal` (L2) hoặc `catalog-health-audit` (L1) để rà soát sâu cấu trúc sản phẩm.
- **Kiểm tra SEO & Schema Product JSON-LD trên landing page quảng cáo:** Chạy tiếp `seo-metadata-serp-audit` (L1) để đảm bảo giá và tồn kho trên HTML khớp 100% với Feed GMC (tránh lỗi Mismatched Price).
- **Kiểm tra đồng bộ sàn & kênh bán:** Kết hợp `omnichannel-marketplace-sync-audit` (L1) khi chạy TikTok Shop + TikTok Ads song song.
