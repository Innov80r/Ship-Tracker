"""Weather REST API router."""

from fastapi import APIRouter

from services.redis_broker import RedisBroker
from services.weather_service import WeatherService
from services.tide_service import TideService

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/grid")
async def get_weather_grid():
    """Get cached weather grid for wind layer."""
    redis = RedisBroker()
    await redis.connect()
    ws = WeatherService(redis)
    data = await ws.get_cached_grid()
    if not data:
        data = await ws.fetch_weather_grid()
    await redis.close()
    return {"weather": data}


@router.get("/tides")
async def get_tides():
    """Get cached tide data."""
    redis = RedisBroker()
    await redis.connect()
    ts = TideService(redis)
    data = await ts.get_cached_tides()
    if not data:
        data = await ts.fetch_all_tides()
    await redis.close()
    return {"tides": data}


@router.get("/point")
async def get_weather_point(lat: float, lon: float):
    """Get weather for a specific coordinate."""
    redis = RedisBroker()
    await redis.connect()
    ws = WeatherService(redis)
    marine = await ws.fetch_marine_weather(lat, lon)
    wind = await ws.fetch_wind_data(lat, lon)
    await redis.close()
    return {"marine": marine, "wind": wind}
