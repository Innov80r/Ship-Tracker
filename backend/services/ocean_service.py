"""
Ocean Service — fetches ocean current and temperature data from Copernicus CMEMS.
"""

import logging
from typing import Optional

import httpx

from config import get_settings
from services.redis_broker import RedisBroker

logger = logging.getLogger("ocean_service")
settings = get_settings()


class OceanService:
    """Fetches ocean current vectors, SST, and salinity from CMEMS."""

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker

    async def fetch_ocean_data(self) -> Optional[dict]:
        """Fetch ocean current and temperature data from CMEMS or cache."""
        if not settings.CMEMS_USERNAME or not settings.CMEMS_PASSWORD:
            logger.debug("CMEMS credentials not set — skipping ocean data")
            return None

        # CMEMS data can be fetched via their REST API or Python toolbox
        # For now, we provide a stub that can be extended with copernicusmarine package
        logger.debug("Ocean data fetch — CMEMS integration placeholder")
        return None

    async def get_cached_ocean_data(self) -> Optional[dict]:
        """Return cached ocean data."""
        import json
        raw = await self.redis.get_cache("ocean:data")
        if raw:
            return json.loads(raw)
        return None
