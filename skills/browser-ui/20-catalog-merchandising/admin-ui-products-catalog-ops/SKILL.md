---
name: admin-ui-products-catalog-ops
description: "Vận hành Sản phẩm & Nhóm sản phẩm trên Haravan Admin (/admin/products & /admin/products/collections): tạo SP đa biến thể Size/Màu + ảnh + SEO, Import/Export Excel chuẩn Haravan, Bulk Edit giá/tồn/tag/ẩn-hiện và tạo Nhóm SP thủ công/tự động."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 20-catalog-merchandising
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/products"
    - "UI /admin/products/new"
    - "UI /admin/products/{product_id}"
    - "UI /admin/products/collections"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: none
  redact_output: true
  export_allowed: true
rollback:
  supported: true
  backup_required: true
---

# Haravan Admin UI — Vận Hành Sản Phẩm & Nhóm Sản Phẩm (`/admin/products`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Thực hiện đầy đủ tác vụ merchandising hàng ngày trên Haravan Admin mà không cần API token: tạo mới sản phẩm đơn hoặc đa biến thể (tối đa 3 thuộc tính như `Màu sắc` / `Kích thước` / `Chất liệu`, ảnh đại diện, ảnh theo biến thể, khối lượng vận chuyển, tối ưu SEO URL handle/Meta), chuẩn bị & kiểm tra Import/Export file Excel chuẩn Haravan, chỉnh sửa hàng loạt (Bulk Edit) giá bán/giá so sánh/tag/trạng thái hiển thị kênh, và cấu hình Nhóm sản phẩm (`Collections`) thủ công lẫn tự động (`Smart Collection`).
- **Phạm vi UI:** `/admin/products`, `/admin/products/new`, `/admin/products/{product_id}`, `/admin/products/collections` và `/admin/products/collections/new`. Không bao gồm bảng giá B2B (dùng `catalog-pricing-list-b2b-proposal`) hay nghiệp vụ nhập/kiểm kho nâng cao (dùng `admin-ui-inventory-advanced-ops`).
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Toàn quyền tạo, sửa, ẩn/hiện, Import/Export sản phẩm và quản lý nhóm sản phẩm.
  - **Staff:** Yêu cầu quyền `Sản phẩm` (`Xem`, `Tạo mới`, `Chỉnh sửa`, `Nhập/Xuất dữ liệu`) và quyền `Nhóm sản phẩm`. Nếu Staff bị ẩn nút `Nhập dữ liệu` hoặc ô `Giá vốn`, báo rõ thiếu quyền trước khi tiếp tục.
- **Yêu cầu Gói dịch vụ Haravan:** Khả dụng trên mọi gói. Giới hạn số biến thể mặc định trên Haravan là tối đa 100 biến thể/sản phẩm và 3 thuộc tính tùy chọn; giới hạn dung lượng ảnh và tổng SKU tuân theo gói cửa hàng đang dùng.
- **Pre-flight Check bắt buộc:**
  1. Xác minh phiên đăng nhập qua `admin-ui-session-navigator` tại `/admin/products`.
  2. Kiểm tra mã SKU dự kiến chưa bị trùng trên hệ thống bằng ô tìm kiếm tại `/admin/products` để tránh xung đột đồng bộ tồn kho đa kênh (POS/Shopee/TikTok).
  3. Chụp trạng thái hiện tại (hoặc xuất file Excel backup danh mục đang sửa) trước khi thực hiện Bulk Edit hoặc Import.

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

> **Live-DOM Verified Snapshot (`api/admin-ui-sitemap.yaml`):** **Native DOM (Live-Verified):** `/admin/products` — Tab: `Tất cả sản phẩm`; Nút: `Nhập dữ liệu`, `Xuất dữ liệu`, `Tạo combo`, `Tạo sản phẩm`; Bộ lọc: `Tìm kiếm`, `Bộ lọc`; Cột: `Sản phẩm`, `Tồn kho`, `Loại`, `Thương hiệu`. `/admin/products/collections` — Tab: `Tất cả danh mục`; Nút: `Tạo nhóm sản phẩm`; Cột: `Tên nhóm`, `Số sản phẩm`, `Điều kiện nhóm`.


| Thành phần UI | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Ghi chú thao tác |
| :--- | :--- | :--- | :--- |
| Danh sách sản phẩm | `/admin/products` | Nút góc phải: `Nhập dữ liệu`, `Xuất dữ liệu`, `Tạo sản phẩm` | Thanh lọc: `Thêm điều kiện lọc` (`Hiển thị`, `Loại sản phẩm`, `Nhà cung cấp`, `Nhóm sản phẩm`, `Tag`, `Kênh bán hàng`) |
| Bảng sản phẩm & Bulk Action | `/admin/products` | Cột: `Sản phẩm`, `Tồn kho`, `Loại`, `Nhà cung cấp`; Dropdown `Thao tác` khi tick chọn | Menu `Thao tác`: `Hiển thị sản phẩm`, `Ẩn sản phẩm`, `Thêm vào nhóm sản phẩm`, `Xóa khỏi nhóm`, `Thêm tag`, `Bỏ tag` |
| Form tạo/sửa sản phẩm | `/admin/products/new` & `/{id}` | Cột trái: `Tên sản phẩm`, `Mô tả`, `Hình ảnh`, `Giá`, `Kho hàng`, `Vận chuyển` (khối lượng gram), `Biến thể`, `Tối ưu SEO` | Cột phải: `Hiển thị` (Website, POS, Facebook...), `Loại sản phẩm`, `Nhà cung cấp`, `Nhóm sản phẩm`, `Nhãn (Tags)` |
| Khối Biến thể | Trong `/admin/products/{id}` | Nút `Thêm thuộc tính` (`Kích thước`, `Màu sắc`, `Chất liệu`) + bảng `Giá`, `Giá so sánh`, `SKU`, `Barcode`, `Tồn kho` | Có thể gắn ảnh riêng cho từng biến thể sau khi tạo xong biến thể |
| Modal Import / Export | `/admin/products` → `Nhập dữ liệu` / `Xuất dữ liệu` | `Tải file mẫu` (`.xlsx`/`.csv`), `Chọn file tải lên`, checkbox `Ghi đè sản phẩm trùng Handle` | Cẩn trọng tuyệt đối với checkbox `Ghi đè sản phẩm trùng Handle` |
| Danh sách Nhóm sản phẩm | `/admin/products/collections` | Nút `Tạo nhóm sản phẩm`; Cột: `Tên nhóm`, `Điều kiện` (`Thủ công` / `Tự động`) | Click tên nhóm để chỉnh thứ tự sắp xếp SP (`Bán chạy`, `Mới nhất`, `Giá tăng dần`, `Thủ công`) |
| Form Nhóm sản phẩm | `/admin/products/collections/new` | `Tên nhóm sản phẩm`, `Mô tả`, `Ảnh đại diện`, `Loại nhóm`: `Thủ công` hoặc `Tự động` (`Thỏa mãn tất cả` / `Thỏa mãn một trong các điều kiện`), `Tối ưu SEO` | Điều kiện tự động: `Tên SP`, `Loại SP`, `Nhà cung cấp`, `Giá`, `Tag`, `Tồn kho` |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Subdomain Haravan Admin hợp lệ (`*.myharavan.com`) |
| `scenario` | `enum` | Có | `create_variant_product` | `create_variant_product` \| `import_export_excel` \| `bulk_edit_catalog` \| `manage_collections` |
| `product_payload` | `object` | Khi tạo SP | `null` | Bắt buộc có `title`, `vendor`, `product_type`, `variants` (1–100 biến thể, `price >= 0`, `weight_grams >= 0`) |
| `seo_fields` | `object` | Không | `{}` | `meta_title` (≤ 70 ký tự), `meta_description` (≤ 320 ký tự), `url_handle` (`^[a-z0-9-]+$`) |
| `excel_file_path` | `string` | Khi Import | `""` | File `.xlsx` hoặc `.csv` đúng cột mẫu Haravan; số dòng ≤ `max_records` (hoặc tách batch) |
| `overwrite_existing_handle` | `boolean` | Không | `false` | Mặc định `false` để tránh ghi đè mất mô tả/ảnh sản phẩm đang bán |
| `bulk_action` | `object` | Khi Bulk Edit | `null` | `action` (`show` \| `hide` \| `add_tags` \| `remove_tags` \| `add_to_collection`), `product_ids` (≤ 50) |
| `collection_spec` | `object` | Khi tạo Nhóm | `null` | `title`, `type` (`manual` \| `smart`), `match_mode` (`all` \| `any`), `rules` hoặc `product_skus` |
| `dry_run` | `boolean` | Không | `true` | Bắt buộc `true` ở pha dựng form/kiểm tra trước khi bấm `Lưu` |

## 4. Ma trận Kịch bản Thao tác Đa dạng (4 Scenarios Click-by-Click)

### Kịch bản 1: Tạo sản phẩm đa biến thể (Size / Màu) kèm ảnh & Tối ưu SEO
1. Mở `https://{store_domain}/admin/products`, bấm nút `Tạo sản phẩm` (`/admin/products/new`).
2. Điền `Tên sản phẩm`, soạn `Mô tả` chuẩn định dạng (bảng size, chất liệu, hướng dẫn bảo quản), tải ảnh lên khối `Hình ảnh` (ảnh đầu tiên tự động làm ảnh đại diện).
3. Tại khối **Biến thể**, bấm `Thêm biến thể` / `Thêm thuộc tính`:
   - Thuộc tính 1: `Màu sắc` → nhập các giá trị (ví dụ `Đen`, `Trắng`, `Xanh Navy`), nhấn Enter sau mỗi giá trị.
   - Thuộc tính 2: `Kích thước` → nhập `S`, `M`, `L`, `XL`.
4. Kiểm tra bảng tổ hợp biến thể tự sinh (ví dụ `3 x 4 = 12` biến thể): điền chính xác `Giá bán`, `Giá so sánh` (nếu có), `Mã SKU` duy nhất, `Barcode` và `Khối lượng (gram)` để tính phí ship chính xác.
5. Cuộn xuống khối **Tối ưu SEO**, bấm `Chỉnh sửa SEO` → kiểm tra `Tiêu đề trang`, `Mô tả trang`, và chuẩn hóa `Đường dẫn / Alias` (không dấu, gạch ngang, không trùng).
6. Tại cột phải, chọn `Loại sản phẩm`, `Nhà cung cấp`, `Nhóm sản phẩm`, `Tag`, và kiểm tra kênh hiển thị (`Website`, `POS` — tạm bỏ tick kênh Live nếu đang tạo bản nháp). **Dừng trước nút `Lưu`**, chụp ảnh preview gửi người dùng duyệt.

### Kịch bản 2: Import / Export sản phẩm bằng Excel chuẩn Haravan
1. **Export backup trước khi Import:** Tại `/admin/products`, bấm `Xuất dữ liệu` → chọn phạm vi (`Trang hiện tại` hoặc `Sản phẩm phù hợp bộ lọc`) → chọn định dạng `Excel (.xlsx)` → bấm `Xuất dữ liệu` để lưu bản sao lưu về máy (hoặc kiểm tra email nhận file).
2. **Kiểm tra file Import:** Bấm `Nhập dữ liệu` → tải `Tải file mẫu` nếu cần đối chiếu cấu trúc cột (`Url`, `Tên sản phẩm`, `Mô tả`, `Nhà cung cấp`, `Loại`, `Tag`, `Thuộc tính 1..3`, `Giá`, `Giá so sánh`, `SKU`, `Link hình`).
3. Tải file `excel_file_path` lên hộp thoại `Nhập dữ liệu`, kiểm tra kỹ checkbox `Ghi đè sản phẩm trùng Handle` (giữ **tắt** trừ khi người dùng xác nhận rõ ràng).
4. **Dừng tại màn hình Preview tải file** (trước khi bấm `Nhập dữ liệu` xác nhận chạy), chụp ảnh tên file + cấu hình ghi đè để người dùng xác nhận.

### Kịch bản 3: Bulk Edit hàng loạt (Ẩn/Hiện kênh, Gắn/Bỏ Tag, Cập nhật Giá/Tồn nhanh)
1. Tại `/admin/products`, bấm `Thêm điều kiện lọc` theo `Loại sản phẩm`, `Nhà cung cấp`, `Nhóm sản phẩm` hoặc `Tag` để khoanh đúng tập sản phẩm mục tiêu (tối đa `50` sản phẩm/đợt).
2. Tick chọn các sản phẩm cần cập nhật; bấm `Thao tác` → chọn tác vụ tương ứng (`Ẩn sản phẩm`, `Hiển thị sản phẩm`, `Thêm tag`, `Bỏ tag`, `Thêm vào nhóm sản phẩm`).
3. Nếu cần sửa giá bán / giá so sánh đồng loạt cho từng biến thể trên UI, mở từng sản phẩm (hoặc chuyển sang màn hình `Chỉnh sửa hàng loạt` nếu gói hỗ trợ) và đảm bảo `Giá so sánh >= Giá bán` (không để giá 0đ ngoài ý muốn).
4. Chụp ảnh modal/bảng thay đổi ở trạng thái chưa bấm `Lưu`/`Áp dụng`, gửi bảng so sánh giá/tag `Before → After` chờ người dùng xác nhận.

### Kịch bản 4: Tạo & Quản lý Nhóm sản phẩm Thủ công & Tự động (`Smart Collection`)
1. Điều hướng tới `https://{store_domain}/admin/products/collections`, bấm `Tạo nhóm sản phẩm`.
2. Nhập `Tên nhóm sản phẩm`, `Mô tả`, ảnh banner nhóm và chỉnh `Tối ưu SEO` (URL handle gọn gàng).
3. Chọn chế độ nhóm:
   - **Thủ công:** Chọn `Sản phẩm được chọn thủ công` → sau khi tạo hoặc tại mục `Danh sách sản phẩm`, tìm và tick thêm từng sản phẩm theo SKU/tên.
   - **Tự động (`Smart Collection`):** Chọn `Sản phẩm tự động cập nhật theo điều kiện` → chọn `Thỏa mãn tất cả điều kiện` hoặc `Thỏa mãn một trong các điều kiện` → thêm bộ quy tắc (ví dụ: `Tag` `bằng` `sale-he-2026` VÀ `Tồn kho` `lớn hơn` `0`).
4. Chọn kiểu `Sắp xếp sản phẩm` (ví dụ `Bán chạy nhất` hoặc `Mới nhất`), chụp ảnh cấu hình nhóm trước khi bấm `Lưu`.

### Kịch bản 5: Gắn Ảnh Biến Thể & Kiểm Tra Hiển Thị Kênh Bán Hàng Đa Kênh
1. Mở `/admin/products/{product_id}` của sản phẩm vừa tạo (hoặc sản phẩm đã có nhiều màu sắc).
2. Cuộn xuống bảng **Biến thể**, bấm vào ô ảnh đại diện bên trái từng dòng biến thể (hoặc lọc theo thuộc tính `Màu sắc`) để gán đúng ảnh màu tương ứng từ thư viện ảnh của sản phẩm.
3. Tại cột phải khối **Hiển thị**, rà soát từng kênh bán (`Website`, `Haravan POS`, `Facebook`, `Instagram`, Sàn TMĐT) và ngày hẹn lịch hiển thị (nếu ra mắt bộ sưu tập mới).
4. **Dừng trước nút `Lưu`**, chụp ảnh bảng biến thể đã gán đủ ảnh màu và danh sách kênh hiển thị chờ người dùng xác nhận.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Protocol)

1. **Pha 1 — Pre-State Capture (Sao lưu danh mục gốc):**
   - Mở `/admin/products` hoặc `/admin/products/collections`, xác nhận đúng `store_domain` và chụp ảnh danh sách gốc (`pre_screenshot`).
   - Với mọi thao tác **Bulk Edit** hoặc **Import Excel**, bắt buộc bấm `Xuất dữ liệu` (`.xlsx`) cho tập sản phẩm bị ảnh hưởng để lưu file backup cục bộ trước khi chỉnh sửa.
2. **Pha 2 — Stage Without Saving (`dry_run: true`):**
   - Điền đầy đủ tên sản phẩm, mô tả, ảnh, thuộc tính biến thể (`Màu sắc`/`Kích thước`), bảng SKU/Giá/Khối lượng, thông số SEO, điều kiện `Smart Collection` hoặc chọn sẵn file Import/tác vụ Bulk.
   - Kiểm tra kỹ không có biến thể nào để giá `0đ` hoặc thiếu `Khối lượng (gram)` ngoài ý muốn.
   - **Dừng tuyệt đối trước nút `Lưu` / `Nhập dữ liệu` / `Áp dụng`**.
3. **Pha 3 — Screenshot-Before-Save Gate (Cổng xác nhận người dùng):**
   - Chụp `preview_screenshot` (hiển thị bảng biến thể + giá bán + kênh hiển thị hoặc hộp thoại cấu hình Import).
   - Lập bảng đối chiếu `Before → After` nhấn mạnh chênh lệch giá bán, số lượng biến thể, SKU mới, trạng thái ẩn/hiện kênh và tùy chọn ghi đè Handle, sau đó dừng chờ người dùng duyệt.
4. **Pha 4 — Save & Post-Save Reload Verification (Xác minh sau lưu):**
   - Sau khi người dùng xác nhận, bấm `Lưu` (hoặc `Nhập dữ liệu`), chờ toast xanh (`Tạo sản phẩm thành công` / `Cập nhật thành công`).
   - Nhấn `F5` reload lại trang chi tiết sản phẩm/nhóm sản phẩm để xác minh đủ số biến thể, ảnh không vỡ, URL handle hợp lệ, Smart Collection khớp số lượng SP dự kiến và chụp `post_screenshot`.

### Checklist Kiểm Định Chất Lượng Danh Mục (Catalog QA Checklist)

- [ ] Tổng số tổ hợp biến thể ≤ `100` và số thuộc tính ≤ `3` (giới hạn kỹ thuật Haravan).
- [ ] Mọi biến thể đều có `Mã SKU` duy nhất (đã kiểm tra không trùng SKU toàn cửa hàng), `Giá bán > 0`, và nếu có `Giá so sánh` thì `Giá so sánh > Giá bán`.
- [ ] Đã nhập `Khối lượng (gram)` thực tế sau đóng gói để các hãng vận chuyển (GHN/GHTK/VTP) tính phí ship không bị sai lệch.
- [ ] `Meta Title` ≤ 70 ký tự, `Meta Description` ≤ 320 ký tự, `URL Handle` không dấu và có Redirect 301 nếu sửa URL sản phẩm cũ.
- [ ] File Import sử dụng định dạng `.xlsx` chuẩn Haravan, cột SKU/Barcode định dạng `Text` để không mất số `0` đầu.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Thay đổi Danh mục

| Đối tượng (SKU / Handle) | Trường thay đổi | Trước (Before) | Sau (After — Staged) | Kiểm tra QA |
| :--- | :--- | :--- | :--- | :--- |
| `ao-polo-pique-nam` | Biến thể & Giá | *(Tạo mới)* | 6 biến thể (`Đen/Trắng` × `M/L/XL`), Giá `350.000đ`, Giá so sánh `420.000đ` | ✅ Đủ SKU & khối lượng `280g` |
| `ao-polo-pique-nam` | Kênh hiển thị & SEO | *(Tạo mới)* | `Website: Tắt (Nháp)`, `POS: Bật`; Handle `/products/ao-polo-pique-nam` | ✅ Không trùng Handle |
| Batch 18 SP (`tag: he-2025`) | Bulk Action (`Thao tác`) | `Hiển thị trên Website` | `Ẩn sản phẩm` + thêm tag `ngung-kinh-doanh-2026` | ✅ Đã Export `.xlsx` backup |
| Nhóm `Sale Hè 2026` | Loại & Điều kiện | *(Chưa tồn tại)* | Tự động (`Tất cả`): `Tag = sale-he-2026` & `Tồn kho > 0` | ✅ Sắp xếp `Bán chạy nhất` |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-products-catalog-ops",
  "mode": "proposal",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/products/new",
  "scenario": "create_variant_product",
  "session_authenticated": true,
  "dry_run": true,
  "backup_exported": true,
  "overwrite_existing_handle": false,
  "affected_products_count": 1,
  "variants_count": 6,
  "pre_screenshot": "artifacts/products_catalog_pre.png",
  "preview_screenshot": "artifacts/products_catalog_staged.png",
  "post_screenshot": null,
  "changes_staged": [
    {
      "handle": "ao-polo-pique-nam",
      "action": "create",
      "variants": 6,
      "price_range_vnd": [350000, 350000],
      "compare_at_price_vnd": 420000,
      "weight_grams": 280,
      "channels": ["POS"]
    }
  ],
  "warnings": [],
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm trên `/admin/products` & `/admin/products/collections`:**
  - `Xóa sản phẩm` / `Xóa vĩnh viễn` / `Xóa nhóm sản phẩm` (gây gãy link SEO 404, mất dữ liệu lịch sử sản phẩm trong báo cáo và hỏng liên kết đồng bộ sàn TMĐT).
  - Bật `Ghi đè sản phẩm trùng Handle` trong hộp thoại Import Excel khi chưa có file Export `.xlsx` backup và chưa có xác nhận rõ ràng của người dùng.
  - Đổi giá hàng loạt giảm > 50% hoặc đặt giá `0đ` mà không có xác nhận kiểm tra chéo (nguy cơ lỗ nặng do đặt nhầm đơn vị nghìn đồng).
- **Credential & Publishing Gate:**
  - Khi phiên hết hạn chuyển về `accounts.haravan.com`, dừng ngay để người dùng tự đăng nhập; không hỏi mật khẩu/OTP qua chat.
  - Với sản phẩm mới tạo chưa chốt ảnh/mô tả cuối cùng, luôn giữ trạng thái **Ẩn trên Website** (`Nháp`) cho đến khi người dùng xác nhận bật hiển thị Live.

### Ma Trận Kiểm Soát Import Excel Chuẩn Haravan (`.xlsx`)

| Cột trọng yếu trong File Mẫu | Quy chuẩn định dạng bắt buộc | Lỗi thường gặp cần chặn trước khi Import |
| :--- | :--- | :--- |
| `Url` (URL Handle) | Viết thường, không dấu, gạch ngang (`ao-polo-nam`) | Để trùng Handle của sản phẩm khác kèm bật `Ghi đè` |
| `SKU` & `Barcode` | Định dạng cột `Text` trong Excel | Excel tự cắt số `0` đầu hoặc chuyển thành `8.93E+12` |
| `Giá` & `Giá so sánh` | Số nguyên VND, không dấu chấm/phẩy, `Giá so sánh >= Giá` | Nhập thiếu ba số `0` (`350` thay vì `350000`) |
| `Khối lượng (gram)` | Số nguyên dương (ví dụ `280`) | Bỏ trống hoặc nhập `kg` thay vì `gram` làm sai cước ship |
| `Link hình` | URL ảnh công khai `https://...` tải được (HTTP 200) | Dán link Google Drive nội bộ hoặc link hết hạn token |

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Vượt quá 100 biến thể / 3 thuộc tính:** Haravan chặn không cho lưu nếu tổ hợp thuộc tính vượt 100 biến thể (ví dụ 10 màu × 12 size = 120). Agent phải dừng và đề xuất tách sản phẩm theo nhóm màu hoặc theo dòng sản phẩm.
2. **Lỗi Import Excel sai encoding / sai link ảnh:** File `.csv` mở bằng Excel thường lỗi font tiếng Việt UTF-8 hoặc mất số `0` đầu của `Barcode`/`SKU`. Luôn ưu tiên định dạng `.xlsx` (Excel) chuẩn tải từ nút `Tải file mẫu` và định dạng cột SKU/Barcode kiểu `Text`.
3. **Đổi URL Handle của sản phẩm đang chạy quảng cáo / có traffic SEO:** Khi sửa `Đường dẫn / Alias` của sản phẩm cũ, bắt buộc tick tùy chọn `Tạo chuyển hướng URL` (Redirect 301) hoặc kiểm tra bằng `store-redirect-audit` để không gây lỗi 404.
4. **Sản phẩm đang liên kết sàn TMĐT (Shopee/Lazada/TikTok):** Thay đổi mã SKU hoặc xóa biến thể trực tiếp trên Haravan có thể làm đứt mapping đồng bộ tồn kho sàn. Agent phải kiểm tra cảnh báo liên kết kênh trước khi sửa SKU.
5. **Smart Collection không hiển thị sản phẩm ngay lập tức:** Khi mới tạo nhóm tự động với hàng trăm sản phẩm, hệ thống mất vài chục giây để lập chỉ mục; reload lại trang sau 15–30 giây trước khi kết luận sai điều kiện lọc.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

### Quy trình Rollback Thủ công theo Từng Kịch bản
- **Sản phẩm mới tạo nhầm:** Không xóa vĩnh viễn ngay nếu đã lỡ phát sinh đơn hàng/lịch sử kho; mở `/admin/products/{id}` → bỏ tick toàn bộ kênh hiển thị (`Ẩn`) và gắn tag `nhap-huy` để giữ toàn vẹn dữ liệu đối soát.
- **Bulk Edit giá / tag / hiển thị sai tập sản phẩm:** Mở `/admin/products` → `Nhập dữ liệu` → tải lại đúng file Export `.xlsx` backup đã xuất ở Pha 1 (chỉ lọc giữ các dòng bị ảnh hưởng) để khôi phục nguyên trạng giá và tag cũ.
- **Nhóm sản phẩm tự động (`Smart Collection`) lọc nhầm sản phẩm:** Mở `/admin/products/collections/{id}` → khôi phục lại điều kiện lọc hoặc đổi chế độ hiển thị sang `Ẩn` khỏi kênh Website.
- **Đổi URL Handle gây lỗi 404:** Kiểm tra và bổ sung ngay chuyển hướng URL 301 tại `/admin/sale_channels/online_store/settings` hoặc qua `store-redirect-audit`.

### Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan
- Kiểm toán chất lượng danh mục, trùng SKU/Barcode, ảnh thiếu Alt bằng API: `skills/api-mcp/20-catalog-merchandising/catalog-data-completeness-audit`, `catalog-duplicate-sku-barcode`, `catalog-image-alt-audit`.
- Đề xuất cập nhật giá bán, dọn giá so sánh & tái cấu trúc collection số lượng lớn qua API: `pricing-bulk-adjustment-proposal`, `pricing-compare-at-cleanup`, `catalog-bulk-import-proposal`, `catalog-collection-reorg-proposal`.
- Cấu hình bảng giá B2B/đại lý & quản lý kho nâng cao trên UI: `skills/browser-ui/20-catalog-merchandising/catalog-pricing-list-b2b-proposal`, `skills/browser-ui/30-inventory-supply/admin-ui-inventory-advanced-ops`.
