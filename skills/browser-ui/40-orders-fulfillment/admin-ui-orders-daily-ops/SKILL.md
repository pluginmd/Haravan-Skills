---
name: admin-ui-orders-daily-ops
description: "Vận hành Đơn hàng hàng ngày trên Haravan Admin (/admin/orders): lọc đa điều kiện, tạo đơn thủ công, xác nhận thanh toán chuyển khoản, gắn tag/ghi chú, tách giao hàng, sửa địa chỉ đơn chưa giao và in phiếu đơn/vận đơn."
version: 1.0.0
execution_channel: browser_ui
requires_token: false
domain: 40-orders-fulfillment
layer: L2
wave: 2
mode: proposal
risk: medium
haravan:
  api_surface: admin_ui
  scopes:
    []
  endpoints:
    - "UI /admin/orders"
    - "UI /admin/orders/new"
    - "UI /admin/orders/{order_id}"
execution:
  dry_run: true
  confirmation_required: true
  separate_turn: false
  max_records: 50
  idempotency_required: true
  partial_failure_policy: stop
privacy:
  pii_level: customer
  redact_output: true
  export_allowed: false
rollback:
  supported: true
  backup_required: true
---

# Haravan Admin UI — Vận Hành Đơn Hàng Hàng Ngày (`/admin/orders`)

## 1. Mục tiêu, Phạm vi UI & Pre-flight Check (Owner vs Staff, Gói dịch vụ)

- **Mục tiêu nghiệp vụ:** Tự động hóa an toàn các thao tác xử lý đơn hàng lặp lại hàng ngày trực tiếp trên giao diện Haravan Admin (`https://{store_domain}/admin/orders`) mà không cần API token: lọc hàng đợi xử lý, tạo đơn thủ công (từ Zalo/Hotline), xác nhận thanh toán chuyển khoản ngân hàng, gắn tag/ghi chú nội bộ, tách giao hàng (partial fulfillment) cho đơn nhiều kho/thiếu hàng, cập nhật địa chỉ nhận hàng cho đơn chưa bàn giao vận chuyển, và mở bản xem trước in phiếu giao hàng / hóa đơn.
- **Phạm vi UI:** Danh sách đơn hàng (`/admin/orders`), màn hình chi tiết đơn hàng (`/admin/orders/{order_id}`), màn hình tạo đơn mới (`/admin/orders/new` hoặc tạo từ `/admin/draft_orders`). Không bao gồm hủy đơn, hoàn tiền, hoặc xuất kho hàng loạt (chuyển sang `admin-ui-shipments-cod-mass-fulfill` hoặc API L3).
- **Quyền tài khoản (Owner vs Staff):**
  - **Owner:** Toàn quyền xem, tạo, sửa, xác nhận thanh toán, tách giao hàng, in phiếu trên mọi kho và kênh bán.
  - **Staff:** Yêu cầu vai trò có quyền `Đơn hàng` (`Xem đơn hàng`, `Tạo đơn hàng`, `Cập nhật đơn hàng`, `Xác nhận thanh toán`, `Giao hàng`). Nếu Staff bị giới hạn chi nhánh/kho hoặc bị ẩn nút `Xác nhận thanh toán`, Agent phải dừng và báo thiếu quyền.
- **Yêu cầu Gói dịch vụ Haravan:** Khả dụng trên mọi gói (Standard, Pro, Grow, Scale). Tính năng tách giao hàng từ nhiều kho yêu cầu cửa hàng đã bật tối thiểu 2 kho tại `/admin/settings/locations` (gói Pro trở lên).
- **Pre-flight Check bắt buộc:**
  1. Kiểm tra phiên đăng nhập qua `admin-ui-session-navigator` tại `https://{store_domain}/admin/orders`. Nếu bị chuyển hướng về `https://accounts.haravan.com`, dừng ngay để người dùng tự đăng nhập.
  2. Xác nhận đúng `store_domain` (không nhầm cửa hàng `staging` và `production`).
  3. Xác nhận các đơn hàng mục tiêu chưa ở trạng thái `Đã hủy` (`Cancelled`) hoặc `Đã lưu trữ` (`Archived`).

## 2. Bản đồ Giao diện Thực tế (Exact Route, Section/Tab, Nhãn nút bấm, Cột bảng & Bộ lọc)

| Thành phần UI | Route / Vị trí chính xác | Nhãn hiển thị thực tế (Exact UI Labels) | Ghi chú thao tác |
| :--- | :--- | :--- | :--- |
| Danh sách đơn hàng | `/admin/orders` | Thanh tab lọc nhanh: `Tất cả đơn hàng`, `Đơn hàng mới`, `Chưa giao hàng`, `Chưa thanh toán` | Hỗ trợ lưu bộ lọc tùy chỉnh (`Lưu bộ lọc`) |
| Nút hành động chính | Góc trên bên phải `/admin/orders` | `Tạo đơn hàng`, `Xuất dữ liệu` (PII — bị chặn mặc định), `Thao tác` (khi tick checkbox) | Nút `Thao tác` mở menu: `Gắn tag`, `Bỏ tag`, `In đơn hàng`, `Xác nhận đơn hàng` |
| Thanh Bộ lọc đa điều kiện | Ngay trên bảng `/admin/orders` | Nút `Thêm điều kiện lọc` + Ô `Tìm kiếm` (mã đơn `#1001`, SĐT, tên, email) | Bộ lọc: `Trạng thái thanh toán`, `Trạng thái giao hàng`, `Kênh bán hàng`, `Kho bán hàng`, `Phương thức thanh toán`, `Tag`, `Ngày tạo` |
| Cột bảng đơn hàng | Bảng chính `/admin/orders` | `Mã đơn hàng`, `Ngày tạo`, `Khách hàng`, `Thanh toán`, `Giao hàng`, `COD`, `Tổng tiền`, `Kênh` | Click vào mã `#10xxx` để mở `/admin/orders/{order_id}` |
| Chi tiết đơn — Khối Sản phẩm & Giao hàng | `/admin/orders/{order_id}` (Cột trái) | `Xác nhận đơn hàng`, `Giao hàng`, `Tách giao hàng` / chọn số lượng từng dòng SP, `In đơn hàng` | Chỉ cho sửa địa chỉ hoặc tách giao khi trạng thái là `Chưa giao hàng` / `Giao một phần` |
| Chi tiết đơn — Khối Thanh toán | `/admin/orders/{order_id}` (Cột trái dưới) | `Xác nhận thanh toán`, `Ghi nhận thanh toán` (chọn phương thức: `Chuyển khoản`, `Tiền mặt`, `COD`) | Cần đối chiếu mã giao dịch ngân hàng trước khi xác nhận |
| Chi tiết đơn — Khối Khách hàng & Tag | `/admin/orders/{order_id}` (Cột phải) | `Thông tin giao hàng` (icon bút chì `Sửa`), `Ghi chú đơn hàng`, `Nhãn (Tags)` | Sửa địa chỉ gồm: `Tỉnh/Thành`, `Quận/Huyện`, `Phường/Xã`, `Địa chỉ chi tiết`, `Số điện thoại` |
| Tạo đơn thủ công | `/admin/orders/new` | `Tìm kiếm sản phẩm`, `Tìm hoặc tạo khách hàng`, `Thêm khuyến mãi`, `Thêm phí giao hàng`, `Thanh toán sau` / `Đã thanh toán` | Nút cuối trang: `Tạo đơn hàng` (hoặc `Lưu nháp`) |

## 3. Bảng Tham số Đầu vào (`Parameter | Type | Required | Default | Validation`)

| Parameter | Type | Required | Default | Validation / Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `store_domain` | `string` | Có | — | Khớp `^[a-z0-9-]+\.myharavan\.com$` hoặc domain admin hợp lệ |
| `scenario` | `enum` | Có | `filter_and_tag` | `filter_and_tag` \| `create_manual_order` \| `confirm_bank_transfer` \| `split_fulfillment` \| `edit_shipping_address` \| `print_order_slip` |
| `order_codes` | `array<string>` | Không | `[]` | Tối đa `50` mã đơn (`max_records: 50`), định dạng `#10001` hoặc `10001` |
| `filter_criteria` | `object` | Không | `{}` | Chứa `payment_status`, `fulfillment_status`, `channel`, `location`, `tag`, `date_from`, `date_to` |
| `tags_to_add` | `array<string>` | Không | `[]` | Mỗi tag ≤ 40 ký tự, không chứa ký tự đặc biệt `,;` |
| `internal_note` | `string` | Không | `""` | Tối đa 500 ký tự; không ghi thông tin nhạy cảm (CCCD/số thẻ) |
| `bank_transfer_ref` | `object` | Khi xác nhận CK | `null` | Bắt buộc có `amount_vnd` (> 0), `bank_code`, `transaction_ref`, `received_at` |
| `shipping_address_patch` | `object` | Khi sửa địa chỉ | `null` | Đủ 4 cấp địa giới VN (`province`, `district`, `ward`, `address1`) và `phone` hợp lệ |
| `split_items` | `array<object>` | Khi tách giao | `[]` | Mỗi phần tử gồm `sku`, `ship_qty` (`1 <= ship_qty <= unfulfilled_qty`), `warehouse` |
| `dry_run` | `boolean` | Không | `true` | Luôn bắt buộc `true` ở lần chạy đầu (Stage Without Saving) |

## 4. Ma trận Kịch bản Thao tác Đa dạng (5 Scenarios Click-by-Click)

### Kịch bản 1: Lọc hàng đợi đơn hàng đa điều kiện & Gắn Tag / Ghi chú hàng loạt
1. Điều hướng tới `https://{store_domain}/admin/orders`, chờ bảng đơn hàng tải hoàn tất (hết spinner).
2. Bấm `Thêm điều kiện lọc` → chọn `Trạng thái giao hàng` = `Chưa giao hàng` → bấm `Thêm điều kiện lọc` → chọn `Trạng thái thanh toán` = `Chờ xử lý` (hoặc `Đã thanh toán`) → chọn thêm `Kênh bán hàng` (ví dụ `Website`, `Harasocial`, `Shopee`) và `Kho bán hàng`.
3. Kiểm tra tổng số đơn khớp bộ lọc trên thanh tiêu đề bảng; đảm bảo số đơn cần xử lý ≤ `50`.
4. Tick checkbox chọn từng đơn mục tiêu (không dùng "Chọn tất cả trang" nếu vượt `max_records`).
5. Bấm dropdown `Thao tác` → chọn `Thêm tag` → nhập `tags_to_add` (ví dụ `uu-tien-giao-sang`, `da-goi-xac-nhan`).
6. **Dừng trước khi bấm `Áp dụng`/`Lưu`**, chụp ảnh modal xác nhận tag để người dùng duyệt; nếu cần thêm ghi chú nội bộ cho từng đơn, mở `/admin/orders/{order_id}` → nhập vào ô `Ghi chú` → dừng trước khi bấm `Lưu`.

### Kịch bản 2: Tạo đơn hàng thủ công từ Hotline / Zalo (`/admin/orders/new`)
1. Tại `/admin/orders`, bấm nút xanh `Tạo đơn hàng` ở góc trên bên phải để mở `/admin/orders/new`.
2. Tại khối **Sản phẩm**, gõ SKU hoặc tên sản phẩm vào ô `Tìm kiếm sản phẩm`, chọn đúng biến thể (Màu/Size), điều chỉnh `Số lượng` và chọn đúng `Kho xuất hàng`.
3. Tại khối **Khách hàng**, nhập số điện thoại khách hàng để tìm hồ sơ có sẵn (tránh tạo trùng); nếu khách mới, bấm `Tạo khách hàng mới`, điền Tên, SĐT và địa chỉ giao hàng đủ 4 cấp.
4. Nếu có mã giảm giá hoặc phí ship thỏa thuận, bấm `Thêm khuyến mãi` / `Thêm phí giao hàng`, nhập giá trị khớp yêu cầu và ghi rõ nguồn đơn ở ô `Ghi chú` (ví dụ `Don Hotline - NV Sale A`).
5. Chọn trạng thái thanh toán: mặc định chọn `Thanh toán sau` (`COD` hoặc `Chuyển khoản`); chỉ chọn `Đã thanh toán` khi người dùng cung cấp bằng chứng tiền về.
6. Cuộn kiểm tra lại `Tổng cộng` và thông tin người nhận (đã che PII khi báo cáo), chụp ảnh toàn trang ở trạng thái **chưa bấm `Tạo đơn hàng`**, chờ người dùng duyệt rồi mới bấm lưu.

### Kịch bản 3: Xác nhận thanh toán chuyển khoản ngân hàng trên đơn hàng
1. Mở trực tiếp `/admin/orders/{order_id}` (hoặc tìm mã đơn tại `/admin/orders` và click vào dòng đơn).
2. Kiểm tra khối **Thanh toán**: xác nhận trạng thái hiện tại là `Chờ xử lý` / `Chưa thanh toán` và `Số tiền cần thu` khớp chính xác `bank_transfer_ref.amount_vnd`.
3. Nếu lệch số tiền (khách chuyển thiếu hoặc dư), **DỪNG NGAY** và báo sai lệch cho người dùng, không tự ý xác nhận toàn phần.
4. Nếu khớp số tiền: bấm nút `Xác nhận thanh toán` (hoặc `Ghi nhận thanh toán`), chọn phương thức `Chuyển khoản ngân hàng`, điền mã tham chiếu `transaction_ref` vào ô ghi chú thanh toán (nếu có).
5. Chụp ảnh modal xác nhận (thể hiện rõ Mã đơn, Số tiền, Phương thức `Chuyển khoản`), chờ người dùng xác nhận trước khi bấm nút `Xác nhận` cuối cùng.

### Kịch bản 4: Tách giao hàng (Partial Fulfillment) & Sửa địa chỉ đơn chưa giao
1. **Tách giao hàng:** Tại `/admin/orders/{order_id}`, kiểm tra trạng thái giao hàng là `Chưa giao hàng` hoặc `Giao một phần`. Bấm nút `Giao hàng` (chọn `Tạo phiếu giao hàng` / không chọn tự động đẩy vận đơn hãng ngay nếu chưa duyệt).
2. Trong màn hình chia số lượng giao, chỉnh cột `Số lượng giao` của từng SKU khớp với `split_items` (đặt `0` cho các món hết hàng/chờ nhập), chọn đúng `Kho lấy hàng` cho đợt giao 1.
3. **Sửa địa chỉ đơn chưa giao:** Tại cột phải khối `Thông tin giao hàng`, kiểm tra đơn **chưa có mã vận đơn đang lấy hàng**. Bấm icon bút chì `Sửa` → cập nhật lần lượt `Tỉnh/Thành`, `Quận/Huyện`, `Phường/Xã`, `Địa chỉ chi tiết`, `Số điện thoại` (chọn từ dropdown địa giới hành chính của Haravan, không gõ tự do).
4. Chụp ảnh màn hình form địa chỉ hoặc màn hình tách số lượng trước khi bấm `Lưu` / `Xác nhận giao hàng`, chờ người dùng phê duyệt.

### Kịch bản 5: In phiếu đơn hàng / Phiếu giao hàng (Print Preview Only)
1. Tại `/admin/orders` (tick tối đa 50 đơn) → bấm `Thao tác` → `In đơn hàng`, hoặc tại `/admin/orders/{order_id}` → bấm `In đơn hàng` ở thanh công cụ trên cùng.
2. Chọn đúng mẫu in đã cấu hình (ví dụ `Mẫu in đơn hàng`, `Mẫu in phiếu giao hàng A5`, `Mẫu in nhiệt K80`).
3. Xác minh bản xem trước hiển thị đúng mã đơn, danh sách SKU, tổng thu hộ COD; chụp ảnh bản preview để người dùng tự bấm `In` hoặc lưu PDF cục bộ trên máy.

## 5. Quy trình An toàn 4 Pha (4-Phase Browser UI Safety Protocol)

1. **Pha 1 — Pre-State Capture (Sao lưu hiện trạng):**
   - Mở `/admin/orders` hoặc `/admin/orders/{order_id}`, chờ bảng/chi tiết tải hoàn tất (không còn spinner).
   - Ghi nhận đầy đủ trạng thái gốc: `order_code`, `payment_status`, `fulfillment_status`, `tags`, `shipping_address`, `total_price`, `tracking_number` (nếu có).
   - Chụp `pre_screenshot` làm bản sao lưu rollback thủ công trước khi chạm vào bất kỳ ô nhập liệu nào.
2. **Pha 2 — Stage Without Saving (`dry_run: true`):**
   - Thực hiện toàn bộ thao tác lọc hàng đợi, điền form tạo đơn mới, nhập tag/ghi chú, chọn số lượng tách giao hoặc sửa địa chỉ giao hàng 4 cấp.
   - Kiểm tra chéo tổng tiền, phí ship, mã SKU và kho xuất hàng ngay trên giao diện đã điền.
   - **Dừng tuyệt đối trước nút `Lưu` / `Tạo đơn hàng` / `Xác nhận thanh toán` / `Xác nhận giao hàng`**.
3. **Pha 3 — Screenshot-Before-Save Gate (Cổng xác nhận người dùng):**
   - Chụp `preview_screenshot` hiển thị rõ form/modal đã điền đầy đủ thông tin.
   - Xuất bảng đối chiếu `Before → After` (đã che toàn bộ PII khách hàng theo `policies/pii-handling.md`: SĐT `090****678`, Email `a***@domain.com`) và danh sách số đơn bị ảnh hưởng.
   - Dừng lại và chờ người dùng xác nhận rõ ràng trước khi bấm nút lưu.
4. **Pha 4 — Save & Post-Save Reload Verification (Xác minh sau lưu):**
   - Sau khi người dùng đồng ý, bấm nút lưu tương ứng đúng 1 lần (không double-click gây tạo trùng đơn).
   - Chờ toast thông báo xanh (`Cập nhật thành công` / `Tạo đơn hàng thành công`) hiển thị và spinner biến mất.
   - Nhấn `F5` reload lại trang `/admin/orders/{order_id}`, đọc lại DOM để xác minh `payment_status`, `tags`, `shipping_address` hoặc phiếu giao hàng mới đã được lưu bền vững, sau đó chụp `post_screenshot`.

### Checklist Xác minh Trước Khi Lưu (Pre-Save Sanity Check)

- [ ] Tổng số đơn trong batch ≤ `50` (`max_records: 50`) và không có đơn nào thuộc trạng thái `Đã hủy` / `Đã lưu trữ`.
- [ ] Nếu xác nhận thanh toán chuyển khoản: `amount_vnd` khớp tuyệt đối 100% với `Số tiền cần thu` trên đơn (không tự xác nhận khi khách chuyển thiếu).
- [ ] Nếu sửa địa chỉ giao hàng: đơn chưa có mã vận đơn đang lấy hàng ở ĐVVC và đủ 4 cấp địa giới hành chính Việt Nam.
- [ ] Nếu tạo đơn thủ công: đã tìm theo SĐT trước để tránh tạo trùng hồ sơ khách hàng, chọn đúng kho xuất có đủ tồn khả dụng.
- [ ] Không có nút Hard-Blocked nào (`Hủy đơn`, `Hoàn tiền`, `Xóa đơn`, `Xuất dữ liệu`) bị vô tình chọn.

## 6. Mẫu Preview `Before → After` & JSON Execution Log Schema

### Bảng Preview Thay đổi (PII đã che theo chuẩn)

| Mã đơn | Khách hàng (Redacted) | Trường thay đổi | Trước (Before) | Sau (After — Staged) | Trạng thái kiểm tra |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `#10482` | Nguyễn Văn A (`090****678`) | `Trạng thái thanh toán` | `Chờ xử lý` (`850.000đ`) | `Đã thanh toán` (`Chuyển khoản` — Ref `VCB98211`) | ✅ Khớp số tiền |
| `#10482` | Nguyễn Văn A (`090****678`) | `Nhãn (Tags)` | `website` | `website, da-ck-vcb, uu-tien-giao` | ✅ Hợp lệ |
| `#10485` | Trần Thị B (`098****123`) | `Địa chỉ giao hàng` | `P. Bến Nghé, Q.1, TP.HCM` | `P. Thảo Điền, TP. Thủ Đức, TP.HCM` | ✅ Chưa có vận đơn |
| `#10490` | Phạm Văn D (`093****889`) | `Tách giao hàng` | `Chưa giao hàng` (3 SKU) | Giao đợt 1: `2 SKU` từ `Kho Tổng HCM`; Chờ: `1 SKU` | ✅ Đủ tồn khả dụng |

### JSON Execution Log Schema

```json
{
  "skill": "admin-ui-orders-daily-ops",
  "mode": "proposal",
  "store_domain": "myshop.myharavan.com",
  "route": "/admin/orders/10482",
  "scenario": "confirm_bank_transfer",
  "session_authenticated": true,
  "dry_run": true,
  "pii_redacted": true,
  "affected_orders_count": 1,
  "max_records_limit": 50,
  "pre_screenshot": "artifacts/orders_10482_pre.png",
  "preview_screenshot": "artifacts/orders_10482_staged.png",
  "post_screenshot": null,
  "changes_staged": [
    {
      "order_code": "#10482",
      "customer_masked": "Nguyễn Văn A (090****678)",
      "field": "payment_status",
      "before": "pending",
      "after": "paid_bank_transfer",
      "amount_vnd": 850000,
      "bank_ref": "VCB98211"
    }
  ],
  "warnings": [],
  "saved_verified": false
}
```

## 7. Hard-Blocked Buttons & Credential/OTP/Financial Handoff Gates

- **Các nút TUYỆT ĐỐI CẤM tự bấm trên `/admin/orders`:**
  - `Hủy đơn hàng` (`Cancel order`) và `Hoàn tiền` (`Refund`) — thuộc rủi ro L3 tài chính/tồn kho, bắt buộc chuyển sang quy trình riêng (`order-cancel-restock-critical`) có xác nhận riêng lượt.
  - `Xóa đơn hàng` (`Delete`) hoặc `Lưu trữ hàng loạt` (`Archive`) khi chưa có yêu cầu tường minh.
  - `Xuất dữ liệu` (Export CSV/Excel toàn bộ danh sách đơn có chứa SĐT/địa chỉ khách) — bị khóa mặc định bởi `export_allowed: false` và `policies/pii-handling.md`.
  - `Đẩy đơn sang ĐVVC` / `Giao hàng hàng loạt` khi chưa chốt kho xuất, khối lượng gói hàng và cước vận chuyển.
- **Credential & Financial Handoff Gate:**
  - Gặp màn hình `accounts.haravan.com` → dừng ngay cho người dùng tự đăng nhập; tuyệt đối không hỏi mật khẩu/OTP qua chat.
  - Mọi xác nhận tiền chuyển khoản đều là **Operational Reconciliation Aid** — Agent không tự truy cập Internet Banking; người dùng chịu trách nhiệm xác minh sao kê ngân hàng thực tế trước khi duyệt bấm `Xác nhận thanh toán`.

### Bảng Phân Định Trách Nhiệm Thao Tác Đơn Hàng (Agent vs Operator)

| Thao tác trên `/admin/orders` | Agent được phép dựng (`Stage`) | Người dùng phải xác nhận / Tự thao tác |
| :--- | :--- | :--- |
| Lọc đơn đa điều kiện, gắn tag, ghi chú nội bộ | ✅ Lọc & nhập sẵn, chụp preview | Duyệt bảng `Before → After` trước khi bấm `Áp dụng` / `Lưu` |
| Tạo đơn thủ công, tách giao hàng, sửa địa chỉ | ✅ Điền đủ form 4 cấp / chọn SKU | Xác minh tổng tiền, kho xuất & địa chỉ trước khi bấm `Tạo` / `Lưu` |
| Xác nhận thanh toán chuyển khoản | ✅ Mở modal, điền mã tham chiếu | Đối chiếu sao kê ngân hàng thực tế trước khi duyệt bấm `Xác nhận` |
| Hủy đơn, hoàn tiền, xuất file Excel PII | ❌ Hard-Blocked | Chuyển sang quy trình L3 riêng hoặc Owner tự thực hiện trực tiếp |

## 8. Xử lý Sự cố UI & Tình huống Biên (Edge Cases)

1. **Đơn đã tạo vận đơn không cho sửa địa chỉ:** Khi đơn đã có mã vận đơn GHN/GHTK/ViettelPost ở trạng thái `Đang lấy hàng`, Haravan khóa hoặc cảnh báo không đồng bộ địa chỉ mới sang hãng vận chuyển. Agent phải dừng, báo rõ mã vận đơn đang hoạt động và đề xuất hủy phiếu vận đơn cũ trước (nếu chưa lấy hàng) thay vì sửa địa chỉ đơn thuần.
2. **Đơn đồng bộ từ Sàn TMĐT (Shopee / Lazada / TikTok Shop):** Các đơn từ sàn bị khóa chỉnh sửa sản phẩm, giá và địa chỉ giao hàng trên Haravan Admin. Agent kiểm tra cột `Kênh`; nếu là đơn sàn, chỉ thực hiện gắn `Tag` / `Ghi chú nội bộ` và cảnh báo không sửa thông tin cốt lõi.
3. **Dropdown Phường/Xã mới sau sáp nhập địa giới hành chính:** Nếu tên Phường/Xã người dùng cung cấp không khớp chính xác danh mục Haravan (ví dụ đổi tên hoặc gộp phường), Agent không chọn bừa mà liệt kê các lựa chọn hiện có trong dropdown để người dùng chốt.
4. **Hết tồn kho khả dụng khi tạo đơn thủ công hoặc tách giao:** Nếu Haravan hiển thị cảnh báo đỏ `Không đủ tồn kho tại kho X`, Agent dừng ở bước staging, chụp cảnh báo và hỏi người dùng đổi sang kho khác hay bật cho phép bán âm.
5. **Mất bộ lọc sau khi mở chi tiết đơn và bấm Back:** Mở chi tiết đơn bằng tab mới (`Ctrl+Click` / `target=_blank`) hoặc dùng nút `Lưu bộ lọc` trên `/admin/orders` để không mất danh sách hàng đợi đang xử lý.

## 9. Rollback Thủ công & Liên kết chéo với `skills/api-mcp/`

- **Rollback thủ công trên UI:**
  - *Tag / Ghi chú:* Mở lại `/admin/orders/{order_id}`, bấm dấu `x` trên tag vừa thêm hoặc khôi phục nội dung `Ghi chú` từ `pre_screenshot`.
  - *Địa chỉ giao hàng:* Bấm `Sửa` ở khối `Thông tin giao hàng`, nhập lại nguyên trạng 4 cấp địa giới từ `pre_screenshot`.
  - *Xác nhận thanh toán nhầm:* Haravan không cho "bỏ xác nhận thanh toán" trực tiếp bằng 1 nút sau khi đã ghi nhận `Đã thanh toán`; cần kế toán đối chiếu sổ quỹ hoặc thực hiện quy trình hủy/tạo lại đơn có phê duyệt Owner.
- **Liên kết chéo với `skills/api-mcp/` & Browser UI liên quan:**
  - Tra cứu/tổng hợp đơn nhanh bằng API (khi có token): `skills/api-mcp/40-orders-fulfillment/order-lookup-summary` và `order-triage-tagging-proposal`.
  - Xử lý hủy đơn hoàn kho hoặc xuất kho hàng loạt an toàn: `skills/api-mcp/40-orders-fulfillment/order-cancel-restock-critical`, `fulfillment-bulk-create-critical`.
  - Quản lý đơn nháp, đơn chưa hoàn tất & vận chuyển COD trên UI: `skills/browser-ui/40-orders-fulfillment/draft-orders-quote-proposal`, `order-abandoned-checkouts-audit`, `skills/browser-ui/95-admin-ui-browser/admin-ui-shipments-cod-mass-fulfill`.
