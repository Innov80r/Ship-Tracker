"""
Alert Engine — generates alerts for zone entries, speed anomalies, dark vessels, etc.
"""

import logging
from typing import Any

from sqlalchemy import select, func

from database import async_session_factory
from models.alert import Alert
from services.notification_service import NotificationService
from services.redis_broker import RedisBroker

logger = logging.getLogger("alert_engine")


class AlertEngine:
    """Generates and manages alerts for various maritime events."""

    def __init__(self, redis_broker: RedisBroker, notification_service: NotificationService | None = None):
        self.redis = redis_broker
        self.notification_service = notification_service or NotificationService()

    async def create_alert(
        self,
        alert_type: str,
        title: str,
        message: str = "",
        severity: str = "info",
        mmsi: int | None = None,
        vessel_name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        zone_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Create a new alert and publish it."""
        try:
            async with async_session_factory() as session:
                alert = Alert(
                    alert_type=alert_type,
                    severity=severity,
                    mmsi=mmsi,
                    vessel_name=vessel_name,
                    title=title,
                    message=message,
                    latitude=latitude,
                    longitude=longitude,
                    zone_id=zone_id,
                )
                session.add(alert)
                await session.commit()
                await session.refresh(alert)

                alert_data = {
                    "id": alert.id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "mmsi": mmsi,
                    "vessel_name": vessel_name,
                    "title": title,
                    "message": message,
                    "latitude": latitude,
                    "longitude": longitude,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                }
                await self.redis.publish_alert(alert_data)
                try:
                    await self.notification_service.dispatch_alert(alert_data, alert_id=alert.id)
                except Exception as notify_exc:  # pylint: disable=broad-exception-caught
                    logger.warning("Alert notification dispatch error: %s", notify_exc)
                return alert_data

        except Exception as e:
            logger.error(f"Alert creation error: {e}")
            return None

    async def check_speed_anomaly(self, vessel_data: dict[str, Any], previous_speed: float | None = None) -> None:
        """Alert on sudden speed changes."""
        speed = vessel_data.get("speed")
        if not isinstance(speed, (int, float)) or previous_speed is None:
            return

        diff = abs(float(speed) - previous_speed)
        if diff > 25:  # >25 knot change is anomalous
            await self.create_alert(
                alert_type="SPEED_ANOMALY",
                title=f"Speed anomaly: {vessel_data.get('name', 'Unknown')}",
                message=f"Speed changed by {diff:.1f} kn (from {previous_speed:.1f} to {float(speed):.1f})",
                severity="warning",
                mmsi=vessel_data.get("mmsi"),
                vessel_name=vessel_data.get("name"),
                latitude=vessel_data.get("latitude"),
                longitude=vessel_data.get("longitude"),
            )

    async def check_military_vessel(self, vessel_data: dict[str, Any]) -> None:
        """Alert on military vessel detection."""
        vtype = vessel_data.get("vessel_type")
        if vtype == 35:  # Military
            await self.create_alert(
                alert_type="MILITARY_DETECTED",
                title=f"Military vessel: {vessel_data.get('name', 'Unknown')}",
                message=f"MMSI {vessel_data.get('mmsi')} from {vessel_data.get('flag_country', 'Unknown')}",
                severity="info",
                mmsi=vessel_data.get("mmsi"),
                vessel_name=vessel_data.get("name"),
                latitude=vessel_data.get("latitude"),
                longitude=vessel_data.get("longitude"),
            )

    async def get_unread_count(self) -> int:
        """Get count of unread alerts."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(func.count(Alert.id)).where(Alert.is_read.is_(False))
                )
                return result.scalar() or 0
        except Exception:
            return 0

    async def get_recent_alerts(self, limit: int = 50) -> list[dict]:
        """Get recent alerts."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Alert).order_by(Alert.created_at.desc()).limit(limit)
                )
                alerts = result.scalars().all()
                return [
                    {
                        "id": a.id,
                        "alert_type": a.alert_type,
                        "severity": a.severity,
                        "mmsi": a.mmsi,
                        "vessel_name": a.vessel_name,
                        "title": a.title,
                        "message": a.message,
                        "latitude": a.latitude,
                        "longitude": a.longitude,
                        "is_read": a.is_read,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in alerts
                ]
        except Exception as e:
            logger.error(f"Get alerts error: {e}")
            return []
