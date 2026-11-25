---
name: customer-review-rating-moderation
description: "Kiểm toán đánh giá sản phẩm (/admin/customers/rating), phát hiện sớm SKU có điểm thấp (1–2 sao) và đề xuất kịch bản phản hồi CSKH."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 50-customer-crm
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: admin_ui
  scopes:
    - com.read_products
  endpoints:
    - "UI /admin/customers/rating"
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

# Haravan Product Reviews & Rating Quality Audit

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Kiểm toán toàn diện hệ thống **Quản lý đánh giá sản phẩm** tích hợp sẵn trên Haravan Admin tại `/admin/customers/rating` (`*.myharavan.com/admin`).
- **Lý do bắt buộc dùng Browser UI:** Haravan Commerce & Web REST API không cung cấp endpoint công khai để đọc danh sách đánh giá sao, ảnh chụp khách hàng đính kèm và trạng thái kiểm duyệt/phản hồi tại `/admin/customers/rating`.
- **Mục tiêu nghiệp vụ (`layer: L1`, `mode: read`, `risk: low`):** Phát hiện sớm các đánh giá tiêu cực (`1–3 sao`), truy vết cụm SKU đang gặp lỗi chất lượng/đóng gói/mô tả sai bảng size, cô lập đánh giá nghi ngờ spam/link lừa đảo và soạn sẵn mẫu phản hồi CSKH chuẩn tiếng Việt để đội CSKH kiểm duyệt trước khi đăng — **tuyệt đối không tự ẩn, xóa hay tự gửi câu trả lời**.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền xem, duyệt, ẩn, xóa và phản hồi đánh giá sản phẩm.
  - **Staff:** Yêu cầu quyền **Xem Khách hàng / Quản lý đánh giá** trong `/admin/settings/group_permissions`.
  - **Lưu ý ứng dụng bên thứ 3:** Một số cửa hàng không dùng tính năng đánh giá gốc của Haravan mà cài app ngoài (ví dụ Judge.me, Loox, Haravan Product Reviews app cũ trong `/admin/apps`). Nếu `/admin/customers/rating` trống dữ liệu dù website có đánh giá, cần kiểm tra chéo danh sách app đã cài.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/customers/rating`.
  2. Nếu bị redirect về `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Chờ bảng danh sách đánh giá và các tab trạng thái (`Tất cả`, `Chờ duyệt`, `Đã duyệt`, `Đã ẩn`) tải hoàn tất.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/customers/rating` | Thanh Tab trạng thái | `Tất cả`, `Chờ duyệt`, `Đã duyệt`, `Đã ẩn` | Đếm số lượng đánh giá theo từng trạng thái kiểm duyệt |
| `/admin/customers/rating` | Thanh Bộ lọc & Tìm kiếm | `Lọc`, `Tìm kiếm` | Bộ lọc: `Số sao` (1★, 2★, 3★, 4★, 5★), `Trạng thái phản hồi` (`Chưa trả lời` / `Đã trả lời`), `Sản phẩm`, `Khoảng thời gian` |
| `/admin/customers/rating` | Bảng danh sách Đánh giá | `Trả lời` (HARD-BLOCKED gửi), `Duyệt` / `Hiển thị` (CẤM tự bấm), `Ẩn` (HARD-BLOCKED), `Xóa` (HARD-BLOCKED) | Cột: Sản phẩm, Số sao (1–5★), Nội dung đánh giá, Ảnh đính kèm (thumbnail), Khách hàng, Ngày đánh giá, Trạng thái duyệt & phản hồi |
| `/admin/customers/rating` | Khung Chi tiết / Phản hồi | `Gửi trả lời` (HARD-BLOCKED trong L1) | Toàn văn nhận xét của khách, ảnh thực tế khách chụp, lịch sử phản hồi từ cửa hàng |

### Nguyên tắc Kiểm duyệt & Quản trị Uy tín Đánh giá
- **Không ẩn/xóa đánh giá thật:** Mọi đánh giá 1–3 sao phản ánh trải nghiệm thực tế của người mua đều là dữ liệu cải thiện sản phẩm/vận hành; chỉ đề xuất cô lập (`suspected_spam`) các bình luận chứa link lạ, nội dung rác hoặc công kích phi thực tế.
- **SLA phản hồi khuyến nghị:** Đánh giá 1–2 sao nên được đội CSKH kiểm duyệt và phản hồi công khai trong vòng `< 24 giờ` để chuyển hóa khủng hoảng thành điểm cộng uy tín cho khách mua sau.
- **Khử nhạy cảm trước khi xuất báo cáo:** Ảnh khách hàng chụp thường dính tem vận đơn có SĐT/địa chỉ — chỉ mô tả tình trạng lỗi sản phẩm/bao bì, không chép dữ liệu trên nhãn giao hàng.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `low_rating_triage` | `rating_health_overview` \| `low_rating_triage` \| `sku_defect_cluster` \| `cs_reply_drafting` \| `spam_isolation_audit` |
| `low_rating_threshold` | `integer` | Không | `3` | Ngưỡng số sao cần cảnh báo và phân tích nguyên nhân (`1..3`) |
| `filter_status` | `string` | Không | `all` | `all` (`Tất cả`) \| `pending` (`Chờ duyệt`) \| `unreplied` (`Chưa trả lời`) |
| `brand_tone` | `string` | Không | `empathetic_professional` | Giọng điệu mẫu phản hồi CSKH: `empathetic_professional`, `friendly`, `formal` |
| `support_channel_text` | `string` | Không | `Zalo OA / Hotline CSKH` | Kênh liên hệ đính kèm cuối câu trả lời đề xuất để xử lý đổi trả riêng |
| `max_reviews_to_draft` | `integer` | Không | `20` | Số lượng đánh giá tiêu cực tối đa soạn mẫu phản hồi trong 1 lượt (`1..50`) |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Quét tổng quan sức khỏe đánh giá & Tồn đọng kiểm duyệt (`rating_health_overview`)
- **Khi nào dùng:** Kiểm tra nhanh tình trạng tồn đọng đánh giá mới, tỷ lệ phản hồi của đội CSKH và điểm trung bình toàn cửa hàng hàng tuần.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/customers/rating` (hoặc `Ctrl+K` gõ `Quản lý đánh giá`), chụp `pre_screenshot`.
  2. Đọc số liệu tổng quan trên 4 tab trạng thái: `Tất cả`, `Chờ duyệt`, `Đã duyệt`, `Đã ẩn` để phát hiện tồn đọng kiểm duyệt.
  3. Kết hợp bộ lọc `Trạng thái phản hồi` = `Chưa trả lời` và từng mức `Số sao` (1★–5★) trên tập mẫu tối đa `max_records: 500` bản ghi.
  4. Tính tỷ lệ phản hồi CSKH và gắn cờ cảnh báo nếu tỷ trọng đánh giá `1–2★` vượt ngưỡng 5% tổng đánh giá gần đây.
- **Điểm dừng an toàn:** Chỉ đọc số liệu; không tự bấm `Duyệt` hàng loạt.

### Kịch bản 2: Lọc & Phân nhóm nguyên nhân đánh giá tiêu cực 1–2 sao (`low_rating_triage`)
- **Khi nào dùng:** Phân loại gốc rễ khiếu nại khách hàng để giao đúng đầu việc cải thiện cho Kho, Sản phẩm, Vận chuyển hay CSKH.
- **Thao tác từng bước:**
  1. Nhấn `Lọc`, chọn `Số sao <= low_rating_threshold` (ưu tiên lọc riêng `1 sao` và `2 sao`) kết hợp `filter_status` (`Chưa trả lời` / `Chờ duyệt`).
  2. Chụp `preview_screenshot` danh sách đánh giá tiêu cực đã lọc để đội CSKH dễ đối chiếu trực tiếp.
  3. Đọc từng nhận xét và phân vào đúng 5 nhãn nguyên nhân chuẩn:
     - `product_quality`: Lỗi đường may, bung keo, hỏng hóc, chất liệu sai cam kết.
     - `description_mismatch`: Sai bảng size, màu thực tế lệch ảnh web, thiếu thông số.
     - `packaging_damage`: Móp méo hộp, đổ vỡ, thiếu phụ kiện/quà tặng khi mở kiện.
     - `delivery_delay`: Giao hàng chậm, thái độ shipper kém, không cho xem hàng.
     - `service_cs`: Hỗ trợ sau bán chậm, tư vấn sai hoặc quy trình đổi trả rườm rà.
- **Điểm dừng an toàn:** Không bấm `Ẩn` hay `Xóa` bất kỳ đánh giá tiêu cực nào.

### Kịch bản 3: Truy vết cụm SKU bị đánh giá thấp lặp lại & Kiểm tra ảnh đính kèm (`sku_defect_cluster`)
- **Khi nào dùng:** Phát hiện sớm một lô hàng lỗi, lỗi đóng gói theo SKU hoặc sản phẩm cần sửa mô tả/bảng size ngay trên Website.
- **Thao tác từng bước:**
  1. Gom toàn bộ đánh giá `<= low_rating_threshold` theo **Tên sản phẩm / SKU** để tìm mã hàng nhận từ `>= 2` đánh giá thấp gần đây.
  2. Quan sát cột **Ảnh đính kèm** (chỉ đọc) trên các đánh giá 1–2★ của nhóm SKU đó để xác nhận lỗi hệ thống (cùng lỗi móp góc, lệch form size).
  3. Lập danh sách **SKU Cảnh báo Đỏ** kèm khuyến nghị hành động rõ ràng cho Kho, Merchandising hoặc Nhà cung cấp.
- **Điểm dừng an toàn:** Không trích xuất thông tin cá nhân trên tem vận đơn trong ảnh khách chụp.

### Kịch bản 4: Soạn thảo hàng loạt kịch bản phản hồi CSKH theo `brand_tone` (`cs_reply_drafting`)
- **Khi nào dùng:** Hỗ trợ đội CSKH phản hồi nhanh, đồng nhất giọng điệu và chuyên nghiệp cho tồn đọng đánh giá 1–3 sao.
- **Thao tác từng bước:**
  1. Chọn tối đa `max_reviews_to_draft` (≤ 50) đánh giá tiêu cực `Chưa trả lời`, ưu tiên đánh giá mới nhất và đánh giá có ảnh thực tế.
  2. Soạn mẫu câu trả lời tiếng Việt cá nhân hóa theo đúng `brand_tone` gồm 4 phần: (1) Xưng hô lịch sự với tên đã che, (2) Xin lỗi chân thành & ghi nhận đúng vấn đề, (3) Đề xuất phương án đổi trả/bảo hành, (4) Mời nhắn qua `support_channel_text` kèm mã đơn hàng.
  3. Trình bày dạng bảng so sánh nhận xét vs câu trả lời đề xuất để CSKH duyệt.
- **Điểm dừng an toàn:** **TUYỆT ĐỐI KHÔNG bấm `Trả lời` / `Gửi trả lời`** trên giao diện Admin.

### Kịch bản 5: Phát hiện & Cô lập đánh giá nghi ngờ spam / link lừa đảo (`spam_isolation_audit`)
- **Khi nào dùng:** Lọc sạch các bình luận rác, chứa đường dẫn lạ hoặc seeding bất thường trước khi đội CSKH duyệt hiển thị.
- **Thao tác từng bước:**
  1. Rà soát tab `Chờ duyệt` và `Tất cả` để nhận diện bình luận chứa link lạ/cờ bạc/SĐT rác, nội dung sao chép y hệt trên nhiều sản phẩm, hoặc công kích không liên quan đến hàng hóa.
  2. Gắn nhãn `suspected_spam` kèm trích đoạn ngắn trong báo cáo để Chủ shop/CSKH tự xem xét và quyết định `Ẩn`/`Xóa`.
- **Điểm dừng an toàn:** Không tự bấm `Ẩn` hay `Xóa`; giữ quyền quyết định cuối cùng cho Chủ shop.

## 5. Quy trình An toàn 4 Pha (4-Phase Read-Only UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Kiểm tra nguồn đánh giá)
- Mở `/admin/customers/rating`, xác nhận phiên đăng nhập hợp lệ (không redirect `accounts.haravan.com`).
- Kiểm tra xem đánh giá có đang lưu tại module gốc hay app ngoài (`/admin/apps`), chụp `pre_screenshot`.

### Pha 2 — Read-Only Filter & Extraction (Lọc & Soạn mẫu không ghi dữ liệu)
- Lọc theo số sao và trạng thái phản hồi, đọc nhận xét, phân nhóm 5 nguyên nhân chuẩn và soạn sẵn mẫu phản hồi ngoài bộ nhớ.
- Tuyệt đối không bấm `Ẩn`, `Xóa`, `Duyệt` hay `Gửi trả lời`.

### Pha 3 — Screenshot & PII Redaction Verification (Xác minh ảnh & Che PII)
- Chụp `preview_screenshot` danh sách đánh giá thấp đã lọc.
- Che toàn bộ tên đầy đủ (`N***`), SĐT (`090****678`) và email (`a***@domain.com`) trong báo cáo.

### Pha 4 — Session Audit & Read-Only Closure (Chốt phiên chỉ đọc)
- Xác nhận 100% thao tác chỉ đọc (`saved_verified: false`, `mode: read`).
- Bàn giao bảng SKU cảnh báo đỏ và mẫu câu trả lời để đội CSKH kiểm duyệt và tự phản hồi trên Haravan Admin.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Kiểm toán Đánh giá Thấp & Mẫu Phản hồi CSKH (Current Review → Proposed Reply)

| Sản phẩm | Sao | Nguyên nhân | Tóm tắt nhận xét (Đã che PII) | Mẫu phản hồi CSKH Đề xuất (Chờ duyệt) |
| :--- | :--- | :--- | :--- | :--- |
| Áo sơ mi Linen Trắng | 2★ | `description_mismatch` | Form rộng hơn bảng size, mặc hơi thùng thình | *"Chào bạn N***, shop rất tiếc vì trải nghiệm size chưa vừa ý ạ. Dòng Linen form relaxed nên rộng hơn chuẩn 1 size. Shop hỗ trợ đổi size miễn phí trong 7 ngày, bạn nhắn giúp shop qua Zalo OA / Hotline CSKH để xử lý ngay nhé!"* |
| Bình giữ nhiệt 500ml | 1★ | `packaging_damage` | Hộp móp góc, có ảnh chụp kiện rách | *"Chào bạn T***, shop thành thật xin lỗi vì khâu vận chuyển làm ảnh hưởng hộp sản phẩm. Shop xin đổi mới 100% sản phẩm nguyên vẹn, bạn gửi giúp mã đơn qua Zalo OA / Hotline CSKH để shop gửi bù ngay ạ!"* |
| Ví da nam Classic | 1★ | `suspected_spam` | Bình luận chứa link lạ không liên quan SP | *(Không phản hồi công khai — Đề xuất Chủ shop tự kiểm tra và bấm `Ẩn`)* |

> **Lưu ý Read-Only:** Agent chỉ đọc, phân nhóm và soạn sẵn mẫu phản hồi. Không có đánh giá nào bị ẩn, xóa hay tự động gửi câu trả lời trên `/admin/customers/rating`.

### JSON Execution Log Schema

```json
{
  "skill": "customer-review-rating-moderation",
  "scenario": "low_rating_triage",
  "mode": "read",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/customers/rating",
  "screenshots": {
    "pre": "artifacts/reviews_pre.png",
    "preview": "artifacts/reviews_low_rating_filtered.png",
    "post": null
  },
  "audit_summary": {
    "low_rating_threshold": 3,
    "scanned_reviews_count": 145,
    "pending_moderation_count": 6,
    "total_low_ratings_found": 12,
    "unreplied_low_ratings_count": 7,
    "suspected_spam_count": 1,
    "by_category": {
      "product_quality": 2,
      "description_mismatch": 4,
      "packaging_damage": 3,
      "delivery_delay": 2,
      "service_cs": 0
    },
    "red_alert_skus": [
      { "product": "Áo sơ mi Linen Trắng", "low_rating_count": 4, "primary_cause": "description_mismatch" },
      { "product": "Bình giữ nhiệt 500ml", "low_rating_count": 3, "primary_cause": "packaging_damage" }
    ],
    "drafted_replies_count": 7,
    "brand_tone": "empathetic_professional"
  },
  "pii_redacted": true,
  "saved_verified": false
}
```

### Checklist Bàn giao Đội CSKH & Vận hành Sản phẩm
- [ ] Đã duyệt lại toàn bộ mẫu câu trả lời CSKH trước khi nhân viên tự đăng công khai trên `/admin/customers/rating`.
- [ ] Đã chuyển danh sách SKU lỗi `description_mismatch` sang đội Merchandising cập nhật bảng size/ảnh thật PDP.
- [ ] Đã chuyển danh sách SKU lỗi `packaging_damage` sang Kho rà soát quy chuẩn bọc chống sốc.
- [ ] Đã cô lập riêng mục `suspected_spam` để Chủ shop tự kiểm tra và quyết định `Ẩn`/`Xóa`.
- [ ] Xác nhận 100% phiên chỉ đọc: không có đánh giá nào bị ẩn/xóa hoặc tự động gửi phản hồi.

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click trong L1 Read-Only):**
  - `Xóa` / `Ẩn` đối với đánh giá của khách hàng (nguy cơ mất dữ liệu phản hồi thật và vi phạm tính minh bạch).
  - `Gửi trả lời` / `Trả lời` công khai khi CSKH chưa kiểm duyệt ngữ điệu và chính sách bồi hoàn/đổi trả.
  - `Duyệt` / `Hiển thị` hàng loạt khi chưa lọc spam/nội dung vi phạm.
- **Credential & PII Handoff Gates:**
  - Gặp màn hình `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.
  - Che toàn bộ họ tên đầy đủ (`N***`), SĐT (`090****678`), email (`a***@domain.com`) trong báo cáo; không sao chép hay phát tán ảnh cá nhân có mặt khách hàng.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Màn hình `/admin/customers/rating` trống dữ liệu dù website có đánh giá:** Cửa hàng có thể đang dùng app đánh giá bên thứ 3 (Judge.me, Loox, app đối tác) → Kiểm tra chỉ đọc `/admin/apps` để xác nhận tên app và báo rõ cho người dùng.
2. **Thiếu quyền Staff (ẩn menu `Quản lý đánh giá` dưới `Khách hàng`):** Báo Chủ shop bổ sung quyền xem đánh giá tại `/admin/settings/group_permissions`.
3. **Đánh giá tiêu cực có đính kèm ảnh chụp lỗi nhạy cảm (mã vận đơn lộ SĐT/địa chỉ khách):** Không trích xuất thông tin cá nhân trên nhãn vận đơn trong ảnh, chỉ mô tả tình trạng sản phẩm/hộp hàng.
4. **Đánh giá 5 sao nhưng nội dung chê bai (hoặc 1 sao nhưng khen nhầm):** Khi đọc mẫu, kiểm tra chéo nội dung text với số sao; nếu phát hiện khách chấm nhầm 1 sao nhưng nội dung khen, đề xuất CSKH nhắn tin cảm ơn và hướng dẫn nhẹ nhàng (không ép sửa).
5. **Khối lượng đánh giá quá lớn (> 500 bản ghi):** Luôn lọc trước theo `Số sao <= 3` và `Chưa trả lời` để tối ưu tốc độ quét thay vì duyệt qua hàng trăm đánh giá 5 sao.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: false`):** Không áp dụng vì skill vận hành hoàn toàn ở chế độ `L1 mode: read`, không ẩn, xóa hay đăng câu trả lời nào trên Haravan Admin.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/20-catalog-merchandising/catalog-product-audit` (API): Cập nhật bảng size, mô tả chi tiết cho các SKU bị phản hồi `description_mismatch`.
  - `skills/api-mcp/40-orders-fulfillment/fulfillment-carrier-sla-vn` (API): Kiểm toán SLA và tỷ lệ hư hại theo từng NVC nếu nguyên nhân 1–2 sao tập trung vào `delivery_delay` / `packaging_damage`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-crm-flows-broadcast` (UI): Thiết lập Flow tự động chăm sóc sau mua và xin đánh giá tại `/admin/customers/flows`, đồng thời loại trừ khách đang khiếu nại khỏi chiến dịch Broadcast bán hàng.
