"""
Weather Service — fetches marine weather from Open-Meteo API.
"""

import asyncio
import itertools
import json
import logging
from typing import Optional

import httpx

from services.redis_broker import RedisBroker

logger = logging.getLogger("weather_service")


class WeatherService:
    """Fetches wind and wave data from Open-Meteo for maritime weather layers."""

    MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    GRID_POINTS = [
        (lat, lon)
        for lat in range(-60, 61, 15)
        for lon in range(-180, 180, 20)
    ]
    GRID_BATCH_SIZE = 24

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker

    async def fetch_marine_weather(self, lat: float, lon: float) -> Optional[dict]:
        """Fetch marine weather for a specific coordinate."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(self.MARINE_URL, params={
                    "latitude": lat, "longitude": lon,
                    "current": "wave_height,wave_direction,wave_period,wind_wave_height",
                    "timezone": "UTC",
                })
                if resp.status_code == 200:
                    return resp.json()
            except (httpx.RequestError, ValueError) as e:
                logger.debug("Marine weather fetch error: %s", e)
        return None

    async def fetch_wind_data(self, lat: float, lon: float) -> Optional[dict]:
        """Fetch wind speed and direction forecast."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(self.FORECAST_URL, params={
                    "latitude": lat, "longitude": lon,
                    "current": "temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure",
                    "timezone": "UTC",
                })
                if resp.status_code == 200:
                    return resp.json()
            except (httpx.RequestError, ValueError) as e:
                logger.debug("Wind data fetch error: %s", e)
        return None

    async def fetch_weather_grid(self) -> list[dict]:
        """Fetch weather data for a grid across major ocean areas."""
        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for batch in _chunked(self.GRID_POINTS, self.GRID_BATCH_SIZE):
                latitudes = ",".join(str(lat) for lat, _ in batch)
                longitudes = ",".join(str(lon) for _, lon in batch)

                try:
                    [wind_resp, marine_resp] = await asyncio.gather(
                        client.get(self.FORECAST_URL, params={
                            "latitude": latitudes,
                            "longitude": longitudes,
                            "current": "wind_speed_10m,wind_direction_10m",
                            "timezone": "UTC",
                        }),
                        client.get(self.MARINE_URL, params={
                            "latitude": latitudes,
                            "longitude": longitudes,
                            "current": (
                                "wave_height,wave_direction,wave_period,"
                                "wind_wave_height,ocean_current_velocity,"
                                "ocean_current_direction,sea_level_height_msl"
                            ),
                            "timezone": "UTC",
                        }),
                    )
                except httpx.RequestError as exc:
                    logger.debug("Weather grid fetch error: %s", exc)
                    continue

                if wind_resp.status_code != 200 or marine_resp.status_code != 200:
                    continue

                try:
                    wind_payload = _normalize_locations(wind_resp.json())
                    marine_payload = _normalize_locations(marine_resp.json())
                except ValueError:
                    continue

                for (lat, lon), wind_data, marine_data in zip(batch, wind_payload, marine_payload):
                    wind_current = wind_data.get("current", {})
                    marine_current = marine_data.get("current", {})
                    results.append({
                        "lat": lat,
                        "lon": lon,
                        "wind_speed": wind_current.get("wind_speed_10m"),
                        "wind_direction": wind_current.get("wind_direction_10m"),
                        "wave_height": marine_current.get("wave_height"),
                        "wave_direction": marine_current.get("wave_direction"),
                        "wave_period": marine_current.get("wave_period"),
                        "wind_wave_height": marine_current.get("wind_wave_height"),
                        "current_speed": marine_current.get("ocean_current_velocity"),
                        "current_direction": marine_current.get("ocean_current_direction"),
                        "sea_level_height": marine_current.get("sea_level_height_msl"),
                    })

        # Cache the grid
        if results:
            await self.redis.set_cache("weather:grid", results, ttl=900)

        return results

    async def get_cached_grid(self) -> list[dict]:
        """Return cached weather grid data."""
        raw = await self.redis.get_cache("weather:grid")
        if raw:
            return json.loads(raw)
        return []


def _chunked(items: list[tuple[int, int]], size: int):
    """Yield fixed-size batches."""
    iterator = iter(items)
    while batch := list(itertools.islice(iterator, size)):
        yield batch


def _normalize_locations(payload) -> list[dict]:
    """Open-Meteo returns an array for multi-coordinate requests and a dict otherwise."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ValueError("Unexpected weather payload shape")
