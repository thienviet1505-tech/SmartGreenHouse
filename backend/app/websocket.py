import logging

from fastapi import WebSocket

logger = logging.getLogger("uvicorn.error")


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.add(websocket)

    def add(self, websocket: WebSocket):
        if websocket not in self.active:
            self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(payload)
            except Exception as exc:  # do not drop clients silently
                logger.warning("Dropping live WebSocket client: %s", exc)
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
