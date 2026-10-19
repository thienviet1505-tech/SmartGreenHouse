# CHANGES (bản vá sau khi review)

## Sửa lỗi
| # | File | Nội dung |
|---|---|---|
| 1 | `backend/app/timeutil.py`, `services/state.py`, `routes.py`, `main.py` | Timestamp luôn là chuỗi ISO có `+00:00`. Trước đây `datetime` làm `send_json` lỗi và trình duyệt bị loại khỏi danh sách realtime; biểu đồ cũng lệch 7 giờ. |
| 2 | `gateway/gateway.py`, `backend/app/main.py` | Backend bắt lỗi từng message nên một message xấu không làm rớt kết nối. (Cách xử lý cảm biến lỗi đã đổi ở mục B1 bên dưới.) |
| 3 | `run_gateway.bat`, README | Chạy bằng `python -m gateway.gateway` (import tương đối). |
| 4 | `backend/app/config.py` | Backend đọc `.env` ở thư mục gốc (trước đây bỏ qua hoàn toàn). |
| 5 | `gateway/gateway.py`, `devices/relay.py` | Khởi động: ghi OFF cả 2 relay để phần cứng và phần mềm khớp nhau. |
| 6 | `gateway/gateway.py`, `control/controller.py` | Đọc từng cảm biến riêng; cảm biến lỗi hoặc dữ liệu cũ hơn `SENSOR_STALE_SECONDS` thì bị AUTO bỏ qua, cảm biến còn lại vẫn điều khiển. |
| 7 | `backend/app/main.py` | Mỗi lần gateway kết nối, backend gửi `set_rules` từ DB. |
| 8 | (cùng mục 1) | Lệch múi giờ biểu đồ. |
| 9 | `gateway/modbus/client.py` | `serial timeout=0.02` + deadline riêng: mỗi lần đọc ~vài ms thay vì 0.8 s; thêm khoảng nghỉ giữa các frame 6 ms. |
| 10 | `backend/app/security.py`, `routes.py`, `main.py`, `frontend/app.js` | `DASHBOARD_TOKEN` (Bearer) cho mọi `/api/*` và `/ws/live`; bỏ `/api/ingest/telemetry`; bỏ CORS `*`; so sánh token bằng `compare_digest`. |
| 11 | `gateway/gateway.py` | Đổi mode chỉ khi ghi relay thành công; khóa `control_lock` giữa luồng poll và lệnh web. |
| 12 | `backend/app/main.py`, `routes.py` | Tự xóa dữ liệu cũ (`RETENTION_DAYS`), `/api/history` giảm mẫu (xem B5 và B8 bên dưới). |
| 13 | `frontend/app.js` | Poll `/api/state` mỗi 5 s, hiển thị `--` khi chưa có số liệu, xử lý token. |

## Đợt sửa thứ 2

| # | File | Nội dung |
|---|---|---|
| B1 | `gateway/gateway.py`, `backend/app/main.py`, `services/state.py` | Gateway **luôn** gửi `telemetry`, cảm biến lỗi hoặc cũ hơn `SENSOR_STALE_SECONDS` gửi `null` (không gửi lại giá trị cuối cùng). Backend vẫn cập nhật trạng thái relay/mode, chỉ lưu dòng lịch sử khi đủ 3 giá trị. Trước đây khi cảm biến nhiệt độ không trả lời, web không bao giờ thấy relay/mode đổi, và giá trị cũ bị lưu như dữ liệu mới. |
| B2 | `services/state.py` | Số đo cũ hơn 30 s (gateway hoặc cảm biến mất) hiển thị `--` thay vì như đang đo. |
| B3 | `gateway/gateway.py`, `config.py` | Relay không trả lời: AUTO nghỉ `RELAY_RETRY_SECONDS` (mặc định 10 s) rồi mới thử lại, và thử lại bằng lệnh ghi không đổi trạng thái (`Relay2CH.restore()`); `rs485_ok` tự về OK khi relay trả lời lại. |
| B4 | `gateway/gateway.py`, `devices/relay.py` | Trạng thái quạt/đèn theo đúng `FAN_CHANNEL`/`LED_CHANNEL` (trước đây gán cứng kênh 0 và 1); cấu hình kênh sai bị từ chối ngay khi khởi động. |
| B5 | `routes.py` | `/api/history` lấy mẫu ngay trong SQL (`id % step`): 7 ngày dữ liệu từ ~4.3 s xuống ~0.04 s mỗi request. |
| B6 | `frontend/app.js` | Hộp thoại token chỉ hiện 1 lần (dùng chung cho các request song song), bấm Cancel thì dừng polling, không xóa nhầm token vừa nhập, WebSocket tự mở lại khi có token. |
| B7 | `frontend/index.html`, `app.js`, `main.py` | Chart.js: ưu tiên file `frontend/chart.umd.js`, nếu không có thì CDN đã ghim `4.4.7`; thiếu Chart.js chỉ mất biểu đồ, dashboard vẫn chạy. |
| B8 | `backend/app/main.py` | `RETENTION_DAYS` <= 0 tắt việc dọn dữ liệu (trước đây xóa sạch bảng mỗi giờ). |
| B9 | `run_gateway.bat` | Bỏ lệnh uvicorn bị dính vào dòng 1. |
| B10 | `gateway/gateway.py` | Tắt gateway: dừng luồng poll trước khi đóng cổng COM (hết lỗi `byref()` trên Windows); gửi `telemetry` ngay sau mỗi lệnh web thành công; ghi log thanh ghi TH đang dùng và cảnh báo nếu `TH_TEMP_REG`/`TH_HUM_REG` chưa có trong `gateway/.env`. |

Để biểu đồ chạy khi không có internet: tải https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.js và lưu thành `frontend/chart.umd.js`.

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
