import asyncio
import json
import httpx
from services.redis_broker import RedisBroker
from services.weather_service import WeatherService

async def main():
    print("Fetching weather grid...")
    redis = RedisBroker()
    await redis.connect()
    
    ws = WeatherService(redis)
    res = await ws.fetch_weather_grid()
    print(f"Weather fetched {len(res)} points.")

    print("Fetching EEZ Boundaries...")
    eez_url = "https://raw.githubusercontent.com/datasets/geo-eez/master/data/eez.geojson"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(eez_url)
            if r.status_code == 200:
                with open("static/eez_boundaries.geojson", "w", encoding="utf-8") as f:
                    # just save what we got
                    f.write(r.text)
                print("EEZ saved.")
            else:
                print(f"EEZ failed mapping with status {r.status_code}")
        except Exception as e:
            print(f"EEZ error: {e}")

    await redis.close()

if __name__ == "__main__":
    asyncio.run(main())
