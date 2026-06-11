"""
Shipping lane service — fetches and caches free global shipping lane GeoJSON.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import aiofiles
import httpx

logger = logging.getLogger("shipping_lane_service")

SHIPPING_LANE_URLS = [
    "https://raw.githubusercontent.com/newzealandpaul/Shipping-Lanes/main/data/Shipping_Lanes_v1.geojson",
    "https://github.com/newzealandpaul/Shipping-Lanes/raw/main/data/Shipping_Lanes_v1.geojson",
]

SHIPPING_LANE_FILE = "static/shipping_lanes.geojson"


class ShippingLaneService:
    """Fetches and caches shipping lane GeoJSON."""

    async def fetch_shipping_lanes(self) -> bool:
        """Download shipping lane GeoJSON from free sources and save it locally."""
        os.makedirs(os.path.dirname(SHIPPING_LANE_FILE) or "static", exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            for url in SHIPPING_LANE_URLS:
                try:
                    response = await client.get(url)
                    if response.status_code != 200:
                        logger.debug("Shipping lane fetch from %s returned HTTP %s", url, response.status_code)
                        continue

                    content = response.text
                    parsed = json.loads(content)
                    if parsed.get("type") != "FeatureCollection" or not isinstance(parsed.get("features"), list):
                        logger.debug("Shipping lane data from %s is not valid GeoJSON", url)
                        continue

                    async with aiofiles.open(SHIPPING_LANE_FILE, "w", encoding="utf-8") as file_handle:
                        await file_handle.write(content)
                    logger.info("Shipping lane GeoJSON downloaded from %s", url)
                    return True
                except Exception as exc:
                    logger.debug("Shipping lane fetch error from %s: %s", url, exc)

        logger.warning("All shipping lane GeoJSON sources failed")
        return False

    async def get_shipping_lanes(self) -> Optional[dict]:
        """Read cached shipping lane GeoJSON from file, fetching it if needed."""
        try:
            async with aiofiles.open(SHIPPING_LANE_FILE, "r", encoding="utf-8") as file_handle:
                return json.loads(await file_handle.read())
        except FileNotFoundError:
            logger.debug("Shipping lane GeoJSON not found — attempting fetch")
            if await self.fetch_shipping_lanes():
                return await self.get_shipping_lanes()
            return None
        except Exception as exc:
            logger.error("Shipping lane read error: %s", exc)
            return None
