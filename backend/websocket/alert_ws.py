"""Alert WebSocket endpoint."""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from websocket.manager import alert_manager
from services.redis_broker import RedisBroker, ALERT_CHANNEL

logger = logging.getLogger("alert_ws")


async def alert_ws_endpoint(websocket: WebSocket):
    """Handle /ws/alerts WebSocket connections."""
    await alert_manager.connect(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await alert_manager.disconnect(websocket)


async def start_alert_broadcaster(redis_broker: RedisBroker):
    """Broadcast alerts from Redis to WebSocket clients."""
    pubsub = await redis_broker.subscribe(ALERT_CHANNEL)
    if not pubsub:
        return
    logger.info("Alert WebSocket broadcaster started")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await alert_manager.broadcast({"type": "alert", "data": data})
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.error(f"Alert broadcaster error: {e}")
