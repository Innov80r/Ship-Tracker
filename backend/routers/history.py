"""History REST API router."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from database import async_session_factory
from models.vessel_history import VesselHistory
from services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/{mmsi}")
async def get_vessel_history(
    mmsi: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(5000, le=50000),
):
    """Get position history for a vessel within a date range."""
    try:
        async with async_session_factory() as session:
            query = select(VesselHistory).where(VesselHistory.mmsi == mmsi)

            if start:
                start_dt = datetime.fromisoformat(start)
                query = query.where(VesselHistory.timestamp >= start_dt)
            if end:
                end_dt = datetime.fromisoformat(end)
                query = query.where(VesselHistory.timestamp <= end_dt)

            query = query.order_by(VesselHistory.timestamp.asc()).limit(limit)
            result = await session.execute(query)
            points = result.scalars().all()

            return {
                "mmsi": mmsi,
                "points": [
                    {
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "speed": p.speed,
                        "heading": p.heading,
                        "course": p.course,
                        "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                    }
                    for p in points
                ],
                "total": len(points),
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/{mmsi}/trail")
async def get_vessel_trail(mmsi: int, minutes: int = Query(180, ge=5, le=1440)):
    """Get recent position trail for map display."""
    try:
        async with async_session_factory() as session:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)
            result = await session.execute(
                select(VesselHistory)
                .where(VesselHistory.mmsi == mmsi, VesselHistory.timestamp >= cutoff)
                .order_by(VesselHistory.timestamp.asc())
            )
            points = result.scalars().all()
            return {
                "mmsi": mmsi,
                "trail": [[p.latitude, p.longitude] for p in points],
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/{mmsi}/events")
async def get_vessel_playback_events(
    mmsi: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(5000, ge=1, le=50000),
):
    """Return derived playback events for a vessel history window."""
    try:
        service = IntelligenceService()
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
        return await service.get_playback_events(mmsi, start=start_dt, end=end_dt, limit=limit)
    except Exception as e:
        return {"error": str(e)}
