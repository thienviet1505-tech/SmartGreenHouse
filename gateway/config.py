import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Always read gateway/.env (not whatever .env happens to be found upwards).
load_dotenv(Path(__file__).resolve().parent / ".env")


def _int(name: str, default) -> int:
    # base 0 -> accepts "10" and "0x07D0"
    return int(str(os.getenv(name, default)).strip(), 0)


def _float(name: str, default) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    # --- serial / timing
    com_port: str = os.getenv("COM_PORT", "COM5")
    baudrate: int = _int("BAUDRATE", 9600)
    timeout: float = _float("MODBUS_TIMEOUT", 0.8)
    poll_interval: float = _float("POLL_INTERVAL", 1.0)
    telemetry_interval: float = _float("TELEMETRY_INTERVAL", 2.0)
    sensor_stale_seconds: float = _float("SENSOR_STALE_SECONDS", 20.0)

    # --- web link
    web_ws_url: str = os.getenv("WEB_WS_URL", "ws://127.0.0.1:8000/ws/gateway")
    gateway_token: str = os.getenv("GATEWAY_TOKEN", "change-me")

    # --- Modbus slave addresses (see gateway/README.md)
    sht30_id: int = _int("SHT30_ID", 1)    # TH10S-B-PE temperature/humidity
    light_id: int = _int("LIGHT_ID", 2)    # DFRobot SEN0644
    relay_id: int = _int("RELAY_ID", 3)    # 2-channel relay

    # --- TH10S-B-PE register map. UNVERIFIED: confirm with the vendor PDF or
    #     tools/probe_modbus.py before trusting AUTO control.
    th_function: int = _int("TH_FUNCTION", 3)       # 3 = holding, 4 = input registers
    th_temp_reg: int = _int("TH_TEMP_REG", 0)
    th_hum_reg: int = _int("TH_HUM_REG", 1)
    th_scale: float = _float("TH_SCALE", 10)        # raw / scale

    # --- relay wiring and AUTO thresholds
    fan_channel: int = _int("FAN_CHANNEL", 0)
    led_channel: int = _int("LED_CHANNEL", 1)
    fan_on_temp: float = _float("FAN_ON_TEMP", 30.0)
    fan_off_temp: float = _float("FAN_OFF_TEMP", 27.0)
    led_on_lux: float = _float("LED_ON_LUX", 3000)
    led_off_lux: float = _float("LED_OFF_LUX", 5000)


settings = Settings()
