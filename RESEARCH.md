# RESEARCH.md — Kiến trúc Kỹ thuật & Tinh hoa Vận hành Haravan Omnichannel

> **Tác giả:** Nguyễn Ngọc Tuấn — Founder, Transform Group  
> **Bộ kỹ năng:** `haravan-ops-skills` — Đúc kết tinh hoa vận hành bán lẻ & thương mại điện tử đa kênh thực chiến trên nền tảng **Haravan (`haravan.com`)**.

Tài liệu này hệ thống hóa nền tảng kỹ thuật của **Haravan Omni / Haraweb** (REST API, `@haravan/cli`, Haravan Liquid, Webhooks HMAC-SHA256) kết hợp kết quả khảo sát trực tiếp trên **Haravan Admin sống (`*.myharavan.com/admin`)**, từ đó kiến trúc nên bộ **88 Canonical Operational Skills** (gồm **62 skills `api-mcp`** chạy qua API/MCP/CLI cần token và **26 skills `browser-ui`** thao tác trực tiếp trên trình duyệt Admin không cần token).

---

## 1. Kiến trúc Kỹ thuật Cốt lõi của Nền tảng Haravan

| Khía cạnh kỹ thuật | Đặc tả thực tế trên Haravan (Omni / Haraweb) | Chuẩn thiết kế trong `haravan-ops-skills` |
| :--- | :--- | :--- |
| **API Architecture** | **REST Omni API** (`/com/*.json`) & **Online Store Web API** (`/web/*.json`) | **REST-first**; chuẩn hóa pagination (`page`, `limit=50..250`, `since_id`), field filtering (`fields=...`) |
| **Base Endpoints** | `https://apis.haravan.com/com/` & `https://apis.haravan.com/web/` | Tách rõ 2 surface `com` (Admin/Omni) và `web` (Theme/Pages/Blogs/Redirects/ScriptTags) |
| **Authentication** | **Private App Bearer Token** hoặc **OAuth2 (`offline_access`)** | Header `Authorization: Bearer <TOKEN>`, đọc tuyệt đối từ ENV, hỗ trợ refresh token cho App |
| **Access Scopes** | Namespace phân tách rõ: `com.read_*`, `com.write_*`, `web.read_*`, `web.write_*`, `wh_api` | Nguyên tắc **Least-Privilege Scopes**: tầng L1 Read-Only tuyệt đối không yêu cầu scope ghi |
| **Rate Limiting** | **Leaky Bucket: 80 requests, leak rate 4 req/s**, HTTP `429 Too Many Requests` | Tích hợp sẵn client-side limiter (`scripts/hrv_client.py`, ngưỡng an toàn ≤ 2.5 req/s) + exponential backoff |
| **Batch & Bulk Ops** | Xử lý theo lô REST có kiểm soát tốc độ | Giới hạn batch cứng (`max_records <= 25` cho L3, `<= 100` cho L2), idempotency key & backup JSON |
| **Theme Engine** | **Haravan Liquid** (`haravan_theme_twenty` & custom themes) | Audit chuyên sâu hiệu năng Liquid, vòng lặp N+1, lazy-load LCP, SEO/CRO trên Staging Theme |
| **CLI Tooling** | **`@haravan/cli`** (`haravan pull`, `haravan deploy`, `haravan watch`) | Tách CLI cho theme ops trên Staging Theme; cấm sửa trực tiếp Live Theme (`role: main`) |
| **Webhooks** | Private Webhook (Admin UI) & Connect Webhook (`webhook.haravan.com/api/subscribe`) | Bắt buộc xác thực chữ ký `X-Haravan-Hmacsha256` (HMAC-SHA256 Base64) |
| **Haravan Admin UI (Agentic Browsing)** | Giao diện quản trị `*.myharavan.com/admin` với 17 mục Cấu hình + Cross-origin iframe `web.haravan.app` | Bộ **26 Agentic Browsing Skills** (`skills/browser-ui/`) dành cho Antigravity Internal Browser, ChatGPT Internal Browser/Operator, Claude in Chrome Extension — bám sát từng route/nút bấm thực tế với **Screenshot-Before-Save** |

---

## 2. Tinh hoa Nghiệp vụ Bán lẻ & TMĐT Việt Nam trên Haravan

Bộ skill được đúc kết từ thực tiễn vận hành bán lẻ đa kênh tại Việt Nam, giải quyết trực diện các bài toán sống còn của chủ doanh nghiệp & đội ngũ vận hành:

1. **Đối soát COD (Cash on Delivery) & Kiểm soát Bom hàng:**
   - Phần lớn đơn hàng TMĐT Việt Nam thanh toán COD. Bộ skill tách rõ cơ chế đồng bộ COD tự động của **GHN / GHTK** với quy trình đối soát thủ công của **Viettel Post**, đồng thời cung cấp `finance-cod-reconciliation` đối chiếu 4 trạng thái và `order-risk-cod-boom-signals` chấm điểm 6 tín hiệu rủi ro bom hàng trước khi kho đóng gói.
2. **CRM Định danh theo Số Điện Thoại (Phone-First CRM):**
   - Khách hàng Việt Nam mua đa kênh (Haraweb, Harasocial, HaraRetail POS) thường định danh bằng SĐT thay vì email. `customer-duplicate-phone-finder` chuẩn hóa đầu số `+84`/`84`/`0` và đầu số cũ, kết hợp phân khúc RFM, Cohort Retention và Watchlist VIP rời bỏ.
3. **Vận hành Đa kênh Đồng bộ (Haravan Omnichannel):**
   - Bao phủ toàn bộ trục **Haraweb + Harasocial (Facebook/Instagram/Zalo) + HaraRetail POS + Sàn TMĐT (Shopee, Lazada, TikTok Shop)** thông qua `finance-sales-by-channel-omni`, `omnichannel-marketplace-sync-audit`, và `inventory-multi-location-audit`.
4. **Quản trị Kho hàng Nâng cao & Thu mua Nội địa:**
   - Khai thác sâu hệ thống kho đa chi nhánh (`inventory_locations`, `purchase_orders`, `v2/inventories/purchase_receives`, `transfers`), kiểm kho cuốn chiếu ABC (`inventory-stocktake-cycle-count`), dự báo Reorder Point và xử lý hàng tồn chậm chôn vốn (`inventory-aging-dead-stock`).
5. **Chăm sóc Khách hàng ZNS / Haraloyalty & Tuân thủ Thuế GTGT / HĐĐT:**
   - Kịch bản giỏ hàng bỏ quên 3 chạm (1h/24h/72h) qua Email & Zalo ZNS, cấu hình OTP Zalo trên Checkout, tổng hợp ước tính thuế GTGT (8%/10% theo NĐ 123/2020/NĐ-CP) và rà soát eTax/Hóa đơn điện tử trên Admin UI.

---

## 3. Nguyên tắc Chuẩn hóa & Kiểm soát An toàn Sản xuất (Production Safety)

- **Tách rành mạch 2 kênh thực thi:** `skills/api-mcp/` (62 skills cần `HARAVAN_ACCESS_TOKEN`) và `skills/browser-ui/` (26 skills thao tác trực tiếp trên trình duyệt Haravan Admin không cần token).
- **Tách riêng giao dịch nguy hiểm:** Không gộp Read/Audit với Mutation; tách riêng hủy đơn, hoàn tiền, tạo vận đơn hàng loạt, chỉnh giá và cấu hình dòng tiền thành các skill độc lập có rào chắn nghiêm ngặt.
- **Mặc định an toàn tuyệt đối:**
  - `100%` skill L2/L3 mặc định `dry_run: true` (hoặc **Screenshot-Before-Save** trên trình duyệt).
  - Bắt buộc `separate_turn: true` (xác nhận ở lượt hội thoại riêng) cho mọi skill `L3` Critical.
  - Bắt buộc ẩn dữ liệu cá nhân (`redact_output: true`, `export_allowed: false`) cho mọi skill có PII khách hàng/tài chính.
  - Gắn **Financial Disclaimer** (Operational Estimate / Reconciliation Aid) cho toàn bộ nhóm Tài chính & Thuế.

---

## 4. Phân bổ 88 Canonical Skills theo 11 Domain & 2 Kênh Thực Thi

| # | Domain | Tổng | `api-mcp` (Token) | `browser-ui` (Admin UI) | L0 | L1 | L2 | L3 |
| :- | :--- | :---: | :---: | :---: | :-: | :-: | :-: | :-: |
| 00 | Core Platform | 4 | 4 | 0 | 4 | 0 | 0 | 0 |
| 10 | Store Bootstrap & Audit | 5 | 5 | 0 | 0 | 5 | 0 | 0 |
| 20 | Catalog & Merchandising | 11 | 9 | 2 | 0 | 3 | 8 | 0 |
| 30 | Inventory & Supply Chain | 9 | 8 | 1 | 0 | 5 | 4 | 0 |
| 40 | Orders & Fulfillment (VN) | 11 | 8 | 3 | 0 | 5 | 4 | 2 |
| 50 | Customer & CRM | 8 | 6 | 2 | 0 | 5 | 3 | 0 |
| 60 | Finance & COD Analytics | 8 | 6 | 2 | 0 | 8 | 0 | 0 |
| 70 | Marketing & Omnichannel | 7 | 6 | 1 | 0 | 3 | 4 | 0 |
| 80 | Theme, Liquid, SEO & CRO | 7 | 5 | 2 | 0 | 5 | 2 | 0 |
| 90 | Control Tower & Governance | 5 | 5 | 0 | 1 | 3 | 0 | 1 |
| 95 | Admin UI Settings & Live Ops | 13 | 0 | 13 | 1 | 1 | 8 | 3 |
| **Tổng** | **11 Domains** | **88** | **62** | **26** | **6** | **43** | **33** | **6** |

*(Danh sách thực tế luôn được đồng bộ tự động vào `registry.json`, `registry-api-mcp.json` và `registry-browser-ui.json` bởi `scripts/generate_registry.py`.)*
