from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..models import ActuatorState, GatewayStatus, SensorReading
from ..timeutil import iso_utc


def build_state(db: Session) -> dict:
    """Current dashboard state. Always JSON-serialisable (timestamps are ISO
    strings) and never raises when there is no sensor row yet."""
    sensor = db.scalar(select(SensorReading).order_by(desc(SensorReading.id)))
    actuator = db.scalar(select(ActuatorState).order_by(desc(ActuatorState.id)))
    gateway = db.scalar(select(GatewayStatus).order_by(desc(GatewayStatus.id)))
    return {
        "temperature": sensor.temperature if sensor else None,
        "humidity": sensor.humidity if sensor else None,
        "light": sensor.light if sensor else None,
        "fan_state": bool(actuator.fan_state) if actuator else False,
        "led_state": bool(actuator.led_state) if actuator else False,
        "fan_mode": actuator.fan_mode if actuator else "AUTO",
        "led_mode": actuator.led_mode if actuator else "AUTO",
        "gateway_online": bool(gateway.online) if gateway else False,
        "rs485_ok": bool(gateway.rs485_ok) if gateway else False,
        "last_error": gateway.last_error if gateway else None,
        "timestamp": iso_utc(sensor.timestamp) if sensor else None,
    }
