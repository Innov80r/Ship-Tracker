"""Vessels REST API router."""

import itertools
from typing import Optional

from fastapi import APIRouter, Query

from config import get_settings
from services.intelligence_service import IntelligenceService
from services.redis_broker import RedisBroker
from services.vessel_tracker import VesselTracker
from utils.vessel_search import matches_vessel_query

router = APIRouter(prefix="/api/vessels", tags=["vessels"])
settings = get_settings()


@router.get("")
async def get_vessels(
    search: Optional[str] = None,
    vessel_type: Optional[int] = None,
    flag: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    speed_min: Optional[float] = None,
    speed_max: Optional[float] = None,
    risk_min: Optional[float] = None,
    dark_only: bool = False,
    destination_required: bool = False,
    last_seen_minutes: Optional[float] = None,
    limit: Optional[int] = Query(None, ge=1),
):
    """Get all active vessels, optionally filtered."""
    effective_last_seen_minutes = (
        last_seen_minutes
        if last_seen_minutes is not None
        else settings.LIVE_FEED_WINDOW_MINUTES
    )
    advanced_filters_requested = any(
        value is not None
        for value in (
            search,
            category,
            source,
            speed_min,
            speed_max,
            risk_min,
            effective_last_seen_minutes,
        )
    ) or dark_only or destination_required

    if advanced_filters_requested:
        intelligence_service = IntelligenceService()
        vessels = await intelligence_service.filter_vessels(
            search=search,
            vessel_type=vessel_type,
            flag=flag,
            category=category,
            source=source,
            speed_min=speed_min,
            speed_max=speed_max,
            risk_min=risk_min,
            dark_only=dark_only,
            destination_required=destination_required,
            last_seen_minutes=effective_last_seen_minutes,
            limit=limit,
        )
        vessels = [
            vessel
            for vessel in vessels
            if vessel.get("latitude") is not None and vessel.get("longitude") is not None
        ]
        return {"vessels": vessels, "total": len(vessels)}

    redis = RedisBroker()
    await redis.connect()
    tracker = VesselTracker(redis)
    vessels = await tracker.get_active_vessels_filtered(
        max_age_minutes=effective_last_seen_minutes,
        require_position=True,
    )
    await redis.close()

    if vessel_type is not None:
        vessels = [v for v in vessels if v.get("vessel_type") == vessel_type]
    if flag:
        vessels = [v for v in vessels if v.get("flag_country", "").lower() == flag.lower()]

    return {
        "vessels": list(itertools.islice(vessels, limit)) if limit is not None else vessels,
        "total": len(vessels),
    }


@router.get("/search")
async def search_vessels(q: str = Query(..., min_length=1)):
    """Search vessels by identifier, type, and maritime keywords."""
    redis = RedisBroker()
    await redis.connect()
    tracker = VesselTracker(redis)
    # Search from Redis cache
    all_vessels = await tracker.get_active_vessels_filtered(
        max_age_minutes=settings.LIVE_FEED_WINDOW_MINUTES,
        require_position=True,
    )
    await redis.close()

    query_text = q.strip()
    if not query_text:
        return {"results": []}

    results = []
    for vessel in all_vessels:
        if matches_vessel_query(vessel, query_text):
            results.append(vessel)
            if len(results) >= 20:
                break

    return {"results": results}


@router.get("/{mmsi}")
async def get_vessel(mmsi: int):
    """Get a specific vessel by MMSI."""
    redis = RedisBroker()
    await redis.connect()
    tracker = VesselTracker(redis)
    vessel = await tracker.get_vessel(mmsi)
    await redis.close()

    if not vessel:
        return {"error": "Vessel not found"}
    return vessel
