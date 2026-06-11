"""
Cable Service — fetches submarine cable GeoJSON.
Uses the community-maintained submarine cable data since TeleGeography
moved their data behind a commercial license.
"""

import logging
import os
from typing import Optional

import httpx
import aiofiles

logger = logging.getLogger("cable_service")

# Multiple fallback URLs for submarine cable GeoJSON
CABLE_URLS = [
    "https://www.submarinecablemap.com/api/v3/cable/cable-geo.json",
    "https://raw.githubusercontent.com/lintaojlu/submarine_cable_information/main/data/submarine_cables.geojson",
    "https://raw.githubusercontent.com/telegeography/www.submarinecablemap.com/master/public/api/v3/cable/cable-geo.json",
]

CABLE_FILE = "static/cables.geojson"


class CableService:
    """Fetches and caches submarine cable route GeoJSON."""

    async def fetch_cables(self) -> bool:
        """Download submarine cable GeoJSON from multiple sources, save to static file."""
        # Ensure static directory exists
        os.makedirs(os.path.dirname(CABLE_FILE) or "static", exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            for url in CABLE_URLS:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        content = resp.text
                        # Quick validation — must be valid JSON with type
                        import json
                        parsed = json.loads(content)
                        if parsed.get("type") in ("FeatureCollection", "Feature") or "features" in parsed:
                            async with aiofiles.open(CABLE_FILE, "w", encoding="utf-8") as f:
                                await f.write(content)
                            logger.info(f"Submarine cable GeoJSON downloaded from {url[:60]}...")
                            return True
                        else:
                            logger.debug(f"Cable data from {url[:50]} is not valid GeoJSON")
                    else:
                        logger.debug(f"Cable fetch from {url[:50]}: HTTP {resp.status_code}")
                except Exception as e:
                    logger.debug(f"Cable fetch error from {url[:50]}: {e}")

        logger.warning("All submarine cable GeoJSON sources failed")
        return False

    async def get_cables(self) -> Optional[dict]:
        """Read cached cable GeoJSON from file."""
        import json
        try:
            async with aiofiles.open(CABLE_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except FileNotFoundError:
            logger.debug("Cable GeoJSON not found — attempting fetch")
            if await self.fetch_cables():
                return await self.get_cables()
            return None
        except Exception as e:
            logger.error(f"Cable read error: {e}")
            return None
