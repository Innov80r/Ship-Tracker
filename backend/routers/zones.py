"""Zones REST API router."""

from fastapi import APIRouter, HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape, mapping
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError

from database import async_session_factory
from models.zone import Zone
from schemas.zone import ZoneCreate

router = APIRouter(prefix="/api/zones", tags=["zones"])


def _serialize_zone(zone: Zone) -> dict:
    geometry = mapping(to_shape(zone.geometry)) if zone.geometry else None
    return {
        "id": zone.id,
        "name": zone.name,
        "zone_type": zone.zone_type,
        "geometry": geometry,
        "alert_on_entry": zone.alert_on_entry,
        "alert_on_exit": zone.alert_on_exit,
        "description": zone.description,
    }


@router.get("")
async def get_zones():
    """Get all active zones."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(Zone).where(Zone.is_active.is_(True)))
            zones = result.scalars().all()
            return {"zones": [_serialize_zone(zone) for zone in zones]}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch zones.",
        ) from exc


@router.post("")
async def create_zone(zone_data: ZoneCreate):
    """Create a new monitoring zone."""
    try:
        async with async_session_factory() as session:
            geom = from_shape(shape(zone_data.geometry), srid=4326) if zone_data.geometry else None
            zone = Zone(
                name=zone_data.name,
                zone_type=zone_data.zone_type,
                geometry=geom,
                alert_on_entry=zone_data.alert_on_entry,
                alert_on_exit=zone_data.alert_on_exit,
                description=zone_data.description,
            )
            session.add(zone)
            await session.commit()
            await session.refresh(zone)
            return {"id": zone.id, "status": "created"}
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid zone geometry payload.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create zone.",
        ) from exc


@router.delete("/{zone_id}")
async def delete_zone(zone_id: int):
    """Delete a zone."""
    try:
        async with async_session_factory() as session:
            await session.execute(delete(Zone).where(Zone.id == zone_id))
            await session.commit()
            return {"status": "deleted"}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete zone.",
        ) from exc
