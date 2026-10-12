from fastapi import WebSocket


class GatewayConnectionManager:
    def __init__(self):
        self.websocket: WebSocket | None = None

    @property
    def connected(self) -> bool:
        return self.websocket is not None

    async def set(self, websocket: WebSocket):
        self.websocket = websocket

    async def clear(self, websocket: WebSocket | None = None):
        if websocket is None or self.websocket is websocket:
            self.websocket = None

    async def send(self, payload: dict) -> bool:
        if self.websocket is None:
            return False
        try:
            await self.websocket.send_json(payload)
            return True
        except Exception:
            self.websocket = None
            return False


gateway_manager = GatewayConnectionManager()
