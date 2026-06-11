"""Alerts REST API router."""

from fastapi import APIRouter, Query
from sqlalchemy import select, update
from database import async_session_factory
from models.alert import Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def get_alerts(limit: int = Query(50, le=200), unread_only: bool = False):
    """Get recent alerts."""
    try:
        async with async_session_factory() as session:
            query = select(Alert).order_by(Alert.created_at.desc())
            if unread_only:
                query = query.where(Alert.is_read == False)
            result = await session.execute(query.limit(limit))
            alerts = result.scalars().all()
            return {
                "alerts": [
                    {
                        "id": a.id, "alert_type": a.alert_type,
                        "severity": a.severity, "mmsi": a.mmsi,
                        "vessel_name": a.vessel_name, "title": a.title,
                        "message": a.message, "latitude": a.latitude,
                        "longitude": a.longitude, "is_read": a.is_read,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in alerts
                ]
            }
    except Exception as e:
        return {"error": str(e)}


@router.put("/{alert_id}/read")
async def mark_alert_read(alert_id: int):
    """Mark an alert as read."""
    try:
        async with async_session_factory() as session:
            await session.execute(
                update(Alert).where(Alert.id == alert_id).values(is_read=True)
            )
            await session.commit()
            return {"status": "read"}
    except Exception as e:
        return {"error": str(e)}


@router.put("/read-all")
async def mark_all_read():
    """Mark all alerts as read."""
    try:
        async with async_session_factory() as session:
            await session.execute(
                update(Alert).where(Alert.is_read == False).values(is_read=True)
            )
            await session.commit()
            return {"status": "all_read"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/count")
async def get_unread_count():
    """Get unread alert count."""
    from sqlalchemy import func
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(func.count(Alert.id)).where(Alert.is_read == False)
            )
            return {"unread_count": result.scalar() or 0}
    except Exception as e:
        return {"error": str(e)}
