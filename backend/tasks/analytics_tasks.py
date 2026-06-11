"""Analytics aggregation periodic tasks."""

import asyncio
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.analytics_tasks.aggregate_analytics")
def aggregate_analytics():
    """Pre-compute analytics for dashboard performance."""
    from services.redis_broker import RedisBroker
    from services.analytics_service import AnalyticsService
    import json

    async def _run():
        redis = RedisBroker()
        await redis.connect()
        analytics = AnalyticsService(redis)

        stats = await analytics.get_dashboard_stats()
        await redis.set_cache("analytics:dashboard", stats, ttl=3600)

        types = await analytics.get_type_breakdown()
        await redis.set_cache("analytics:types", types, ttl=3600)

        flags = await analytics.get_flag_breakdown()
        await redis.set_cache("analytics:flags", flags, ttl=3600)

        await redis.close()

    asyncio.run(_run())
