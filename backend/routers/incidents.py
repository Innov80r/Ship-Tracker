"""Incidents REST API router."""

from fastapi import APIRouter
from datetime import datetime, timezone

from sqlalchemy import select, update
from database import async_session_factory
from models.incident import Incident

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
async def get_incidents(active_only: bool = True):
    """Get all incidents, optionally filtered by active status."""
    try:
        async with async_session_factory() as session:
            query = select(Incident).order_by(Incident.detected_at.desc())
            if active_only:
                query = query.where(Incident.is_active == True)
            result = await session.execute(query.limit(100))
            incidents = result.scalars().all()
            return {
                "incidents": [
                    {
                        "id": i.id, "mmsi": i.mmsi,
                        "vessel_name": i.vessel_name,
                        "vessel_type": i.vessel_type,
                        "incident_type": i.incident_type,
                        "description": i.description,
                        "latitude": i.latitude, "longitude": i.longitude,
                        "speed_at_incident": i.speed_at_incident,
                        "is_active": i.is_active, "is_resolved": i.is_resolved,
                        "detected_at": i.detected_at.isoformat() if i.detected_at else None,
                    }
                    for i in incidents
                ]
            }
    except Exception as e:
        return {"error": str(e)}


@router.put("/{incident_id}/resolve")
async def resolve_incident(incident_id: int):
    """Mark an incident as resolved."""
    try:
        async with async_session_factory() as session:
            await session.execute(
                update(Incident).where(Incident.id == incident_id).values(
                    is_resolved=True, is_active=False,
                    resolved_at=datetime.utcnow(),
                )
            )
            await session.commit()
            return {"status": "resolved"}
    except Exception as e:
        return {"error": str(e)}
