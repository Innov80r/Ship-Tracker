"""
Redis Broker — Pub/Sub for real-time WebSocket broadcasting + caching.
"""

import json
import logging
from typing import Any, Optional, cast

import redis.asyncio as aioredis

from config import get_settings

logger = logging.getLogger("redis_broker")
settings = get_settings()

# Channel names
VESSEL_CHANNEL = "vessels:updates"
ALERT_CHANNEL = "alerts:new"
INCIDENT_CHANNEL = "incidents:new"


class RedisBroker:
    """
    Async Redis client for:
    - Pub/Sub broadcasting of vessel updates, alerts, incidents
    - Caching vessel state, weather, and other hot data
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[Any] = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20,
            )
            await cast(Any, self._redis).ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without Redis caching.")
            self._redis = None

    @property
    def connected(self) -> bool:
        return self._redis is not None

    # ── Pub/Sub ───────────────────────────────────────────────

    async def publish_vessel(self, vessel_data: dict):
        """Publish a vessel update to the channel."""
        if self._redis:
            try:
                await self._redis.publish(VESSEL_CHANNEL, json.dumps(vessel_data, default=str))
            except Exception as e:
                logger.debug(f"Redis publish error: {e}")

    async def publish_alert(self, alert_data: dict):
        """Publish a new alert."""
        if self._redis:
            try:
                await self._redis.publish(ALERT_CHANNEL, json.dumps(alert_data, default=str))
            except Exception as e:
                logger.debug(f"Redis publish error: {e}")

    async def publish_incident(self, incident_data: dict):
        """Publish a new incident."""
        if self._redis:
            try:
                await self._redis.publish(INCIDENT_CHANNEL, json.dumps(incident_data, default=str))
            except Exception as e:
                logger.debug(f"Redis publish error: {e}")

    async def subscribe(self, channel: str):
        """Subscribe to a Redis channel. Returns a PubSub object."""
        if self._redis:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        return None

    # ── Caching ───────────────────────────────────────────────

    async def set_vessel(self, mmsi: int, data: dict, ttl: int = 600):
        """Cache vessel state in Redis (TTL in seconds)."""
        if self._redis:
            try:
                await self._redis.setex(f"vessel:{mmsi}", ttl, json.dumps(data, default=str))
            except Exception:
                pass

    async def get_vessel(self, mmsi: int) -> Optional[dict]:
        """Get cached vessel state."""
        if self._redis:
            try:
                raw = await self._redis.get(f"vessel:{mmsi}")
                return json.loads(raw) if raw else None
            except Exception:
                return None
        return None

    async def get_all_vessels(self) -> list[dict]:
        """Get all cached vessels."""
        if not self._redis:
            return []
        try:
            keys = []
            async for key in self._redis.scan_iter("vessel:*"):
                keys.append(key)
            if not keys:
                return []
            values = await self._redis.mget(keys)
            return [json.loads(v) for v in values if v]
        except Exception as e:
            logger.debug(f"Redis get_all_vessels error: {e}")
            return []

    async def set_cache(self, key: str, data, ttl: int = 300):
        """Generic cache set."""
        if self._redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(data, default=str))
            except Exception:
                pass

    async def get_cache(self, key: str) -> Optional[str]:
        """Generic cache get."""
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception:
                return None
        return None

    async def get_vessel_count(self) -> int:
        """Count cached vessels."""
        if not self._redis:
            return 0
        try:
            count = 0
            async for _ in self._redis.scan_iter("vessel:*"):
                count += 1
            return count
        except Exception:
            return 0

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            logger.info("Redis disconnected")
