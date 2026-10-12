import asyncio
<<<<<<< HEAD
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
=======
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import delete, desc, select
>>>>>>> Rac

from .api.routes import router
from .config import settings
from .database import Base, SessionLocal, engine
from .gateway_ws import gateway_manager
from .models import ActuatorState, CommandLog, ControlRule, GatewayStatus, SensorReading
<<<<<<< HEAD
from .services.simulator import GreenhouseSimulator
from .websocket import manager

=======
from .security import dashboard_token_ok, gateway_token_ok
from .services.simulator import GreenhouseSimulator
from .services.state import build_state
from .websocket import manager

logger = logging.getLogger("uvicorn.error")

>>>>>>> Rac
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


async def simulator_task():
    await GreenhouseSimulator(settings.simulator_interval).run()


<<<<<<< HEAD
=======
async def retention_task():
    """Delete old sensor rows so the SQLite file does not grow forever."""
    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
            with SessionLocal() as db:
                db.execute(delete(SensorReading).where(SensorReading.timestamp < cutoff))
                db.commit()
        except Exception as exc:
            logger.warning("Retention cleanup failed: %s", exc)
        await asyncio.sleep(3600)


>>>>>>> Rac
def update_gateway_status(db, online: bool, rs485_ok: bool, last_error=None):
    status = db.scalars(select(GatewayStatus).order_by(desc(GatewayStatus.id))).first()
    if status is None:
        status = GatewayStatus()
        db.add(status)
    status.online = online
    status.rs485_ok = rs485_ok
    status.last_error = last_error
    status.timestamp = datetime.now(timezone.utc)
    db.commit()


<<<<<<< HEAD
def state_from_db(db):
    sensor = db.scalars(select(SensorReading).order_by(desc(SensorReading.id))).first()
    actuator = db.scalars(select(ActuatorState).order_by(desc(ActuatorState.id))).first()
    gateway = db.scalars(select(GatewayStatus).order_by(desc(GatewayStatus.id))).first()
    if not sensor or not actuator or not gateway:
        return None
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


=======
>>>>>>> Rac
async def handle_gateway_message(message: dict):
    message_type = message.get("type")

    with SessionLocal() as db:
        if message_type == "telemetry":
            db.add(SensorReading(
                temperature=float(message["temperature"]),
                humidity=float(message["humidity"]),
                light=float(message["light"]),
                timestamp=datetime.now(timezone.utc),
            ))
            actuator = db.scalars(select(ActuatorState).order_by(desc(ActuatorState.id))).first()
            if actuator is None:
                actuator = ActuatorState()
                db.add(actuator)
            actuator.fan_state = bool(message["fan_state"])
            actuator.led_state = bool(message["led_state"])
            actuator.fan_mode = str(message["fan_mode"])
            actuator.led_mode = str(message["led_mode"])
            actuator.timestamp = datetime.now(timezone.utc)
            update_gateway_status(db, True, bool(message.get("rs485_ok", True)), message.get("last_error"))
            db.commit()
<<<<<<< HEAD
            state = state_from_db(db)
            if state:
                await manager.broadcast(state)
=======
            await manager.broadcast(build_state(db))
>>>>>>> Rac
            return

        if message_type == "status":
            update_gateway_status(db, bool(message.get("online", True)), bool(message.get("rs485_ok", False)), message.get("last_error"))
<<<<<<< HEAD
            state = state_from_db(db)
            if state:
                await manager.broadcast(state)
=======
            await manager.broadcast(build_state(db))
>>>>>>> Rac
            return

        if message_type == "ack":
            db.add(CommandLog(
                source="GATEWAY",
                device=str(message.get("device", "UNKNOWN")).upper(),
                command=str(message.get("command", "ACK")),
                result="ACK" if message.get("ok", False) else "ERROR",
            ))
            db.commit()
            await manager.broadcast({
                "type": "command_ack",
                "request_id": message.get("request_id"),
                "device": message.get("device"),
                "ok": message.get("ok", False),
                "message": message.get("message", ""),
                "timestamp": message.get("timestamp"),
            })
            return

        if message_type == "event":
            await manager.broadcast({
                "type": "gateway_event",
                "level": message.get("level", "INFO"),
                "message": message.get("message", ""),
                "timestamp": message.get("timestamp"),
            })


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(ActuatorState).count() == 0:
            db.add(ActuatorState())
        if db.query(ControlRule).count() == 0:
            db.add(ControlRule())
        if db.query(GatewayStatus).count() == 0:
            db.add(GatewayStatus(online=False, rs485_ok=False))
        db.commit()

<<<<<<< HEAD
    task = asyncio.create_task(simulator_task()) if settings.simulator_enabled else None
    yield
    if task is not None:
        task.cancel()
=======
    if settings.gateway_token == "change-me":
        logger.warning("GATEWAY_TOKEN is still 'change-me' - set a secret in .env (root) and gateway/.env")
    if not settings.dashboard_token:
        logger.warning("DASHBOARD_TOKEN is empty: the dashboard and relay-control API are OPEN to anyone "
                       "who can reach this server. Set DASHBOARD_TOKEN before exposing it to the internet.")

    tasks = [asyncio.create_task(retention_task())]
    if settings.simulator_enabled:
        tasks.append(asyncio.create_task(simulator_task()))
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
>>>>>>> Rac
        try:
            await task
        except asyncio.CancelledError:
            pass


<<<<<<< HEAD
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
=======
# The frontend is served by this same app (same origin), so no CORS is needed.
app = FastAPI(title=settings.app_name, lifespan=lifespan)
>>>>>>> Rac
app.include_router(router)


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
<<<<<<< HEAD
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
=======
    await websocket.accept()
    try:
        # First message must be {"type": "auth", "token": "..."}; sending the
        # token in a message keeps it out of URLs and access logs.
        first = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if first.get("type") != "auth" or not dashboard_token_ok(first.get("token")):
            await websocket.close(code=1008)
            return
        manager.add(websocket)
        with SessionLocal() as db:
            await websocket.send_json(build_state(db))
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
>>>>>>> Rac
        manager.disconnect(websocket)


@app.websocket("/ws/gateway")
async def websocket_gateway(websocket: WebSocket):
    await websocket.accept()
    authenticated = False
    try:
        hello = await asyncio.wait_for(websocket.receive_json(), timeout=10)
<<<<<<< HEAD
        if hello.get("type") != "hello" or hello.get("token") != settings.gateway_token:
=======
        if hello.get("type") != "hello" or not gateway_token_ok(hello.get("token")):
>>>>>>> Rac
            await websocket.close(code=1008)
            return

        authenticated = True
        await gateway_manager.set(websocket)
        with SessionLocal() as db:
            update_gateway_status(db, True, False, None)
<<<<<<< HEAD
        await websocket.send_json({"type": "hello_ack", "message": "Gateway authenticated"})

        while True:
            await handle_gateway_message(await websocket.receive_json())
=======
            rules = db.scalar(select(ControlRule).order_by(desc(ControlRule.id)))
        await websocket.send_json({"type": "hello_ack", "message": "Gateway authenticated"})
        if rules is not None:  # keep the gateway's AUTO thresholds in sync with the website
            await websocket.send_json({
                "type": "set_rules",
                "request_id": str(uuid4()),
                "fan_on_temp": rules.fan_on_temp,
                "fan_off_temp": rules.fan_off_temp,
                "led_on_lux": rules.led_on_lux,
                "led_off_lux": rules.led_off_lux,
            })

        while True:
            message = await websocket.receive_json()
            try:
                await handle_gateway_message(message)
            except Exception as exc:  # one bad message must not drop the gateway
                logger.warning("Bad gateway message %r: %s", message.get("type"), exc)
>>>>>>> Rac

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception as exc:
<<<<<<< HEAD
        print(f"Gateway websocket error: {exc}")
    finally:
        if authenticated:
            await gateway_manager.clear(websocket)
            with SessionLocal() as db:
                update_gateway_status(db, False, False, "Gateway disconnected")
                state = state_from_db(db)
            if state:
                state["gateway_online"] = False
                state["rs485_ok"] = False
=======
        logger.warning("Gateway websocket error: %s", exc)
    finally:
        if authenticated:
            await gateway_manager.clear(websocket)
            if not gateway_manager.connected:  # a newer connection may already have replaced this one
                with SessionLocal() as db:
                    update_gateway_status(db, False, False, "Gateway disconnected")
                    state = build_state(db)
>>>>>>> Rac
                await manager.broadcast(state)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app.js")
async def app_js():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/style.css")
async def style_css():
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")
