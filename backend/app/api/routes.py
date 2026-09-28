from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActuatorState, CommandLog, ControlRule, GatewayStatus, SensorReading
from ..schemas import ControlCommand, ControlRules, TelemetryPayload
from ..services.command_bus import command_bus
from ..websocket import manager

router = APIRouter(prefix="/api")


def current_state(db: Session):
    sensor = db.scalar(select(SensorReading).order_by(desc(SensorReading.id)))
    actuator = db.scalar(select(ActuatorState).order_by(desc(ActuatorState.id)))
    gateway = db.scalar(select(GatewayStatus).order_by(desc(GatewayStatus.id)))

    if sensor is None or actuator is None or gateway is None:
        raise HTTPException(status_code=503, detail="System state is not ready")

    return {
        "temperature": sensor.temperature,
        "humidity": sensor.humidity,
        "light": sensor.light,
        "fan_state": actuator.fan_state,
        "led_state": actuator.led_state,
        "fan_mode": actuator.fan_mode,
        "led_mode": actuator.led_mode,
        "gateway_online": gateway.online,
        "rs485_ok": gateway.rs485_ok,
        "timestamp": sensor.timestamp,
    }


@router.get("/state")
def get_state(db: Session = Depends(get_db)):
    return current_state(db)


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    gateway = db.scalar(select(GatewayStatus).order_by(desc(GatewayStatus.id)))
    if gateway is None:
        return {"gateway_online": False, "rs485_ok": False}
    return {
        "gateway_online": gateway.online,
        "rs485_ok": gateway.rs485_ok,
        "timestamp": gateway.timestamp,
        "last_error": gateway.last_error,
    }


@router.get("/history")
def get_history(minutes: int = 60, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(minutes=max(1, min(minutes, 10080)))
    rows = db.scalars(
        select(SensorReading)
        .where(SensorReading.timestamp >= since)
        .order_by(SensorReading.timestamp)
    ).all()

    return [
        {
            "timestamp": row.timestamp,
            "temperature": row.temperature,
            "humidity": row.humidity,
            "light": row.light,
        }
        for row in rows
    ]


@router.post("/control/fan")
async def control_fan(command: ControlCommand, db: Session = Depends(get_db)):
    payload = {"mode": command.mode, "state": command.state}
    result = await command_bus.publish("fan", payload)

    actuator = db.scalar(select(ActuatorState).order_by(desc(ActuatorState.id)))
    if actuator is None:
        raise HTTPException(status_code=503, detail="Actuator state is not ready")

    actuator.fan_mode = command.mode
    if command.mode == "MANUAL" and command.state is not None:
        actuator.fan_state = command.state

    db.add(CommandLog(source="WEB", device="FAN", command=str(payload), result="ACCEPTED" if result.accepted else "REJECTED"))
    db.commit()

    await manager.broadcast(current_state(db))
    return {"accepted": result.accepted, "message": result.message}


@router.post("/control/led")
async def control_led(command: ControlCommand, db: Session = Depends(get_db)):
    payload = {"mode": command.mode, "state": command.state}
    result = await command_bus.publish("led", payload)

    actuator = db.scalar(select(ActuatorState).order_by(desc(ActuatorState.id)))
    if actuator is None:
        raise HTTPException(status_code=503, detail="Actuator state is not ready")

    actuator.led_mode = command.mode
    if command.mode == "MANUAL" and command.state is not None:
        actuator.led_state = command.state

    db.add(CommandLog(source="WEB", device="LED", command=str(payload), result="ACCEPTED" if result.accepted else "REJECTED"))
    db.commit()

    await manager.broadcast(current_state(db))
    return {"accepted": result.accepted, "message": result.message}


@router.get("/rules")
def get_rules(db: Session = Depends(get_db)):
    rules = db.scalar(select(ControlRule).order_by(desc(ControlRule.id)))
    if rules is None:
        rules = ControlRule()
        db.add(rules)
        db.commit()
        db.refresh(rules)

    return {
        "fan_on_temp": rules.fan_on_temp,
        "fan_off_temp": rules.fan_off_temp,
        "led_on_lux": rules.led_on_lux,
        "led_off_lux": rules.led_off_lux,
    }


@router.put("/rules")
async def update_rules(payload: ControlRules, db: Session = Depends(get_db)):
    if payload.fan_off_temp >= payload.fan_on_temp:
        raise HTTPException(status_code=400, detail="fan_off_temp must be lower than fan_on_temp")

    if payload.led_on_lux >= payload.led_off_lux:
        raise HTTPException(status_code=400, detail="led_on_lux must be lower than led_off_lux")

    rules = db.scalar(select(ControlRule).order_by(desc(ControlRule.id)))
    if rules is None:
        rules = ControlRule()
        db.add(rules)

    rules.fan_on_temp = payload.fan_on_temp
    rules.fan_off_temp = payload.fan_off_temp
    rules.led_on_lux = payload.led_on_lux
    rules.led_off_lux = payload.led_off_lux

    db.commit()
    return payload.model_dump()


@router.post("/ingest/telemetry")
async def ingest_telemetry(payload: TelemetryPayload, db: Session = Depends(get_db)):
    """
    Future real Gateway endpoint.

    Hardware/Gateway code will call this endpoint or an equivalent MQTT adapter.
    No RS485/Modbus logic belongs here.
    """
    db.add(
        SensorReading(
            temperature=payload.temperature,
            humidity=payload.humidity,
            light=payload.light,
        )
    )

    actuator = db.scalar(select(ActuatorState).order_by(desc(ActuatorState.id)))
    if actuator is None:
        actuator = ActuatorState()
        db.add(actuator)

    actuator.fan_state = payload.fan_state
    actuator.led_state = payload.led_state
    actuator.fan_mode = payload.fan_mode
    actuator.led_mode = payload.led_mode
    actuator.timestamp = datetime.now(timezone.utc)

    gateway = db.scalar(select(GatewayStatus).order_by(desc(GatewayStatus.id)))
    if gateway is None:
        gateway = GatewayStatus()
        db.add(gateway)

    gateway.online = payload.gateway_online
    gateway.rs485_ok = payload.rs485_ok
    gateway.timestamp = datetime.now(timezone.utc)

    db.commit()
    await manager.broadcast(current_state(db))
    return {"accepted": True}
