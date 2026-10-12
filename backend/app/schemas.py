from datetime import datetime

from pydantic import BaseModel, Field


class ControlCommand(BaseModel):
    mode: str = Field(default="MANUAL", pattern="^(AUTO|MANUAL)$")
    state: bool | None = None


class ControlRules(BaseModel):
    fan_on_temp: float
    fan_off_temp: float
    led_on_lux: float
    led_off_lux: float


class DashboardState(BaseModel):
    temperature: float
    humidity: float
    light: float
    fan_state: bool
    led_state: bool
    fan_mode: str
    led_mode: str
    gateway_online: bool
    rs485_ok: bool
    timestamp: datetime


class TelemetryPayload(BaseModel):
    temperature: float
    humidity: float
    light: float
    fan_state: bool = False
    led_state: bool = False
    fan_mode: str = "AUTO"
    led_mode: str = "AUTO"
    gateway_online: bool = True
    rs485_ok: bool = True
