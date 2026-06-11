"""Analytics REST API router."""

from fastapi import APIRouter

from services.redis_broker import RedisBroker
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard statistics."""
    redis = RedisBroker()
    await redis.connect()
    analytics = AnalyticsService(redis)
    stats = await analytics.get_dashboard_stats()
    await redis.close()
    return stats


@router.get("/types")
async def get_type_breakdown():
    """Vessel type breakdown."""
    redis = RedisBroker()
    await redis.connect()
    analytics = AnalyticsService(redis)
    data = await analytics.get_type_breakdown()
    await redis.close()
    return {"types": data}


@router.get("/flags")
async def get_flag_breakdown():
    """Flag country breakdown."""
    redis = RedisBroker()
    await redis.connect()
    analytics = AnalyticsService(redis)
    data = await analytics.get_flag_breakdown()
    await redis.close()
    return {"flags": data}


@router.get("/sources")
async def get_source_breakdown():
    """Data source breakdown."""
    redis = RedisBroker()
    await redis.connect()
    analytics = AnalyticsService(redis)
    data = await analytics.get_source_breakdown()
    await redis.close()
    return {"sources": data}


@router.get("/fastest")
async def get_fastest_vessels():
    """Top fastest vessels."""
    redis = RedisBroker()
    await redis.connect()
    analytics = AnalyticsService(redis)
    data = await analytics.get_fastest_vessels()
    await redis.close()
    return {"fastest": data}


@router.get("/coverage")
async def get_coverage_diagnostics():
    """Live coverage diagnostics for free/public AIS tracking."""
    redis = RedisBroker()
    await redis.connect()
    analytics = AnalyticsService(redis)
    data = await analytics.get_coverage_diagnostics()
    await redis.close()
    return data
