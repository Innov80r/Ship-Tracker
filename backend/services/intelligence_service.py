"""
Backend intelligence service for risk, routing, congestion, and enrichment.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from sqlalchemy import func, or_, select

from database import async_session_factory
from models.alert import Alert
from models.incident import Incident
from models.intelligence import ExternalIntelEvent, VesselProfile
from models.vessel_history import VesselHistory
from services.port_service import PortService
from services.redis_broker import RedisBroker
from services.vessel_tracker import VesselTracker
from services.weather_service import WeatherService
from utils.intel_utils import (
    build_playback_events,
    destination_eta_hours,
    get_last_seen_minutes,
    get_port_congestion,
    get_projected_route,
    get_risk_assessment,
    get_traffic_corridors,
    get_vessel_category,
    get_weather_impact_score,
    haversine_nm,
    is_dark_vessel,
    is_military_vessel,
    nearest_point,
    to_float,
)
from utils.vessel_search import matches_vessel_query

logger = logging.getLogger("intelligence_service")


class IntelligenceService:
    """Aggregate intelligence views from vessel, history, alert, and port data."""

    async def _get_active_vessels(self) -> list[dict]:
        redis = RedisBroker()
        await redis.connect()
        try:
            tracker = VesselTracker(redis)
            return await tracker.get_active_vessels()
        finally:
            await redis.close()

    async def _get_ports(self) -> list[dict]:
        port_service = PortService()
        return await port_service.get_all_ports()

    async def _get_cached_weather_grid(self) -> list[dict]:
        redis = RedisBroker()
        await redis.connect()
        try:
            weather_service = WeatherService(redis)
            return await weather_service.get_cached_grid()
        finally:
            await redis.close()

    async def _get_vessel_by_mmsi(self, mmsi: int) -> dict | None:
        redis = RedisBroker()
        await redis.connect()
        try:
            tracker = VesselTracker(redis)
            return await tracker.get_vessel(mmsi)
        finally:
            await redis.close()

    async def filter_vessels(
        self,
        *,
        search: str | None = None,
        vessel_type: int | None = None,
        flag: str | None = None,
        category: str | None = None,
        source: str | None = None,
        speed_min: float | None = None,
        speed_max: float | None = None,
        risk_min: float | None = None,
        dark_only: bool = False,
        destination_required: bool = False,
        last_seen_minutes: float | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        vessels = await self._get_active_vessels()
        weather_grid = await self._get_cached_weather_grid()
        filtered = []

        for vessel in vessels:
            if search and not matches_vessel_query(vessel, search):
                continue
            if vessel_type is not None and vessel.get("vessel_type") != vessel_type:
                continue
            if flag and (vessel.get("flag_country") or "").lower() != flag.lower():
                continue
            if category and get_vessel_category(vessel) != category.lower():
                continue
            if source and (vessel.get("data_source") or "").lower() != source.lower():
                continue

            speed = to_float(vessel.get("speed"), 0.0) or 0.0
            if speed_min is not None and speed < speed_min:
                continue
            if speed_max is not None and speed > speed_max:
                continue
            if destination_required and not vessel.get("destination"):
                continue

            last_seen_value = get_last_seen_minutes(vessel)
            if last_seen_minutes is not None and (last_seen_value is None or last_seen_value > last_seen_minutes):
                continue
            if dark_only and not is_dark_vessel(vessel):
                continue

            weather_point = None
            if weather_grid and vessel.get("latitude") is not None and vessel.get("longitude") is not None:
                weather_point = nearest_point(vessel["latitude"], vessel["longitude"], weather_grid)

            risk = get_risk_assessment(vessel, weather_point=weather_point)
            if risk_min is not None and risk["score"] < risk_min:
                continue

            filtered.append({**vessel, "category": get_vessel_category(vessel), "risk": risk})

        filtered.sort(key=lambda item: (item["risk"]["score"], item.get("speed") or 0), reverse=True)
        return filtered if limit is None else filtered[:limit]

    async def get_risk_leaderboard(self, limit: int = 25) -> list[dict]:
        vessels = await self._get_active_vessels()
        weather_grid = await self._get_cached_weather_grid()
        leaderboard = []
        for vessel in vessels:
            weather_point = None
            if weather_grid and vessel.get("latitude") is not None and vessel.get("longitude") is not None:
                weather_point = nearest_point(vessel["latitude"], vessel["longitude"], weather_grid)
            risk = get_risk_assessment(vessel, weather_point=weather_point)
            leaderboard.append({**vessel, "category": get_vessel_category(vessel), "risk": risk})
        leaderboard.sort(key=lambda item: item["risk"]["score"], reverse=True)
        return leaderboard[:limit]

    async def get_dark_vessels(self, threshold_minutes: float = 60.0, limit: int = 25) -> list[dict]:
        vessels = await self._get_active_vessels()
        dark_vessels = []
        for vessel in vessels:
            if is_dark_vessel(vessel, threshold_minutes=threshold_minutes):
                dark_vessels.append(
                    {
                        **vessel,
                        "category": get_vessel_category(vessel),
                        "last_seen_minutes": round(get_last_seen_minutes(vessel) or 0.0, 2),
                    }
                )
        dark_vessels.sort(key=lambda item: item["last_seen_minutes"], reverse=True)
        return dark_vessels[:limit]

    async def get_port_congestion(self, limit: int = 20) -> list[dict]:
        ports = await self._get_ports()
        vessels = await self._get_active_vessels()
        return get_port_congestion(ports, vessels)[:limit]

    async def get_corridors(self, limit: int = 20) -> list[dict]:
        vessels = await self._get_active_vessels()
        return get_traffic_corridors(vessels)[:limit]

    async def get_weather_impact_leaderboard(self, limit: int = 25) -> list[dict]:
        vessels = await self._get_active_vessels()
        weather_grid = await self._get_cached_weather_grid()
        leaderboard = []
        for vessel in vessels:
            lat = to_float(vessel.get("latitude"))
            lon = to_float(vessel.get("longitude"))
            if lat is None or lon is None:
                continue
            weather_point = nearest_point(lat, lon, weather_grid)
            impact_score = get_weather_impact_score(vessel, weather_point)
            if impact_score <= 0:
                continue
            leaderboard.append(
                {
                    **vessel,
                    "weather_impact_score": impact_score,
                    "weather": weather_point,
                    "category": get_vessel_category(vessel),
                }
            )
        leaderboard.sort(key=lambda item: item["weather_impact_score"], reverse=True)
        return leaderboard[:limit]

    async def get_route_prediction(self, mmsi: int) -> dict:
        vessel = await self._get_vessel_by_mmsi(mmsi)
        if not vessel:
            return {"error": "Vessel not found"}

        ports = await self._get_ports()
        route = get_projected_route(vessel)
        matched_port = None
        destination = (vessel.get("destination") or "").strip().lower()
        if destination:
            matched_port = next(
                (
                    port for port in ports
                    if destination in (port.get("name") or "").lower()
                    or (port.get("name") or "").lower() in destination
                ),
                None,
            )

        eta_hours = destination_eta_hours(
            vessel,
            matched_port.get("latitude") if matched_port else None,
            matched_port.get("longitude") if matched_port else None,
        )
        return {
            "mmsi": mmsi,
            "destination": vessel.get("destination"),
            "matched_port": matched_port,
            "eta_hours": eta_hours,
            "projected_route": route,
        }

    async def get_playback_events(
        self,
        mmsi: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 5000,
    ) -> dict:
        async with async_session_factory() as session:
            query = select(VesselHistory).where(VesselHistory.mmsi == mmsi)
            if start:
                query = query.where(VesselHistory.timestamp >= start)
            if end:
                query = query.where(VesselHistory.timestamp <= end)
            query = query.order_by(VesselHistory.timestamp.asc()).limit(limit)
            result = await session.execute(query)
            history_rows = result.scalars().all()

        points = [
            {
                "latitude": row.latitude,
                "longitude": row.longitude,
                "speed": row.speed,
                "heading": row.heading,
                "course": row.course,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in history_rows
        ]
        return {"mmsi": mmsi, "events": build_playback_events(points), "points": len(points)}

    async def get_vessel_profile(self, mmsi: int, include_related: bool = True) -> dict:
        vessel = await self._get_vessel_by_mmsi(mmsi)
        if not vessel:
            return {"error": "Vessel not found"}

        async with async_session_factory() as session:
            profile = await session.get(VesselProfile, mmsi)
            alert_count = await session.scalar(select(func.count(Alert.id)).where(Alert.mmsi == mmsi))
            incident_count = await session.scalar(select(func.count(Incident.id)).where(Incident.mmsi == mmsi))
            history_count = await session.scalar(select(func.count(VesselHistory.id)).where(VesselHistory.mmsi == mmsi))
            related_events = []
            if include_related:
                conditions = [ExternalIntelEvent.related_mmsi == mmsi]
                if vessel.get("flag_country"):
                    conditions.append(ExternalIntelEvent.related_flag == vessel.get("flag_country"))
                if profile and profile.owner_name:
                    conditions.append(ExternalIntelEvent.related_owner == profile.owner_name)
                event_result = await session.execute(
                    select(ExternalIntelEvent)
                    .where(or_(*conditions))
                    .order_by(ExternalIntelEvent.occurred_at.desc())
                    .limit(20)
                )
                related_events = [self._external_event_to_dict(event) for event in event_result.scalars().all()]

        risk = get_risk_assessment(vessel)
        return {
            "mmsi": mmsi,
            "vessel": vessel,
            "category": get_vessel_category(vessel),
            "risk": risk,
            "dark_vessel": is_dark_vessel(vessel),
            "profile": self._profile_to_dict(profile) if profile else None,
            "stats": {
                "alert_count": alert_count or 0,
                "incident_count": incident_count or 0,
                "history_points": history_count or 0,
            },
            "related_external_events": related_events,
        }

    async def upsert_vessel_profile(self, mmsi: int, payload: dict) -> dict:
        async with async_session_factory() as session:
            profile = await session.get(VesselProfile, mmsi)
            if not profile:
                profile = VesselProfile(mmsi=mmsi)
                session.add(profile)

            for field in (
                "owner_name",
                "operator_name",
                "manager_name",
                "country_of_control",
                "sanctions_status",
                "vessel_classification",
                "profile_source",
                "intelligence_notes",
            ):
                setattr(profile, field, payload.get(field))
            profile.risk_flags = payload.get("risk_flags") or []
            profile.known_aliases = payload.get("known_aliases") or []
            profile.metadata_json = payload.get("metadata_json") or {}
            profile.last_enriched_at = self._parse_datetime(payload.get("last_enriched_at")) or datetime.utcnow()
            await session.commit()
            await session.refresh(profile)
            return self._profile_to_dict(profile)

    async def list_external_events(
        self,
        *,
        event_type: str | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        async with async_session_factory() as session:
            query = select(ExternalIntelEvent)
            if event_type:
                query = query.where(ExternalIntelEvent.event_type == event_type)
            if active_only:
                query = query.where(ExternalIntelEvent.is_active.is_(True))
            query = query.order_by(ExternalIntelEvent.occurred_at.desc()).limit(limit)
            result = await session.execute(query)
            return [self._external_event_to_dict(event) for event in result.scalars().all()]

    async def create_external_event(self, payload: dict) -> dict:
        async with async_session_factory() as session:
            event = ExternalIntelEvent(
                event_type=payload.get("event_type"),
                severity=payload.get("severity") or "info",
                title=payload.get("title"),
                summary=payload.get("summary"),
                source_name=payload.get("source_name"),
                source_url=payload.get("source_url"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                country=payload.get("country"),
                region=payload.get("region"),
                related_mmsi=payload.get("related_mmsi"),
                related_flag=payload.get("related_flag"),
                related_owner=payload.get("related_owner"),
                details=payload.get("details") or {},
                is_active=payload.get("is_active", True),
                occurred_at=self._parse_datetime(payload.get("occurred_at")) or datetime.utcnow(),
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return self._external_event_to_dict(event)

    async def seed_demo_external_events(self) -> list[dict]:
        demo_events = [
            {
                "event_type": "piracy",
                "severity": "critical",
                "title": "Piracy advisory near Gulf of Aden",
                "summary": "Regional advisory reports elevated boarding risk for slow-moving commercial traffic.",
                "source_name": "Demo Maritime Feed",
                "country": "Yemen",
                "region": "Gulf of Aden",
                "latitude": 13.4,
                "longitude": 48.6,
                "details": {"advisory": "Transit corridor watch"},
            },
            {
                "event_type": "sanctions",
                "severity": "warning",
                "title": "Sanctions watchlist update",
                "summary": "Ownership structure linked to a newly sanctioned shipping operator.",
                "source_name": "Demo Compliance Feed",
                "country": "United Arab Emirates",
                "region": "Arabian Sea",
                "related_owner": "Blue Horizon Shipping",
                "details": {"list": "demo-ofac-style"},
            },
            {
                "event_type": "maritime_notice",
                "severity": "info",
                "title": "Temporary exclusion zone notice",
                "summary": "Naval exercise exclusion zone published for the next 72 hours.",
                "source_name": "Demo Notice Feed",
                "country": "India",
                "region": "Arabian Sea",
                "latitude": 15.8,
                "longitude": 71.2,
                "details": {"radius_nm": 45},
            },
        ]
        results = []
        for event in demo_events:
            results.append(await self.create_external_event(event))
        return results

    async def get_external_correlations(self, radius_nm: float = 80.0, hours: int = 168) -> list[dict]:
        vessels = await self._get_active_vessels()
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        async with async_session_factory() as session:
            result = await session.execute(
                select(ExternalIntelEvent).where(ExternalIntelEvent.occurred_at >= cutoff)
            )
            events = result.scalars().all()

        correlations = []
        for vessel in vessels:
            vessel_lat = to_float(vessel.get("latitude"))
            vessel_lon = to_float(vessel.get("longitude"))
            if vessel_lat is None or vessel_lon is None:
                continue
            for event in events:
                event_lat = to_float(event.latitude)
                event_lon = to_float(event.longitude)
                if event_lat is None or event_lon is None:
                    continue
                distance = haversine_nm(vessel_lat, vessel_lon, event_lat, event_lon)
                if distance <= radius_nm:
                    correlations.append(
                        {
                            "mmsi": vessel.get("mmsi"),
                            "vessel_name": vessel.get("name"),
                            "event_id": event.id,
                            "event_type": event.event_type,
                            "event_title": event.title,
                            "severity": event.severity,
                            "distance_nm": round(distance, 2),
                            "risk": get_risk_assessment(vessel),
                        }
                    )
        correlations.sort(key=lambda item: (item["distance_nm"], -item["risk"]["score"]))
        return correlations[:100]

    async def get_military_board(self, limit: int = 25) -> list[dict]:
        vessels = await self._get_active_vessels()
        military = []
        for vessel in vessels:
            if not is_military_vessel(vessel):
                continue
            military.append(
                {
                    **vessel,
                    "category": "military",
                    "risk": get_risk_assessment(vessel),
                }
            )
        military.sort(key=lambda item: item["risk"]["score"], reverse=True)
        return military[:limit]

    async def get_report(self) -> dict:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "risk_leaderboard": await self.get_risk_leaderboard(limit=10),
            "dark_vessels": await self.get_dark_vessels(limit=10),
            "port_congestion": await self.get_port_congestion(limit=10),
            "traffic_corridors": await self.get_corridors(limit=10),
            "external_events": await self.list_external_events(limit=10),
        }

    def _profile_to_dict(self, profile: VesselProfile) -> dict:
        return {
            "mmsi": profile.mmsi,
            "owner_name": profile.owner_name,
            "operator_name": profile.operator_name,
            "manager_name": profile.manager_name,
            "country_of_control": profile.country_of_control,
            "sanctions_status": profile.sanctions_status,
            "vessel_classification": profile.vessel_classification,
            "profile_source": profile.profile_source,
            "risk_flags": profile.risk_flags or [],
            "intelligence_notes": profile.intelligence_notes,
            "known_aliases": profile.known_aliases or [],
            "metadata_json": profile.metadata_json or {},
            "last_enriched_at": profile.last_enriched_at.isoformat() if profile.last_enriched_at else None,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    def _external_event_to_dict(self, event: ExternalIntelEvent) -> dict:
        return {
            "id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
            "title": event.title,
            "summary": event.summary,
            "source_name": event.source_name,
            "source_url": event.source_url,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "country": event.country,
            "region": event.region,
            "related_mmsi": event.related_mmsi,
            "related_flag": event.related_flag,
            "related_owner": event.related_owner,
            "details": event.details or {},
            "is_active": event.is_active,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }

    def _parse_datetime(self, value) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
