"""
WebSocket Connection Manager — handles multiple client connections and broadcasting.
"""

import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger("ws_manager")


class ConnectionManager:
    """
    Manages WebSocket connections for real-time vessel/alert/incident streaming.
    Thread-safe broadcasting to all connected clients.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WS client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WS client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """Send data to all connected WebSocket clients."""
        if not self.active_connections:
            return

        message = json.dumps(data, default=str)
        disconnected = set()

        for ws in self.active_connections.copy():
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)

        if disconnected:
            async with self._lock:
                self.active_connections -= disconnected

    async def send_personal(self, websocket: WebSocket, data: dict):
        """Send data to a specific client."""
        try:
            await websocket.send_json(data)
        except Exception:
            await self.disconnect(websocket)

    @property
    def count(self) -> int:
        return len(self.active_connections)


# Global instances for different channels
vessel_manager = ConnectionManager()
alert_manager = ConnectionManager()
incident_manager = ConnectionManager()
