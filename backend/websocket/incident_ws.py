"""Incident WebSocket endpoint."""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from websocket.manager import incident_manager
from services.redis_broker import RedisBroker, INCIDENT_CHANNEL

logger = logging.getLogger("incident_ws")


async def incident_ws_endpoint(websocket: WebSocket):
    """Handle /ws/incidents WebSocket connections."""
    await incident_manager.connect(websocket)
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
        await incident_manager.disconnect(websocket)


async def start_incident_broadcaster(redis_broker: RedisBroker):
    """Broadcast incidents from Redis to WebSocket clients."""
    pubsub = await redis_broker.subscribe(INCIDENT_CHANNEL)
    if not pubsub:
        return
    logger.info("Incident WebSocket broadcaster started")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await incident_manager.broadcast({"type": "incident", "data": data})
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.error(f"Incident broadcaster error: {e}")
