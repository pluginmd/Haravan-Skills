# Policy: Customer PII Handling (Chuẩn dữ liệu cá nhân Việt Nam)

## Phân loại dữ liệu PII trên Haravan
- **`none`**: Sản phẩm, bộ sưu tập, tồn kho, cấu hình shop, theme, blog.
- **`customer`**: Họ tên khách hàng, số điện thoại (`phone`), email, địa chỉ giao hàng (`shipping_address`), ghi chú khách hàng (`note`).
- **`financial`**: Dữ liệu giao dịch, đối soát COD, số tiền hoàn trả, mã số thuế, thông tin xuất hóa đơn.

## Quy tắc che/ẩn (Redaction Rules)
1. **Số điện thoại VN:** Luôn che phần giữa khi in ra báo cáo/log: `0901234567` → `090****567` (chỉ giữ 3 số đầu và 3 số cuối).
2. **Email:** Che tên người dùng: `nguyen.van.a@gmail.com` → `ng***@gmail.com`.
3. **Địa chỉ chi tiết:** Trong báo cáo tổng hợp/phân tích vùng miền, chỉ giữ **Tỉnh/Thành phố** và **Quận/Huyện**; ẩn số nhà, tên đường.
4. **Họ tên:** Trong báo cáo nhóm (RFM, cohort, churn), chỉ dùng `customer_id` thay cho họ tên đầy đủ.

## Quy tắc Export & Lưu trữ
- `export_allowed: false` là mặc định cho mọi skill có `pii_level: customer`.
- Không bao giờ xuất toàn bộ danh sách khách hàng ra file CSV/JSON chỉ để trả lời câu hỏi phân tích.
- File tạm chứa dữ liệu khách hàng (nếu có) chỉ được giữ tối đa **7 ngày** và tuyệt đối không commit vào git.
