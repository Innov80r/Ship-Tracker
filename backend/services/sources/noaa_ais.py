"""
NOAA Marine Data source — US coastal environmental data.
NOAA does not provide a free live AIS API; instead, we poll their
Tides & Currents and NDBC APIs for weather/ocean overlay data
that enhances the maritime tracker with environmental context.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

import httpx

from config import get_settings

logger = logging.getLogger("noaa_ais")
settings = get_settings()
Payload = dict[str, Any]


# Major NOAA tide stations for ocean current / water level data
TIDE_STATIONS = [
    {"id": "8518750", "name": "The Battery, NY"},
    {"id": "8461490", "name": "New London, CT"},
    {"id": "8452660", "name": "Newport, RI"},
    {"id": "8443970", "name": "Boston, MA"},
    {"id": "8658120", "name": "Wilmington, NC"},
    {"id": "8720218", "name": "Mayport, FL"},
    {"id": "8726520", "name": "St. Petersburg, FL"},
    {"id": "8771341", "name": "Galveston Bay, TX"},
    {"id": "9414290", "name": "San Francisco, CA"},
    {"id": "9410230", "name": "La Jolla, CA"},
]


class NOAAAISClient:
    """
    REST polling client for NOAA marine environmental data.
    Fetches water levels, wind, and meteorological data
    from NOAA CO-OPS Tides and Currents stations.
    """

    BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    def __init__(self, on_message: Callable[[dict[str, Any]], Awaitable[None]]):
        self.on_message = on_message
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
        self._station_idx = 0

    async def start(self):
        """Start periodic polling of NOAA stations."""
        self._running = True
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "sea-tracker/1.0"},
        )
        logger.info("NOAA marine data poller started")

        while self._running:
            try:
                await self._poll_station()
            except Exception as e:
                logger.debug(f"NOAA poll error: {e}")
            await asyncio.sleep(settings.NOAA_POLL_INTERVAL)

    async def _poll_station(self):
        """Fetch water level data from the next NOAA station."""
        station = TIDE_STATIONS[self._station_idx % len(TIDE_STATIONS)]
        self._station_idx += 1
        client = self._client
        if client is None:
            return

        # Water levels (verified working product)
        params = {
            "date": "latest",
            "station": station["id"],
            "product": "water_level",
            "datum": "MLLW",
            "units": "english",
            "time_zone": "gmt",
            "application": "sea_tracker",
            "format": "json",
        }

        try:
            response = await client.get(self.BASE_URL, params=params)
            if response.status_code == 200:
                wl = self._first_data_row(response.json())
                if wl is not None:
                    logger.debug(
                        f"NOAA {station['name']}: water level {wl.get('v', 'N/A')} ft "
                        f"at {wl.get('t', 'N/A')}"
                    )
            else:
                logger.debug(f"NOAA station {station['id']} HTTP {response.status_code}")
        except httpx.HTTPError as e:
            logger.debug(f"NOAA HTTP error for {station['name']}: {e}")

        # Also fetch wind data if available
        wind_params = {
            "date": "latest",
            "station": station["id"],
            "product": "wind",
            "units": "english",
            "time_zone": "gmt",
            "application": "sea_tracker",
            "format": "json",
        }

        try:
            response = await client.get(self.BASE_URL, params=wind_params)
            if response.status_code == 200:
                wind = self._first_data_row(response.json())
                if wind is not None:
                    logger.debug(
                        f"NOAA {station['name']}: wind {wind.get('s', 'N/A')} kts "
                        f"from {wind.get('dr', 'N/A')}"
                    )
        except httpx.HTTPError:
            pass

    async def stop(self):
        """Stop the poller."""
        self._running = False
        if self._client:
            await self._client.aclose()
        logger.info("NOAA marine data poller stopped")

    @staticmethod
    def _first_data_row(payload: Any) -> Payload | None:
        if not isinstance(payload, dict):
            return None
        rows = payload.get("data")
        if not isinstance(rows, list) or not rows:
            return None
        first = rows[0]
        if not isinstance(first, dict):
            return None
        return first
