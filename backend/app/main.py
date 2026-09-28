import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import settings
from .database import Base, SessionLocal, engine
from .models import ActuatorState, ControlRule, GatewayStatus
from .services.simulator import GreenhouseSimulator
from .websocket import manager


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


async def simulator_task():
    simulator = GreenhouseSimulator(settings.simulator_interval)
    await simulator.run()


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

    task = None
    if settings.simulator_enabled:
        task = asyncio.create_task(simulator_task())

    yield

    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app.js")
async def app_js():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/style.css")
async def style_css():
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")
