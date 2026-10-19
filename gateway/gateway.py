import json
import os
import threading
import time
from datetime import datetime, timezone

import websocket

from .config import settings
from .control.controller import AutoController, ControlRules
from .devices.light import SEN0644
from .devices.relay import Relay2CH
from .devices.sht30 import SHT30
from .logger import setup_logging
from .modbus.client import ModbusRTU


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class GreenhouseGateway:
    def __init__(self):
        self.log = setup_logging()
        self.bus = ModbusRTU(settings.com_port, settings.baudrate, settings.timeout)
        self.sht30 = SHT30(self.bus, settings.sht30_id, settings.th_function,
                           settings.th_temp_reg, settings.th_hum_reg, settings.th_scale)
        self.light = SEN0644(self.bus, settings.light_id)
        self.relay = Relay2CH(self.bus, settings.relay_id)
        self.controller = AutoController(ControlRules(
            settings.fan_on_temp, settings.fan_off_temp, settings.led_on_lux, settings.led_off_lux))
        if {settings.fan_channel, settings.led_channel} != {0, 1}:
            raise ValueError("FAN_CHANNEL and LED_CHANNEL must be 0 and 1 (in either order)")
        self.ws = None
        self.ws_app = None
        self.ws_lock = threading.Lock()
        self.control_lock = threading.RLock()  # poll thread vs. web commands
        self.ws_connected = False
        self.stop_event = threading.Event()
        self.threads = []
        self._relay_error = None       # last relay failure, cleared by the next successful write
        self._relay_retry_at = 0.0     # AUTO control does not touch the relay before this time
        self.temperature = None
        self.humidity = None
        self.light_lux = None
        self.th_time = 0.0      # monotonic time of last good SHT30 read
        self.light_time = 0.0   # monotonic time of last good light read
        self.rs485_ok = False
        self.last_error = None
        self.last_telemetry = 0.0
        self._logged_error = None
        self._logged_at = 0.0

    # ------------------------------------------------------------ web link
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
        self.send_ws({"type": "event", "level": level, "message": message, "timestamp": now_iso()})

    def ack(self, request_id, device, command, ok, message):
        self.send_ws({"type": "ack", "request_id": request_id, "device": device, "command": command,
                      "ok": ok, "message": message, "timestamp": now_iso()})

    # ------------------------------------------------------------- relays
    @property
    def fan_state(self):
        return self.relay.states[settings.fan_channel]

    @property
    def led_state(self):
        return self.relay.states[settings.led_channel]

    def _relay_ok(self):
        self._relay_error = None
        self._relay_retry_at = 0.0

    def _relay_failed(self, exc):
        self._relay_error = f"RELAY(id={settings.relay_id}): {exc}"
        self._relay_retry_at = time.monotonic() + settings.relay_retry_seconds

    def set_relay_state(self, device, state, source, reason):
        channel = settings.fan_channel if device == "fan" else settings.led_channel
        try:
            self.relay.set_channel(channel, state)
        except Exception as exc:
            self._relay_failed(exc)
            raise
        self._relay_ok()
        self.log.info("[%s] %s -> %s | CH%d | reason=%s", source, device.upper(),
                      "ON" if state else "OFF", channel + 1, reason)

    def init_relays(self):
        """Start from a known state: both relays OFF (also fail-safe)."""
        try:
            self.relay.initialize_off()
            self._relay_ok()
            self.log.info("[RELAY] id=%d initialised: FAN=OFF LED=OFF", settings.relay_id)
        except Exception as exc:
            self._relay_failed(exc)
            self.log.warning("[RELAY] id=%d not reachable at start-up: %s", settings.relay_id, exc)

    def handle_control(self, message):
        request_id = message.get("request_id", "")
        device = message.get("device")
        mode = message.get("mode")
        state = message.get("state")
        command = f"{mode}:{state}"
        try:
            if device not in ("fan", "led"):
                raise ValueError(f"Unknown device: {device}")
            if mode not in ("AUTO", "MANUAL"):
                raise ValueError(f"Unknown mode: {mode}")
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
        else:
            self.publish_telemetry()  # the website sees the new state now, not at the next 2 s tick

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
    def on_open(self, ws):
        with self.ws_lock:
            self.ws = ws
            self.ws_connected = True
        self.log.info("[WEB] Connected to %s", settings.web_ws_url)
        self.send_ws({"type": "hello", "token": settings.gateway_token, "gateway": "windows-rs485"})

    def on_message(self, ws, raw_message):
        try:
            message = json.loads(raw_message)
            kind = message.get("type")
            if kind == "hello_ack":
                self.log.info("[WEB] Authentication accepted")
            elif kind == "control":
                self.handle_control(message)
            elif kind == "set_rules":
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
            next_fan, next_led = self.controller.evaluate(temperature, lux, self.fan_state, self.led_state)
            wanted = []
            if self.controller.fan_mode == "AUTO" and next_fan != self.fan_state:
                wanted.append(("fan", next_fan, f"temperature={temperature:.1f}°C"))
            if self.controller.led_mode == "AUTO" and next_led != self.led_state:
                wanted.append(("led", next_led, f"light={lux:.1f} lux"))

            if time.monotonic() >= self._relay_retry_at:
                if wanted:
                    for device, state, reason in wanted:
                        try:
                            self.set_relay_state(device, state, "AUTO", reason)
                        except Exception:
                            break  # relay is not answering: skip the rest, retry after RELAY_RETRY_SECONDS
                elif self._relay_error:
                    try:  # nothing to switch, but the relay was failing: probe it with an idempotent write
                        self.relay.restore()
                        self._relay_ok()
                        self.log.info("[RELAY] id=%d answering again", settings.relay_id)
                    except Exception as exc:
                        self._relay_failed(exc)
        if self._relay_error:
            errors.append(self._relay_error)
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
        """Always sent, so the website sees relay state/modes even while a sensor is
        down. A sensor that failed or is older than SENSOR_STALE_SECONDS is sent as
        null (never as its last good value)."""
        self.send_ws({
            "type": "telemetry",
            "temperature": self._fresh(self.temperature, self.th_time),
            "humidity": self._fresh(self.humidity, self.th_time),
            "light": self._fresh(self.light_lux, self.light_time),
            "fan_state": self.fan_state,
            "led_state": self.led_state,
            "fan_mode": self.controller.fan_mode,
            "led_mode": self.controller.led_mode,
            "rs485_ok": self.rs485_ok,
            "last_error": self.last_error,
            "timestamp": now_iso(),
        })

    def poll_loop(self):
        self.log.info("[RS485] COM=%s baud=%d | TH=%d | LIGHT=%d | RELAY=%d", settings.com_port,
                      settings.baudrate, settings.sht30_id, settings.light_id, settings.relay_id)
        while not self.stop_event.is_set():
            try:
                self.read_hardware()
                now = time.monotonic()
                if now - self.last_telemetry >= settings.telemetry_interval:
                    self.publish_telemetry()
                    self.last_telemetry = now
            except Exception as exc:  # never let the poll thread die
                self.log.exception("[POLL] unexpected error: %s", exc)
            self.stop_event.wait(settings.poll_interval)

    def websocket_loop(self):
        while not self.stop_event.is_set():
            try:
                ws = websocket.WebSocketApp(settings.web_ws_url, on_open=self.on_open, on_message=self.on_message,
                                            on_error=self.on_error, on_close=self.on_close)
                self.ws_app = ws
                ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                self.log.error("[WEB] Connection error: %s", exc)
            self.stop_event.wait(3)

    def run(self):
        self.log.info("==============================================")
        self.log.info("SMART GREENHOUSE WINDOWS GATEWAY")
        self.log.info("==============================================")
        self.log.info("[TH] function=%d temp_reg=%d hum_reg=%d scale=%g", settings.th_function,
                      settings.th_temp_reg, settings.th_hum_reg, settings.th_scale)
        if "TH_TEMP_REG" not in os.environ or "TH_HUM_REG" not in os.environ:
            self.log.warning("[TH] TH_TEMP_REG / TH_HUM_REG are not set in gateway/.env, so the built-in defaults "
                             "are used. Check them against the sensor manual (tools/probe_modbus.py).")
        try:
            self.bus.open()
            self.log.info("[RS485] Port opened successfully")
            self.init_relays()
            self.threads = [threading.Thread(target=self.poll_loop, daemon=True),
                            threading.Thread(target=self.websocket_loop, daemon=True)]
            for thread in self.threads:
                thread.start()
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.log.info("Stopping gateway...")
        except Exception as exc:
            self.log.exception("Fatal gateway error: %s", exc)
        finally:
            self.stop_event.set()
            if self.ws_app is not None:
                try:
                    self.ws_app.close()
                except Exception:
                    pass
            if self.threads:
                self.threads[0].join(timeout=3)  # poll thread must finish before the COM port is closed
                self.threads[1].join(timeout=1)  # websocket thread is a daemon
            self.bus.close()
            self.log.info("Gateway stopped.")


if __name__ == "__main__":
    GreenhouseGateway().run()
