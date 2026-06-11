"""
Global Fishing Watch API client — fishing vessel activity data.
Polls GFW REST API v3 for fishing vessel positions and identity.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

import httpx

from config import get_settings
from utils.country_utils import normalize_country_identity
from utils.flag_utils import get_flag_from_mmsi

logger = logging.getLogger("gfw")
settings = get_settings()


class GlobalFishingWatchClient:
    """
    REST polling client for Global Fishing Watch API v3.
    Uses the /vessels/search endpoint with proper query parameters.
    """

    BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"

    def __init__(self, on_message: Callable[[dict[str, Any]], Awaitable[None]]):
        self.on_message = on_message
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
        self._search_queries = [
            "fishing", "trawler", "longliner", "seiner", "drifter",
            "tuna", "squid", "shrimp", "crab",
        ]
        self._query_idx = 0

    async def start(self):
        """Start periodic polling of GFW API."""
        if not settings.GFW_API_KEY:
            logger.warning("GFW_API_KEY not set — skipping Global Fishing Watch source")
            return

        self._running = True
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {settings.GFW_API_KEY}",
            },
        )
        logger.info("Global Fishing Watch poller started")

        while self._running:
            try:
                await self._poll()
            except Exception as e:
                logger.error(f"GFW poll error: {e}")
            await asyncio.sleep(settings.GFW_POLL_INTERVAL)

    async def _poll(self):
        """Fetch fishing vessel data from GFW API v3 search endpoint."""
        try:
            query_term = self._search_queries[self._query_idx % len(self._search_queries)]
            self._query_idx += 1
            client = self._client
            if client is None:
                return

            url = f"{self.BASE_URL}/vessels/search"
            params = {
                "query": query_term,
                "datasets[0]": "public-global-vessel-identity:latest",
                "limit": 50,
            }
            response = await client.get(url, params=params)

            if response.status_code == 200:
                payload = response.json()
                if not isinstance(payload, dict):
                    return
                entries = payload.get("entries", [])
                if not isinstance(entries, list):
                    return
                count = 0
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    vessel = self._parse_vessel(entry)
                    if vessel:
                        await self.on_message(vessel)
                        count += 1
                if count > 0:
                    logger.info(f"GFW: processed {count} fishing vessels (query: {query_term})")
            elif response.status_code == 401:
                logger.warning("GFW API key invalid or expired")
                self._running = False
            elif response.status_code == 429:
                logger.warning("GFW rate limit hit — backing off 60s")
                await asyncio.sleep(60)
            else:
                logger.warning(f"GFW HTTP {response.status_code}: {response.text[:200]}")
        except httpx.HTTPError as e:
            logger.warning(f"GFW HTTP error: {e}")

    def _parse_vessel(self, entry: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Parse a GFW vessel entry into normalized vessel dict."""
        mmsi = entry.get("ssvid")
        if not mmsi:
            return None
        try:
            mmsi = int(mmsi)
        except (ValueError, TypeError):
            return None

        vessel: dict[str, Any] = {
            "mmsi": mmsi,
            "data_source": "gfw",
            "vessel_type": 30,  # Fishing vessel AIS code
            "vessel_type_name": "Fishing vessel",
        }

        # Identity fields from combinedSourcesInfo
        combined = entry.get("combinedSourcesInfo")
        if combined:
            info = combined[0] if isinstance(combined, list) else combined
            if isinstance(info, dict):
                if info.get("shipsname"):
                    vessel["name"] = info["shipsname"].strip()
                if info.get("imo"):
                    try:
                        vessel["imo"] = int(info["imo"])
                    except (ValueError, TypeError):
                        pass
                if info.get("callsign"):
                    vessel["call_sign"] = info["callsign"].strip()

        # registryInfo may have more details
        registry = entry.get("registryInfo")
        if registry:
            reg = registry[0] if isinstance(registry, list) else registry
            if isinstance(reg, dict):
                if not vessel.get("name") and reg.get("shipname"):
                    vessel["name"] = reg["shipname"].strip()
                if reg.get("flag"):
                    vessel["flag_country"], vessel["flag_code"] = normalize_country_identity(
                        reg.get("flag"),
                        reg.get("flag"),
                    )

        # Fallback flag from MMSI
        if not vessel.get("flag_country"):
            country, iso = get_flag_from_mmsi(mmsi)
            vessel["flag_country"] = country
            vessel["flag_code"] = iso
        else:
            vessel["flag_country"], vessel["flag_code"] = normalize_country_identity(
                vessel.get("flag_country"),
                vessel.get("flag_code"),
            )

        return vessel

    async def stop(self):
        """Stop the poller."""
        self._running = False
        if self._client:
            await self._client.aclose()
        logger.info("Global Fishing Watch poller stopped")
