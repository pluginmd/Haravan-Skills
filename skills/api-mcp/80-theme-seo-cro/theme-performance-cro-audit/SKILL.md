---
name: theme-performance-cro-audit
description: "Đánh giá tối ưu tỷ lệ chuyển đổi (CRO) trên trang chủ, trang danh mục, trang chi tiết sản phẩm (PDP) và luồng thanh toán Haraweb (Mobile-First VN)."
version: 1.0.0
execution_channel: api_mcp
requires_token: true
domain: 80-theme-seo-cro
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: web
  scopes:
    - web.read_themes
    - com.read_products
  endpoints:
    - "GET https://apis.haravan.com/web/themes.json"
    - "GET https://apis.haravan.com/com/products.json"
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

# Haravan Storefront CRO, PDP & Checkout UX Audit

## 1. Mục tiêu, Ngữ cảnh Haravan & Tiêu chí hoàn thành (Definition of Done)

- **Mục tiêu nghiệp vụ:** Kiểm toán toàn diện trải nghiệm mua hàng và tỷ lệ chuyển đổi (Conversion Rate Optimization — CRO) trên 4 điểm chạm cốt lõi của storefront Haraweb (`Homepage`, `Collection`, `PDP`, `Cart/Checkout`) theo chuẩn **Mobile-First Việt Nam** (> 80% lưu lượng TMĐT đến từ màn hình 360px–430px qua Facebook/TikTok/Zalo in-app browser).
- **Ngữ cảnh Haravan:** Nhiều shop chạy quảng cáo tốt nhưng tỷ lệ chuyển đổi (CR) dưới 1% do các điểm nghẽn đặc thù tại VN: nút **Mua ngay / Thêm vào giỏ** bị trôi khỏi màn hình mobile, biến thể Size/Màu hiển thị dạng dropdown khó bấm thay vì swatch, không công khai chính sách **đồng kiểm COD / đổi trả 7 ngày** ngay gần nút mua, và giỏ hàng thiếu thanh tiến độ Freeship (Free Shipping Progress Bar) để kéo tăng AOV.
- **Definition of Done (DoD):**
  1. Lấy danh sách theme đang chạy (`GET /web/themes.json`) và mẫu sản phẩm bán chạy (`GET /com/products.json`) để phân tích cấu trúc biến thể, giá so sánh (`compare_at_price`), ảnh và mô tả.
  2. Chấm điểm 4 trụ cột CRO (Homepage, Collection, PDP, Cart/Checkout) trên thang 100 điểm theo bộ 20 tiêu chí Mobile-First VN.
  3. Lập **Ma trận Ưu tiên CRO (ICE Score: Impact × Confidence ÷ Effort)** và đề xuất 3–5 kịch bản A/B Testing cụ thể.

## 2. Quyền truy cập, Endpoints & Ví dụ Request/Payload thực tế

| Thành phần | Giá trị bắt buộc |
| --- | --- |
| **API Surface** | `web` & `com` (`https://apis.haravan.com/web`, `/com`) |
| **Scopes tối thiểu** | `web.read_themes`, `com.read_products` |
| **Endpoints** | `GET /web/themes.json`, `GET /com/products.json` |

**Ví dụ gọi qua `scripts/hrv_client.py`:**
```python
from scripts.hrv_client import HaravanClient

client = HaravanClient(dry_run=True)
themes = client.request("GET", "web", "/themes.json").get("themes", [])
live_theme = next((t for t in themes if t.get("role") == "main"), None)
sample_products = client.paginate(
    surface="com",
    path="/products.json",
    resource_key="products",
    params={"published_status": "published"},
    limit=50,
    max_pages=4,
)
```

**Ví dụ dữ liệu PDP kiểm tra CRO từ `GET /com/products.json`:**
```json
{
  "id": 1054218901,
  "title": "Áo Khoác Gió Chống Nước 2 Lớp",
  "images": [{ "id": 1, "src": "https://product.hstatic.net/.../img1.jpg" }],
  "options": [{ "name": "Màu sắc" }, { "name": "Kích thước" }],
  "variants": [
    { "id": 1120334455, "price": "399000", "compare_at_price": "550000", "inventory_quantity": 25 }
  ]
}
```

## 3. Bảng tham số đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation / Mô tả |
| --- | --- | --- | --- | --- |
| `store_url` | `string` | Không | `""` | URL storefront Haraweb (ví dụ `https://shop.vn`) để đối chiếu cấu trúc giao diện. |
| `focus_pages` | `array[string]` | Không | `["home", "collection", "pdp", "cart"]` | Danh sách nhóm trang trọng tâm cần kiểm toán. |
| `sample_products` | `integer` | Không | `50` | Số lượng sản phẩm mẫu kiểm tra cấu trúc PDP (`10..200`). |
| `target_aov_vnd` | `integer` | Không | `500000` | Mức AOV mục tiêu (VND) để đề xuất ngưỡng Freeship Bar trên giỏ hàng. |

## 4. Thuật toán, Công thức tính toán & Quy trình thực thi chi tiết

1. **Bộ 20 tiêu chí chấm điểm CRO Mobile-First VN (mỗi trụ cột 25 điểm = 100 điểm):**
   - **Homepage (25đ):** Value Proposition rõ trong màn hình đầu (Above-the-fold); thanh tìm kiếm trực diện kèm gợi ý từ khóa; lối tắt danh mục (Quick Category Icons); không chạy slider > 3 banner nặng gây tụt LCP.
   - **Collection / Danh mục (25đ):** Bộ lọc nhanh theo Giá / Size / Màu; thẻ sản phẩm hiển thị rõ % giảm giá từ `compare_at_price`, trạng thái Hết hàng và nút Thêm nhanh (Quick Add).
   - **PDP — Trang Chi tiết Sản phẩm (25đ):** Tối thiểu ≥ 4 ảnh sản phẩm (góc chụp + ảnh thật/bảng size); chọn biến thể bằng nút bấm (Swatch/Pill) thay vì `<select>` mặc định; hiển thị rõ **Tiết kiệm bao nhiêu VND/%**; cụm Trust Badges sát nút CTA (*Đồng kiểm COD • Đổi size 7 ngày • Freeship đơn từ X*); **Sticky Bottom Bar** chứa nút `Mua ngay` + `Thêm vào giỏ` trên mobile.
   - **Cart & Checkout (25đ):** Drawer Cart trượt nhanh (không reload trang); thanh tiến độ Freeship (`Mua thêm 101,000đ để được Freeship`); ô nhập mã giảm giá dễ thấy; form chọn Tỉnh/Quận/Phường gọn nhẹ và hỗ trợ cả COD lẫn VietQR.
2. **Công thức ưu tiên triển khai (ICE Priority Score):**
   $$\text{ICE Score} = \frac{\text{Impact (1–10)} \times \text{Confidence (1–10)}}{\text{Effort (1–10)}}$$
   - `ICE >= 12`: **Quick Win (Làm ngay tuần này)**.
   - `6 <= ICE < 12`: **Sprint kế tiếp (Cần dev/staging theme)**.
   - `ICE < 6`: **Backlog**.

## 5. Mẫu đầu ra chuẩn (Human Report Template + JSON Output Schema)

```markdown
### Báo cáo Kiểm toán CRO Storefront Haraweb (Mobile-First VN)
- **Live Theme:** `Dawn-VN-Live` (`id: 10012948`) | **Điểm CRO tổng:** `62 / 100`
- **Điểm thành phần:** Homepage `18/25` | Collection `15/25` | PDP `14/25` | Cart/Checkout `15/25`

#### Ma trận Ưu tiên CRO (ICE Score)
| Ưu tiên | Trang | Vấn đề phát hiện | Đề xuất cải tiến | Impact | Conf. | Effort | ICE |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | PDP | Nút Mua ngay trôi khuất khi cuộn trên mobile | Thêm Sticky CTA bar cố định đáy màn hình mobile | 9 | 9 | 3 | **27.0** |
| 2 | Cart | Chưa có động lực tăng giá trị đơn | Thêm thanh tiến độ Freeship (ngưỡng 500k) trong Cart Drawer | 8 | 8 | 3 | **21.3** |
| 3 | PDP | 38% sản phẩm chỉ có 1–2 ảnh, thiếu bảng size | Bổ sung ảnh bảng size + Trust Badge COD/Đổi trả 7 ngày | 8 | 8 | 4 | **16.0** |
| 4 | Collection | Biến thể hết hàng vẫn cho bấm rồi báo lỗi | Gạch chéo biến thể hết hàng trực tiếp trên swatch | 7 | 8 | 5 | **11.2** |

> *Lưu ý:* Các mức cải thiện tỷ lệ chuyển đổi dự kiến chỉ là giả thuyết CRO, cần đo lường thực tế qua GA4/A/B Testing ít nhất 14 ngày trước khi kết luận.
```

```json
{
  "skill": "theme-performance-cro-audit",
  "live_theme_id": 10012948,
  "scores": { "total": 62, "homepage": 18, "collection": 15, "pdp": 14, "cart_checkout": 15 },
  "ice_backlog": [
    { "rank": 1, "page": "pdp", "issue": "MISSING_MOBILE_STICKY_CTA", "impact": 9, "confidence": 9, "effort": 3, "ice_score": 27.0, "ab_test_metric": "Add-to-Cart Rate (Mobile)" }
  ]
}
```

## 6. Kiểm soát An toàn, Dry-Run, Xác nhận & Rollback

- **Read-Only tuyệt đối (L1):** Chỉ đọc metadata theme và sản phẩm; không tự sửa giao diện hay chèn mã HTML/CSS lên Live Theme.
- **Minh bạch giả thuyết:** Không bao giờ cam kết chắc chắn "% tăng doanh thu" khi chưa chạy thử nghiệm A/B thực tế trên lưu lượng của chính cửa hàng.
- **Rollback:** Không áp dụng (`rollback.supported: false`). Khi triển khai các thay đổi UI từ báo cáo này, bắt buộc làm trên Staging Theme qua `haravan-cli-theme-ops`.

## 7. Xử lý lỗi & Tình huống biên (Error Handling & Edge Cases)

| HTTP Code | Nguyên nhân trên Haravan | Cách xử lý của Agent |
| --- | --- | --- |
| `401 Unauthorized` | Token hết hạn | Dừng audit, báo kiểm tra `HARAVAN_ACCESS_TOKEN`. |
| `403 Forbidden` | Thiếu `web.read_themes` hoặc `com.read_products` | Yêu cầu cấp đủ 2 scope đọc. |
| `404 Not Found` | Cửa hàng chưa bật Online Store / không có Live Theme | Kiểm tra lại cấu hình kênh Website trên Haravan Admin. |
| `422 Unprocessable` | Tham số filter sản phẩm không hợp lệ | Xác nhận `published_status=published`, `limit <= 250`. |
| `429 Too Many Requests` | Tải mẫu sản phẩm quá nhanh | Dùng `HaravanClient` tự backoff `1s -> 2s -> 4s`. |

- **Edge Case 1 — Storefront chạy dạng Headless hoặc Landing Page ngoài Haravan (LadiPage/Webcake):** Nếu traffic quảng cáo đổ về LadiPage rồi mới đẩy đơn về Haravan qua API, việc tối ưu theme Haraweb sẽ chỉ tác động lên kênh Organic/Direct; cần hỏi rõ nguồn traffic chính trước khi ưu tiên backlog.
- **Edge Case 2 — Sản phẩm có giá so sánh ảo (`compare_at_price <= price`):** Một số shop nhập `compare_at_price` bằng hoặc nhỏ hơn `price` khiến badge `-0%` hiển thị lỗi trên giao diện. Agent cần gắn cờ lỗi dữ liệu giá này trong phần PDP.
- **Edge Case 3 — Traffic chủ yếu từ In-App Browser (TikTok/Zalo/Facebook):** Nút Sticky Bottom trên iOS Safari/In-App Browser dễ bị che bởi thanh điều hướng hệ thống; đề xuất CSS luôn phải nhắc dùng `padding-bottom: env(safe-area-inset-bottom)`.

## 8. Liên kết Workflow & Skill kế tiếp

- **Rà soát mã Liquid để hiện thực hóa các cải tiến CRO:** Chuyển sang `theme-liquid-code-review` (L1) và `haravan-cli-theme-ops` (L2).
- **Dọn dẹp script bên thứ ba làm chậm tốc độ tải trang mobile:** Chạy tiếp `storefront-script-tag-audit` (L1).
- **Tối ưu giỏ hàng bỏ quên sau khi cải thiện Cart UX:** Kết hợp `marketing-cart-recovery-zns` (L2).
