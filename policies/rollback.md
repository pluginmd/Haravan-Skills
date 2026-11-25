# Policy: Backup, Idempotency & Rollback

## 1. Backup Trước Khi Ghi (Pre-Write Snapshot)
- Trước mọi thao tác `PUT` / `POST` / `DELETE` trên sản phẩm, giá, tồn kho, tag, redirect hoặc theme asset, bắt buộc lưu trạng thái `before` dưới dạng JSON (kèm `timestamp`, `store_domain`, `skill_name`, `operator`).
- Backup artifact phải lưu đủ thông tin để khôi phục nguyên trạng (ví dụ: `product_id`, `variant_id`, `price`, `compare_at_price`, `inventory_quantity`, `tags`).

## 2. Idempotency (Chống chạy trùng)
- Mỗi lần chạy batch ghi dữ liệu phải sinh một `run_id` / `idempotency_key` duy nhất (ví dụ: `hrv-20261125-pricing-001`).
- Ghi nhận từng bản ghi đã xử lý thành công vào execution log (`applied_ids`). Nếu phải chạy lại sau khi gián đoạn, tự động bỏ qua các ID đã thành công.

## 3. Xử lý Lỗi Một Phần (Partial Failure)
- Với **L3 Critical Write** (`order-cancel-restock-critical`, `fulfillment-bulk-create-critical`): áp dụng `partial_failure_policy: stop` — gặp lỗi ở bản ghi thứ *k* thì dừng ngay, không tiếp tục bản ghi *k+1*, báo cáo rõ danh sách đã chạy và chưa chạy.
- Với **L2 Proposal** (cập nhật tag, alt text, SEO metadata): có thể áp dụng `continue_with_error_log` nếu lỗi cục bộ (422 validation), nhưng vẫn phải dừng ngay nếu gặp `401`, `403`, hoặc `429` vượt số lần retry.

## 4. Khả năng Rollback theo loại thao tác
| Thao tác | Có thể Rollback tự động? | Cách xử lý |
| :--- | :---: | :--- |
| Giá bán / Giá so sánh / Tags / SEO / Redirect | Có | Dùng `governance-rollback-executor` từ file backup JSON |
| Điều chỉnh tồn kho (Inventory Adjustment) | Có (bằng phiếu bù trừ) | Tạo phiếu điều chỉnh ngược dấu, không xóa lịch sử kho |
| Theme Asset (Liquid/CSS/JS) | Có | Khôi phục file từ bản backup local / `@haravan/cli` |
| Hủy đơn hàng (`orders/{id}/cancel.json`) | **Không** | Không thể mở lại đơn đã hủy trên Haravan; phải tạo đơn mới |
| Hoàn tiền (`orders/{id}/refunds.json`) | **Không** | Giao dịch tài chính không đảo ngược |
| Tạo vận đơn đã đẩy sang NVC (GHN/GHTK...) | **Hạn chế** | Phải hủy vận đơn trên cả Haravan và cổng NVC trước khi lấy hàng |
