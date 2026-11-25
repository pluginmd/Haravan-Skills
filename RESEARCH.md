# RESEARCH.md — Kiến trúc kỹ thuật Haravan & Chuyển đổi từ Hệ sinh thái Shopify Skills

Báo cáo này tổng hợp kết quả nghiên cứu nền tảng **Haravan (`haravan.com`)**, đối chiếu trực tiếp với hệ sinh thái AI Agent Skills của Shopify (`Shopify/shopify-ai-toolkit`, `Shopify/agent-skills`, `storehand/storehand`, `40RTY-ai/shopify-admin-skills`, `Pikka-Shopify/Pikka-shopify-skills`) và khảo sát trực tiếp giao diện **Haravan Admin sống (`*.myharavan.com/admin`)**, từ đó định hình bộ **88 Canonical Operational Skills** (gồm **62 skills `api-mcp`** cần token và **26 skills `browser-ui`** thao tác trình duyệt Admin không cần token).

---

## 1. Đối chiếu nền tảng: Haravan vs. Shopify

| Khía cạnh | Shopify (2026) | Haravan (Omni / Haraweb) | Hệ quả thiết kế cho bộ Skills |
| :--- | :--- | :--- | :--- |
| **API Architecture** | GraphQL Admin API (REST đã là legacy) | **REST Omni API** (`/com/*.json`) & **Web API** (`/web/*.json`) | **REST-first**; chuẩn hóa pagination (`page`, `limit`, `since_id`), field filtering (`fields=...`) |
| **Base Endpoints** | `https://{shop}.myshopify.com/admin/api/{ver}/graphql.json` | `https://apis.haravan.com/com/` & `https://apis.haravan.com/web/` | Tách rõ 2 surface `com` (Admin/Omni) và `web` (Theme/Pages/Blogs/Redirects/ScriptTags) |
| **Authentication** | Client Credentials Grant (24h) / OAuth2 | **Private App Bearer Token** hoặc **OAuth2 (`offline_access`)** | Header `Authorization: Bearer <TOKEN>`, hỗ trợ refresh token cho Public/Custom App |
| **Access Scopes** | `read_products`, `write_orders`, ... | Namespace rõ ràng: `com.read_*`, `com.write_*`, `web.read_*`, `web.write_*`, `wh_api` | Mapping least-privilege scopes chính xác theo từng endpoint |
| **Rate Limiting** | GraphQL Cost Points (calculated query cost) | **Leaky Bucket: 80 requests, leak rate 4 req/s**, HTTP `429` | Bắt buộc có rate-limiter client-side (`hrv_client.py`) & backoff khi nhận 429 |
| **Bulk Operations** | Async Bulk GraphQL (`JSONL`) | Không có Bulk GraphQL native; dùng batch REST + queue | Giới hạn batch (`max_records`), checkpoint/resume, idempotency log |
| **Theme Engine** | Liquid + Online Store 2.0 (JSON templates) | **Haravan Liquid** (tương đồng Shopify Liquid, `haravan_theme_twenty`) | Tái sử dụng phương pháp audit Liquid/CRO/SEO nhưng mapping đúng objects Haravan |
| **CLI Tooling** | `@shopify/cli` (`shopify store execute`, `theme dev`) | **`@haravan/cli`** (`haravan pull`, `haravan deploy`, `haravan watch`) | Tách CLI cho theme ops, dùng Python REST client (`hrv_client.py`) cho Admin/Omni ops |
| **Webhooks** | App webhooks + EventBridge/PubSub | Private Webhook (Admin UI) & Connect Webhook (`webhook.haravan.com/api/subscribe`) | Verify chữ ký bắt buộc qua header `X-Haravan-Hmacsha256` |
| **MCP Ecosystem** | Official Dev MCP + community GraphQL MCPs | Community `Haravan-MCP` (TypeScript) | Dùng skill độc lập với adapter; có thể chạy qua `hrv_client.py`, CLI hoặc MCP |

---

## 2. Đặc thù nghiệp vụ TMĐT Việt Nam trên Haravan (VN-Specific Capabilities)

So với bộ skill gốc của Shopify (tập trung thị trường US/EU với Stripe/Shopify Payments, USPS/UPS), vận hành Haravan tại Việt Nam có những bài toán đặc thù sống còn cần đưa trực tiếp vào bộ skill:

1. **Đối soát COD (Cash on Delivery) & Tỷ lệ hoàn hàng (Boom hàng):**
   - Phần lớn đơn hàng VN thanh toán COD. Cần skill riêng `finance-cod-reconciliation` đối chiếu giữa trạng thái giao hàng (`fulfillments`), trạng thái thu hộ (`financial_status`), phí ship 2 chiều và biên bản đối soát từ GHN, GHTK, Viettel Post, J&T, Ahamove.
   - Skill `order-risk-cod-boom-signals` phát hiện tín hiệu rủi ro bom hàng (địa chỉ thiếu phường/xã, SĐT lịch sử hủy nhiều lần, đơn COD giá trị cao bất thường).
2. **Định danh khách hàng theo Số Điện Thoại (Phone-First CRM):**
   - Khách hàng VN thường đặt hàng qua SĐT (kể cả từ Harasocial/POS) mà không có email hoặc dùng email giả. Cần `customer-duplicate-phone-finder` chuẩn hóa đầu số `+84`/`0` để tìm trùng lặp và gộp ngữ cảnh.
3. **Vận hành Đa kênh (Haravan Omnichannel):**
   - Haravan kết nối đồng bộ **Haraweb + Harasocial (Facebook/Instagram/Zalo) + HaraRetail POS + Sàn TMĐT (Shopee, Lazada, TikTok Shop)**.
   - Cần các skill chuyên biệt: `finance-sales-by-channel-omni`, `omnichannel-marketplace-sync-audit`, `inventory-multi-location-audit`.
4. **Kho hàng & Nhập hàng nội địa:**
   - Haravan có API chuyên biệt cho `inventory_locations`, `inventories/purchase_orders`, `v2/inventories/purchase_receives` và điều chuyển kho (`transfers`) — được phủ đầy đủ trong nhóm `30-inventory-supply`.
5. **Chăm sóc khách hàng qua ZNS / Haraloyalty & Hóa đơn GTGT (VAT):**
   - Kịch bản giỏ hàng bỏ quên (`marketing-cart-recovery-zns`) kết hợp Email + Zalo ZNS.
   - Báo cáo thuế ước tính (`finance-tax-vat-summary`) hỗ trợ đối chiếu xuất hóa đơn điện tử GTGT tại VN.

---

## 3. Ánh xạ & Dedupe từ Corpus Shopify (500+ Raw Entries → 88 Canonical Haravan Skills)

Áp dụng nguyên tắc dedupe từ nghiên cứu gốc:
- **Gộp trùng lặp:** Các skill trùng chức năng giữa StoreHand, 40RTY, Daino, Dragonfruit, Selofy, Pikka được gộp thành 1 canonical skill duy nhất.
- **Tách transaction nguy hiểm:** Tách hẳn `read` / `audit` khỏi `proposal` và `critical write` (ví dụ: tách `order-lookup-summary` khỏi `order-cancel-restock-critical`; tách `inventory-multi-location-audit` khỏi `inventory-adjustment-proposal`).
- **Sửa lỗi an toàn từ community repos:**
  - Sửa lỗi `dry_run: false` mặc định của 40RTY → **100% đặt `dry_run: true` mặc định**.
  - Gắn `separate_turn: true` cho mọi L3 critical mutation.
  - Gắn disclaimer **Operational Estimate** cho toàn bộ nhóm Finance (60-finance-analytics).
  - Loại bỏ thao tác tự động sửa `robots.txt.liquid` live theme không qua kiểm duyệt.

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
