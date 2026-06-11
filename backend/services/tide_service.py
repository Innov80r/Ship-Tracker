"""
Tide Service — fetches tide predictions from NOAA Tides and Currents.
"""

import logging

import httpx

from services.redis_broker import RedisBroker
from services.weather_service import WeatherService

logger = logging.getLogger("tide_service")

# Major US coastal tide stations
TIDE_STATIONS = [
    {"id": "8518750", "name": "The Battery, NY", "lat": 40.7006, "lon": -74.0142},
    {"id": "9414290", "name": "San Francisco, CA", "lat": 37.8063, "lon": -122.4659},
    {"id": "8723214", "name": "Virginia Key, FL", "lat": 25.7316, "lon": -80.1618},
    {"id": "8658120", "name": "Wilmington, NC", "lat": 34.2270, "lon": -77.9530},
    {"id": "8443970", "name": "Boston, MA", "lat": 42.3539, "lon": -71.0500},
    {"id": "8761724", "name": "Grand Isle, LA", "lat": 29.2633, "lon": -89.9563},
    {"id": "9447130", "name": "Seattle, WA", "lat": 47.6026, "lon": -122.3393},
    {"id": "1612340", "name": "Honolulu, HI", "lat": 21.3069, "lon": -157.8667},
    {"id": "8574680", "name": "Baltimore, MD", "lat": 39.2669, "lon": -76.5780},
    {"id": "8452660", "name": "Newport, RI", "lat": 41.5043, "lon": -71.3269},
]


class TideService:
    """Fetches tide predictions from NOAA for major US coastal stations."""

    BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker

    def _build_global_sea_level_samples(self, weather_grid: list[dict]) -> list[dict]:
        """Convert cached global marine grid points into sea-level samples."""
        samples = []
        for point in weather_grid:
            latitude = point.get("lat")
            longitude = point.get("lon")
            sea_level = point.get("sea_level_height")
            if latitude is None or longitude is None or sea_level is None:
                continue

            samples.append({
                "station_id": f"grid:{latitude}:{longitude}",
                "station_name": "Open-Meteo marine grid",
                "latitude": latitude,
                "longitude": longitude,
                "water_level": float(sea_level),
                "time": "grid",
                "source": "open-meteo",
            })
        return samples

    async def fetch_all_tides(self) -> list[dict]:
        """Fetch current tide levels and global sea-level samples."""
        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for station in TIDE_STATIONS:
                try:
                    resp = await client.get(self.BASE_URL, params={
                        "date": "latest",
                        "station": station["id"],
                        "product": "water_level",
                        "datum": "MLLW",
                        "units": "english",
                        "time_zone": "gmt",
                        "application": "sea_tracker",
                        "format": "json",
                    })
                    if resp.status_code == 200:
                        data = resp.json()
                        obs = data.get("data", [])
                        if obs:
                            latest = obs[-1]
                            results.append({
                                "station_id": station["id"],
                                "station_name": station["name"],
                                "latitude": station["lat"],
                                "longitude": station["lon"],
                                "water_level": float(latest.get("v", 0)),
                                "time": latest.get("t"),
                                "source": "noaa",
                            })
                except Exception as e:
                    logger.debug("Tide fetch error for %s: %s", station["name"], e)

        weather_service = WeatherService(self.redis)
        weather_grid = await weather_service.get_cached_grid()
        if not weather_grid:
            weather_grid = await weather_service.fetch_weather_grid()
        results.extend(self._build_global_sea_level_samples(weather_grid))

        # Cache results
        if results:
            await self.redis.set_cache("tides:all", results, ttl=1800)

        return results

    async def get_cached_tides(self) -> list[dict]:
        """Return cached tide data."""
        import json
        raw = await self.redis.get_cache("tides:all")
        if raw:
            return json.loads(raw)
        return []
