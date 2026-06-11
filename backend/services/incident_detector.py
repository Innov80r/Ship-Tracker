"""
Incident Detector — auto-detects distress signals from AIS data.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import async_session_factory
from models.incident import Incident
from services.redis_broker import RedisBroker

logger = logging.getLogger("incident_detector")


class IncidentDetector:
    """Detects distress events from vessel data and creates incidents."""

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker

    async def check_vessel(self, vessel_data: dict):
        """Check a vessel update for distress indicators."""
        nav_status = vessel_data.get("nav_status")
        mmsi = vessel_data.get("mmsi")

        if not mmsi:
            return

        # Nav status 14 = AIS-SART / MOB / EPIRB (distress)
        if nav_status == 14:
            await self._create_incident(
                vessel_data,
                incident_type="AIS_SART",
                description="AIS-SART / MOB / EPIRB signal detected",
            )

        # Nav status 2 = Not under command
        elif nav_status == 2:
            await self._create_incident(
                vessel_data,
                incident_type="NOT_UNDER_COMMAND",
                description="Vessel not under command",
            )

        # Nav status 6 = Aground
        elif nav_status == 6:
            await self._create_incident(
                vessel_data,
                incident_type="AGROUND",
                description="Vessel aground",
            )

        # MMSI starting with 970 = AIS-SART
        if str(mmsi).startswith("970"):
            await self._create_incident(
                vessel_data,
                incident_type="AIS_SART",
                description="AIS-SART beacon detected (MMSI 970xxxxx)",
            )

        # MMSI starting with 972 = MOB (Man Overboard)
        if str(mmsi).startswith("972"):
            await self._create_incident(
                vessel_data,
                incident_type="MOB",
                description="Man overboard device detected (MMSI 972xxxxx)",
            )

    async def _create_incident(self, vessel_data: dict, incident_type: str, description: str):
        """Create or update an incident in the database."""
        mmsi = vessel_data["mmsi"]

        try:
            async with async_session_factory() as session:
                # Check for existing active incident of same type for this vessel
                result = await session.execute(
                    select(Incident).where(
                        Incident.mmsi == mmsi,
                        Incident.incident_type == incident_type,
                        Incident.is_active == True,
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.latitude = vessel_data.get("latitude")
                    existing.longitude = vessel_data.get("longitude")
                    existing.speed_at_incident = vessel_data.get("speed")
                    existing.last_updated = datetime.utcnow()
                else:
                    # Create new incident
                    incident = Incident(
                        mmsi=mmsi,
                        vessel_name=vessel_data.get("name"),
                        vessel_type=vessel_data.get("vessel_type_name"),
                        incident_type=incident_type,
                        description=description,
                        latitude=vessel_data.get("latitude"),
                        longitude=vessel_data.get("longitude"),
                        speed_at_incident=vessel_data.get("speed"),
                        heading_at_incident=vessel_data.get("heading"),
                        is_active=True,
                    )
                    session.add(incident)

                    # Publish to WebSocket
                    await self.redis.publish_incident({
                        "mmsi": mmsi,
                        "vessel_name": vessel_data.get("name"),
                        "incident_type": incident_type,
                        "description": description,
                        "latitude": vessel_data.get("latitude"),
                        "longitude": vessel_data.get("longitude"),
                    })

                await session.commit()

        except Exception as e:
            logger.error(f"Incident creation error: {e}")

    async def get_active_incidents(self) -> list[dict]:
        """Get all active incidents."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Incident).where(Incident.is_active == True).order_by(
                        Incident.detected_at.desc()
                    )
                )
                incidents = result.scalars().all()
                return [
                    {
                        "id": i.id,
                        "mmsi": i.mmsi,
                        "vessel_name": i.vessel_name,
                        "vessel_type": i.vessel_type,
                        "incident_type": i.incident_type,
                        "description": i.description,
                        "latitude": i.latitude,
                        "longitude": i.longitude,
                        "speed_at_incident": i.speed_at_incident,
                        "is_active": i.is_active,
                        "detected_at": i.detected_at.isoformat() if i.detected_at else None,
                    }
                    for i in incidents
                ]
        except Exception as e:
            logger.error(f"Get incidents error: {e}")
            return []
