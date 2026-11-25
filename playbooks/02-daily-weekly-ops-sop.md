# Playbook 02: Vận hành Hàng ngày & Hàng tuần (Daily / Weekly Ops SOP)

## Nhịp vận hành Hàng ngày (UTC+7)
- **08:00 — Ban điều hành:** Chạy `ops-daily-morning-briefing` (`python3 scripts/hrv_ops.py morning-briefing`) nắm doanh thu đa kênh hôm qua, backlog đơn và cảnh báo tồn kho.
- **09:00 — CSKH & Xác nhận COD:** Chạy `order-risk-cod-boom-signals` (`cod-risk`) gọi xác nhận các đơn COD rủi ro cao trước khi kho đóng gói; chạy `fulfillment-status-digest-wismo` (`wismo`) xử lý đơn kẹt > 48h.
- **10:00 — Kho & Đồng bộ đa kênh:** Chạy `inventory-low-stock-watchdog` (`low-stock`) & `omnichannel-marketplace-sync-audit` kiểm tra lệch tồn Shopee/Lazada/TikTok/POS.
- **14:00 — Đóng gói & Đẩy vận đơn:** Dùng `admin-ui-shipments-cod-mass-fulfill` (duyệt trước khi đẩy hàng loạt `/admin/orders/mass_fulfill`) và `order-triage-tagging-proposal`.
- **16:00 — Khôi phục giỏ hàng:** Chạy `marketing-cart-recovery-zns` & `order-abandoned-checkouts-audit`.

## Nhịp vận hành Hàng tuần
- **Thứ Hai:** `ops-weekly-business-review` (WBR WoW) + `fulfillment-carrier-sla-vn` (đánh giá SLA GHN/GHTK/VTP/J&T).
- **Thứ Ba:** `finance-cod-reconciliation` + `finance-cashbook-debt-audit` (đối soát COD & sổ quỹ/công nợ).
- **Thứ Tư:** `catalog-data-completeness-audit` + `marketing-ads-feed-google-tiktok-audit`.
- **Thứ Năm:** `seo-metadata-serp-audit` + `store-redirect-audit`.
- **Thứ Sáu:** `inventory-aging-dead-stock` + `marketing-promotion-hygiene-audit`.
- **Thứ Bảy:** `customer-vip-churn-watchlist` + `customer-review-rating-moderation`.
