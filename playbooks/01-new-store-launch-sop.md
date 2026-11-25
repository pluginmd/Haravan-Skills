# Playbook 01: Quy trình Khai trương Cửa hàng Haravan Mới (Zero → Go-Live)

## Bước 1 — Xác thực & Nền tảng (`L0`)
1. Chạy `haravan-auth-setup` thiết lập Private App (chỉ cấp `com.read_*`, `web.read_*` trước) và kiểm tra kết nối bằng `python3 scripts/hrv_ops.py probe`.
2. Kiểm tra điều hướng Admin UI qua `admin-ui-session-navigator`.

## Bước 2 — Cấu hình 17 mục Haravan Admin UI (`95-admin-ui-browser`)
1. **Thông tin & Chính sách:** `admin-ui-general-policies-setup` (`/admin/settings/general`, `/admin/settings/policies` — đủ 5 trang chính sách phục vụ thông báo Bộ Công Thương).
2. **Kho & Địa chỉ lấy hàng:** `admin-ui-locations-inventory-ops` (`/admin/settings/locations` — bật `Địa điểm lấy hàng` & `Cập nhật thông tin xuất hoá đơn`).
3. **Vận chuyển & NVC VN:** `admin-ui-shipping-carriers-setup` (`/admin/settings/shipments` — biểu phí Tỉnh/Thành, kết nối GHN/GHTK/VTP/J&T, kích thước kiện hàng).
4. **Thanh toán (`L3` duyệt riêng):** `admin-ui-payment-methods-setup` (`/admin/settings/payments` — bật COD, Chuyển khoản/Haravan QR, cổng VNPay/MoMo).
5. **Checkout tối ưu chuyển đổi:** `admin-ui-checkout-settings` (`/admin/settings/checkouts` — chọn `Không ràng buộc tài khoản`, bật nhắc đơn 6h/24h, cân nhắc OTP Zalo).
6. **Phân quyền nhân sự (`L3` duyệt riêng):** `admin-ui-staff-roles-config` (`/admin/settings/group_permissions`, `accounts`).
7. **Thông báo & Mẫu in:** `admin-ui-notifications-print-webhooks` (`/admin/settings/notifications`).
8. **Tên miền & SSL (`L3` duyệt riêng):** `admin-ui-domains-channels-website` (`/admin/settings/domains` — xác minh DNS + SSL xanh trước khi đổi tên miền chính).

## Bước 3 — Chuẩn hóa Catalog, Theme & Go-Live Gate (`L1`)
1. Nhập sản phẩm qua `catalog-bulk-import-proposal` (`published: false` trước).
2. Chạy `catalog-data-completeness-audit` & `catalog-duplicate-sku-barcode` đảm bảo điểm ≥ 85, 0 SKU trùng, đủ `grams` tính ship.
3. Chạy `theme-liquid-code-review`, `seo-metadata-serp-audit` và cuối cùng chạy `store-bootstrap-checklist` đạt ≥ 90/100 trước khi mở chạy quảng cáo.
