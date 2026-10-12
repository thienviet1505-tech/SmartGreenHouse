# CHANGES (bản vá sau khi review)

## Sửa lỗi
| # | File | Nội dung |
|---|---|---|
| 1 | `backend/app/timeutil.py`, `services/state.py`, `routes.py`, `main.py` | Timestamp luôn là chuỗi ISO có `+00:00`. Trước đây `datetime` làm `send_json` lỗi và trình duyệt bị loại khỏi danh sách realtime; biểu đồ cũng lệch 7 giờ. |
| 2 | `gateway/gateway.py`, `backend/app/main.py` | Chưa có dữ liệu cảm biến thì gateway gửi `status` thay vì `telemetry` chứa `None`. Backend bắt lỗi từng message nên một message xấu không làm rớt kết nối. |
| 3 | `run_gateway.bat`, README | Chạy bằng `python -m gateway.gateway` (import tương đối). |
| 4 | `backend/app/config.py` | Backend đọc `.env` ở thư mục gốc (trước đây bỏ qua hoàn toàn). |
| 5 | `gateway/gateway.py`, `devices/relay.py` | Khởi động: ghi OFF cả 2 relay để phần cứng và phần mềm khớp nhau. |
| 6 | `gateway/gateway.py`, `control/controller.py` | Đọc từng cảm biến riêng; cảm biến lỗi hoặc dữ liệu cũ hơn `SENSOR_STALE_SECONDS` thì bị AUTO bỏ qua, cảm biến còn lại vẫn điều khiển. |
| 7 | `backend/app/main.py` | Mỗi lần gateway kết nối, backend gửi `set_rules` từ DB. |
| 8 | (cùng mục 1) | Lệch múi giờ biểu đồ. |
| 9 | `gateway/modbus/client.py` | `serial timeout=0.02` + deadline riêng: mỗi lần đọc ~vài ms thay vì 0.8 s; thêm khoảng nghỉ giữa các frame 6 ms. |
| 10 | `backend/app/security.py`, `routes.py`, `main.py`, `frontend/app.js` | `DASHBOARD_TOKEN` (Bearer) cho mọi `/api/*` và `/ws/live`; bỏ `/api/ingest/telemetry`; bỏ CORS `*`; so sánh token bằng `compare_digest`. |
| 11 | `gateway/gateway.py` | Đổi mode chỉ khi ghi relay thành công; khóa `control_lock` giữa luồng poll và lệnh web. |
| 12 | `backend/app/main.py`, `routes.py` | Tự xóa dữ liệu cũ (`RETENTION_DAYS`), `/api/history` giảm mẫu còn tối đa 720 điểm. |
| 13 | `frontend/app.js` | Poll `/api/state` mỗi 5 s, hiển thị `--` khi chưa có số liệu, xử lý token. |

## Mới
* `gateway/tools/probe_modbus.py` - dò chỉ-đọc: thiết bị nào trả lời ở địa chỉ nào, bản đồ thanh ghi nào.
* `gateway/tools/set_relay_id.py` - đổi địa chỉ relay (khung lệnh theo tài liệu họ module relay cùng loại, CHƯA kiểm chứng với đúng board của bạn).
* Bảng địa chỉ: TH10S-B-PE = 1, SEN0644 = 2, Relay = 3 (không dùng 255).
* Bản đồ thanh ghi TH10S-B-PE cấu hình được trong `gateway/.env` (`TH_FUNCTION`, `TH_TEMP_REG`, `TH_HUM_REG`, `TH_SCALE`).

## Đã thử / chưa thử
* Đã thử: logic gateway trên bus RS485 giả lập 3 thiết bị (17 kiểm tra), 2 công cụ dò và đổi địa chỉ, biên dịch toàn bộ Python, cú pháp `app.js`.
* **Chưa thử**: backend FastAPI chạy thật (môi trường của mình không cài được FastAPI), phần cứng thật.

## Việc cần làm trước khi chạy thật
1. `copy .env.example .env` và `copy gateway\.env.example gateway\.env`; đặt `GATEWAY_TOKEN` giống nhau, đặt `DASHBOARD_TOKEN`.
2. Đổi địa chỉ từng thiết bị một (xem `gateway/README.md`).
3. Chạy `probe_modbus.py` với TH10S-B-PE, đối chiếu PDF rồi sửa `TH_*` trong `gateway\.env`.
4. Chạy `run_web.bat`, `run_gateway.bat`; mở web, nhập token; kiểm tra số liệu cập nhật và bấm thử quạt/đèn.
