<<<<<<< HEAD
from fastapi import WebSocket

=======
import logging

from fastapi import WebSocket

logger = logging.getLogger("uvicorn.error")

>>>>>>> Rac

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
<<<<<<< HEAD
        self.active.append(websocket)
=======
        self.add(websocket)

    def add(self, websocket: WebSocket):
        if websocket not in self.active:
            self.active.append(websocket)
>>>>>>> Rac

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, payload: dict):
        dead = []
<<<<<<< HEAD
        for ws in self.active:
            try:
                await ws.send_json(payload)
            except Exception:
=======
        for ws in list(self.active):
            try:
                await ws.send_json(payload)
            except Exception as exc:  # do not drop clients silently
                logger.warning("Dropping live WebSocket client: %s", exc)
>>>>>>> Rac
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
