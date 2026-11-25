# Playbook 03: Trực chiến Mega Sale (9.9 / 11.11 / 12.12 / Tết) trên Haravan Omni

## T-3 Ngày (Chuẩn bị & Kiểm thử)
1. **Khóa tồn kho & đồng bộ sàn:** Chạy `inventory-multi-location-audit`, `catalog-duplicate-sku-barcode` và `inventory-stocktake-cycle-count` cho nhóm SKU chủ lực (nhóm A) để chống oversell và phạt hủy đơn trên Shopee/TikTok Shop.
2. **Thiết lập giá & khuyến mãi an toàn:** Dùng `pricing-bulk-adjustment-proposal` (`dry_run: true` + lưu `.backup.json`) và `marketing-promo-code-proposal` (có `ends_at` rõ ràng, kiểm tra không chồng mã qua `marketing-promotion-hygiene-audit`).
3. **Kiểm tra Storefront & Tracking:** Chạy `theme-performance-cro-audit`, `storefront-script-tag-audit` và `storefront-file-storage-audit` (nén banner < 500KB).

## T-24 Giờ (Đóng băng kỹ thuật — Code Freeze)
- **CẤM sửa Live Theme**, **CẤM đổi tên miền**, **CẤM cài thêm app/script mới**.
- Tạm dừng các scheduled audit quét toàn catalog trong khung giờ cao điểm (00:00–02:00 và 20:00–23:00) để dành trọn leaky bucket `80 req / 4 req/s` cho webhooks đơn hàng, POS và đồng bộ sàn.

## Trong ngày Sale (T-0)
- Theo dõi `inventory-low-stock-watchdog` mỗi 2 giờ và `order-risk-cod-boom-signals` mỗi 30 phút.
- Nếu phát hiện sai giá diện rộng hoặc bão `429`: kích hoạt ngay `ops-incident-runbook-escalation` + `governance-rollback-executor` từ file `.backup.json`.

## Sau Sale (T+2 Ngày)
- Chạy `pricing-compare-at-cleanup` dọn giá gạch ngang sau sale, `marketing-promotion-hygiene-audit` tắt mã hết hạn và `finance-profit-margin-analyzer` đánh giá biên lợi nhuận thực tế.
