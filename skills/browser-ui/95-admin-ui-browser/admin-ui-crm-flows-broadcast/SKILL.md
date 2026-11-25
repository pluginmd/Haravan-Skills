---
name: admin-ui-crm-flows-broadcast
description: "Vận hành CRM nâng cao trên Admin UI: Nhóm khách hàng (/admin/customers/segments), Broadcast (/admin/customers/broadcast_campaigns), Kịch bản tự động (/admin/customers/flows) và Thành viên."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 95-admin-ui-browser
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/customers/segments"
    - "UI /admin/customers/broadcast_campaigns"
    - "UI /admin/customers/flows"
    - "UI /admin/customers/rating"
    - "UI /admin/customers/settings"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Admin UI: Segments, Broadcasts, Auto Flows & Member Tiers

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Bao phủ 5 màn hình CRM tích hợp trên Haravan Admin (`*.myharavan.com/admin`): **Nhóm khách hàng** (`/admin/customers/segments`), **Chiến dịch Broadcast** (`/admin/customers/broadcast_campaigns`), **Kịch bản tự động** (`/admin/customers/flows`), **Cấu hình thành viên** (`/admin/customers/settings`) và đối chiếu **Quản lý đánh giá** (`/admin/customers/rating`).
- **Lý do bắt buộc dùng Browser UI:** Haravan REST API không có endpoint công khai để tạo bộ lọc phân nhóm động (Dynamic Segments), soạn chiến dịch Broadcast (Email/ZNS/SMS), vẽ sơ đồ Kịch bản tự động (Automation Flows) hay thiết lập quy tắc tích điểm hạng thành viên.
- **Mục tiêu nghiệp vụ (`layer: L2`, `mode: proposal`):** Chuẩn bị bản nháp (Draft) phân nhóm RFM/hành vi, soạn nội dung Broadcast/Flow và đề xuất cấu hình hạng thành viên để đội Marketing/CRM kiểm duyệt — **tuyệt đối không tự ý gửi tin hàng loạt hay kích hoạt Flow** gây spam khách hàng hoặc phát sinh cước ZNS/SMS.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền tạo/sửa/xóa nhóm, chiến dịch, kịch bản tự động và cấu hình thành viên.
  - **Staff:** Cần quyền **Khách hàng** và **Marketing / CRM** trong `/admin/settings/group_permissions`.
  - **Giới hạn gói Haravan (QUAN TRỌNG):**
    - Gói **Standard / Pro / Advanced:** Giới hạn tối đa **10 nhóm khách hàng** tại `/admin/customers/segments`; số lượng Flow và kênh gửi ZNS/SMS bị giới hạn theo gói.
    - Gói **Grow / Scale / Omnichannel:** Hỗ trợ tối đa **200 nhóm khách hàng** và đầy đủ Automation Flows đa kênh. Nếu chạm trần hạn mức, dừng và báo người dùng, **cấm bấm `Nâng cấp gói`**.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở route đích (ví dụ `https://{store_domain}/admin/customers/segments`).
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Kiểm tra chỉ số hạn mức hiện tại (`x/10` hoặc `x/200` nhóm) và tình trạng kết nối kênh gửi (Email/Zalo OA/SMS Brandname).

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Cross-Origin Iframe (Live-Verified):** Toàn bộ `/admin/customers/{segments,broadcast_campaigns,flows,rating,settings}` nhúng `https://customers.haravan.app` (mục `broadcast_campaigns` có thể yêu cầu nâng cấp gói). Nếu sandbox browser ẩn iframe, dùng `skills/api-mcp/50-customer-crm/` hoặc thao tác trên Claude in Chrome.


| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/customers/segments` | Danh sách Nhóm khách hàng | `Tạo nhóm khách hàng`, `Lọc`, `Tìm kiếm`, `Lưu` | Bộ lọc: `Loại nhóm` (`Tự động` / `Cố định`). Cột: Tên nhóm, Loại nhóm, Số lượng khách hàng, Ngày cập nhật, Hạn mức (`x/10` hoặc `x/200`) |
| `/admin/customers/broadcast_campaigns` | Chiến dịch Broadcast | `Tạo chiến dịch`, `Lưu nháp`, `Gửi ngay` (HARD-BLOCKED), `Lên lịch gửi` (HARD-BLOCKED) | Bộ lọc: `Trạng thái` (`Bản nháp` / `Đã lên lịch` / `Đã gửi`), `Kênh gửi` (`Email` / `ZNS` / `SMS`). Cột: Tên chiến dịch, Kênh, Tập nhận, Tỷ lệ mở/click |
| `/admin/customers/flows` | Kịch bản tự động (Flows) | `Tạo kịch bản`, `Lưu nháp`, `Kích hoạt` (HARD-BLOCKED), `Tắt` | Bộ lọc: `Trạng thái` (`Đang hoạt động` / `Bản nháp` / `Ngừng hoạt động`). Cột: Tên kịch bản, Trigger sự kiện, Số lượt chạy, Tỷ lệ chuyển đổi |
| `/admin/customers/settings` | Cấu hình thành viên | `Lưu`, `Thêm hạng thành viên`, Toggle bật/tắt tích điểm | Cấu hình: Quy tắc tích điểm (`X VND = 1 điểm`), Quy đổi điểm giảm giá, Điều kiện lên/giữ hạng (`Bạc`, `Vàng`, `Kim cương`), Ưu đãi sinh nhật |
| `/admin/customers/rating` | Quản lý đánh giá (Tham chiếu) | `Tất cả`, `Chờ duyệt`, `Đã duyệt`, `Lọc` | Bộ lọc: `Số sao` (1–5★), `Trạng thái phản hồi`. Dùng đối chiếu trải nghiệm khách trước khi chạy chiến dịch chăm sóc |

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `segment_create` | `segment_create` \| `broadcast_draft` \| `flow_draft` \| `member_tiers_config` \| `crm_health_audit` |
| `item_name` | `string` | Khi tạo mới | — | Tên Nhóm / Chiến dịch / Kịch bản, không trùng tên đang tồn tại (3–100 ký tự) |
| `segment_type` | `string` | Khi `segment_create` | `dynamic` | `dynamic` (Nhóm tự động theo điều kiện) hoặc `static` (Nhóm cố định) |
| `segment_conditions` | `array<object>` | Khi `dynamic` | `[]` | Mảng điều kiện `{field, operator, value}` kết hợp `AND` / `OR` (ví dụ `total_spent >= 5000000`) |
| `target_segment_name` | `string` | Khi `broadcast`/`flow` | — | Phải khớp chính xác tên nhóm đã tồn tại tại `/admin/customers/segments` |
| `channel` | `string` | Khi `broadcast_draft` | `Email` | `Email` \| `ZNS` \| `SMS` (cảnh báo chi phí nếu `ZNS` hoặc `SMS`) |
| `message_template` | `string` | Khi `broadcast`/`flow` | — | Tiêu đề & nội dung tin nhắn dự thảo, có biến cá nhân hóa (`{{customer_name}}`) |
| `loyalty_rules` | `object` | Khi `member_tiers_config` | `{}` | Tỷ lệ tích điểm, ngưỡng chi tiêu lên hạng và % ưu đãi từng hạng |
| `dry_run` | `boolean` | Có | `true` | Luôn bắt buộc `true` trước khi bấm `Lưu` / `Lưu nháp` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Tạo Nhóm khách hàng tự động / cố định tại `/admin/customers/segments`
- **Khi nào dùng:** Phân nhóm khách VIP, khách có nguy cơ rời bỏ (at-risk), hoặc nhóm đại lý B2B để dùng chung cho Broadcast, Flow và Bảng giá riêng.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/customers/segments`, kiểm tra chỉ số hạn mức nhóm (`x/10` ở gói Standard/Pro/Advanced hoặc `x/200` ở gói Grow/Scale) và chụp `pre_screenshot`.
  2. Nếu đã chạm trần hạn mức (ví dụ `10/10`), **dừng ngay**, liệt kê các nhóm cũ có `0 khách hàng` hoặc không gắn Flow/Bảng giá để người dùng tự cân nhắc dọn dẹp (cấm bấm `Nâng cấp gói`).
  3. Click `Tạo nhóm khách hàng`, nhập `item_name` (theo quy ước không dấu/rõ mục đích), chọn loại nhóm: `Nhóm tự động` (cập nhật động theo `segment_conditions`) hoặc `Nhóm cố định` (gán thủ công).
  4. Với `Nhóm tự động`, thêm lần lượt từng điều kiện (ví dụ: `Tổng chi tiêu >= 5,000,000`, `Số đơn hàng >= 3`, `Ngày mua gần nhất trong vòng 90 ngày`), chọn chính xác toán tử `Thỏa mãn tất cả (AND)` hoặc `Thỏa mãn bất kỳ (OR)`.
  5. Chờ hệ thống tính toán và hiển thị **Số lượng khách hàng ước tính** khớp điều kiện; kiểm tra số lượng hợp lý (không bị `0` hoặc `100%` toàn bộ khách do sai toán tử).
- **Điểm dừng an toàn:** **DỪNG LẠI — CHƯA BẤM `Lưu`**, chụp `preview_screenshot` và trình bày bảng duyệt.

### Kịch bản 2: Soạn Chiến dịch Broadcast dạng Draft tại `/admin/customers/broadcast_campaigns`
- **Khi nào dùng:** Chuẩn bị chiến dịch tri ân VIP, thông báo ra mắt BST mới hoặc nhắc mã giảm giá sắp hết hạn qua Email/ZNS/SMS.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/customers/broadcast_campaigns`, kiểm tra lịch sử 5 chiến dịch gần nhất để tránh gửi dồn dập (marketing fatigue) và chụp `pre_screenshot`.
  2. Click `Tạo chiến dịch`, nhập `item_name` theo chuẩn `[YYYYMM]-[Kenh]-[MucTieu]`, chọn kênh gửi (`Email` / `ZNS` / `SMS`).
  3. Tại mục **Đối tượng nhận**, chọn chính xác `target_segment_name`; ghi nhận số lượng khách hàng hợp lệ có email/SĐT đăng ký nhận tin (opt-in).
  4. Nhập tiêu đề, nội dung từ `message_template` (hoặc chọn template ZNS đã được Zalo phê duyệt nếu gửi qua `ZNS`), gắn biến cá nhân hóa (`{{customer_name}}`) và link đích có UTM tracking.
  5. Kiểm tra bảng **Ước tính chi phí gửi tin** (đặc biệt khi gửi `ZNS` / `SMS` trả phí theo tin nhắn).
- **Điểm dừng an toàn:** **TUYỆT ĐỐI CHƯA BẤM `Gửi ngay` hay `Lên lịch gửi`**, chỉ chuẩn bị lưu ở chế độ **Bản nháp**, chụp `preview_screenshot`.

### Kịch bản 3: Thiết lập Kịch bản tự động (Flow) dạng Draft tại `/admin/customers/flows`
- **Khi nào dùng:** Tự động hóa chăm sóc khách hàng sau mua (Post-Purchase), chúc mừng sinh nhật, nhắc bỏ giỏ hoặc kéo lại khách ngủ đông 60–90 ngày.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/customers/flows`, rà soát các Flow đang ở trạng thái `Đang hoạt động` để tránh tạo 2 Flow cùng trigger gây gửi tin trùng lặp cho cùng 1 khách; chụp `pre_screenshot`.
  2. Click `Tạo kịch bản`, nhập `item_name` và chọn Trigger sự kiện (ví dụ: `Đơn hàng hoàn tất`, `Khách bỏ giỏ hàng`, `Trước ngày sinh nhật 3 ngày`, `Khách không mua lại sau 60 ngày`).
  3. Thiết lập nút **Điều kiện rẽ nhánh** (ví dụ: `Giá trị đơn >= 500,000₫` hoặc `Không có tag cs-pending`) và thiết lập nút **Thời gian chờ** (`Đợi 24 giờ` / `Đợi 3 ngày`).
  4. Cấu hình nút **Hành động** (Gửi Email/ZNS theo `message_template`, tự động gắn tag chăm sóc) và kiểm tra sơ đồ không có nhánh cụt hoặc vòng lặp vô hạn.
- **Điểm dừng an toàn:** Giữ nguyên trạng thái **Bản nháp (Tắt)**, **TUYỆT ĐỐI KHÔNG bấm `Kích hoạt`**, chụp `preview_screenshot` toàn bộ sơ đồ Flow.

### Kịch bản 4: Cấu hình Hạng thành viên & Tích điểm tại `/admin/customers/settings`
- **Khi nào dùng:** Thiết lập hoặc cập nhật chương trình khách hàng thân thiết (Loyalty) gồm tỷ lệ tích điểm và quyền lợi các hạng Bạc / Vàng / Kim cương.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/customers/settings`, ghi nhận đầy đủ cấu hình tích điểm và bảng hạng thành viên hiện có, chụp `pre_screenshot`.
  2. Rà soát mục **Quy tắc tích điểm**: nhập tỷ lệ quy đổi (`X VND = 1 điểm`), thời hạn hết hạn điểm và tùy chọn loại trừ đơn hàng khuyến mãi sâu.
  3. Rà soát mục **Hạng thành viên**: click `Thêm hạng thành viên` hoặc điều chỉnh ngưỡng chi tiêu/điểm tích lũy cho từng hạng (`Thành viên`, `Bạc`, `Vàng`, `Kim cương`) và % ưu đãi tương ứng từ `loyalty_rules`.
  4. Đánh giá tác động ngược: cảnh báo rõ nếu việc nâng ngưỡng chi tiêu có thể khiến nhóm khách VIP hiện hữu bị tụt hạng đột ngột trong kỳ xét hạng tiếp theo.
- **Điểm dừng an toàn:** **DỪNG LẠI — CHƯA BẤM `Lưu`**, chụp `preview_screenshot` toàn bộ bảng quy tắc tích điểm và hạng thành viên.

### Kịch bản 5: Audit nhanh Sức khỏe CRM & Đối chiếu Đánh giá tại `/admin/customers/rating` (Read-Only)
- **Khi nào dùng:** Trước khi chạy chiến dịch Broadcast bán hàng lớn, cần kiểm tra chéo sức khỏe phân nhóm và loại trừ khách đang khiếu nại.
- **Thao tác từng bước:**
  1. Mở `/admin/customers/segments` và `/admin/customers/flows` (chỉ đọc) để thống kê tỷ lệ sử dụng hạn mức nhóm, số Flow đang chạy và tỷ lệ mở/click của 5 chiến dịch Broadcast gần nhất.
  2. Điều hướng sang `/admin/customers/rating`, lọc nhanh đánh giá `1–2 sao` chưa phản hồi trong 30 ngày gần nhất.
  3. Khuyến nghị loại trừ nhóm khách đang có khiếu nại chưa xử lý (`cs-pending`) khỏi chiến dịch Broadcast quảng cáo để tránh gây phản cảm.
- **Điểm dừng an toàn:** 100% chỉ đọc, không lưu hay kích hoạt bất kỳ thay đổi nào.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Hạn mức gói)
- Mở đúng route CRM theo `scenario`, xác nhận phiên đăng nhập hợp lệ (không redirect `accounts.haravan.com`).
- Kiểm tra hạn mức nhóm (`x/10` hoặc `x/200`), rà soát trùng tên và các Flow/Chiến dịch đang chạy, chụp `pre_screenshot`.

### Pha 2 — Stage Without Saving (Dựng bản nháp không gửi tin)
- Điền điều kiện phân nhóm, soạn nội dung Broadcast, dựng sơ đồ Flow hoặc nhập bảng hạng thành viên trên giao diện.
- Tuyệt đối không bấm `Lưu`, `Gửi ngay`, `Lên lịch gửi` hay `Kích hoạt`.

### Pha 3 — Screenshot-Before-Save & Human Approval Gate (Duyệt trước khi lưu)
- Chụp `preview_screenshot` thể hiện rõ quy mô tập khách hàng mục tiêu và ước tính chi phí ZNS/SMS (nếu có).
- Che toàn bộ PII mẫu, lập bảng `Before → After` và dừng chờ người dùng xác nhận tường minh.

### Pha 4 — Save Draft & Post-Save Reload Verification (Lưu nháp & Reload xác minh)
- Sau khi người dùng xác nhận, chỉ bấm `Lưu` (cho `segments`/`member_tiers_config`) hoặc `Lưu nháp` (cho `broadcast`/`flows`).
- Chờ toast thành công, nhấn `F5` reload trang xác minh trạng thái an toàn (**Bản nháp / Chưa gửi / Chưa kích hoạt**) và chụp `post_screenshot`.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Preview Before → After (CRM Staging)

| Hạng mục / Route | Trước (Before) | Bản nháp Đề xuất (After) | Quy mô & Cảnh báo |
| :--- | :--- | :--- | :--- |
| `/admin/customers/segments` | Đang dùng `4/10` nhóm (Gói Pro) | Tạo nhóm tự động `VIP-ChiTieu-Tren-5Tr` | Khớp **`142 khách hàng`** (Tổng chi ≥ 5tr & ≥ 3 đơn) |
| `/admin/customers/broadcast_campaigns` | *(Chưa có)* | `202611-Email-TriAnVIP` (**Bản nháp**) | Kênh Email (`0₫` phí ZNS) — **Chưa gửi** |
| `/admin/customers/flows` | `2` Flow đang chạy | `Flow-ChamSoc-SauMua-7Ngay` (**Bản nháp/Tắt**) | Không trùng trigger với Flow cũ — **Chưa kích hoạt** |
| `/admin/customers/settings` | Chưa bật hạng Kim cương | Thêm hạng `Kim cương` (≥ 20,000,000₫, giảm 10%) | Chờ xác nhận trước khi bấm `Lưu` |

> **Yêu cầu xác nhận:** Đã dựng sẵn nhóm khách hàng `VIP-ChiTieu-Tren-5Tr` (`142 khách`) và bản nháp chiến dịch trên Haravan Admin (chưa lưu). Vui lòng xác nhận **"Đồng ý lưu cấu hình / lưu bản nháp"** để Agent thực thi. Agent cam kết **không** bấm `Gửi ngay` hay `Kích hoạt`.

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-crm-flows-broadcast",
  "scenario": "segment_create",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/customers/segments",
  "screenshots": {
    "pre": "artifacts/crm_segments_pre.png",
    "preview": "artifacts/crm_segments_preview.png",
    "post": null
  },
  "quota_check": {
    "used_segments": 4,
    "plan_limit": 10
  },
  "changes_staged": {
    "item_name": "VIP-ChiTieu-Tren-5Tr",
    "segment_type": "dynamic",
    "estimated_audience_count": 142,
    "status": "draft_only",
    "estimated_messaging_cost_vnd": 0
  },
  "pii_redacted": true,
  "saved_verified": false,
  "awaiting_human_confirmation": true
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click):**
  - `Gửi ngay` / `Gửi chiến dịch` / `Lên lịch gửi` tại `/admin/customers/broadcast_campaigns` (nguy cơ spam diện rộng và phát sinh chi phí ZNS/SMS ngay lập tức).
  - `Kích hoạt` tại `/admin/customers/flows` khi mới yêu cầu tạo/sửa kịch bản.
  - `Xóa` đối với nhóm khách hàng đang gắn vào Bảng giá B2B, Flow đang chạy hoặc hạng thành viên hiện hữu.
  - `Nâng cấp gói` / `Mua thêm` / `Nạp tiền ZNS-SMS` (phát sinh thanh toán dịch vụ).
- **Credential / OTP / PII Handoff Gates:**
  - Gặp `accounts.haravan.com` hoặc màn hình kết nối **Zalo OA / SMS Brandname** yêu cầu đăng nhập/OTP → dừng ngay để người dùng tự kết nối.
  - Che toàn bộ SĐT (`090****678`) và email (`a***@domain.com`) nếu giao diện hiển thị danh sách khách hàng mẫu; tuyệt đối không bấm xuất file raw danh sách khách.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Chạm trần giới hạn 10 nhóm khách hàng (Gói Standard/Pro/Advanced):** Nút `Tạo nhóm khách hàng` bị vô hiệu hóa hoặc bật popup nâng gói → Dừng ngay, liệt kê nhóm cũ ít dùng để người dùng tự xử lý, tuyệt đối không bấm nâng cấp gói.
2. **Bộ lọc nhóm tự động trả về `0 khách hàng`:** Thường do nhầm toán tử `Và (AND)` thay vì `Hoặc (OR)`, hoặc nhập dấu chấm/phẩy thừa vào ô số tiền VND → Kiểm tra lại định dạng số nguyên và báo người dùng điều chỉnh.
3. **Kênh ZNS không hiện mẫu tin nhắn khả dụng:** Do Zalo OA chưa kết nối hoặc template ZNS chưa được Zalo kiểm duyệt → Chụp thông báo lỗi và bàn giao người dùng đăng nhập Zalo OA xử lý.
4. **Flow mới tạo bị trùng Trigger với Flow đang hoạt động:** Có thể khiến khách nhận 2 email/ZNS giống nhau cùng lúc → Cảnh báo rõ tên Flow trùng trong bảng preview và giữ Flow mới ở trạng thái `Bản nháp (Tắt)`.
5. **Nhân viên Staff không thấy menu `Kịch bản tự động` hoặc `Cấu hình thành viên`:** Thiếu quyền CRM/Marketing → Báo Owner kiểm tra tại `/admin/settings/group_permissions`.
6. **Xóa nhầm nhóm khách hàng đang gắn với Bảng giá B2B:** Luôn kiểm tra chéo tên nhóm với `/admin/products/pricing_list` trước khi đề xuất thay đổi điều kiện nhóm khách sỉ.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: true`):**
  1. Đối chiếu `pre_screenshot` đã lưu tại Pha 1.
  2. Với **Flow:** Mở `/admin/customers/flows`, gạt toggle trạng thái sang `Tắt` / `Ngừng hoạt động` nếu đã lỡ kích hoạt.
  3. Với **Cấu hình thành viên:** Mở `/admin/customers/settings`, khôi phục lại chính xác tỷ lệ tích điểm và ngưỡng hạng cũ theo `pre_screenshot`, bấm `Lưu`.
  4. Với **Nhóm / Broadcast nháp:** Người dùng tự bấm `Xóa` bản nháp nếu không sử dụng.
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/50-customer-crm/crm-rfm-segmentation` (API): Chạy phân tích RFM (Recency, Frequency, Monetary) từ lịch sử đơn hàng trước khi dựng ngưỡng điều kiện trên `/admin/customers/segments`.
  - `skills/browser-ui/50-customer-crm/customer-review-rating-moderation` (UI): Kiểm toán chuyên sâu đánh giá 1–3 sao tại `/admin/customers/rating`.
  - `skills/browser-ui/20-catalog-merchandising/catalog-pricing-list-b2b-proposal` (UI): Gắn Nhóm khách hàng vừa tạo vào Bảng giá riêng cho VIP/Đại lý B2B.
