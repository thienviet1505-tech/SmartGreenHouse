from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    light: Mapped[float] = mapped_column(Float)


class ActuatorState(Base):
    __tablename__ = "actuator_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    fan_state: Mapped[bool] = mapped_column(Boolean, default=False)
    led_state: Mapped[bool] = mapped_column(Boolean, default=False)
    fan_mode: Mapped[str] = mapped_column(String(16), default="AUTO")
    led_mode: Mapped[str] = mapped_column(String(16), default="AUTO")


class ControlRule(Base):
    __tablename__ = "control_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fan_on_temp: Mapped[float] = mapped_column(Float, default=30.0)
    fan_off_temp: Mapped[float] = mapped_column(Float, default=27.0)
    led_on_lux: Mapped[float] = mapped_column(Float, default=3000.0)
    led_off_lux: Mapped[float] = mapped_column(Float, default=5000.0)


class CommandLog(Base):
    __tablename__ = "command_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(32))
    device: Mapped[str] = mapped_column(String(32))
    command: Mapped[str] = mapped_column(String(32))
    result: Mapped[str] = mapped_column(String(32))


class GatewayStatus(Base):
    __tablename__ = "gateway_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    rs485_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
