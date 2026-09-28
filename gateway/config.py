import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    com_port: str = os.getenv("COM_PORT", "COM5")
    baudrate: int = int(os.getenv("BAUDRATE", "9600"))
    timeout: float = float(os.getenv("MODBUS_TIMEOUT", "0.8"))
    poll_interval: float = float(os.getenv("POLL_INTERVAL", "1.0"))
    telemetry_interval: float = float(os.getenv("TELEMETRY_INTERVAL", "2.0"))
    web_ws_url: str = os.getenv("WEB_WS_URL", "ws://127.0.0.1:8000/ws/gateway")
    gateway_token: str = os.getenv("GATEWAY_TOKEN", "change-me")
    sht30_id: int = int(os.getenv("SHT30_ID", "1"))
    light_id: int = int(os.getenv("LIGHT_ID", "2"))
    relay_id: int = int(os.getenv("RELAY_ID", "255"))
    fan_channel: int = int(os.getenv("FAN_CHANNEL", "0"))
    led_channel: int = int(os.getenv("LED_CHANNEL", "1"))
    fan_on_temp: float = float(os.getenv("FAN_ON_TEMP", "30.0"))
    fan_off_temp: float = float(os.getenv("FAN_OFF_TEMP", "27.0"))
    led_on_lux: float = float(os.getenv("LED_ON_LUX", "3000"))
    led_off_lux: float = float(os.getenv("LED_OFF_LUX", "5000"))

settings = Settings()
