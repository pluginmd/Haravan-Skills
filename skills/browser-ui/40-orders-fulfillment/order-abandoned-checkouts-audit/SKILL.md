---
name: order-abandoned-checkouts-audit
description: "Phân tích danh sách đơn chưa hoàn tất (/admin/orders/checkouts) để tìm nguyên nhân khách bỏ giỏ tại bước thanh toán/vận chuyển."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 40-orders-fulfillment
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: admin_ui
  scopes:
    - com.read_orders
  endpoints:
    - "UI /admin/orders/checkouts"
    - "GET https://apis.haravan.com/com/orders.json"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
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

# Haravan Abandoned Checkouts Drop-Off Audit

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Kiểm toán toàn diện màn hình **Đơn hàng chưa hoàn tất** (`/admin/orders/checkouts`), chi tiết từng giỏ bị bỏ (`/admin/orders/checkouts/{id}`) và đối chiếu chỉ đọc với **Cấu hình thanh toán** (`/admin/settings/checkouts`) trên Haravan Admin (`*.myharavan.com/admin`).
- **Lý do bắt buộc dùng Browser UI:** Danh sách Đơn chưa hoàn tất trên Haravan Admin hiển thị trực tiếp trạng thái gửi email nhắc tự động (`Đã gửi` / `Chưa gửi`), trạng thái khôi phục (`Đã khôi phục` / `Chưa khôi phục`), phí vận chuyển thực tế hệ thống đã tính theo tỉnh/thành và bước khách thoát — thuận tiện chẩn đoán CRO trực tiếp mà không cần cấp API token.
- **Mục tiêu nghiệp vụ (`layer: L1`, `mode: read`, `risk: low`):** Xác định chính xác nguyên nhân rớt đơn tại bước checkout (phí ship ngoại tỉnh cao, chưa có freeship, thiếu phương thức thanh toán quen thuộc, bắt buộc đăng nhập/nhập email, hoặc SKU bị lỗi giá/tồn) và đề xuất giải pháp tối ưu chuyển đổi mà **tuyệt đối không tự gửi email hay sửa cấu hình**.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền xem danh sách đơn chưa hoàn tất và đối chiếu cấu hình `/admin/settings/checkouts`.
  - **Staff:** Yêu cầu quyền **Xem đơn hàng / Đơn hàng chưa hoàn tất** trong nhóm quyền **Đơn hàng** (`/admin/settings/group_permissions`). Để đối chiếu chéo `/admin/settings/checkouts`, cần thêm quyền xem Cấu hình thanh toán.
  - **Giới hạn gói & Kênh:** Chỉ các đơn khách đặt qua **Kênh Website** (Checkout online) mới xuất hiện tại `/admin/orders/checkouts`; đơn POS hoặc Harasocial không nằm trong màn hình này. Tính năng email nhắc đơn tự động phụ thuộc cấu hình gói Haravan và mục Thông báo.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/orders/checkouts`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Chờ bảng danh sách đơn chưa hoàn tất tải hoàn tất và xác nhận bộ lọc ngày khả dụng.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/orders/checkouts` | Thanh công cụ & Bộ lọc | `Lọc`, `Tìm kiếm`, `Xuất dữ liệu` (HARD-BLOCKED) | Bộ lọc: `Ngày tạo`, `Trạng thái gửi email` (`Đã gửi` / `Chưa gửi`), `Trạng thái khôi phục` (`Đã khôi phục` / `Chưa khôi phục`) |
| `/admin/orders/checkouts` | Bảng danh sách Đơn chưa hoàn tất | Link mã đơn `#...` để xem chi tiết | Cột: Mã đơn chưa hoàn tất, Ngày đặt, Khách hàng, Trạng thái email, Trạng thái khôi phục, Tổng tiền |
| `/admin/orders/checkouts/{id}` | Chi tiết Đơn chưa hoàn tất | `Gửi lại link đặt hàng` (HARD-BLOCKED), `Sao chép link` | Sản phẩm trong giỏ (SKU, SL, Giá), Tỉnh/Thành phố & Quận/Huyện nhận hàng, Phí vận chuyển tính được, Lịch sử gửi email nhắc, Có/Không có Email |
| `/admin/settings/checkouts` | Tham chiếu cấu hình (Read-Only) | Không click bất kỳ nút `Lưu` nào | Kiểm tra 3 mục: `Tài khoản khách hàng` (`Không bắt buộc` vs `Bắt buộc`), `Yêu cầu nhập Email/SĐT`, `Gửi email nhắc nhở đơn hàng chưa thanh toán` (`Không bao giờ` / `Sau 6 tiếng` / `Sau 24 tiếng`) |

### Quy ước Đọc Trạng thái & Tín hiệu CRO trên Haravan Admin
- **Trạng thái `Đã khôi phục`:** Chỉ ghi nhận khi khách hàng quay lại hoàn tất thanh toán đúng qua đường dẫn checkout gốc (hoặc email nhắc tự động). Các đơn khách tự đặt lại mới hoặc CSKH chốt qua Zalo sẽ vẫn hiển thị `Chưa khôi phục`.
- **Trạng thái email `Chưa gửi`:** Xảy ra trong 2 trường hợp phổ biến — (1) cửa hàng đang tắt tự động gửi email nhắc tại `/admin/settings/checkouts`, hoặc (2) khách hàng trên mobile chỉ điền SĐT và bỏ trống trường Email.
- **Ngưỡng cảnh báo CRO chuẩn eCommerce VN:** Tỷ lệ khôi phục `< 10%` hoặc tỷ lệ đơn thiếu email `> 50%` là tín hiệu cần bổ sung luồng chăm sóc qua ZNS/CSKH gọi lại cho các giỏ giá trị cao.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `full_dropoff_audit` | `full_dropoff_audit` \| `high_value_tier_filter` \| `detail_root_cause_sample` \| `checkout_settings_crosscheck` \| `cs_callback_priority` |
| `lookback_days` | `integer` | Không | `14` | Khoảng thời gian kiểm toán (`1..90` ngày) |
| `sample_detail_count` | `integer` | Không | `10` | Số lượng đơn bỏ giỏ mở xem chi tiết để chẩn đoán (`1..25`) |
| `min_cart_value_vnd` | `number` | Không | `0` | Ngưỡng lọc ưu tiên các giỏ giá trị cao (`>= 0`) |
| `check_checkout_settings` | `boolean` | Không | `true` | Nếu `true`, mở chỉ đọc `/admin/settings/checkouts` để đối chiếu cấu hình nhắc đơn |
| `max_records` | `integer` | Không | `500` | Tối đa `500` dòng đọc tổng hợp trong một phiên kiểm toán |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Kiểm toán tổng quan tỷ lệ bỏ giỏ & hiệu quả khôi phục (`full_dropoff_audit`)
- **Khi nào dùng:** Đánh giá sức khỏe phễu thanh toán Website định kỳ hàng tuần/sau chiến dịch chạy quảng cáo lớn.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/orders/checkouts` (hoặc `Ctrl+K` gõ `Chưa hoàn tất`), chụp `pre_screenshot`.
  2. Nhấn `Lọc`, chọn `Ngày tạo` trong `lookback_days` ngày gần nhất (mặc định 14 ngày).
  3. Đếm và tổng hợp tối đa `max_records: 500` bản ghi theo ma trận 2×2:
     - `Đã khôi phục` vs `Chưa khôi phục` (tính **Recovery Rate %** và **Tổng GMV bỏ giỏ ước tính**).
     - `Đã gửi email` vs `Chưa gửi email` (phát hiện tỷ lệ đơn bị lọt không gửi được email nhắc).
  4. Ghi nhận phân bổ khung giờ bỏ giỏ cao điểm (ví dụ 20h–23h buổi tối) để tối ưu lịch gửi tin nhắc và ca trực CSKH.
- **Điểm dừng an toàn:** Chỉ đọc và thống kê tổng hợp; tuyệt đối không bấm `Xuất dữ liệu`.

### Kịch bản 2: Phân tầng giá trị giỏ hàng & Lọc giỏ giá trị cao chưa nhắc (`high_value_tier_filter`)
- **Khi nào dùng:** Tìm nhanh nhóm giỏ hàng giá trị lớn đang có nguy cơ mất doanh thu cao nhất để phân tích trước.
- **Thao tác từng bước:**
  1. Tại `/admin/orders/checkouts`, kết hợp bộ lọc `Trạng thái khôi phục` = `Chưa khôi phục` và `Trạng thái gửi email` = `Chưa gửi`.
  2. Phân nhóm các đơn chưa khôi phục thành 3 tầng giá trị giỏ hàng: `< 300,000₫` (giỏ nhỏ nhạy cảm phí ship), `300,000₫ – 1,000,000₫` (phân khúc chủ lực) và `> 1,000,000₫` (giỏ giá trị cao / mua combo).
  3. Lọc riêng các đơn có tổng tiền `>= min_cart_value_vnd` (hoặc `> 1,000,000₫`) để đưa vào danh sách ưu tiên mở mẫu chi tiết.
- **Điểm dừng an toàn:** Che toàn bộ tên/SĐT khách hàng ngay khi tổng hợp bảng phân tầng.

### Kịch bản 3: Mở mẫu chi tiết đơn bỏ giỏ chẩn đoán nguyên nhân gốc rễ (`detail_root_cause_sample`)
- **Khi nào dùng:** Cần tìm nguyên nhân thực tế khiến khách dừng lại ở bước vận chuyển hoặc thanh toán thay vì đoán mò.
- **Thao tác từng bước:**
  1. Mở lần lượt tối đa `sample_detail_count` (mặc định 10) đường dẫn `/admin/orders/checkouts/{id}` ưu tiên từ giỏ giá trị cao nhất ở chế độ **chỉ đọc**.
  2. Ghi nhận 4 tín hiệu chẩn đoán trên mỗi đơn:
     - **Tỉnh/Thành phố & Phí ship tính được:** Nếu phí ship chiếm `> 15%` giá trị giỏ hàng hoặc ngoại tỉnh báo lỗi không có NVC, đánh dấu lỗi biểu phí ship.
     - **Email khách hàng:** Khách bỏ trống email (chỉ nhập SĐT) → hệ thống không gửi được email nhắc tự động.
     - **SKU lặp lại nhiều lần:** Sản phẩm xuất hiện dày đặc trong giỏ bị bỏ có thể đang thiếu thông tin size/phí ship cồng kềnh.
     - **Thời gian gửi email nhắc:** Đánh dấu nếu khách bỏ giỏ quá 24h mới nhận email nhắc (quá nguội).
- **Điểm dừng an toàn:** **TUYỆT ĐỐI KHÔNG bấm `Gửi lại link đặt hàng`** trên bất kỳ trang chi tiết nào.

### Kịch bản 4: Đối chiếu chéo cấu hình Thanh toán & Nhắc đơn tự động (`checkout_settings_crosscheck`)
- **Khi nào dùng:** Kiểm chứng xem cài đặt trang Checkout hiện tại có đang tự tạo rào cản chuyển đổi hay tắt nhắc đơn hay không.
- **Thao tác từng bước:**
  1. Khi `check_checkout_settings = true`, mở tab đọc `https://{store_domain}/admin/settings/checkouts`.
  2. Kiểm tra 3 thiết lập trọng yếu ảnh hưởng trực tiếp tới tỷ lệ rớt đơn:
     - `Tài khoản khách hàng`: Đang đặt `Bắt buộc đăng nhập` hay `Không bắt buộc`.
     - `Thông tin liên hệ`: Có bắt buộc nhập cả Email lẫn SĐT hay cho phép linh hoạt.
     - `Gửi email nhắc nhở đơn hàng chưa thanh toán`: Đang tắt (`Không bao giờ`) hay bật `Sau 6 tiếng` / `Sau 24 tiếng`.
  3. Chụp `preview_screenshot` màn hình cấu hình hiện tại làm căn cứ đề xuất tối ưu.
- **Điểm dừng an toàn:** Chỉ đọc 100%; **tuyệt đối không thay đổi radio/switch hay bấm `Lưu`**.

### Kịch bản 5: Lập danh sách ưu tiên CSKH gọi lại (Đã che PII) & Đề xuất CRO (`cs_callback_priority`)
- **Khi nào dùng:** Bàn giao danh sách cơ hội thu hồi doanh thu nhanh trong 48 giờ gần nhất cho đội CSKH và kế hoạch tối ưu cho đội Growth.
- **Thao tác từng bước:**
  1. Lập danh sách Top 10–20 giỏ giá trị cao bị bỏ trong 48 giờ gần nhất gồm: Mã đơn `#...`, Giờ bỏ giỏ, Tỉnh/Thành, Số SKU, Tổng tiền, SĐT đã che (`090****678`) để CSKH tự tra cứu và hỗ trợ trên Admin.
  2. Sắp xếp kế hoạch hành động CRO theo thứ tự tác động: (1) Bật email nhắc `Sau 6 tiếng`, (2) Mở khóa Guest Checkout, (3) Thiết lập ngưỡng Freeship, (4) Bổ sung Haravan QR/COD.
- **Điểm dừng an toàn:** Không xuất file thô CSV/Excel; không tự gửi tin nhắn ra ngoài.

## 5. Quy trình An toàn 4 Pha (4-Phase Read-Only UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Kiểm tra phiên)
- Mở `/admin/orders/checkouts`, xác nhận không bị redirect `accounts.haravan.com`.
- Áp dụng bộ lọc `lookback_days`, ghi nhận tổng số đơn bỏ giỏ và chụp `pre_screenshot`.

### Pha 2 — Read-Only Filter & Extraction (Lọc & Chẩn đoán không ghi dữ liệu)
- Thực hiện lọc phân tầng giá trị giỏ, mở mẫu chi tiết `/admin/orders/checkouts/{id}` và đối chiếu chỉ đọc `/admin/settings/checkouts`.
- Tuyệt đối không bấm `Gửi lại link đặt hàng`, `Xuất dữ liệu` hay bất kỳ nút `Lưu` nào.

### Pha 3 — Screenshot & PII Redaction Verification (Xác minh ảnh & Che PII)
- Chụp `preview_screenshot` màn hình cấu hình checkout tham chiếu.
- Rà soát che 100% PII (`090****678`, `a***@domain.com`, ẩn số nhà/tên đường) trước khi lập báo cáo.

### Pha 4 — Session Audit & Read-Only Closure (Chốt phiên chỉ đọc)
- Xác nhận `saved_verified: false`, `mode: read`, không phát sinh thao tác ghi hay gửi email.
- Bàn giao báo cáo nguyên nhân gốc rễ và gợi ý skill tiếp theo (`admin-ui-checkout-settings`, `admin-ui-shipping-carriers-setup`).

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Kiểm toán Hiện trạng vs Khuyến nghị Tối ưu (Current State → Proposed Action)

| Hạng mục kiểm toán (14 ngày) | Hiện trạng ghi nhận (Before / Current) | Mục tiêu Đề xuất (After / Target) | Tác động chuyển đổi dự kiến |
| :--- | :--- | :--- | :--- |
| Tỷ lệ khôi phục đơn bỏ giỏ | `10 / 84 đơn` (`11.9%`, mất ~`62.4M₫`) | Mục tiêu `18%–22%` (+5–8 đơn/2 tuần) | Thu hồi ước tính `4–6M₫`/chu kỳ |
| Trạng thái email nhắc đơn | `58 / 84 đơn` (`69%`) chưa gửi email | Bật nhắc tự động `Sau 6 tiếng` + ZNS khi thiếu email | Giảm 50%+ đơn bỏ quên không được nhắc |
| Phí ship khu vực ngoại tỉnh | Phí ship chiếm `18%–25%` giỏ `< 500k` | Thiết lập đồng giá ship / Freeship từ `499,000₫` | Giảm rớt đơn tại bước chọn NVC |
| Cấu hình `/admin/settings/checkouts` | Nhắc đơn: `Không bao giờ` \| Bắt buộc Email | Chuyển sang `Sau 6 tiếng` \| Guest Checkout | Chạy qua skill `admin-ui-checkout-settings` |

> **Lưu ý Read-Only:** Báo cáo chỉ thực hiện kiểm toán đọc trên Haravan Admin, không gửi email nhắc cho khách và không chỉnh sửa cấu hình. Để áp dụng khuyến nghị bật nhắc đơn sau 6 tiếng, hãy yêu cầu chạy `admin-ui-checkout-settings`.

### JSON Execution Log Schema

```json
{
  "skill": "order-abandoned-checkouts-audit",
  "scenario": "full_dropoff_audit",
  "mode": "read",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/orders/checkouts",
  "screenshots": {
    "pre": "artifacts/abandoned_checkouts_pre.png",
    "preview": "artifacts/checkout_settings_ref.png",
    "post": null
  },
  "audit_summary": {
    "lookback_days": 14,
    "total_abandoned": 84,
    "recovered_count": 10,
    "recovery_rate_pct": 11.9,
    "unnotified_email_count": 58,
    "estimated_lost_gmv_vnd": 62400000,
    "sampled_details_count": 10,
    "top_dropoff_causes": [
      "Email nhắc đơn chưa hoàn tất đang tắt",
      "Khách chỉ nhập SĐT, bỏ trống email (62% mẫu)",
      "Phí ship ngoại tỉnh cao trên giỏ < 500,000₫"
    ],
    "cart_value_tiers": {
      "under_300k": 29,
      "300k_to_1m": 38,
      "over_1m": 17
    },
    "recommended_next_skills": [
      "admin-ui-checkout-settings",
      "admin-ui-shipping-carriers-setup",
      "admin-ui-payment-methods-setup"
    ]
  },
  "pii_redacted": true,
  "saved_verified": false
}
```

### Checklist Bàn giao Đội Growth & CSKH
- [ ] Đã tách riêng danh sách giỏ `> 1,000,000₫` trong 48h gần nhất (đã che PII) cho CSKH tra cứu mã đơn trên Admin.
- [ ] Đã đối chiếu cấu hình `/admin/settings/checkouts` để xác nhận lý do tỷ lệ `Chưa gửi email` cao.
- [ ] Đã ghi nhận Top 3 tỉnh/thành có phí vận chuyển vượt `15%` giá trị giỏ hàng để tối ưu biểu phí ship.
- [ ] Xác nhận 100% phiên chỉ đọc: không bấm `Gửi lại link đặt hàng` và không bấm `Xuất dữ liệu`.

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click trong L1 Read-Only):**
  - `Gửi lại link đặt hàng` tại `/admin/orders/checkouts/{id}` (gửi email thật trực tiếp ra khách hàng).
  - `Xuất dữ liệu` tại `/admin/orders/checkouts` (tải file CSV/Excel chứa danh sách raw SĐT/email — vi phạm `export_allowed: false`).
  - Mọi nút `Lưu` hoặc toggle cấu hình khi mở tham chiếu `/admin/settings/checkouts`.
- **Credential & PII Handoff Gates:**
  - Gặp màn hình `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.
  - Bắt buộc che SĐT (`090****678`), email (`a***@domain.com`), tên đầy đủ và địa chỉ nhà riêng; chỉ giữ lại cấp Tỉnh/Thành phố phục vụ phân tích phí vận chuyển.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Danh sách trống (`Chưa có đơn hàng chưa hoàn tất`):** Kiểm tra lại bộ lọc thời gian và xác nhận cơ cấu kênh bán hàng — nếu cửa hàng bán 100% qua POS/Harasocial/Sàn TMĐT mà chưa có traffic Website thì danh sách sẽ trống.
2. **Đơn bị bỏ giỏ trùng lặp cùng 1 khách trong vài phút:** Khách bấm quay lại/nhập lại thông tin nhiều lần tạo ra 2–3 bản ghi bỏ giỏ liên tiếp → Loại trừ bản ghi trùng khi tính tổng GMV mất đi để tránh thổi phồng số liệu.
3. **Thiếu quyền Staff (ẩn mục `Chưa hoàn tất` hoặc không mở được `/admin/settings/checkouts`):** Vẫn hoàn thành phần đọc khả dụng và báo Chủ shop bổ sung quyền tại `/admin/settings/group_permissions`.
4. **Phân trang lớn (> 500 đơn trong đợt Flash Sale / Mega Sale):** Thu hẹp `lookback_days` xuống 3–7 ngày hoặc lọc theo `Trạng thái khôi phục: Chưa khôi phục` để tránh timeout trình duyệt.
5. **Khách bỏ giỏ nhưng sau đó đã đặt thành công qua kênh khác (Zalo/POS):** Luôn ghi chú tỷ lệ khôi phục trên UI chỉ tính đơn tự hoàn tất qua link checkout Website, chưa bao gồm đơn CSKH chốt tay qua kênh chat.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: false`):** Không áp dụng vì skill hoạt động 100% ở chế độ `L1 mode: read`, không ghi dữ liệu, không gửi email và không thay đổi cấu hình hệ thống.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/40-orders-fulfillment/order-status-audit` (API): Đối chiếu tỷ lệ chuyển đổi và trạng thái đơn thành công qua `GET /com/orders.json`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-checkout-settings` (UI): Bật tự động nhắc đơn `Sau 6 tiếng` và tối ưu trường nhập liệu tại `/admin/settings/checkouts`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-shipping-carriers-setup` (UI): Tối ưu biểu phí vận chuyển ngoại tỉnh và cấu hình ngưỡng freeship tại `/admin/settings/shipments`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-payment-methods-setup` (UI): Bổ sung Haravan QR / COD / Ví điện tử nếu khách bỏ giỏ tại bước thanh toán.
