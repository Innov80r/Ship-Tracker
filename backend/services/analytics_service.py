"""
Analytics Service — aggregated statistics and dashboard queries.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, case, String
from sqlalchemy import cast as sa_cast

from config import get_settings
from database import async_session_factory
from models.vessel import Vessel
from models.vessel_history import VesselHistory
from models.incident import Incident
from models.alert import Alert
from models.port_call import PortCall
from services.redis_broker import RedisBroker

logger = logging.getLogger("analytics_service")
settings = get_settings()


def build_coverage_warnings(
    *,
    active_vessels: int,
    active_source_count: int,
    top_source_share: float,
    unique_flag_countries: int,
    unknown_flag_count: int,
) -> list[str]:
    """Return user-facing coverage warnings for free/public-source tracking."""
    warnings = []

    if active_source_count <= 1:
        warnings.append(
            "Coverage is currently driven by one free AIS feed; offshore, smaller, and military contacts may be missing."
        )
    elif top_source_share >= 0.9:
        warnings.append(
            "One AIS source dominates the current picture, so country and region coverage may be uneven."
        )

    if unique_flag_countries < 100:
        warnings.append(
            "The live fleet spans relatively few flag states right now, which usually indicates uneven upstream feed coverage."
        )

    if unknown_flag_count > max(25, int(active_vessels * 0.01)):
        warnings.append(
            "Some vessels still lack resolved flag information, so country views may undercount them."
        )

    if active_vessels < 5000:
        warnings.append(
            "The active vessel count is low for a global picture; source health or upstream throttling may be limiting coverage."
        )

    if not warnings:
        warnings.append(
            "Free AIS coverage is healthy, but it is still not complete worldwide and will miss some fleets and military traffic."
        )

    return warnings


class AnalyticsService:
    """Provides aggregated analytics for the dashboard and statistics pages."""

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker

    @staticmethod
    def _active_filter():
        cutoff = datetime.utcnow() - timedelta(minutes=settings.VESSEL_TIMEOUT_MINUTES)
        return (
            Vessel.is_active == True,
            Vessel.last_updated >= cutoff,
        )

    async def get_dashboard_stats(self) -> dict:
        """Get overall dashboard statistics."""
        try:
            async with async_session_factory() as session:
                # Total and active vessels
                total = await session.execute(select(func.count(Vessel.mmsi)))
                total_count = total.scalar() or 0

                active = await session.execute(
                    select(func.count(Vessel.mmsi)).where(
                        *self._active_filter(),
                    )
                )
                active_count = active.scalar() or 0

                # By navigation status
                underway = await session.execute(
                    select(func.count(Vessel.mmsi)).where(
                        *self._active_filter(),
                        Vessel.nav_status == 0,
                    )
                )
                anchored = await session.execute(
                    select(func.count(Vessel.mmsi)).where(
                        *self._active_filter(),
                        Vessel.nav_status == 1,
                    )
                )
                moored = await session.execute(
                    select(func.count(Vessel.mmsi)).where(
                        *self._active_filter(),
                        Vessel.nav_status == 5,
                    )
                )

                # Incidents and alerts
                incidents = await session.execute(
                    select(func.count(Incident.id)).where(Incident.is_active == True)
                )
                unread = await session.execute(
                    select(func.count(Alert.id)).where(Alert.is_read == False)
                )

                return {
                    "total_vessels": total_count,
                    "active_vessels": active_count,
                    "vessels_underway": underway.scalar() or 0,
                    "vessels_anchored": anchored.scalar() or 0,
                    "vessels_moored": moored.scalar() or 0,
                    "active_incidents": incidents.scalar() or 0,
                    "unread_alerts": unread.scalar() or 0,
                }
        except Exception as e:
            logger.error(f"Dashboard stats error: {e}")
            return {}

    async def get_type_breakdown(self) -> list[dict]:
        """Vessel type breakdown."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(
                        Vessel.vessel_type_name,
                        func.count(Vessel.mmsi).label("count"),
                    )
                    .where(*self._active_filter())
                    .group_by(Vessel.vessel_type_name)
                    .order_by(func.count(Vessel.mmsi).desc())
                    .limit(20)
                )
                return [
                    {"vessel_type_name": r[0] or "Unknown", "count": r[1]}
                    for r in result.all()
                ]
        except Exception as e:
            logger.error(f"Type breakdown error: {e}")
            return []

    async def get_flag_breakdown(self) -> list[dict]:
        """Flag country breakdown."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(
                        Vessel.flag_country,
                        func.count(Vessel.mmsi).label("count"),
                    )
                    .where(*self._active_filter())
                    .group_by(Vessel.flag_country)
                    .order_by(func.count(Vessel.mmsi).desc())
                    .limit(20)
                )
                return [
                    {"flag_country": r[0] or "Unknown", "count": r[1]}
                    for r in result.all()
                ]
        except Exception as e:
            logger.error(f"Flag breakdown error: {e}")
            return []

    async def get_source_breakdown(self) -> list[dict]:
        """Data source breakdown."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(
                        Vessel.data_source,
                        func.count(Vessel.mmsi).label("count"),
                    )
                    .where(*self._active_filter())
                    .group_by(Vessel.data_source)
                    .order_by(func.count(Vessel.mmsi).desc())
                )
                return [
                    {"data_source": r[0] or "unknown", "count": r[1]}
                    for r in result.all()
                ]
        except Exception as e:
            logger.error(f"Source breakdown error: {e}")
            return []

    async def get_fastest_vessels(self, limit: int = 10) -> list[dict]:
        """Top fastest vessels by speed."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Vessel)
                    .where(*self._active_filter(), Vessel.speed > 0)
                    .order_by(Vessel.speed.desc())
                    .limit(limit)
                )
                return [
                    {
                        "mmsi": v.mmsi, "name": v.name,
                        "speed": v.speed, "vessel_type_name": v.vessel_type_name,
                    }
                    for v in result.scalars().all()
                ]
        except Exception as e:
            logger.error(f"Fastest vessels error: {e}")
            return []

    async def get_coverage_diagnostics(self) -> dict:
        """Summarize live coverage quality for free/public maritime sources."""
        try:
            async with async_session_factory() as session:
                active_filter = self._active_filter()

                active_vessels = await session.scalar(
                    select(func.count(Vessel.mmsi)).where(*active_filter)
                ) or 0

                unique_flag_countries = await session.scalar(
                    select(func.count(func.distinct(Vessel.flag_country))).where(
                        *active_filter,
                        Vessel.flag_country.is_not(None),
                        Vessel.flag_country != "",
                        Vessel.flag_country != "Unknown",
                    )
                ) or 0

                unknown_flag_count = await session.scalar(
                    select(func.count(Vessel.mmsi)).where(
                        *active_filter,
                        case(
                            (Vessel.flag_country.is_(None), True),
                            (Vessel.flag_country == "", True),
                            (Vessel.flag_country == "Unknown", True),
                            else_=False,
                        ),
                    )
                ) or 0

                result = await session.execute(
                    select(
                        Vessel.data_source,
                        func.count(Vessel.mmsi).label("count"),
                    )
                    .where(*active_filter)
                    .group_by(Vessel.data_source)
                    .order_by(func.count(Vessel.mmsi).desc())
                )
                source_breakdown = [
                    {"data_source": row[0] or "unknown", "count": row[1]}
                    for row in result.all()
                ]

            top_source_count = source_breakdown[0]["count"] if source_breakdown else 0
            top_source_share = round(
                (top_source_count / active_vessels) if active_vessels else 0.0,
                4,
            )
            warnings = build_coverage_warnings(
                active_vessels=active_vessels,
                active_source_count=len(source_breakdown),
                top_source_share=top_source_share,
                unique_flag_countries=unique_flag_countries,
                unknown_flag_count=unknown_flag_count,
            )

            return {
                "active_vessels": active_vessels,
                "unique_flag_countries": unique_flag_countries,
                "unknown_flag_count": unknown_flag_count,
                "active_source_count": len(source_breakdown),
                "top_source_share": top_source_share,
                "source_breakdown": source_breakdown,
                "warnings": warnings,
            }
        except Exception as e:
            logger.error("Coverage diagnostics error: %s", e)
            return {
                "active_vessels": 0,
                "unique_flag_countries": 0,
                "unknown_flag_count": 0,
                "active_source_count": 0,
                "top_source_share": 0.0,
                "source_breakdown": [],
                "warnings": [
                    "Coverage diagnostics are temporarily unavailable."
                ],
            }
