# Policy: Read-Only Operations (Layer L1)

## Nguyên tắc cốt lõi
1. Tất cả skill tầng **L1** chỉ được phép sử dụng phương thức HTTP **`GET`**.
2. Không bao giờ gửi `POST`, `PUT`, `PATCH`, `DELETE` trong quá trình chạy skill L1.
3. Chỉ yêu cầu các scope đọc (`com.read_*`, `web.read_*`).

## Kiểm soát hiệu năng & Rate Limit
- Luôn truyền tham số `fields=` nếu chỉ cần một tập nhỏ thuộc tính (ví dụ `fields=id,title,variants` khi kiểm tra giá/SKU) để giảm tải payload.
- Tôn trọng leaky bucket Haravan (`80` req / `4` req/s), giữ tốc độ mục tiêu ≤ `2.5` req/s.
- Luôn giới hạn phạm vi thời gian (`created_at_min`, `created_at_max`) khi quét đơn hàng (`GET /com/orders.json`).

## Tính xác thực của dữ liệu
- Nếu cửa hàng có số lượng bản ghi vượt `max_pages_per_audit_run`, phải ghi rõ trong báo cáo rằng kết quả là **partial sample** kèm mốc thời gian/số lượng đã quét.
- Không suy diễn hoặc bịa số liệu khi API trả về thiếu trường (ví dụ thiếu `cost_price` / COGS).
