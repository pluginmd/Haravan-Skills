# Haravan API Error Codes & Recovery Playbook

| HTTP Status | Ý nghĩa | Nguyên nhân phổ biến trên Haravan | Hành động bắt buộc của Agent |
| :---: | :--- | :--- | :--- |
| **400** | Bad Request | Sai định dạng JSON, thiếu wrapper key (ví dụ thiếu `{"product": {...}}`) | Không retry; kiểm tra payload schema |
| **401** | Unauthorized | Token hết hạn, sai `Bearer` token, hoặc Private App bị thu hồi | **Dừng ngay lập tức**; yêu cầu người dùng làm mới token (OAuth2 refresh hoặc kiểm tra ENV) |
| **403** | Forbidden | Thiếu scope (ví dụ gọi `/com/inventories` nhưng thiếu `com.read_inventories`) hoặc tính năng chỉ có trên gói Plus/Omni | **Dừng ngay**; báo chính xác scope bị thiếu đối chiếu `config/permissions.yaml` |
| **404** | Not Found | Sai `id` bản ghi hoặc dùng nhầm prefix `/com/` thay vì `/web/` | Kiểm tra lại surface (`/com/` vs `/web/`) và tồn tại của bản ghi |
| **422** | Unprocessable Entity | Dữ liệu vi phạm nghiệp vụ (ví dụ SKU trùng, hủy đơn đã hoàn tất, giá âm) | Ghi nhận vào error log; không retry payload giống hệt |
| **429** | Too Many Requests | Vượt giới hạn leaky bucket Haravan (**80 req / 4 req/s**) | **Exponential backoff** (`1s → 2s → 4s → 8s`) + giảm tốc độ gọi xuống ≤ 2 req/s |
| **500 / 502 / 503 / 504** | Server / Gateway Error | Sự cố tạm thời phía máy chủ Haravan | Retry tối đa 5 lần với jitter; nếu đang chạy L3 mutation phải kiểm tra lại bằng `GET` để tránh tạo trùng |
