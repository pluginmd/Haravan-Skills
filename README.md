# Haravan Operational AI Skills (`haravan-ops-skills`)

**Tác giả:** **Nguyễn Ngọc Tuấn** — *Founder, Transform Group*

> **Đúc kết tinh hoa vận hành bán lẻ & thương mại điện tử đa kênh thực chiến với nền tảng Haravan (`haravan.com`).**  
> Đây không chỉ là tập tài liệu hướng dẫn, mà là **hệ điều hành AI Agent hoàn chỉnh** gói gọn toàn bộ kinh nghiệm triển khai, quản trị và tối ưu doanh nghiệp bán lẻ Việt Nam trên Haravan — từ khâu khởi tạo cửa hàng, cấu hình 17 phân hệ quản trị, chuẩn hóa catalog & tồn kho đa chi nhánh, kiểm soát bom hàng & đối soát COD (GHN, GHTK, Viettel Post, J&T, Ahamove), chăm sóc khách hàng Phone-First CRM / Zalo ZNS / Haraloyalty, đến báo cáo tài chính, thuế GTGT/HĐĐT và trực chiến Mega Sale.

Bộ **88 Canonical AI Agent Skills chuẩn hóa toàn diện** được chia tách rành mạch thành **2 kênh thực thi độc lập**:

1. **Loại 1 — `skills/api-mcp/` (62 skills, `requires_token: true`):** Chạy qua **Haravan REST API (`/com/`, `/web/`), CLI Runner (`scripts/hrv_ops.py`), MCP Server (`mcp/haravan_mcp_server.py`) hoặc `@haravan/cli`** — yêu cầu `HARAVAN_ACCESS_TOKEN`.
2. **Loại 2 — `skills/browser-ui/` — Agentic Browsing Skills (26 skills, `requires_token: false`):** Thiết kế chuyên biệt cho **Agentic Browsing** — giúp các **trình duyệt AI nội bộ & extension tự động thao tác chuột/bàn phím** (như **Antigravity Internal Browser**, **ChatGPT Internal Browser / Operator**, **Claude in Chrome Extension / Computer Use**, hoặc các AI Browser Agent khác) trực tiếp điều khiển **Haravan Admin (`*.myharavan.com/admin`)** mà **không cần API token**, chỉ cần người dùng tự đăng nhập trình duyệt. Toàn bộ đường dẫn URL, 17 mục Cấu hình và nhãn nút bấm tiếng Việt đã được **khảo sát xác minh trực tiếp trên Haravan Admin thật** với 4–5 kịch bản click-by-click chi tiết mỗi skill.

### Vì sao bộ kỹ năng này tạo ra khác biệt khi vận hành Haravan?
- **100% Thuần Haravan & Thực chiến Việt Nam:** Thiết kế chuẩn xác cho Haravan Omni REST API (`/com/`), Online Store Web API (`/web/`), Haravan Liquid, `@haravan/cli`, Webhooks HMAC-SHA256 và toàn bộ hệ sinh thái Haraweb — Harasocial — HaraRetail POS — Sàn TMĐT (Shopee, Lazada, TikTok Shop).
- **An toàn chuẩn sản xuất (Zero-Accident Guardrails):** Read-Only mặc định ở tầng L1, bắt buộc `dry_run: true` + backup JSON/CSV ở tầng L2, xác nhận lượt riêng (`separate_turn: true`) ở tầng L3, và **Screenshot-Before-Save** trên trình duyệt Admin.
- **Sẵn sàng dùng ngay (Turnkey Execution):** Đi kèm sẵn Python Client chống lỗi 429 (`hrv_client.py`), CLI 11 lệnh (`hrv_ops.py`), MCP Server (`haravan_mcp_server.py`), 3 SOP Playbooks (Khai trương, Daily/Weekly, Mega Sale) và 16 lịch vận hành tự động.

---

## 0. Hướng dẫn Định tuyến cho AI Agent (Biết ngay dùng loại Skill nào!)

> **Dành cho AI Agent (Antigravity, ChatGPT, Claude, Cursor, Codex):** Đọc bảng này **trước khi bắt đầu bất kỳ tác vụ nào** để chọn đúng kênh thực thi (`skills/api-mcp/` hay `skills/browser-ui/`).

### A. Công cụ AI của bạn nên dùng nhánh Skill nào?

| Công cụ AI đang chạy | Nhánh Skill ưu tiên | Cần API Token? | Cách thức thao tác |
| :--- | :--- | :---: | :--- |
| **Antigravity** (IDE / CLI) | **Cả 2 nhánh (Hybrid)** | Tùy tác vụ | Dùng `skills/api-mcp/` (qua Terminal/MCP) cho dữ liệu lớn & audit; dùng `skills/browser-ui/` (qua `/browser`) cho cấu hình Admin UI |
| **ChatGPT** (Internal Browser / Operator) | **`skills/browser-ui/`** | **Không** | Mở `*.myharavan.com/admin` trên trình duyệt nội bộ, đọc [registry-browser-ui.json](registry-browser-ui.json) & [admin-ui-sitemap.yaml](api/admin-ui-sitemap.yaml) để tự thao tác chuột |
| **Claude in Chrome Extension** / Computer Use | **`skills/browser-ui/`** | **Không** | Chạy trực tiếp trên tab Chrome đã đăng nhập Haravan Admin, áp dụng luật **Screenshot-Before-Save** trong [browser-ui-safety.md](policies/browser-ui-safety.md) |
| **Claude Code / Cursor / Codex / n8n** | **`skills/api-mcp/`** | **Có** | Đọc [registry-api-mcp.json](registry-api-mcp.json), gọi `scripts/hrv_ops.py`, `scripts/hrv_client.py` hoặc gắn [mcp/haravan_mcp_server.py](mcp/haravan_mcp_server.py) |

### B. Luật chọn nhanh theo loại nghiệp vụ

| Tình huống / Yêu cầu của người dùng | Chọn nhánh | Lý do |
| :--- | :--- | :--- |
| Quét hàng trăm/nghìn sản phẩm, đơn hàng, tồn kho, RFM, đối soát COD, báo cáo sáng/tuần/tháng | **`skills/api-mcp/`** | Nhanh, chính xác, không bị giới hạn phân trang giao diện |
| Chỉnh sửa Theme Liquid, Pages, Blogs, Redirects, Script Tags | **`skills/api-mcp/`** | 5 màn hình Website chạy trong cross-origin iframe `web.haravan.app` nên API (`/web/*`) và `@haravan/cli` hiệu quả hơn |
| Cấu hình **17 mục Settings** (Vận chuyển & GHN/GHTK/VTP, Thanh toán/Haravan QR/COD, Checkout/OTP Zalo, Phân quyền Vai trò, Mẫu in, Tên miền/SSL, Thuế/HĐĐT) | **`skills/browser-ui/`** | Các cấu hình này **không có API công khai**, bắt buộc thao tác bằng Agentic Browsing |
| Vận hành trực tiếp trên Admin khi **chưa có API Token** (tạo đơn, đẩy giao hàng hàng loạt, quản lý thu hộ COD, tạo khuyến mãi, bảng giá B2B, đơn nháp, CRM Flows/Broadcast, xuất báo cáo UI) | **`skills/browser-ui/`** | Chỉ cần người dùng đăng nhập trình duyệt là AI thao tác được ngay |

### C. Prompt mẫu dán vào ChatGPT / Antigravity / Claude in Chrome
- **Chạy Agentic Browsing (không cần token):**
  > *"Đọc `AGENTS.md`, `policies/browser-ui-safety.md`, `api/admin-ui-sitemap.yaml` và `registry-browser-ui.json`. Sử dụng trình duyệt đang đăng nhập Haravan Admin để thực hiện skill `<tên-skill>` ở chế độ Screenshot-Before-Save (chụp ảnh chờ tôi duyệt trước khi bấm Lưu)."*
- **Chạy API / MCP / CLI (có `HARAVAN_ACCESS_TOKEN`):**
  > *"Đọc `AGENTS.md` và `registry-api-mcp.json`. Chạy skill `<tên-skill>` qua `scripts/hrv_ops.py` hoặc `scripts/hrv_client.py` ở chế độ Read-Only / `dry_run: true` trước."*

---

## 1. Tổng quan số liệu & Kiến trúc an toàn

| Chỉ số | Giá trị |
| :--- | :--- |
| **Tổng số Canonical Skills** | **88 skills** (100% đã qua `validate_registry.py` — 0 lỗi) |
| **Phân theo kênh thực thi** | `api_mcp`: **62 skills** (cần token) \| `browser_ui`: **26 skills** (trình duyệt Admin, không cần token) |
| **Phân theo tầng an toàn (`L0–L3`)** | `L0` Reference: **6** \| `L1` Read-Only: **43** \| `L2` Proposal/Dry-Run: **33** \| `L3` Critical Write: **6** |
| **Phân theo đợt triển khai (`Wave 1–3`)** | **Wave 1** (chạy ngay, Read-Only): **49** \| **Wave 2** (Proposal-first): **33** \| **Wave 3** (Critical, `separate_turn: true`): **6** |
| **Công cụ thực thi đi kèm** | Python REST Client (`hrv_client.py`), CLI 11 lệnh (`hrv_ops.py`), MCP Server (`haravan_mcp_server.py`), 16 lịch định kỳ (`schedules.yaml`), n8n Webhook mẫu, 3 SOP Playbooks |

### Kiến trúc 4 tầng an toàn (`L0–L3`)
| Tầng | Tên tầng | Cơ chế thực thi & Bảo vệ |
| :---: | :--- | :--- |
| **L0** | Core Platform & Reference | Kiến thức kỹ thuật chuẩn về API, Auth, Rate Limit (`80 req / 4 req/s`), `@haravan/cli`, Webhooks HMAC-SHA256, Admin Sitemap và Incident Runbook. |
| **L1** | Read-Only Audit & Analytics | Chỉ gọi HTTP `GET` (hoặc chế độ chỉ đọc trên trình duyệt). **Không cấp scope ghi**, không sửa dữ liệu, an toàn tuyệt đối trên production. |
| **L2** | Proposal-First (Dry-Run) | Luôn mặc định `dry_run: true` (API) hoặc **Screenshot-Before-Save** (Admin UI). Tạo bản xem trước CSV/JSON + backup trước khi người dùng duyệt áp dụng. |
| **L3** | Critical Mutations (`separate_turn`) | Thao tác rủi ro cao/bất khả nghịch (Hủy đơn & hoàn kho, Tạo vận đơn hàng loạt, Rollback, Phương thức thanh toán, Phân quyền nhân viên, Tên miền/SSL). Bắt buộc xác nhận ở **lượt hội thoại riêng**, giới hạn `max_records <= 25`, `partial_failure_policy: stop`. |

---

## 2. Cấu trúc Repository

```text
haravan-ops-skills/
├── README.md                              # Tài liệu tổng quan, hướng dẫn & danh mục đầy đủ 88 skills
├── AGENTS.md                              # Quy tắc an toàn bắt buộc cho AI Agent vận hành Haravan
├── RESEARCH.md                            # Kiến trúc kỹ thuật & Tinh hoa vận hành Haravan Omnichannel
├── registry.json                          # Chỉ mục tổng hợp 88 skills (auto-generated)
├── registry-api-mcp.json                  # Chỉ mục 62 skills chạy qua API / MCP / CLI (Cần Token)
├── registry-browser-ui.json               # Chỉ mục 26 skills thao tác trình duyệt Admin UI (Không cần Token)
├── config/
│   ├── stores.example.yaml                # Cấu hình multi-store (staging/production), không chứa secrets
│   ├── permissions.yaml                   # Ma trận phân quyền least-privilege theo Haravan scopes
│   ├── rate-limits.yaml                   # Leaky bucket Haravan (80 req / 4 req/s) & retry backoff
│   └── operation-policies.yaml            # Guardrails toàn cục (dry_run, max_records, PII, Financial Disclaimer)
├── policies/
│   ├── read-only.md                       # Quy chuẩn vận hành tầng L1
│   ├── write-confirmation.md              # Quy trình Propose -> Confirm -> Apply & separate-turn
│   ├── pii-handling.md                    # Che SĐT (090****567), email & địa chỉ khách hàng VN
│   ├── rollback.md                        # Backup JSON, idempotency & khả năng rollback theo thao tác
│   └── browser-ui-safety.md               # Luật an toàn thao tác trình duyệt & giới hạn iframe web.haravan.app
├── api/
│   ├── endpoints-catalog.yaml             # Danh mục đầy đủ Haravan Commerce (/com/) & Web (/web/) endpoints
│   ├── webhooks-catalog.yaml              # Danh mục webhook topics & xác thực X-Haravan-Hmacsha256
│   ├── admin-ui-sitemap.yaml              # Bản đồ URL & 17 mục Cấu hình Haravan Admin (live-verified)
│   └── error-codes.md                     # Xử lý mã lỗi HTTP 400/401/403/404/422/429/5xx
├── scripts/
│   ├── hrv_client.py                      # Haravan REST Client (leaky-bucket, retry 429, dry-run gate, PII redactor, HMAC)
│   ├── hrv_ops.py                         # CLI vận hành 11 tác vụ lõi (hỗ trợ cả --demo offline & live token)
│   ├── generate_registry.py               # Tự động sinh đồng bộ 3 file registry JSON từ skills/
│   ├── validate_registry.py               # Kiểm tra toàn bộ contract, scopes, channel & safety defaults
│   └── dry_run_report.py                  # Xuất file *.backup.json & *.preview.csv trước khi ghi
├── mcp/
│   ├── haravan_mcp_server.py              # MCP Server (JSON-RPC 2.0 stdio, zero external dependencies)
│   └── mcp-config.example.json            # File cấu hình gắn MCP vào Antigravity / Claude Code / Cursor / Codex
├── playbooks/
│   ├── 01-new-store-launch-sop.md         # Quy trình khai trương cửa hàng mới (Zero -> Go-Live)
│   ├── 02-daily-weekly-ops-sop.md         # Quy trình vận hành hàng ngày (8h-16h) & hàng tuần (T2-T7)
│   └── 03-mega-sale-readiness-sop.md      # Quy trình trực chiến Mega Sale (9.9 / 11.11 / 12.12 / Tết)
├── workflows/
│   ├── schedules.yaml                     # 16 lịch vận hành định kỳ (6 Daily, 7 Weekly, 3 Monthly)
│   └── n8n/haravan-order-webhook.json     # Workflow n8n mẫu: nhận orders/create -> verify HMAC -> chấm điểm COD
├── tests/
│   └── test_skills_suite.py               # Bộ 9 test tự động (Client, PII, HMAC, 88 skills, CLI, MCP)
└── skills/
    ├── api-mcp/                           # 62 Skills — Chạy qua API / MCP / CLI (requires_token: true)
    └── browser-ui/                        # 26 Skills — Thao tác trình duyệt Admin UI (requires_token: false)
```

---

## 3. Hướng dẫn Cài đặt & Sử dụng Nhanh (Quickstart)

### Cách A — Dùng nhóm `skills/api-mcp/` (Qua CLI hoặc MCP Server, cần Token)

1. **Thiết lập biến môi trường (tuyệt đối không commit token vào git):**
   ```bash
   export HARAVAN_STORE_DOMAIN="myshop.myharavan.com"
   export HARAVAN_ACCESS_TOKEN="your_private_app_or_oauth_bearer_token"
   export HARAVAN_ENV="staging"   # dev | staging | production
   ```
2. **Kiểm tra toàn vẹn hệ thống & chạy thử offline với `--demo`:**
   ```bash
   python3 scripts/generate_registry.py
   python3 scripts/validate_registry.py
   python3 -m unittest discover -s tests -v

   # Chạy thử 11 tác vụ vận hành lõi trên dữ liệu mẫu VN (không cần token):
   python3 scripts/hrv_ops.py --demo probe
   python3 scripts/hrv_ops.py --demo health-check
   python3 scripts/hrv_ops.py --demo catalog-audit
   python3 scripts/hrv_ops.py --demo low-stock
   python3 scripts/hrv_ops.py --demo cod-risk
   python3 scripts/hrv_ops.py --demo wismo
   python3 scripts/hrv_ops.py --demo rfm
   python3 scripts/hrv_ops.py --demo promo-audit
   python3 scripts/hrv_ops.py --demo redirect-audit
   python3 scripts/hrv_ops.py --demo morning-briefing
   python3 scripts/hrv_ops.py --demo price-dry-run --pct 10 --out /tmp/hrv-preview
   ```
   *(Bỏ cờ `--demo` để chạy trực tiếp lên cửa hàng Haravan thật qua `HARAVAN_ACCESS_TOKEN`.)*

3. **Gắn Haravan MCP Server vào Antigravity / Claude Code / Cursor / Codex:**
   - Copy cấu hình từ [mcp/mcp-config.example.json](mcp/mcp-config.example.json).
   - Các MCP tools khả dụng (100% Read-Only / Safe): `haravan_list_skills` (lọc theo `execution_channel: "api_mcp" | "browser_ui"`, `domain`, `layer`), `haravan_health_check`, `haravan_catalog_audit`, `haravan_low_stock`, `haravan_cod_risk`, `haravan_morning_briefing`.

### Cách B — Dùng nhóm `skills/browser-ui/` (Agentic Browsing trên Trình duyệt AI — KHÔNG cần Token)

> **Tương thích trực tiếp với:** **Antigravity Internal Browser (`/browser`)**, **ChatGPT Internal Browser / Operator**, **Claude in Chrome Extension / Computer Use**, và mọi **AI Browser Agent** hỗ trợ điều khiển chuột/form.

1. Mở trình duyệt AI của bạn tới `https://accounts.haravan.com`.
2. Người dùng **tự đăng nhập** vào Haravan Admin (`*.myharavan.com/admin`) — Agent tuyệt đối không hỏi hay tự nhập mật khẩu/OTP.
3. Nạp skill tương ứng trong `skills/browser-ui/` (kèm [policies/browser-ui-safety.md](policies/browser-ui-safety.md) và [api/admin-ui-sitemap.yaml](api/admin-ui-sitemap.yaml)) để AI Agent nhảy thẳng tới đúng route `/admin/...` và click đúng nhãn nút tiếng Việt.
4. Agent bắt buộc áp dụng **Screenshot-Before-Save** (chụp trạng thái trước + điền form chưa bấm `Lưu` → chờ xác nhận → bấm `Lưu` → reload xác minh) và tuân thủ danh sách nút **Hard-Blocked** cấm tự bấm.
   > **Lưu ý kỹ thuật đã kiểm chứng:** 5 màn hình con dưới **Kênh bán hàng > Website** (`/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}`) chạy trong cross-origin iframe `https://web.haravan.app`. Với Theme/Pages/Blogs/Redirects, hãy dùng các skill `api-mcp` (`/web/*` và `@haravan/cli`).

---

## 4. Phủ đủ 7 Giai đoạn Vận hành Haravan (End-to-End SOP)

| Giai đoạn | Playbook hướng dẫn | Nhóm Skill áp dụng |
| :--- | :--- | :--- |
| **1. Nền tảng & Kết nối** | [README.md](README.md) | `00-core-platform` (`api-mcp`) + `admin-ui-session-navigator` (`browser-ui`) |
| **2. Setup & Cấu hình 17 mục Admin** | [01-new-store-launch-sop.md](playbooks/01-new-store-launch-sop.md) | `10-store-bootstrap` (`api-mcp`) + 7 skill Settings (`browser-ui`) |
| **3. Sản phẩm, Bảng giá & Giá bán** | [01-new-store-launch-sop.md](playbooks/01-new-store-launch-sop.md) | `20-catalog-merchandising` (`9 api-mcp` + `1 browser-ui`) |
| **4. Kho hàng, Kiểm kho & Nhập hàng** | [02-daily-weekly-ops-sop.md](playbooks/02-daily-weekly-ops-sop.md) | `30-inventory-supply` (`8 api-mcp`) + `admin-ui-locations-inventory-ops` (`browser-ui`) |
| **5. Đơn hàng, Giao vận VN & COD** | [02-daily-weekly-ops-sop.md](playbooks/02-daily-weekly-ops-sop.md) | `40-orders-fulfillment` (`8 api-mcp` + `2 browser-ui`) + `admin-ui-shipments-cod-mass-fulfill` |
| **6. CRM, Marketing, Đa kênh & SEO/CRO** | [03-mega-sale-readiness-sop.md](playbooks/03-mega-sale-readiness-sop.md) | `50-customer-crm`, `70-marketing-omnichannel`, `80-theme-seo-cro` + `admin-ui-crm-flows-broadcast` |
| **7. Tài chính, COD, Thuế/HĐĐT & Governance** | [02-daily-weekly-ops-sop.md](playbooks/02-daily-weekly-ops-sop.md) | `60-finance-analytics`, `90-control-tower-governance` + `admin-ui-tax-einvoice-accounting` |

---

## 5. Danh mục đầy đủ Loại 1: `skills/api-mcp/` (62 Skills — Cần API Token)

> Chỉ mục máy đọc: [registry-api-mcp.json](registry-api-mcp.json) | `execution_channel: api_mcp` | `requires_token: true`

#### 00 — Core Platform (API, Auth, CLI, Webhooks) (4 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`haravan-api-core`](skills/api-mcp/00-core-platform/haravan-api-core/SKILL.md) | `L0` | `reference` | `low` | `com.read_shop` | Chuẩn kỹ thuật gọi Haravan REST API (/com/ và /web/), pagination, rate-limit leaky bucket và xử lý lỗi. |
| [`haravan-auth-setup`](skills/api-mcp/00-core-platform/haravan-auth-setup/SKILL.md) | `L0` | `reference` | `low` | `com.read_shop`, `offline_access` | Hướng dẫn thiết lập xác thực Private App hoặc OAuth2 (offline_access), kiểm tra kết nối và đối chiếu least-privilege scopes. |
| [`haravan-cli-theme-ops`](skills/api-mcp/00-core-platform/haravan-cli-theme-ops/SKILL.md) | `L0` | `reference` | `low` | `web.read_themes`, `web.write_themes` | Quy trình cài đặt và sử dụng @haravan/cli (pull, watch, deploy) kết hợp staging theme để phát triển giao diện Haravan Liquid an toàn. |
| [`haravan-webhook-manager`](skills/api-mcp/00-core-platform/haravan-webhook-manager/SKILL.md) | `L0` | `reference` | `low` | `wh_api` | Thiết kế, kiểm tra và xác thực chữ ký HMAC-SHA256 (X-Haravan-Hmacsha256) cho Private Webhook và Connect Webhook (wh_api). |

#### 10 — Store Bootstrap & Health Audit (5 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`store-bootstrap-checklist`](skills/api-mcp/10-store-bootstrap/store-bootstrap-checklist/SKILL.md) | `L1` | `read` | `low` | `com.read_shop`, `com.read_products`, `com.read_contents`, `web.read_themes`, `web.read_script_tags` | Đánh giá toàn diện độ sẵn sàng khai trương cửa hàng Haravan (tên miền, thanh toán VN, vận chuyển, chính sách, tracking, giao diện). |
| [`store-config-audit`](skills/api-mcp/10-store-bootstrap/store-config-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_shop` | Kiểm toán cấu hình chung cửa hàng, chi nhánh/kho hàng, đơn vị tiền tệ, thuế và khu vực hành chính Việt Nam. |
| [`store-health-check`](skills/api-mcp/10-store-bootstrap/store-health-check/SKILL.md) | `L1` | `read` | `low` | `com.read_shop`, `com.read_products`, `com.read_orders`, `com.read_inventories`, `com.read_discounts`, `web.read_themes` | Khám sức khỏe tổng quát cửa hàng Haravan trên 5 trụ cột: Catalog, Tồn kho, Đơn hàng/Giao vận, Khuyến mãi và Storefront. |
| [`store-redirect-audit`](skills/api-mcp/10-store-bootstrap/store-redirect-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_contents` | Kiểm toán toàn bộ luật chuyển hướng URL (/web/redirects.json) để phát hiện redirect loop, chain dài và đường dẫn xung đột SEO. |
| [`store-staff-permission-audit`](skills/api-mcp/10-store-bootstrap/store-staff-permission-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_shop` | Kiểm toán danh sách tài khoản nhân viên (/com/users.json), phát hiện tài khoản dư quyền, không hoạt động lâu ngày hoặc email cá nhân. |

#### 20 — Catalog, Merchandising & Pricing (9 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`catalog-bulk-import-proposal`](skills/api-mcp/20-catalog-merchandising/catalog-bulk-import-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_products`, `com.write_products` | Chuẩn hóa dữ liệu đầu vào (CSV/JSON), kiểm tra trùng SKU và tạo proposal nhập sản phẩm mới lên Haravan (dry-run trước). |
| [`catalog-collection-reorg-proposal`](skills/api-mcp/20-catalog-merchandising/catalog-collection-reorg-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_products`, `com.write_products` | Kiểm toán sản phẩm mồ côi (không thuộc nhóm nào) và đề xuất sắp xếp lại sản phẩm vào Custom Collections (/com/collects.json). |
| [`catalog-data-completeness-audit`](skills/api-mcp/20-catalog-merchandising/catalog-data-completeness-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_products` | Chấm điểm độ hoàn thiện dữ liệu sản phẩm (tiêu đề, mô tả HTML, ảnh, SKU, barcode, giá so sánh, trọng lượng, tags, vendor). |
| [`catalog-duplicate-sku-barcode`](skills/api-mcp/20-catalog-merchandising/catalog-duplicate-sku-barcode/SKILL.md) | `L1` | `read` | `low` | `com.read_products` | Phát hiện toàn bộ SKU hoặc Barcode bị trùng lặp giữa các variant trên Haravan — nguyên nhân hàng đầu gây lệch tồn kho đa kênh. |
| [`catalog-image-alt-audit`](skills/api-mcp/20-catalog-merchandising/catalog-image-alt-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_products` | Kiểm tra ảnh sản phẩm bị thiếu, ảnh thiếu thuộc tính alt text SEO và đề xuất bộ alt text chuẩn tiếng Việt. |
| [`catalog-metafield-bulk-update`](skills/api-mcp/20-catalog-merchandising/catalog-metafield-bulk-update/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_products`, `com.write_products` | Đọc, kiểm chuẩn và đề xuất cập nhật hàng loạt Metafields cho sản phẩm/variant (thông số kỹ thuật, xuất xứ, hướng dẫn bảo quản). |
| [`catalog-product-lifecycle-proposal`](skills/api-mcp/20-catalog-merchandising/catalog-product-lifecycle-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_products`, `com.write_products` | Đề xuất ẩn/hiện sản phẩm hoặc gắn tag vòng đời (new-arrival, clearance, out-of-season) theo quy tắc tồn kho & doanh số. |
| [`pricing-bulk-adjustment-proposal`](skills/api-mcp/20-catalog-merchandising/pricing-bulk-adjustment-proposal/SKILL.md) | `L2` | `proposal` | `high` | `com.read_products`, `com.write_products` | Tính toán, kiểm tra biên an toàn và đề xuất điều chỉnh giá bán hàng loạt cho các variant trên Haravan với backup rollback đầy đủ. |
| [`pricing-compare-at-cleanup`](skills/api-mcp/20-catalog-merchandising/pricing-compare-at-cleanup/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_products`, `com.write_products` | Phát hiện và đề xuất dọn dẹp giá so sánh (compare_at_price) bất hợp lệ (nhỏ hơn hoặc bằng giá bán, giảm ảo > 80%) sau đợt sale. |

#### 30 — Inventory, Multi-Location & Supply Chain (8 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`inventory-adjustment-proposal`](skills/api-mcp/30-inventory-supply/inventory-adjustment-proposal/SKILL.md) | `L2` | `proposal` | `high` | `com.read_inventories`, `com.write_inventories` | So sánh tồn thực tế kiểm kê với tồn trên Haravan và tạo phiếu đề xuất điều chỉnh tồn kho (dry-run + backup bắt buộc). |
| [`inventory-aging-dead-stock`](skills/api-mcp/30-inventory-supply/inventory-aging-dead-stock/SKILL.md) | `L1` | `read` | `low` | `com.read_inventories`, `com.read_orders`, `com.read_products` | Phát hiện hàng tồn kho chậm luân chuyển (30/60/90+ ngày không phát sinh đơn) và ước tính giá trị vốn bị chôn. |
| [`inventory-low-stock-watchdog`](skills/api-mcp/30-inventory-supply/inventory-low-stock-watchdog/SKILL.md) | `L1` | `read` | `low` | `com.read_inventories`, `com.read_products`, `com.read_orders` | Cảnh báo sớm các SKU bán chạy sắp hết hàng theo ngưỡng tồn kho tối thiểu và tốc độ bán thực tế (days of cover). |
| [`inventory-multi-location-audit`](skills/api-mcp/30-inventory-supply/inventory-multi-location-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_inventories`, `com.read_shop`, `com.read_products` | Kiểm toán tồn kho đa chi nhánh/kho (/com/inventory_locations.json), phát hiện tồn âm, mất cân bằng giữa kho online và cửa hàng POS. |
| [`inventory-purchase-order-audit`](skills/api-mcp/30-inventory-supply/inventory-purchase-order-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_inventories` | Theo dõi tiến độ đơn đặt hàng nhà cung cấp (PO) và đối chiếu phiếu nhập kho thực tế (/com/inventories/purchase_orders.json & purchase_receives.json). |
| [`inventory-stock-velocity-forecast`](skills/api-mcp/30-inventory-supply/inventory-stock-velocity-forecast/SKILL.md) | `L1` | `read` | `low` | `com.read_inventories`, `com.read_orders`, `com.read_products` | Phân tích tốc độ luân chuyển hàng hóa (ABC/XYZ) và tính điểm đặt hàng lại (Reorder Point) dựa trên lead time nhà cung cấp. |
| [`inventory-stocktake-cycle-count`](skills/api-mcp/30-inventory-supply/inventory-stocktake-cycle-count/SKILL.md) | `L2` | `proposal` | `high` | `com.read_inventories`, `com.write_inventories`, `com.read_shop` | Chuẩn hóa quy trình kiểm kho định kỳ (cycle count), đối chiếu chênh lệch thừa/thiếu theo SKU và lập đề xuất cân bằng kho. |
| [`inventory-transfer-proposal`](skills/api-mcp/30-inventory-supply/inventory-transfer-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_inventories`, `com.write_inventories`, `com.read_shop` | Đề xuất và tạo phiếu điều chuyển hàng giữa kho trung tâm và các chi nhánh HaraRetail POS (/com/inventories/transfers.json). |

#### 40 — Orders, Fulfillment & VN Carriers (8 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`fulfillment-bulk-create-critical`](skills/api-mcp/40-orders-fulfillment/fulfillment-bulk-create-critical/SKILL.md) | `L3` | `write` | `critical` | `com.read_orders`, `com.write_orders` | Tạo vận đơn / cập nhật mã tracking hàng loạt (/com/orders/{id}/fulfillments.json) — yêu cầu dry-run, giới hạn ≤ 25 đơn và separate-turn approval. |
| [`fulfillment-carrier-sla-vn`](skills/api-mcp/40-orders-fulfillment/fulfillment-carrier-sla-vn/SKILL.md) | `L1` | `read` | `low` | `com.read_orders` | So sánh hiệu suất giao hàng và tỷ lệ hoàn đơn giữa các nhà vận chuyển VN (GHN, GHTK, Viettel Post, J&T, Ahamove) theo tuyến nội tỉnh/liên miền. |
| [`fulfillment-status-digest-wismo`](skills/api-mcp/40-orders-fulfillment/fulfillment-status-digest-wismo/SKILL.md) | `L1` | `read` | `low` | `com.read_orders` | Tổng hợp trạng thái giao vận hàng loạt (chưa đóng gói, chờ lấy hàng, đang giao, giao thất bại, hoàn hàng) để xử lý WISMO chủ động. |
| [`order-cancel-restock-critical`](skills/api-mcp/40-orders-fulfillment/order-cancel-restock-critical/SKILL.md) | `L3` | `write` | `critical` | `com.read_orders`, `com.write_orders` | Hủy đơn hàng và hoàn kho có kiểm soát (/com/orders/{id}/cancel.json) — yêu cầu dry-run, xác nhận kho chưa lấy hàng và separate-turn approval. |
| [`order-lookup-summary`](skills/api-mcp/40-orders-fulfillment/order-lookup-summary/SKILL.md) | `L1` | `read` | `low` | `com.read_orders` | Tra cứu nhanh chi tiết đơn hàng, trạng thái thanh toán, vận đơn và lịch sử giao dịch phục vụ CSKH (đã che PII khi xuất báo cáo). |
| [`order-risk-cod-boom-signals`](skills/api-mcp/40-orders-fulfillment/order-risk-cod-boom-signals/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_customers` | Phát hiện sớm các tín hiệu rủi ro bom hàng COD tại Việt Nam (địa chỉ thiếu phường/xã, SĐT lịch sử hủy cao, đơn COD giá trị lớn bất thường). |
| [`order-triage-tagging-proposal`](skills/api-mcp/40-orders-fulfillment/order-triage-tagging-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_orders`, `com.write_orders` | Phân loại và đề xuất gắn nhãn (tags) hàng loạt cho đơn hàng Haravan (/com/orders/{id}/tags.json) theo kênh, rủi ro COD, VIP hoặc yêu cầu xuất hóa đơn. |
| [`returns-reason-restock-proposal`](skills/api-mcp/40-orders-fulfillment/returns-reason-restock-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_orders`, `com.read_inventories`, `com.write_inventories` | Phân tích nguyên nhân hoàn/trả hàng (size, lỗi SX, bom hàng COD) và lập phiếu đề xuất nhập lại kho hàng đạt chuẩn. |

#### 50 — Customer & Vietnam Phone-First CRM (6 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`customer-address-correction-proposal`](skills/api-mcp/50-customer-crm/customer-address-correction-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_customers`, `com.write_customers`, `com.read_shop` | Kiểm tra và đề xuất chuẩn hóa địa chỉ giao hàng Việt Nam (Tỉnh/Thành, Quận/Huyện, Phường/Xã) để giảm lỗi đẩy đơn NVC. |
| [`customer-cohort-retention`](skills/api-mcp/50-customer-crm/customer-cohort-retention/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_customers` | Phân tích tỷ lệ mua lại (Repeat Purchase Rate) và bảng giữ chân theo tháng đầu mua hàng (Monthly Cohort Retention). |
| [`customer-duplicate-phone-finder`](skills/api-mcp/50-customer-crm/customer-duplicate-phone-finder/SKILL.md) | `L1` | `read` | `low` | `com.read_customers` | Chuẩn hóa đầu số điện thoại Việt Nam (+84 / 84 / 0) để phát hiện hồ sơ khách hàng bị trùng giữa Website, Harasocial và POS. |
| [`customer-rfm-segmentation`](skills/api-mcp/50-customer-crm/customer-rfm-segmentation/SKILL.md) | `L1` | `read` | `low` | `com.read_customers`, `com.read_orders` | Phân khúc toàn bộ khách hàng Haravan theo mô hình RFM (Recency, Frequency, Monetary) để tối ưu chăm sóc và Haraloyalty. |
| [`customer-tag-note-proposal`](skills/api-mcp/50-customer-crm/customer-tag-note-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_customers`, `com.write_customers` | Đề xuất gắn tag phân hạng (VIP, Loyal, Churn-Risk, B2B-Si) và ghi chú chăm sóc hàng loạt cho khách hàng (/com/customers/{id}.json). |
| [`customer-vip-churn-watchlist`](skills/api-mcp/50-customer-crm/customer-vip-churn-watchlist/SKILL.md) | `L1` | `read` | `low` | `com.read_customers`, `com.read_orders` | Nhận diện khách hàng VIP có dấu hiệu rời bỏ (quá chu kỳ mua lặp lại bình thường) để kích hoạt kịch bản chăm sóc cá nhân hóa. |

#### 60 — Finance, COD Reconciliation & VAT (6 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`finance-aov-discount-roi`](skills/api-mcp/60-finance-analytics/finance-aov-discount-roi/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_discounts` | Phân tích xu hướng giá trị đơn trung bình (AOV), tỷ lệ đơn dùng mã giảm giá và hiệu quả thực tế của các chương trình khuyến mãi. |
| [`finance-cod-reconciliation`](skills/api-mcp/60-finance-analytics/finance-cod-reconciliation/SKILL.md) | `L1` | `read` | `low` | `com.read_orders` | Đối chiếu tiền thu hộ COD giữa đơn hàng Haravan và biên bản đối soát nhà vận chuyển (GHN/GHTK/VTP/J&T) để phát hiện chênh lệch. |
| [`finance-profit-margin-analyzer`](skills/api-mcp/60-finance-analytics/finance-profit-margin-analyzer/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_products` | Ước tính biên lợi nhuận gộp theo sản phẩm/danh mục/kênh bán dựa trên giá bán thuần, giá vốn (COGS), chiết khấu và ước tính phí ship/sàn. |
| [`finance-refund-rate-analysis`](skills/api-mcp/60-finance-analytics/finance-refund-rate-analysis/SKILL.md) | `L1` | `read` | `low` | `com.read_orders` | Đo lường tỷ lệ hoàn tiền, hủy đơn và tổn thất doanh thu theo kênh bán, phương thức thanh toán và dòng sản phẩm. |
| [`finance-sales-by-channel-omni`](skills/api-mcp/60-finance-analytics/finance-sales-by-channel-omni/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_shop` | Báo cáo doanh thu, số đơn, AOV và tỷ lệ hoàn theo từng kênh trong hệ sinh thái Haravan Omni (Haraweb, Harasocial, HaraRetail POS, Shopee, Lazada, TikTok Shop). |
| [`finance-tax-vat-summary`](skills/api-mcp/60-finance-analytics/finance-tax-vat-summary/SKILL.md) | `L1` | `read` | `low` | `com.read_orders` | Tổng hợp ước tính doanh thu chịu thuế GTGT (VAT) và danh sách đơn có yêu cầu xuất hóa đơn điện tử để bàn giao kế toán. |

#### 70 — Marketing, Promotions & Omnichannel (6 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`marketing-ads-feed-google-tiktok-audit`](skills/api-mcp/70-marketing-omnichannel/marketing-ads-feed-google-tiktok-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_products` | Kiểm toán chất lượng Product Feed đồng bộ sang Google Ads (/admin/googleshop) và TikTok Ads (/admin/marketings/tiktok_ads/products) để tránh bị từ chối sản phẩm. |
| [`marketing-cart-recovery-zns`](skills/api-mcp/70-marketing-omnichannel/marketing-cart-recovery-zns/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_orders`, `com.read_customers` | Phân tích đơn bỏ quên/chưa thanh toán và lập đề xuất kịch bản nhắc giỏ hàng 3 chạm (1h / 24h / 72h) qua Email và Zalo ZNS. |
| [`marketing-promo-code-proposal`](skills/api-mcp/70-marketing-omnichannel/marketing-promo-code-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_discounts`, `com.write_discounts` | Thiết kế, kiểm tra biên an toàn và đề xuất tạo hoặc bật/tắt mã khuyến mãi trên Haravan (/com/promotions.json). |
| [`marketing-promotion-hygiene-audit`](skills/api-mcp/70-marketing-omnichannel/marketing-promotion-hygiene-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_discounts` | Kiểm toán toàn bộ chương trình khuyến mãi (/com/promotions.json), phát hiện mã hết hạn chưa tắt, rủi ro chồng mã (stacking) hoặc giảm quá sâu. |
| [`marketing-winback-campaign`](skills/api-mcp/70-marketing-omnichannel/marketing-winback-campaign/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_customers`, `com.read_orders` | Xây dựng chiến dịch kéo lại khách hàng ngủ đông (Hibernating/At-Risk) từ dữ liệu RFM Haravan với thông điệp và ưu đãi phân tầng. |
| [`omnichannel-marketplace-sync-audit`](skills/api-mcp/70-marketing-omnichannel/omnichannel-marketplace-sync-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_inventories`, `com.read_products` | Kiểm tra sức khỏe đồng bộ đơn hàng và tồn kho giữa Haravan Omni với Harasocial, HaraRetail POS và các sàn TMĐT (Shopee, Lazada, TikTok Shop). |

#### 80 — Theme Liquid, SEO & CRO (5 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`seo-blog-content-optimizer`](skills/api-mcp/80-theme-seo-cro/seo-blog-content-optimizer/SKILL.md) | `L2` | `proposal` | `medium` | `com.read_contents`, `com.write_contents` | Đánh giá bài viết tin tức (/web/blogs/{id}/articles.json) và đề xuất tạo mới hoặc tối ưu cấu trúc SEO, internal link về sản phẩm. |
| [`seo-metadata-serp-audit`](skills/api-mcp/80-theme-seo-cro/seo-metadata-serp-audit/SKILL.md) | `L1` | `read` | `low` | `com.read_products`, `com.read_contents` | Kiểm toán tiêu đề SEO, meta description, cấu trúc URL handle, trang nội dung (/web/pages.json) và dữ liệu có cấu trúc Product JSON-LD trên Haraweb. |
| [`storefront-script-tag-audit`](skills/api-mcp/80-theme-seo-cro/storefront-script-tag-audit/SKILL.md) | `L1` | `read` | `low` | `web.read_script_tags` | Kiểm toán toàn bộ mã nhúng JavaScript bên thứ ba (/web/script_tags.json) để phát hiện script thừa, trùng pixel tracking hoặc làm chậm website. |
| [`theme-liquid-code-review`](skills/api-mcp/80-theme-seo-cro/theme-liquid-code-review/SKILL.md) | `L1` | `read` | `low` | `web.read_themes` | Kiểm toán mã nguồn Haravan Liquid (layout, templates, snippets, assets) phát hiện vòng lặp N+1, ảnh chưa lazy-load, script chặn render và lỗi cú pháp. |
| [`theme-performance-cro-audit`](skills/api-mcp/80-theme-seo-cro/theme-performance-cro-audit/SKILL.md) | `L1` | `read` | `low` | `web.read_themes`, `com.read_products` | Đánh giá tối ưu tỷ lệ chuyển đổi (CRO) trên trang chủ, trang danh mục, trang chi tiết sản phẩm (PDP) và luồng thanh toán Haraweb (Mobile-First VN). |

#### 90 — Control Tower, Briefings & Rollback (5 skills)

| Skill | Tầng | Mode | Rủi ro | Scopes tối thiểu | Mô tả |
| :--- | :-: | :-: | :-: | :--- | :--- |
| [`governance-rollback-executor`](skills/api-mcp/90-control-tower-governance/governance-rollback-executor/SKILL.md) | `L3` | `write` | `critical` | `com.read_products`, `com.write_products`, `com.read_inventories`, `com.write_inventories`, `com.write_contents` | Khôi phục dữ liệu Haravan (giá bán, tags, trạng thái sản phẩm, redirects, tồn kho bù trừ) từ file backup JSON đã tạo bởi dry_run_report.py. |
| [`ops-daily-morning-briefing`](skills/api-mcp/90-control-tower-governance/ops-daily-morning-briefing/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_inventories`, `com.read_products` | Bản tin vận hành đầu ngày (8:00 AM UTC+7): doanh thu hôm qua theo kênh, đơn chờ xử lý, cảnh báo COD rủi ro, SKU sắp hết hàng. |
| [`ops-incident-runbook-escalation`](skills/api-mcp/90-control-tower-governance/ops-incident-runbook-escalation/SKILL.md) | `L0` | `reference` | `low` | `com.read_shop` | Sổ tay ứng cứu sự cố khẩn cấp Haravan: bão đơn 429 Mega Sale, đẩy nhầm giá/tồn kho, đứt đồng bộ sàn TMĐT, lỗi cổng thanh toán hoặc sập domain/SSL. |
| [`ops-monthly-financial-close`](skills/api-mcp/90-control-tower-governance/ops-monthly-financial-close/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_inventories`, `com.read_discounts`, `com.read_products` | Gói tổng hợp đóng sổ vận hành cuối tháng: doanh thu thuần đa kênh, hoàn hủy, chi phí khuyến mãi, đối soát COD, tồn kho và ước tính VAT. |
| [`ops-weekly-business-review`](skills/api-mcp/90-control-tower-governance/ops-weekly-business-review/SKILL.md) | `L1` | `read` | `low` | `com.read_orders`, `com.read_products`, `com.read_inventories`, `com.read_customers` | Báo cáo tổng kết kinh doanh tuần (so sánh WoW): doanh thu đa kênh, AOV, tỷ lệ hoàn/hủy, hiệu suất NVC VN và sức khỏe tồn kho. |


---

## 6. Danh mục đầy đủ Loại 2: `skills/browser-ui/` (26 Skills — Thao tác Trình duyệt Admin, Không cần Token)

> Chỉ mục máy đọc: [registry-browser-ui.json](registry-browser-ui.json) | `execution_channel: browser_ui` | `requires_token: false` | Sitemap thực tế: [api/admin-ui-sitemap.yaml](api/admin-ui-sitemap.yaml)

#### 20 — Catalog, Merchandising & Pricing (2 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-products-catalog-ops`](skills/browser-ui/20-catalog-merchandising/admin-ui-products-catalog-ops/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/products`, `/admin/products/new`, `/admin/products/{product_id}`, `/admin/products/collections` — Vận hành Sản phẩm & Nhóm sản phẩm trên Haravan Admin (/admin/products & /admin/products/collections): tạo SP đa biến thể Size/Màu + ảnh + SEO, Import/Export Excel chuẩn Haravan, Bulk Edit giá/tồn/tag/ẩn-hiện và tạo Nhóm SP thủ công/tự động. |
| [`catalog-pricing-list-b2b-proposal`](skills/browser-ui/20-catalog-merchandising/catalog-pricing-list-b2b-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/products/pricing_list` — Thiết kế và kiểm chuẩn Bảng giá riêng cho kênh bán hàng (Web/POS/Harasocial), chi nhánh và nhóm khách sỉ B2B (/admin/products/pricing_list). |

#### 30 — Inventory, Multi-Location & Supply Chain (1 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-inventory-advanced-ops`](skills/browser-ui/30-inventory-supply/admin-ui-inventory-advanced-ops/SKILL.md) | `L2` | `proposal` | `high` | `/admin/products/inventories`, `/admin/purchase_orders`, `/admin/purchase_receives`, `/admin/purchase_returns`, `/admin/transfers`, `/admin/inventory_adjustments` — Vận hành Tồn kho Nâng cao trên Haravan Admin (/admin/products/inventories & phân hệ kho): Đặt hàng nhập PO, Nhập hàng cập nhật giá vốn, Trả hàng NCC, Điều chuyển giữa 2 kho + duyệt xuất/nhận, Kiểm kho barcode/Excel và Cân bằng kho. |

#### 40 — Orders, Fulfillment & VN Carriers (3 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-orders-daily-ops`](skills/browser-ui/40-orders-fulfillment/admin-ui-orders-daily-ops/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/orders`, `/admin/orders/new`, `/admin/orders/{order_id}` — Vận hành Đơn hàng hàng ngày trên Haravan Admin (/admin/orders): lọc đa điều kiện, tạo đơn thủ công, xác nhận thanh toán chuyển khoản, gắn tag/ghi chú, tách giao hàng, sửa địa chỉ đơn chưa giao và in phiếu đơn/vận đơn. |
| [`draft-orders-quote-proposal`](skills/browser-ui/40-orders-fulfillment/draft-orders-quote-proposal/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/draft_orders` — Chuẩn hóa quy trình lập Đơn hàng nháp (/admin/draft_orders) cho báo giá khách sỉ B2B, đơn đặt qua Zalo/Harasocial và theo dõi chuyển đổi. |
| [`order-abandoned-checkouts-audit`](skills/browser-ui/40-orders-fulfillment/order-abandoned-checkouts-audit/SKILL.md) | `L1` | `read` | `low` | `/admin/orders/checkouts` — Phân tích danh sách đơn chưa hoàn tất (/admin/orders/checkouts) để tìm nguyên nhân khách bỏ giỏ tại bước thanh toán/vận chuyển. |

#### 50 — Customer & Vietnam Phone-First CRM (2 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-customers-profile-ops`](skills/browser-ui/50-customer-crm/admin-ui-customers-profile-ops/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/customers`, `/admin/customers/new`, `/admin/customers/{customer_id}` — Vận hành Hồ sơ Khách hàng trên Haravan Admin (/admin/customers): tìm theo SĐT Việt Nam, tạo khách mới, sửa địa chỉ/tag/ghi chú, tra cứu lịch sử đơn & điểm Haraloyalty, xử lý khách trùng SĐT và Import/Export có kiểm soát PII. |
| [`customer-review-rating-moderation`](skills/browser-ui/50-customer-crm/customer-review-rating-moderation/SKILL.md) | `L1` | `read` | `low` | `/admin/customers/rating` — Kiểm toán đánh giá sản phẩm (/admin/customers/rating), phát hiện sớm SKU có điểm thấp (1–2 sao) và đề xuất kịch bản phản hồi CSKH. |

#### 60 — Finance, COD Reconciliation & VAT (2 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-reports-analytics-export`](skills/browser-ui/60-finance-analytics/admin-ui-reports-analytics-export/SKILL.md) | `L1` | `read` | `low` | `/admin/reports/dashboard`, `/admin/reports/listing` — Khai thác & xuất Báo cáo trên Haravan Admin (/admin/reports/dashboard & /admin/reports/listing): Bán hàng đa kênh, Chi tiết khuyến mãi, Lợi nhuận, Tồn kho, Công nợ COD và Báo cáo khách hàng RFM theo bộ lọc ngày/chi nhánh/kênh. |
| [`finance-cashbook-debt-audit`](skills/browser-ui/60-finance-analytics/finance-cashbook-debt-audit/SKILL.md) | `L1` | `read` | `low` | `/admin/accounting/transactions`, `/admin/accounting/debts` — Rà soát Sổ quỹ thu chi (/admin/accounting/transactions) và Công nợ (/admin/accounting/debts) để phát hiện khoản treo quá hạn. |

#### 70 — Marketing, Promotions & Omnichannel (1 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-discounts-promotions-ops`](skills/browser-ui/70-marketing-omnichannel/admin-ui-discounts-promotions-ops/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/discounts`, `/admin/discounts/new`, `/admin/discounts/{discount_id}` — Quản lý Khuyến mãi trên Haravan Admin (/admin/discounts): cấu hình 4 loại mã giảm giá (đơn hàng, sản phẩm, đồng giá, vận chuyển), Mua X tặng Y, Dùng chung khuyến mãi (Grow/Scale+), giới hạn kênh/chi nhánh/nhóm khách và bật/tắt/nhân bản. |

#### 80 — Theme Liquid, SEO & CRO (2 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-website-theme-menu-assist`](skills/browser-ui/80-theme-seo-cro/admin-ui-website-theme-menu-assist/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/sale_channels/online_store/themes`, `/admin/sale_channels/online_store/articles`, `/admin/sale_channels/online_store/pages`, `/admin/sale_channels/online_store/menus`, `/admin/sale_channels/online_store/settings` — Vận hành Website Haravan (/admin/sale_channels/online_store/{themes,articles,pages,menus,settings}): xử lý thông minh giới hạn cross-origin iframe web.haravan.app, định tuyến Hybrid sang Web API/@haravan/cli và hướng dẫn Assisted-UI cho Menu đa cấp & Theme Customizer. |
| [`storefront-file-storage-audit`](skills/browser-ui/80-theme-seo-cro/storefront-file-storage-audit/SKILL.md) | `L1` | `read` | `low` | `/admin/settings/files` — Kiểm toán kho tệp tin (/admin/settings/files) để phát hiện ảnh/video quá nặng (> 500KB) làm chậm Core Web Vitals và tệp rác không sử dụng. |

#### 95 — Haravan Admin Settings & Live UI Operations (13 skills)

| Skill | Tầng | Mode | Rủi ro | Đường dẫn Haravan Admin / Mô tả |
| :--- | :-: | :-: | :-: | :--- |
| [`admin-ui-apps-addons-billing`](skills/browser-ui/95-admin-ui-browser/admin-ui-apps-addons-billing/SKILL.md) | `L1` | `read` | `low` | `/admin/apps`, `/admin/settings/order_addon`, `/admin/settings/billings` — Quản lý & kiểm toán chỉ đọc trên Haravan Admin: danh sách Ứng dụng (/admin/apps), kiểm tra Private App/OAuth, Tiện ích đơn hàng (/admin/settings/order_addon) và rà soát Gói dịch vụ / Hóa đơn (/admin/settings/billings). |
| [`admin-ui-checkout-settings`](skills/browser-ui/95-admin-ui-browser/admin-ui-checkout-settings/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/settings/checkouts` — Cấu hình luồng đặt hàng tại /admin/settings/checkouts: tài khoản khách hàng, Multipass, xác thực OTP Zalo, nhắc đơn chưa thanh toán, đặt cọc và nhận tại cửa hàng. |
| [`admin-ui-crm-flows-broadcast`](skills/browser-ui/95-admin-ui-browser/admin-ui-crm-flows-broadcast/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/customers/segments`, `/admin/customers/broadcast_campaigns`, `/admin/customers/flows`, `/admin/customers/rating`, `/admin/customers/settings` — Vận hành CRM nâng cao trên Admin UI: Nhóm khách hàng (/admin/customers/segments), Broadcast (/admin/customers/broadcast_campaigns), Kịch bản tự động (/admin/customers/flows) và Thành viên. |
| [`admin-ui-domains-channels-website`](skills/browser-ui/95-admin-ui-browser/admin-ui-domains-channels-website/SKILL.md) | `L3` | `write` | `critical` | `/admin/settings/domains`, `/admin/settings/sale_channels`, `/admin/settings/marketing_channels`, `/admin/sale_channels/online_store/themes`, `/admin/sale_channels/online_store/menus` — Quản lý Tên miền (/admin/settings/domains), Kênh bán hàng (/admin/settings/sale_channels), Kênh marketing (/admin/settings/marketing_channels) và hướng dẫn xử lý iframe Website. |
| [`admin-ui-general-policies-setup`](skills/browser-ui/95-admin-ui-browser/admin-ui-general-policies-setup/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/settings/general`, `/admin/settings/policies` — Cấu hình thông tin cửa hàng, logo, tiêu chuẩn định dạng (/admin/settings/general) và Điều khoản & Chính sách (/admin/settings/policies) trên trình duyệt. |
| [`admin-ui-locations-inventory-ops`](skills/browser-ui/95-admin-ui-browser/admin-ui-locations-inventory-ops/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/settings/locations`, `/admin/products/pricing_list`, `/admin/products/inventories` — Cấu hình Địa chỉ & Kho hàng (/admin/settings/locations), bật Địa điểm lấy hàng / xuất hóa đơn, và quản lý Bảng giá đa kênh (/admin/products/pricing_list). |
| [`admin-ui-notifications-print-webhooks`](skills/browser-ui/95-admin-ui-browser/admin-ui-notifications-print-webhooks/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/settings/notifications` — Quản lý 13 mẫu Email khách hàng, Mẫu in (Đơn hàng/Vận đơn/Tồn kho), Thông báo đơn hàng nội bộ và Private Webhooks tại /admin/settings/notifications. |
| [`admin-ui-payment-methods-setup`](skills/browser-ui/95-admin-ui-browser/admin-ui-payment-methods-setup/SKILL.md) | `L3` | `write` | `critical` | `/admin/settings/payments` — Cấu hình Haravan QR, Cổng thanh toán trực tuyến (VNPay, MoMo, ZaloPay) và Thanh toán thủ công (COD, Chuyển khoản) tại /admin/settings/payments. |
| [`admin-ui-session-navigator`](skills/browser-ui/95-admin-ui-browser/admin-ui-session-navigator/SKILL.md) | `L0` | `reference` | `low` | `https://accounts.haravan.com`, `/admin/dashboard/generals`, `/admin/settings` — Quy chuẩn điều hướng Haravan Admin (*.myharavan.com/admin), xử lý đăng nhập/2FA, bản đồ 17 mục Cấu hình và luật Screenshot-Before-Save. |
| [`admin-ui-shipments-cod-mass-fulfill`](skills/browser-ui/95-admin-ui-browser/admin-ui-shipments-cod-mass-fulfill/SKILL.md) | `L2` | `proposal` | `high` | `/admin/orders/mass_fulfill`, `/admin/shipments/dashboard`, `/admin/shipments/managecod`, `/admin/shipments/packed`, `/admin/shipments/shipment_handovers`, `/admin/shipments/shipment_returns` — Điều phối giao hàng hàng loạt (/admin/orders/mass_fulfill), Quản lý thu hộ COD (/admin/shipments/managecod), Đóng gói, Biên bản bàn giao & Hoàn hàng. |
| [`admin-ui-shipping-carriers-setup`](skills/browser-ui/95-admin-ui-browser/admin-ui-shipping-carriers-setup/SKILL.md) | `L2` | `proposal` | `medium` | `/admin/settings/shipments`, `/admin/settings/locations` — Cấu hình biểu phí vận chuyển theo khu vực/Tỉnh-Thành, kết nối NVC VN (GHN, GHTK, Viettel Post, J&T, Ahamove) và kích thước kiện hàng tại /admin/settings/shipments. |
| [`admin-ui-staff-roles-config`](skills/browser-ui/95-admin-ui-browser/admin-ui-staff-roles-config/SKILL.md) | `L3` | `write` | `critical` | `/admin/settings/accounts`, `/admin/settings/group_permissions`, `/admin/settings/group_accounts` — Thiết lập Vai trò phân quyền (/admin/settings/group_permissions), Nhóm phân công (/admin/settings/group_accounts) và Nhân viên (/admin/settings/accounts). |
| [`admin-ui-tax-einvoice-accounting`](skills/browser-ui/95-admin-ui-browser/admin-ui-tax-einvoice-accounting/SKILL.md) | `L2` | `proposal` | `high` | `/admin/settings/vat_setting`, `/admin/etax/declarations`, `/admin/etax/revenue_ledgers`, `/admin/accounting/transactions`, `/admin/accounting/debts` — Kiểm tra & hỗ trợ thiết lập Thuế/Hóa đơn điện tử (/admin/settings/vat_setting), Tờ khai thuế (/admin/etax/declarations), Sổ kế toán & Sổ quỹ/Công nợ. |


---

## 7. Lịch vận hành tự động & Kiểm thử

- **16 Scheduled Routines** (6 Daily, 7 Weekly, 3 Monthly — chỉ chạy ở chế độ Read-Only/Dry-Run): xem [workflows/schedules.yaml](workflows/schedules.yaml).
- **n8n Webhook Automation mẫu** (`orders/create` + Verify `X-Haravan-Hmacsha256` + Cảnh báo rủi ro COD): xem [workflows/n8n/haravan-order-webhook.json](workflows/n8n/haravan-order-webhook.json).
- **Lệnh kiểm chứng toàn bộ repo sau mỗi lần chỉnh sửa:**
  ```bash
  python3 scripts/generate_registry.py && python3 scripts/validate_registry.py && python3 -m unittest discover -s tests -v
  ```
