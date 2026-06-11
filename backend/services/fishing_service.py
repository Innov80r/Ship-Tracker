"""
Fishing Service — enriches fishing vessel data from GFW.
"""

import logging
from typing import Optional

from services.redis_broker import RedisBroker

logger = logging.getLogger("fishing_service")


class FishingService:
    """Provides fishing-specific vessel enrichment and analytics."""

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker

    async def enrich_vessel(self, vessel_data: dict) -> dict:
        """
        Enrich a fishing vessel with additional GFW data.
        Called by the aggregator when a vessel is identified as fishing type.
        """
        if vessel_data.get("vessel_type") != 30:
            return vessel_data

        # Add fishing-specific metadata
        vessel_data.setdefault("vessel_type_name", "Fishing vessel")
        return vessel_data

    async def get_fishing_stats(self) -> dict:
        """Return fishing vessel statistics from cache."""
        import json
        raw = await self.redis.get_cache("fishing:stats")
        if raw:
            return json.loads(raw)
        return {"total_fishing_vessels": 0, "active_fishing": 0}
