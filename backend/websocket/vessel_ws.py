"""
Vessel WebSocket endpoint — streams live vessel positions to connected clients.
"""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from websocket.manager import vessel_manager
from services.redis_broker import RedisBroker, VESSEL_CHANNEL

logger = logging.getLogger("vessel_ws")


async def vessel_ws_endpoint(websocket: WebSocket):
    """Handle /ws/vessels WebSocket connections."""
    await vessel_manager.connect(websocket)

    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                # Client can send filter preferences (e.g., bounding box)
                logger.debug(f"WS client message: {data[:100]}")
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"Vessel WS error: {e}")
    finally:
        await vessel_manager.disconnect(websocket)


async def start_vessel_broadcaster(redis_broker: RedisBroker):
    """
    Background task: subscribes to Redis vessel channel and broadcasts
    updates to all connected WebSocket clients.
    """
    pubsub = await redis_broker.subscribe(VESSEL_CHANNEL)
    if not pubsub:
        logger.warning("Redis not available — WebSocket broadcasting disabled")
        return

    logger.info("Vessel WebSocket broadcaster started")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await vessel_manager.broadcast({
                        "type": "vessel_update",
                        "data": data,
                    })
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.error(f"Vessel broadcaster error: {e}")
    finally:
        await pubsub.unsubscribe(VESSEL_CHANNEL)
