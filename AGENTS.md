# AGENTS.md — Quy tắc bắt buộc cho AI Agent vận hành Haravan

Tài liệu này quy định **luật bắt buộc** cho mọi AI Agent (Antigravity, Claude Code, Cursor, Codex, MCP client) khi làm việc với repository `haravan-ops-skills` và kết nối tới cửa hàng Haravan (`*.myharavan.com` / `apis.haravan.com`).

---

## 1. Quy tắc an toàn tối thượng (Non-Negotiable Safety Rules)

1. **Read-Only Mặc Định (L1 First):**
   - Khi người dùng yêu cầu phân tích, kiểm tra, báo cáo hoặc audit, **chỉ sử dụng** HTTP `GET` và các skill ở `mode: read`.
   - Không bao giờ tự ý thực hiện `POST`, `PUT`, `PATCH`, `DELETE` khi chưa có yêu cầu ghi dữ liệu rõ ràng.
2. **Dry-Run Bắt Buộc (`dry_run: true`):**
   - Mọi skill ở tầng `L2` (`proposal`) và `L3` (`write`) **phải** chạy `dry_run: true` trước để tạo bản xem trước (preview diff + số lượng bản ghi bị ảnh hưởng + ước tính rủi ro).
   - Không bao giờ bỏ qua bước dry-run kể cả khi người dùng nói "làm nhanh đi".
3. **Xác Nhận Ở Lượt Riêng (Separate-Turn Confirmation):**
   - Với mọi skill `L3` (`risk: high` hoặc `critical`), Agent phải trình bày bản preview/dry-run, dừng lại và chờ người dùng xác nhận tường minh ở **lượt hội thoại tiếp theo** trước khi gọi API ghi.
   - Các thao tác **tuyệt đối không được tự ý chạy**: hủy đơn hàng (`cancel`), hoàn tiền (`refund`), xuất kho/tạo vận đơn hàng loạt (`fulfillment`), sửa giá hàng loạt, publish theme trực tiếp lên live theme, chỉnh `robots.txt` live.
4. **Least-Privilege Scopes:**
   - Chỉ yêu cầu đúng Haravan scopes khai báo trong `SKILL.md` (xem `config/permissions.yaml`).
   - Không bao giờ đề xuất cấp full scopes nếu chỉ cần `com.read_*`.
5. **Không Bao Giờ Lộ Bí Mật (Zero Secret Exposure):**
   - Không commit, không in ra log/stdout/artifact bất kỳ `HARAVAN_ACCESS_TOKEN`, `CLIENT_SECRET`, hay `WEBHOOK_SECRET` nào.
   - Luôn đọc credentials từ biến môi trường (`ENV`).
6. **Bảo Vệ Dữ Liệu Cá Nhân (PII Protection):**
   - Tuân thủ `policies/pii-handling.md`: che số điện thoại (`090****678`), che email (`a***@domain.com`), không xuất toàn bộ danh sách khách hàng (raw export) trừ khi có yêu cầu rõ ràng và được duyệt.
7. **Giới Hạn Batch & Dừng Khi Lỗi Một Phần:**
   - Tôn trọng `max_records` khai báo trong từng skill (mặc định ≤ 25 với L3 critical write, ≤ 100 với L2 proposal).
   - Áp dụng `partial_failure_policy: stop` cho các mutation tài chính/đơn hàng: gặp lỗi đầu tiên phải dừng ngay, ghi log trạng thái các bản ghi đã chạy và chưa chạy.

---

## 2. Quy chuẩn kỹ thuật Haravan

- **Base URLs:**
  - Commerce API: `https://apis.haravan.com/com/`
  - Online Store / Web API: `https://apis.haravan.com/web/`
  - Connect Webhook API: `https://webhook.haravan.com/api/subscribe`
- **Auth Header:** `Authorization: Bearer <HARAVAN_ACCESS_TOKEN>` và `Content-Type: application/json`.
- **Rate Limit (Leaky Bucket):** Bucket = `80` requests, Leak rate = `4` requests/second.
  - Khi gặp HTTP `429 Too Many Requests`, áp dụng exponential backoff (tối thiểu 1s, 2s, 4s) và giảm concurrency xuống 1–2 req/s.
  - Luôn ưu tiên dùng `scripts/hrv_client.py` thay vì tự viết raw `curl` trong vòng lặp.
- **Theme Operations:**
  - Không sửa trực tiếp Live Theme (`role: "main"`). Phải duplicate/staging theme trước và dùng `@haravan/cli` (`haravan pull` / `haravan deploy`) hoặc kiểm tra kỹ bản backup asset trước khi `PUT`.
- **Haravan Admin Browser UI Operations (`95-admin-ui-browser`):**
  - Tuân thủ nghiêm ngặt `policies/browser-ui-safety.md` và `api/admin-ui-sitemap.yaml`.
  - Khi chưa đăng nhập (`accounts.haravan.com`), dừng lại để người dùng tự đăng nhập trực tiếp trên trình duyệt; tuyệt đối không hỏi hoặc tự nhập mật khẩu/OTP.
  - Áp dụng **Screenshot-Before-Save**: điền form/cấu hình xong phải chụp ảnh preview và chờ người dùng xác nhận trước khi bấm nút `Lưu` (với L3 như Thanh toán `/admin/settings/payments`, Phân quyền `/admin/settings/accounts`, Tên miền `/admin/settings/domains` bắt buộc `separate_turn: true`).
  - Với 5 màn hình con dưới `Website` (`/admin/sale_channels/online_store/*`) chạy trong cross-origin iframe `https://web.haravan.app`, ưu tiên dùng Web API (`/web/*`) và `@haravan/cli`.
- **Tuyên bố trách nhiệm tài chính (Financial Disclaimer):**
  - Mọi báo cáo doanh thu, biên lợi nhuận, đối soát COD, thuế GTGT là **Operational Estimate / Reconciliation Aid** — không khẳng định là sổ cái kế toán chính thức hay bằng chứng sai lệch thanh toán của đơn vị vận chuyển/cổng thanh toán khi chưa đối chiếu chứng từ gốc.

---

## 3. Quy trình làm việc chuẩn của Agent

1. **Tra cứu đúng Loại Skill (2 Kênh Thực Thi Tách Biệt):**
   - **Loại 1 — `skills/api-mcp/` (`execution_channel: api_mcp`, `requires_token: true`, chỉ mục [registry-api-mcp.json](registry-api-mcp.json)):** Chạy qua Haravan REST API (`/com/`, `/web/`), `scripts/hrv_ops.py`, `mcp/haravan_mcp_server.py` hoặc `@haravan/cli` — yêu cầu `HARAVAN_ACCESS_TOKEN`.
   - **Loại 2 — `skills/browser-ui/` (`execution_channel: browser_ui`, `requires_token: false`, chỉ mục [registry-browser-ui.json](registry-browser-ui.json)):** Thao tác chuột/form trực tiếp trên trình duyệt Haravan Admin (`*.myharavan.com/admin`) — không cần API token, chỉ cần người dùng tự đăng nhập trình duyệt.
2. **Đọc Contract:** Đọc YAML frontmatter của `SKILL.md` để nắm `mode`, `risk`, `scopes`, `max_records`, `pii_level`.
3. **Kiểm tra Môi trường:** Xác nhận đang trỏ đúng `dev`/`staging` hay `production`. Với thao tác mới, luôn ưu tiên thử trên `staging`/dev store trước.
4. **Thực thi Read / Dry-Run:** Gọi API qua `scripts/hrv_client.py`, lưu backup artifact nếu chuẩn bị ghi dữ liệu.
5. **Báo cáo & Xác nhận:** Trả kết quả theo đúng Output Template (Human Summary + JSON/CSV). Nếu là L2/L3, chờ xác nhận trước khi apply.
6. **Xác minh sau ghi (Post-Write Verification):** Sau khi ghi thành công, gọi lại `GET` để xác nhận trạng thái thực tế trên Haravan khớp với kỳ vọng.
