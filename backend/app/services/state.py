import time
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..models import ActuatorState, GatewayStatus, SensorReading
from ..timeutil import iso_utc

# A sensor value is shown as "current" only if it is at most this old (seconds).
SENSOR_MAX_AGE = 30.0

# Latest telemetry exactly as the gateway sent it: a sensor that failed is None.
# (The sensor_readings table cannot hold partial rows, so it cannot tell us that.)
_live = {"values": None, "at": 0.0, "stamp": None}


def remember_live(temperature, humidity, light):
    _live.update(values=(temperature, humidity, light), at=time.monotonic(), stamp=datetime.now(timezone.utc))


def _current_sensors(sensor):
    """-> ((temperature, humidity, light), timestamp); all None when nothing is fresh."""
    if _live["values"] is not None and time.monotonic() - _live["at"] <= SENSOR_MAX_AGE:
        return _live["values"], _live["stamp"]
    if sensor is not None:  # no live telemetry (simulator, or backend just restarted)
        stamp = sensor.timestamp if sensor.timestamp.tzinfo else sensor.timestamp.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - stamp).total_seconds() <= SENSOR_MAX_AGE:
            return (sensor.temperature, sensor.humidity, sensor.light), stamp
    return (None, None, None), None


def build_state(db: Session) -> dict:
    """Current dashboard state. Always JSON-serialisable (timestamps are ISO
    strings) and never raises when there is no sensor row yet. Sensor values
    older than SENSOR_MAX_AGE (gateway or sensor down) are reported as None
    instead of being shown as if they were current."""
    sensor = db.scalar(select(SensorReading).order_by(desc(SensorReading.id)))
    (temperature, humidity, light), stamp = _current_sensors(sensor)
    actuator = db.scalar(select(ActuatorState).order_by(desc(ActuatorState.id)))
    gateway = db.scalar(select(GatewayStatus).order_by(desc(GatewayStatus.id)))
    return {
        "temperature": temperature,
        "humidity": humidity,
        "light": light,
        "fan_state": bool(actuator.fan_state) if actuator else False,
        "led_state": bool(actuator.led_state) if actuator else False,
        "fan_mode": actuator.fan_mode if actuator else "AUTO",
        "led_mode": actuator.led_mode if actuator else "AUTO",
        "gateway_online": bool(gateway.online) if gateway else False,
        "rs485_ok": bool(gateway.rs485_ok) if gateway else False,
        "last_error": gateway.last_error if gateway else None,
        "timestamp": iso_utc(stamp),
    }
