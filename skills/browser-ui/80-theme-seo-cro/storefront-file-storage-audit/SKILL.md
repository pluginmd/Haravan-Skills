---
name: storefront-file-storage-audit
description: "Kiểm toán kho tệp tin (/admin/settings/files) để phát hiện ảnh/video quá nặng (> 500KB) làm chậm Core Web Vitals và tệp rác không sử dụng."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 80-theme-seo-cro
layer: L1
wave: 1
mode: read
risk: low
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/settings/files"
execution:
  dry_run: true
  confirmation_required: false
  separate_turn: false
  max_records: 500
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

# Haravan File Storage & Heavy Media Performance Audit

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check

- **Phạm vi vận hành thực tế:** Kiểm toán chỉ đọc kho lưu trữ **Quản lý file** (`/admin/settings/files`) trên Haravan Admin (`*.myharavan.com/admin`) — nơi lưu trữ toàn bộ banner homepage, ảnh bài viết blog, ảnh trang nội dung, bảng size, logo email, PDF catalog và video upload trực tiếp lên CDN `file.hstatic.net`.
- **Lý do bắt buộc dùng Browser UI:** Haravan Commerce & Web REST API **không cung cấp endpoint công khai** để liệt kê danh sách tệp trong `/admin/settings/files` kèm dung lượng (KB/MB) và đường dẫn CDN tương ứng.
- **Mục tiêu nghiệp vụ (`layer: L1`, `mode: read`, `risk: low`):** Cải thiện tốc độ tải trang di động và chỉ số Core Web Vitals (đặc biệt **LCP — Largest Contentful Paint**) bằng cách phát hiện các ảnh PNG/JPG siêu nặng (`> 500KB`, nhiều tệp 2–10MB), tệp trùng lặp nhiều phiên bản và lập kế hoạch chuyển đổi WebP + checklist kiểm tra tham chiếu trước khi dọn rác — **tuyệt đối không tự xóa hay upload đè file**.
- **Phân quyền Owner vs Staff & Giới hạn gói dịch vụ:**
  - **Owner:** Toàn quyền truy cập **Cấu hình > Quản lý file** (`/admin/settings/files`).
  - **Staff:** Yêu cầu có quyền **Cấu hình cửa hàng / Quản lý file** tại `/admin/settings/group_permissions`. Nhân viên bán hàng hoặc kho thường không mở được `/admin/settings/files`.
  - **Giới hạn kỹ thuật Haravan CDN:** Haravan giới hạn kích thước tối đa mỗi file tải lên (thường ≤ 20MB tùy loại tệp), tuy nhiên ảnh web không tự động nén sang WebP tối ưu kích thước pixel khi upload vào `/admin/settings/files`, dễ gây nghẽn băng thông di động nếu tải ảnh gốc từ máy ảnh/Photoshop.
- **Pre-flight Check phiên đăng nhập:**
  1. Mở `https://{store_domain}/admin/settings/files`.
  2. Nếu bị redirect sang `https://accounts.haravan.com/Account/Login`, **dừng ngay lập tức** để người dùng tự đăng nhập; không hỏi/nhập mật khẩu hay OTP.
  3. Chờ bảng danh sách tệp tin và ảnh thu nhỏ (thumbnail) tải hoàn tất.

## 2. Bản đồ Giao diện Thực tế (Exact Routes, Controls, Columns & Filters)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/settings/files` — H1 `Quản lý danh sách file`; Nút: `Tải file`.


| Route / URL | Section / Tab | Nhãn nút bấm thực tế (Exact UI Labels) | Cột bảng & Bộ lọc thực tế |
| :--- | :--- | :--- | :--- |
| `/admin/settings/files` | Thanh tiêu đề & Bộ lọc | `Tải file lên` (HARD-BLOCKED), `Tìm kiếm`, `Lọc` | Ô tìm kiếm theo tên tệp; bộ lọc loại tệp (`Hình ảnh`, `Tài liệu`, `Video`, `Tất cả`) |
| `/admin/settings/files` | Bảng danh sách Tệp tin | `Sao chép đường dẫn` (Copy URL), biểu tượng `Xóa` (HARD-BLOCKED) | Cột: Ảnh thu nhỏ (Thumbnail), Tên tệp & Định dạng (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.pdf`, `.mp4`), Kích thước/Dung lượng (`KB`/`MB`), Ngày tải lên, Đường dẫn CDN (`file.hstatic.net/...`) |
| `/admin/settings/files` | Thanh phân trang | `Trang trước`, `Trang sau`, Dropdown số dòng/trang | Duyệt tuần tự tối đa `max_pages_to_scan` trang (tương ứng ≤ `max_records: 500` tệp) |

### Quy chuẩn Dung lượng Media cho Core Web Vitals (Haravan Storefront)
- **Hero Banner Desktop (`1920px`):** Định dạng `.webp` (quality 80), mục tiêu `<= 300KB` để đạt LCP `< 2.5s`.
- **Hero Banner Mobile (`750px–900px`):** Định dạng `.webp`, mục tiêu `<= 150KB` (tránh tải chung ảnh Desktop 3–5MB lên thiết bị di động 4G).
- **Ảnh Blog / Trang nội dung / Bảng size (`1000px–1200px`):** Định dạng `.webp`, mục tiêu `<= 200KB`.
- **Cảnh báo không có Thùng rác (No Trash Bin):** Xóa tệp trên `/admin/settings/files` là thao tác vĩnh viễn trên CDN `file.hstatic.net` và không thể hoàn tác.

## 3. Bảng Tham số Đầu vào (Input Parameters)

| Parameter | Type | Required | Default | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Tên miền Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `string` | Có | `full_storage_audit` | `full_storage_audit` \| `lcp_banner_webp_plan` \| `duplicate_orphan_scan` \| `heavy_media_pdf_video_triage` \| `cdn_reference_checklist` |
| `max_recommended_kb` | `integer` | Không | `500` | Ngưỡng cảnh báo dung lượng ảnh web (`100..2000` KB; khuyến nghị `500` KB) |
| `critical_size_mb` | `number` | Không | `2.0` | Ngưỡng nghiêm trọng gây tụt LCP ngay lập tức (`0.5..20.0` MB) |
| `max_pages_to_scan` | `integer` | Không | `10` | Số trang tối đa quét trong 1 lượt (`1..25`, tổng ≤ 500 tệp) |
| `check_duplicates` | `boolean` | Không | `true` | Quét các tệp trùng tiền tố kèm hậu tố `_1`, `_2`, `copy`, `final`, `v2` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Quét toàn diện kho tệp & Phân tầng dung lượng (`full_storage_audit`)
- **Khi nào dùng:** Kiểm toán tổng thể tốc độ tải media trên website định kỳ hàng quý hoặc khi điểm Google PageSpeed/LCP tụt dưới ngưỡng xanh.
- **Thao tác từng bước:**
  1. Điều hướng tới `https://{store_domain}/admin/settings/files` (hoặc `Ctrl+K` gõ `Quản lý file`), chụp `pre_screenshot`.
  2. Duyệt tuần tự tối đa `max_pages_to_scan` trang (≤ 500 tệp) ở chế độ chỉ đọc; ghi nhận Tên tệp, Phần mở rộng, Dung lượng (`KB`/`MB`) và Ngày tải lên.
  3. Phân loại toàn bộ tệp ảnh thành 3 tầng sức khỏe:
     - 🔴 **Nghiêm trọng (`>= critical_size_mb`, mặc định ≥ 2MB):** Ảnh gốc chưa nén hoặc GIF nặng làm chậm tải trang trực tiếp.
     - 🟡 **Cảnh báo (`> max_recommended_kb` đến `< critical_size_mb`):** Ảnh từ 500KB đến < 2MB cần ưu tiên nén.
     - 🟢 **Đạt chuẩn (`<= max_recommended_kb`):** Dung lượng tối ưu cho hiển thị web.
  4. Chụp `preview_screenshot` khu vực tập trung nhiều tệp dung lượng lớn nhất để làm bằng chứng trực quan.
- **Điểm dừng an toàn:** Chỉ đọc và thống kê; tuyệt đối không bấm `Xóa` hay `Tải file lên`.

### Kịch bản 2: Phát hiện Banner/Lookbook PNG/JPG gây chậm LCP & Lập kế hoạch WebP (`lcp_banner_webp_plan`)
- **Khi nào dùng:** Cần tối ưu nhanh trang chủ và landing page trước các đợt sale lớn (11.11, 12.12, Tết).
- **Thao tác từng bước:**
  1. Lọc tập trung các tệp `.png`, `.jpg`, `.jpeg` mang tên vị trí trọng yếu (`banner`, `slider`, `hero`, `popup`, `lookbook`, `homepage`, `mobile`).
  2. Ước tính băng thông tiết kiệm khi chuyển sang `.webp` (trung bình giảm 65%–85% dung lượng) theo quy chuẩn Desktop `<= 300KB`, Mobile `<= 150KB`, Nội dung `<= 200KB`.
  3. Lập bảng Top tệp ưu tiên bàn giao cho đội Thiết kế nén lại và thay thế trên staging theme trước khi đưa lên live.
- **Điểm dừng an toàn:** Không tự ghi đè ảnh lên CDN; nhắc rõ phải cập nhật URL CDN mới trước khi dọn ảnh cũ.

### Kịch bản 3: Phát hiện tệp trùng lặp nhiều phiên bản & Tệp cũ nghi không dùng (`duplicate_orphan_scan`)
- **Khi nào dùng:** Kho file tích tụ hàng trăm bản upload thử nghiệm gây rối quản lý và khó tìm ảnh chuẩn.
- **Thao tác từng bước:**
  1. Khi `check_duplicates = true`, gom nhóm các tệp cùng tiền tố tải lên nhiều lần (`banner-tet.png`, `banner-tet_1.png`, `banner-tet_final.png`, `logo-copy.png`) hoặc cùng dung lượng chính xác tải lên liên tiếp.
  2. Đánh dấu các tệp mang tên chiến dịch mùa vụ đã qua trên 6–12 tháng (`flash-sale-2024`, `black-friday-2023`, `tet-2024`) vào nhóm **Nghi ngờ không còn sử dụng**.
- **Điểm dừng an toàn:** **TUYỆT ĐỐI KHÔNG bấm biểu tượng `Xóa`** — chỉ xuất danh sách đề xuất kèm bước đối chiếu tham chiếu ở Kịch bản 5.

### Kịch bản 4: Phân tách tệp đa phương tiện đặc thù (PDF Catalog, Video MP4, GIF động) (`heavy_media_pdf_video_triage`)
- **Khi nào dùng:** Tránh gộp nhầm catalog PDF hoặc video sản phẩm vào ngưỡng 500KB của ảnh tĩnh.
- **Thao tác từng bước:**
  1. Dùng bộ lọc loại tệp (hoặc lọc theo đuôi `.pdf`, `.mp4`, `.mov`, `.gif`) để tách riêng nhóm phi-ảnh tĩnh.
  2. Đưa khuyến nghị tối ưu riêng theo từng loại:
     - **Video `.mp4` > 5MB:** Cảnh báo nếu nhúng autoplay trên trang chủ, đề xuất chuyển sang nhúng **YouTube / Vimeo** (lazy-load).
     - **Ảnh động `.gif` > 1MB:** Đề xuất chuyển sang video ngắn MP4 muted hoặc WebP động (giảm 70%–90% dung lượng).
     - **PDF > 5MB:** Đề xuất nén PDF (150 DPI) cho khách tải nhanh trên điện thoại.
- **Điểm dừng an toàn:** Không xóa hoặc chỉnh sửa trực tiếp tệp đa phương tiện.

### Kịch bản 5: Lập Checklist kiểm tra tham chiếu URL CDN trước khi dọn rác (`cdn_reference_checklist`)
- **Khi nào dùng:** Bắt buộc chạy trước khi người dùng tự xóa bất kỳ file cũ nào trên `/admin/settings/files` để chống lỗi ảnh vỡ 404.
- **Thao tác từng bước:**
  1. Ghi nhận chính xác tên tệp trong URL CDN (`file.hstatic.net/.../{filename}`) của từng file nằm trong danh sách dọn dẹp.
  2. Xuất Checklist 5 vị trí bắt buộc phải rà soát không còn tham chiếu trước khi tự bấm `Xóa`:
     - (1) **Theme Liquid & Theme Settings** (`config/settings_data.json`, `sections/*`, `snippets/*`).
     - (2) **Trang nội dung** (`/admin/sale_channels/online_store/pages`).
     - (3) **Bài viết Blog** (`/admin/sale_channels/online_store/articles`).
     - (4) **13 Mẫu Email Thông báo & Mẫu In** (`/admin/settings/notifications` — tránh xóa nhầm logo/QR ngân hàng).
     - (5) **Mô tả sản phẩm** (`/admin/products` — bảng size, ảnh chi tiết nhúng trong HTML).
- **Điểm dừng an toàn:** Giữ nguyên 100% file hiện có cho tới khi hoàn tất kiểm tra đủ 5 vị trí.

## 5. Quy trình An toàn 4 Pha (4-Phase Read-Only UI Safety Workflow)

### Pha 1 — Pre-State Capture (Ghi nhận hiện trạng & Kiểm tra quyền Cấu hình)
- Mở `/admin/settings/files`, xác nhận phiên đăng nhập hợp lệ và quyền truy cập kho tệp tin.
- Chụp `pre_screenshot` trang đầu tiên của bảng Quản lý file.

### Pha 2 — Read-Only Scan & Classification (Quét & Phân tầng không ghi/xóa)
- Quét tuần tự tối đa `max_pages_to_scan` trang (≤ 500 tệp), phân loại tệp nặng, tệp trùng lặp và nhóm PDF/Video/GIF.
- Tuyệt đối không bấm biểu tượng `Xóa` hay nút `Tải file lên`.

### Pha 3 — Screenshot & Impact Verification (Bằng chứng trực quan & Checklist CDN)
- Chụp `preview_screenshot` khu vực chứa các tệp dung lượng lớn nhất.
- Tính toán băng thông tiết kiệm khi chuyển WebP và đính kèm Checklist 5 vị trí kiểm tra tham chiếu CDN.

### Pha 4 — Session Audit & Read-Only Closure (Chốt phiên chỉ đọc)
- Xác nhận 100% thao tác chỉ đọc (`saved_verified: false`, `mode: read`).
- Bàn giao kế hoạch tối ưu media cho đội Thiết kế/Marketing triển khai an toàn trên staging trước.

## 6. Mẫu Preview Before → After & JSON Execution Log Schema

### Bảng Top Tệp Tin Nặng & Kế hoạch Tối ưu (Current File → Target Optimized)

| Tên tệp | Loại | Hiện tại (Before) | Mức độ | Mục tiêu Tối ưu (After) | Lưu ý Tham chiếu CDN |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `banner-tet-desktop.png` | PNG | `4.8 MB` | 🔴 Nghiêm trọng | WebP `1920px` (q=80) → ~`280 KB` (-94%) | Kiểm tra Homepage Slider trong Theme |
| `lookbook-2026-full.jpg` | JPG | `2.6 MB` | 🔴 Nghiêm trọng | Resize `1400px` + WebP → ~`220 KB` (-91%) | Kiểm tra Blog / Landing Page |
| `intro-product.gif` | GIF | `3.9 MB` | 🔴 Nghiêm trọng | Chuyển MP4 muted / WebP động → ~`450 KB` | Tránh load đồng bộ trên Mobile |
| `size-chart-ao-thun.png` | PNG | `980 KB` | 🟡 Cảnh báo | Nén WebP `1000px` → ~`150 KB` (-85%) | Đang nhúng trong mô tả SP & Pages |
| `banner-tet-desktop_1.png` | PNG | `4.8 MB` | ⚪ Nghi trùng lặp | Xác minh 0 tham chiếu trước khi tự xóa | Kiểm tra đủ 5 vị trí Checklist |

> **Lưu ý Read-Only:** Agent chỉ kiểm toán danh sách tệp, **không tự bấm xóa hoặc tải đè bất kỳ tệp nào** trên `/admin/settings/files` để tránh gây lỗi ảnh vỡ 404 toàn storefront hoặc hỏng logo trong email giao dịch.

### JSON Execution Log Schema

```json
{
  "skill": "storefront-file-storage-audit",
  "scenario": "full_storage_audit",
  "mode": "read",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/settings/files",
  "screenshots": {
    "pre": "artifacts/files_storage_pre.png",
    "preview": "artifacts/files_heavy_list.png",
    "post": null
  },
  "audit_summary": {
    "scanned_pages": 6,
    "scanned_files": 180,
    "max_recommended_kb": 500,
    "critical_files_count": 8,
    "warning_files_count": 29,
    "heavy_gif_video_count": 3,
    "suspected_duplicates_count": 6,
    "estimated_bandwidth_saving_mb": 42.5,
    "cdn_reference_checklist_locations": [
      "Theme Liquid & settings_data.json",
      "Online Store Pages",
      "Online Store Blogs/Articles",
      "13 Notification Email & Print Templates",
      "Product Descriptions HTML"
    ]
  },
  "saved_verified": false
}
```

### Checklist Bàn giao Đội Thiết kế & Kỹ thuật Theme
- [ ] Đã ưu tiên nén và chuyển `.webp` toàn bộ tệp nhóm 🔴 Nghiêm trọng (`>= 2MB`) trước các đợt campaign lớn.
- [ ] Đã tách riêng kích thước Desktop (`1920px`, ≤ 300KB) và Mobile (`750px–900px`, ≤ 150KB) cho Hero Banner.
- [ ] Đã cập nhật URL CDN `file.hstatic.net` mới vào Theme/Pages/Blogs và kiểm thử hiển thị trên Staging Theme.
- [ ] Đã kiểm tra sạch đủ 5 vị trí tham chiếu CDN (bao gồm 13 mẫu Email) trước khi người dùng tự xóa bất kỳ file cũ nào.
- [ ] Xác nhận 100% phiên chỉ đọc: không bấm `Xóa` và không bấm `Tải file lên`.

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Hard-Blocked Buttons (TUYỆT ĐỐI CẤM tự click trong L1 Read-Only):**
  - Biểu tượng `Xóa` / `Xóa file` (xóa nhầm tệp đang nhúng trên live theme, bài blog, mô tả sản phẩm hoặc email giao dịch sẽ lập tức gây ảnh vỡ 404).
  - `Tải file lên` (không tự upload hoặc ghi đè tệp lên CDN trong phiên kiểm toán L1).
  - Mọi thao tác chọn nhiều file để xóa hàng loạt khi chưa xác minh sạch 5 vị trí tham chiếu CDN.
- **Credential Handoff Gate:**
  - Gặp màn hình `accounts.haravan.com` → dừng ngay để người dùng tự đăng nhập.

## 8. Xử lý Sự cố UI & Tình huống Biên (UI Troubleshooting & Edge Cases)

1. **Giao diện không hỗ trợ sắp xếp cột theo dung lượng giảm dần:** Bảng mặc định sắp xếp theo ngày tải lên mới nhất → Quét tuần tự qua `max_pages_to_scan` trang, trích xuất dung lượng từng dòng và tự sắp xếp tổng hợp trong báo cáo.
2. **Thiếu quyền Staff (403 hoặc ẩn mục `Quản lý file` trong `/admin/settings`):** Báo Chủ shop bổ sung quyền **Cấu hình > Quản lý file** tại `/admin/settings/group_permissions`.
3. **Tệp logo/QR thanh toán nằm lẫn trong kho file cũ:** Không bao giờ đề xuất xóa các file chứa từ khóa `logo`, `favicon`, `qr`, `bank`, `chung-nhan`, `bct` (Bộ Công Thương) khi chưa đối chiếu `/admin/settings/general` và `/admin/settings/notifications`.
4. **File cùng tên tải lên lại bị Haravan tự đổi URL (thêm hậu tố hoặc hash mới):** Nhắc đội Thiết kế rằng sau khi nén WebP và tải lên file mới, bắt buộc phải **cập nhật lại URL CDN mới** vào Theme/Page/Blog rồi mới được xóa file cũ.
5. **Thumbnail không hiển thị đối với tệp PDF, font (`.woff2`) hoặc CSS/JS tĩnh:** Chỉ phân loại theo phần mở rộng và dung lượng; cảnh báo không xóa các tệp `.woff2`, `.svg`, `.js`, `.css` vì có thể đang được nhúng cứng trong Theme Liquid.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Quy trình Rollback thủ công (`rollback.supported: false`):** Không áp dụng vì skill vận hành 100% ở chế độ `L1 mode: read`, không xóa hay thay đổi bất kỳ tệp nào trên CDN Haravan. *(Lưu ý: Nếu người dùng tự xóa nhầm file trên `/admin/settings/files`, Haravan không có thùng rác khôi phục — phải tải lại bản gốc từ máy tính và cập nhật lại URL mới).*
- **Liên kết chéo với `skills/api-mcp/` và Browser UI khác:**
  - `skills/api-mcp/80-theme-seo-cro/seo-storefront-audit` (API): Quét chéo thẻ `alt`, dung lượng ảnh và URL ảnh trong Pages/Blogs/Products qua Haravan API.
  - `skills/api-mcp/80-theme-seo-cro/haravan-cli-theme-ops` (API/CLI): Pull mã nguồn theme để grep chính xác tham chiếu `file.hstatic.net` trước khi dọn file cũ.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-notifications-print-webhooks` (UI): Kiểm tra ảnh/logo đang nhúng trong 13 mẫu email thông báo và mẫu in tại `/admin/settings/notifications`.
  - `skills/browser-ui/95-admin-ui-browser/admin-ui-general-policies-setup` (UI): Kiểm tra logo thương hiệu và thông tin chung tại `/admin/settings/general`.
