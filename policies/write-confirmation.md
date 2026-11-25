# Policy: Write Confirmation & Proposal-First Workflow (Layers L2 & L3)

## Quy trình bắt buộc 3 bước (Propose → Confirm → Apply)

### Bước 1: Dry-Run & Proposal (Luôn chạy trước)
- Mọi skill L2 và L3 phải mặc định `dry_run: true`.
- Thực hiện truy vấn `GET` để lấy trạng thái hiện tại, tính toán diff (Before → After) và lưu bản preview + backup snapshot vào thư mục artifacts/scratch (`dry_run_report.py`).
- Trình bày rõ cho người dùng:
  1. Cửa hàng mục tiêu (`store_domain`, môi trường `staging` hay `production`).
  2. Tổng số bản ghi bị ảnh hưởng (phải ≤ `max_records`).
  3. Bảng diff mẫu (ít nhất 5 dòng đầu + tóm tắt min/max thay đổi).
  4. Rủi ro và khả năng rollback (`supported: true/false`).

### Bước 2: Xác nhận của người vận hành (Human Approval Gate)
- **Tầng L2 (`medium` risk):** Yêu cầu người dùng xác nhận rõ ràng trước khi chạy `dry_run: false`.
- **Tầng L3 (`high` / `critical` risk):** **Bắt buộc `separate_turn: true`** — Agent phải kết thúc lượt trả lời sau khi hiển thị dry-run, chờ người dùng phản hồi xác nhận tường minh (ví dụ: *"Xác nhận chạy batch #ID trên production"*) ở lượt tiếp theo mới được phép gọi API ghi.

### Bước 3: Apply & Post-Write Verification
- Trước khi ghi, kiểm tra xung đột (conflict check): nếu `updated_at` của bản ghi trên Haravan đã thay đổi so với lúc tạo proposal → **dừng và cảnh báo**.
- Áp dụng `partial_failure_policy: stop` cho L3.
- Sau khi ghi xong, gọi `GET` xác minh lại các bản ghi đã thay đổi và xuất báo cáo kết quả kèm đường dẫn file backup để rollback nếu cần.
