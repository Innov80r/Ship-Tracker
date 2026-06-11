"""Weather periodic tasks."""

import asyncio
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.weather_tasks.fetch_weather_grid")
def fetch_weather_grid():
    """Fetch weather grid data from Open-Meteo."""
    from services.redis_broker import RedisBroker
    from services.weather_service import WeatherService

    async def _run():
        redis = RedisBroker()
        await redis.connect()
        ws = WeatherService(redis)
        await ws.fetch_weather_grid()
        await redis.close()

    asyncio.run(_run())


@celery_app.task(name="tasks.weather_tasks.fetch_tides")
def fetch_tides():
    """Fetch tide data from NOAA."""
    from services.redis_broker import RedisBroker
    from services.tide_service import TideService

    async def _run():
        redis = RedisBroker()
        await redis.connect()
        ts = TideService(redis)
        await ts.fetch_all_tides()
        await redis.close()

    asyncio.run(_run())
