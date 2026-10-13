import json
import threading
import time
from datetime import datetime, timezone
<<<<<<< HEAD
import websocket
=======

import websocket

>>>>>>> Rac
from .config import settings
from .control.controller import AutoController, ControlRules
from .devices.light import SEN0644
from .devices.relay import Relay2CH
from .devices.sht30 import SHT30
from .logger import setup_logging
from .modbus.client import ModbusRTU

<<<<<<< HEAD
=======

def now_iso():
    return datetime.now(timezone.utc).isoformat()


>>>>>>> Rac
class GreenhouseGateway:
    def __init__(self):
        self.log = setup_logging()
        self.bus = ModbusRTU(settings.com_port, settings.baudrate, settings.timeout)
<<<<<<< HEAD
        self.sht30 = SHT30(self.bus, settings.sht30_id)
        self.light = SEN0644(self.bus, settings.light_id)
        self.relay = Relay2CH(self.bus, settings.relay_id)
        self.controller = AutoController(ControlRules(settings.fan_on_temp, settings.fan_off_temp, settings.led_on_lux, settings.led_off_lux))
        self.ws = None
        self.ws_lock = threading.Lock()
=======
        self.sht30 = SHT30(self.bus, settings.sht30_id, settings.th_function,
                           settings.th_temp_reg, settings.th_hum_reg, settings.th_scale)
        self.light = SEN0644(self.bus, settings.light_id)
        self.relay = Relay2CH(self.bus, settings.relay_id)
        self.controller = AutoController(ControlRules(
            settings.fan_on_temp, settings.fan_off_temp, settings.led_on_lux, settings.led_off_lux))
        self.ws = None
        self.ws_lock = threading.Lock()
        self.control_lock = threading.RLock()  # poll thread vs. web commands
>>>>>>> Rac
        self.ws_connected = False
        self.running = True
        self.temperature = None
        self.humidity = None
        self.light_lux = None
<<<<<<< HEAD
        self.rs485_ok = False
        self.last_error = None
        self.last_telemetry = 0.0

=======
        self.th_time = 0.0      # monotonic time of last good SHT30 read
        self.light_time = 0.0   # monotonic time of last good light read
        self.rs485_ok = False
        self.last_error = None
        self.last_telemetry = 0.0
        self._logged_error = None
        self._logged_at = 0.0

    # ------------------------------------------------------------ web link
>>>>>>> Rac
    def send_ws(self, payload):
        with self.ws_lock:
            if self.ws is None or not self.ws_connected:
                return False
            try:
                self.ws.send(json.dumps(payload))
                return True
            except Exception as exc:
                self.log.warning("[WEB] Send failed: %s", exc)
                return False

    def send_event(self, message, level="INFO"):
<<<<<<< HEAD
        self.send_ws({"type": "event", "level": level, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()})

    def set_relay_state(self, device, state, source, reason):
        channel = settings.fan_channel if device == "fan" else settings.led_channel
        self.relay.set_channel(channel, state)
        self.log.info("[%s] %s -> %s | CH%d | reason=%s", source, device.upper(), "ON" if state else "OFF", channel + 1, reason)
=======
        self.send_ws({"type": "event", "level": level, "message": message, "timestamp": now_iso()})

    def ack(self, request_id, device, command, ok, message):
        self.send_ws({"type": "ack", "request_id": request_id, "device": device, "command": command,
                      "ok": ok, "message": message, "timestamp": now_iso()})

    # ------------------------------------------------------------- relays
    def set_relay_state(self, device, state, source, reason):
        channel = settings.fan_channel if device == "fan" else settings.led_channel
        self.relay.set_channel(channel, state)
        self.log.info("[%s] %s -> %s | CH%d | reason=%s", source, device.upper(),
                      "ON" if state else "OFF", channel + 1, reason)

    def init_relays(self):
        """Start from a known state: both relays OFF (also fail-safe)."""
        try:
            self.relay.initialize_off()
            self.log.info("[RELAY] id=%d initialised: FAN=OFF LED=OFF", settings.relay_id)
        except Exception as exc:
            self.log.warning("[RELAY] id=%d not reachable at start-up: %s", settings.relay_id, exc)
>>>>>>> Rac

    def handle_control(self, message):
        request_id = message.get("request_id", "")
        device = message.get("device")
        mode = message.get("mode")
        state = message.get("state")
<<<<<<< HEAD
=======
        command = f"{mode}:{state}"
>>>>>>> Rac
        try:
            if device not in ("fan", "led"):
                raise ValueError(f"Unknown device: {device}")
            if mode not in ("AUTO", "MANUAL"):
                raise ValueError(f"Unknown mode: {mode}")
<<<<<<< HEAD
            if device == "fan":
                self.controller.fan_mode = mode
            else:
                self.controller.led_mode = mode
            if mode == "MANUAL":
                if state is None:
                    raise ValueError("MANUAL command requires state=true/false")
                self.set_relay_state(device, bool(state), "WEB COMMAND", "manual control from website")
            else:
                self.log.info("[WEB COMMAND] %s -> AUTO", device.upper())
            self.send_ws({"type": "ack", "request_id": request_id, "device": device, "command": f"{mode}:{state}", "ok": True, "message": f"{device} {mode} applied", "timestamp": datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            self.log.error("[WEB COMMAND ERROR] %s | %s", device, exc)
            self.send_ws({"type": "ack", "request_id": request_id, "device": device, "command": f"{mode}:{state}", "ok": False, "message": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()})

    def handle_rules(self, message):
        try:
            rules = ControlRules(float(message["fan_on_temp"]), float(message["fan_off_temp"]), float(message["led_on_lux"]), float(message["led_off_lux"]))
            self.controller.update_rules(rules)
            self.log.info("[WEB RULES] FAN %.1f/%.1f°C | LED %.0f/%.0f lux", rules.fan_off_temp, rules.fan_on_temp, rules.led_on_lux, rules.led_off_lux)
            self.send_ws({"type": "ack", "request_id": message.get("request_id", ""), "device": "CONTROL_RULES", "command": "SET_RULES", "ok": True, "message": "AUTO rules applied to gateway", "timestamp": datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            self.log.error("[WEB RULES ERROR] %s", exc)

=======
            if mode == "MANUAL" and state is None:
                raise ValueError("MANUAL command requires state=true/false")
            with self.control_lock:
                previous = self.controller.fan_mode if device == "fan" else self.controller.led_mode
                self._set_mode(device, mode)
                if mode == "MANUAL":
                    try:
                        self.set_relay_state(device, bool(state), "WEB COMMAND", "manual control from website")
                    except Exception:
                        self._set_mode(device, previous)  # relay write failed: keep old mode
                        raise
                else:
                    self.log.info("[WEB COMMAND] %s -> AUTO", device.upper())
            self.ack(request_id, device, command, True, f"{device} {mode} applied")
        except Exception as exc:
            self.log.error("[WEB COMMAND ERROR] %s | %s", device, exc)
            self.ack(request_id, device, command, False, str(exc))

    def _set_mode(self, device, mode):
        if device == "fan":
            self.controller.fan_mode = mode
        else:
            self.controller.led_mode = mode

    def handle_rules(self, message):
        request_id = message.get("request_id", "")
        try:
            rules = ControlRules(float(message["fan_on_temp"]), float(message["fan_off_temp"]),
                                 float(message["led_on_lux"]), float(message["led_off_lux"]))
            self.controller.update_rules(rules)
            self.log.info("[WEB RULES] FAN %.1f/%.1f°C | LED %.0f/%.0f lux", rules.fan_off_temp,
                          rules.fan_on_temp, rules.led_on_lux, rules.led_off_lux)
            self.ack(request_id, "CONTROL_RULES", "SET_RULES", True, "AUTO rules applied to gateway")
        except Exception as exc:
            self.log.error("[WEB RULES ERROR] %s", exc)
            self.ack(request_id, "CONTROL_RULES", "SET_RULES", False, str(exc))

    # ---------------------------------------------------------- websocket
>>>>>>> Rac
    def on_open(self, ws):
        with self.ws_lock:
            self.ws = ws
            self.ws_connected = True
        self.log.info("[WEB] Connected to %s", settings.web_ws_url)
        self.send_ws({"type": "hello", "token": settings.gateway_token, "gateway": "windows-rs485"})

    def on_message(self, ws, raw_message):
        try:
            message = json.loads(raw_message)
<<<<<<< HEAD
            if message.get("type") == "hello_ack":
                self.log.info("[WEB] Authentication accepted")
            elif message.get("type") == "control":
                self.handle_control(message)
            elif message.get("type") == "set_rules":
=======
            kind = message.get("type")
            if kind == "hello_ack":
                self.log.info("[WEB] Authentication accepted")
            elif kind == "control":
                self.handle_control(message)
            elif kind == "set_rules":
>>>>>>> Rac
                self.handle_rules(message)
        except Exception as exc:
            self.log.error("[WEB] Invalid message: %s", exc)

    def on_error(self, ws, error):
        self.log.error("[WEB SOCKET] %s", error)

    def on_close(self, ws, status_code, message):
        with self.ws_lock:
            self.ws_connected = False
            self.ws = None
        self.log.warning("[WEB] Disconnected: code=%s message=%s", status_code, message)

<<<<<<< HEAD
    def read_hardware(self):
        try:
            sht = self.sht30.read()
            light = self.light.read()
            self.temperature = sht.temperature
            self.humidity = sht.humidity
            self.light_lux = light.lux
            self.rs485_ok = True
            self.last_error = None

            next_fan, next_led = self.controller.evaluate(self.temperature, self.light_lux, self.relay.fan_state, self.relay.led_state)
            if next_fan != self.relay.fan_state and self.controller.fan_mode == "AUTO":
                self.set_relay_state("fan", next_fan, "AUTO", f"temperature={self.temperature:.1f}°C")
            if next_led != self.relay.led_state and self.controller.led_mode == "AUTO":
                self.set_relay_state("led", next_led, "AUTO", f"light={self.light_lux:.1f} lux")
        except Exception as exc:
            self.rs485_ok = False
            self.last_error = str(exc)
            self.log.warning("[RS485] %s", exc)

    def publish_telemetry(self):
=======
    # ----------------------------------------------------------- hardware
    def _fresh(self, value, read_time):
        if value is None:
            return None
        return value if time.monotonic() - read_time <= settings.sensor_stale_seconds else None

    def apply_auto_control(self):
        errors = []
        temperature = self._fresh(self.temperature, self.th_time)
        lux = self._fresh(self.light_lux, self.light_time)
        with self.control_lock:
            next_fan, next_led = self.controller.evaluate(temperature, lux, self.relay.fan_state, self.relay.led_state)
            if self.controller.fan_mode == "AUTO" and next_fan != self.relay.fan_state:
                try:
                    self.set_relay_state("fan", next_fan, "AUTO", f"temperature={temperature:.1f}°C")
                except Exception as exc:
                    errors.append(f"RELAY(id={settings.relay_id}): {exc}")
            if self.controller.led_mode == "AUTO" and next_led != self.relay.led_state:
                try:
                    self.set_relay_state("led", next_led, "AUTO", f"light={lux:.1f} lux")
                except Exception as exc:
                    errors.append(f"RELAY(id={settings.relay_id}): {exc}")
        return errors

    def read_hardware(self):
        """Each sensor is read on its own: one failing sensor must not stop
        AUTO control that depends on the other one."""
        errors = []
        try:
            reading = self.sht30.read()
            self.temperature, self.humidity = reading.temperature, reading.humidity
            self.th_time = time.monotonic()
        except Exception as exc:
            errors.append(f"TH(id={settings.sht30_id}): {exc}")
        try:
            self.light_lux = self.light.read().lux
            self.light_time = time.monotonic()
        except Exception as exc:
            errors.append(f"LIGHT(id={settings.light_id}): {exc}")
        errors += self.apply_auto_control()

        self.rs485_ok = not errors
        self.last_error = ("; ".join(errors))[:250] if errors else None
        self._log_errors(self.last_error)

    def _log_errors(self, text):
        now = time.monotonic()
        if text is None:
            if self._logged_error is not None:
                self.log.info("[RS485] Recovered, all devices answering")
            self._logged_error = None
            return
        if text != self._logged_error or now - self._logged_at > 30:
            self.log.warning("[RS485] %s", text)
            self._logged_error, self._logged_at = text, now

    def publish_telemetry(self):
        if self.temperature is None or self.humidity is None or self.light_lux is None:
            # No complete reading yet: report link status only (the backend
            # cannot store telemetry with empty values).
            self.send_ws({"type": "status", "online": True, "rs485_ok": self.rs485_ok,
                          "last_error": self.last_error or "Waiting for first sensor readings",
                          "timestamp": now_iso()})
            return
>>>>>>> Rac
        self.send_ws({
            "type": "telemetry",
            "temperature": self.temperature,
            "humidity": self.humidity,
            "light": self.light_lux,
            "fan_state": self.relay.fan_state,
            "led_state": self.relay.led_state,
            "fan_mode": self.controller.fan_mode,
            "led_mode": self.controller.led_mode,
            "rs485_ok": self.rs485_ok,
            "last_error": self.last_error,
<<<<<<< HEAD
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def poll_loop(self):
        self.log.info("[RS485] COM=%s baud=%d | SHT30=%d | LIGHT=%d | RELAY=%d", settings.com_port, settings.baudrate, settings.sht30_id, settings.light_id, settings.relay_id)
        while self.running:
            self.read_hardware()
            now = time.monotonic()
            if now - self.last_telemetry >= settings.telemetry_interval:
                self.publish_telemetry()
                self.last_telemetry = now
=======
            "timestamp": now_iso(),
        })

    def poll_loop(self):
        self.log.info("[RS485] COM=%s baud=%d | TH=%d | LIGHT=%d | RELAY=%d", settings.com_port,
                      settings.baudrate, settings.sht30_id, settings.light_id, settings.relay_id)
        while self.running:
            try:
                self.read_hardware()
                now = time.monotonic()
                if now - self.last_telemetry >= settings.telemetry_interval:
                    self.publish_telemetry()
                    self.last_telemetry = now
            except Exception as exc:  # never let the poll thread die
                self.log.exception("[POLL] unexpected error: %s", exc)
>>>>>>> Rac
            time.sleep(settings.poll_interval)

    def websocket_loop(self):
        while self.running:
            try:
<<<<<<< HEAD
                ws = websocket.WebSocketApp(settings.web_ws_url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
=======
                ws = websocket.WebSocketApp(settings.web_ws_url, on_open=self.on_open, on_message=self.on_message,
                                            on_error=self.on_error, on_close=self.on_close)
>>>>>>> Rac
                ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                self.log.error("[WEB] Connection error: %s", exc)
            if self.running:
                time.sleep(3)

    def run(self):
        self.log.info("==============================================")
        self.log.info("SMART GREENHOUSE WINDOWS GATEWAY")
        self.log.info("==============================================")
        try:
            self.bus.open()
            self.log.info("[RS485] Port opened successfully")
<<<<<<< HEAD
=======
            self.init_relays()
>>>>>>> Rac
            threading.Thread(target=self.poll_loop, daemon=True).start()
            threading.Thread(target=self.websocket_loop, daemon=True).start()
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log.info("Stopping gateway...")
        except Exception as exc:
            self.log.exception("Fatal gateway error: %s", exc)
        finally:
            self.running = False
            self.bus.close()
            self.log.info("Gateway stopped.")

<<<<<<< HEAD
=======

>>>>>>> Rac
if __name__ == "__main__":
    GreenhouseGateway().run()
