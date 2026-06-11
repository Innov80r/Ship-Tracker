"""
Vessel Tracker — central vessel state management.
Receives normalized updates, persists to DB and Redis, broadcasts via WebSocket.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import async_session_factory
from models.vessel import Vessel
from models.vessel_history import VesselHistory
from services.redis_broker import RedisBroker
from config import get_settings
from utils.country_utils import normalize_country_identity
from utils.geo_utils import is_valid_coordinate
from utils.vessel_search import matches_vessel_query

logger = logging.getLogger("vessel_tracker")
settings = get_settings()


class VesselTracker:
    """
    Core vessel state manager.
    - Updates vessel records in PostgreSQL (upsert)
    - Logs position history
    - Caches in Redis for fast WebSocket delivery
    - Triggers incident/alert checks
    """

    def __init__(self, redis_broker: RedisBroker):
        self.redis = redis_broker
        self._update_count = 0

    async def update_vessel(self, data: dict[str, Any]):
        """
        Process a normalized vessel update dict.
        Upserts into DB, logs history, caches in Redis, publishes.
        """
        mmsi = data.get("mmsi")
        if not mmsi:
            return

        incoming_lat = self._as_optional_float(data.get("latitude"))
        incoming_lon = self._as_optional_float(data.get("longitude"))
        flag_country, flag_code = normalize_country_identity(
            data.get("flag_country"),
            data.get("flag_code"),
        )

        # Validate coordinates
        if incoming_lat is not None and incoming_lon is not None:
            has_new_position = True
            if not is_valid_coordinate(incoming_lat, incoming_lon):
                return
        else:
            has_new_position = False

        now = datetime.utcnow()
        existing_state = await self.redis.get_vessel(mmsi)

        try:
            async with async_session_factory() as session:
                if not existing_state:
                    existing_vessel = await session.get(Vessel, mmsi)
                    existing_state = self._vessel_to_dict(existing_vessel) if existing_vessel else {}

                merged = self._merge_vessel_state(
                    existing_state or {},
                    data,
                    flag_country=flag_country,
                    flag_code=flag_code,
                    now=now,
                )

                # Upsert vessel
                stmt = pg_insert(Vessel).values(
                    mmsi=mmsi,
                    name=merged.get("name"),
                    imo=merged.get("imo"),
                    call_sign=merged.get("call_sign"),
                    vessel_type=merged.get("vessel_type"),
                    vessel_type_name=merged.get("vessel_type_name"),
                    flag_country=merged.get("flag_country"),
                    flag_code=merged.get("flag_code"),
                    latitude=merged.get("latitude"),
                    longitude=merged.get("longitude"),
                    speed=merged.get("speed"),
                    heading=merged.get("heading"),
                    course=merged.get("course"),
                    rot=merged.get("rot"),
                    nav_status=merged.get("nav_status"),
                    nav_status_text=merged.get("nav_status_text"),
                    length=merged.get("length"),
                    width=merged.get("width"),
                    draught=merged.get("draught"),
                    destination=merged.get("destination"),
                    data_source=merged.get("data_source"),
                    last_updated=now,
                    created_at=now,
                    is_active=True,
                )

                update_dict = {
                    k: getattr(stmt.excluded, k)
                    for k in [
                        "name", "imo", "call_sign", "vessel_type", "vessel_type_name",
                        "flag_country", "flag_code", "latitude", "longitude", "speed",
                        "heading", "course", "rot", "nav_status", "nav_status_text",
                        "length", "width", "draught", "destination", "data_source",
                        "last_updated", "is_active",
                    ]
                }

                stmt = stmt.on_conflict_do_update(
                    index_elements=["mmsi"],
                    set_=update_dict,
                )
                await session.execute(stmt)

                # Log history only when the incoming update included a fresh position.
                if has_new_position:
                    history = VesselHistory(
                        mmsi=mmsi,
                        latitude=incoming_lat,
                        longitude=incoming_lon,
                        speed=data.get("speed"),
                        heading=data.get("heading"),
                        course=data.get("course"),
                        nav_status=data.get("nav_status"),
                        data_source=merged.get("data_source"),
                        timestamp=now,
                    )
                    session.add(history)

                await session.commit()

        except Exception as e:
            logger.error("DB update error for MMSI %s: %s", mmsi, e)
            merged = self._merge_vessel_state(
                existing_state or {},
                data,
                flag_country=flag_country,
                flag_code=flag_code,
                now=now,
            )

        # Cache in Redis and publish
        await self.redis.set_vessel(
            mmsi,
            merged,
            ttl=max(settings.VESSEL_TIMEOUT_MINUTES * 60, 60),
        )
        await self.redis.publish_vessel(merged)

        self._update_count += 1

    async def get_active_vessels(self) -> list[dict[str, Any]]:
        """Get all active vessels from Redis cache, fallback to DB."""
        return await self.get_active_vessels_filtered()

    async def get_active_vessels_filtered(
        self,
        *,
        max_age_minutes: float | None = None,
        require_position: bool = False,
    ) -> list[dict[str, Any]]:
        """Get active vessels with optional freshness and position filters."""
        # Try Redis first
        cached = await self.redis.get_all_vessels()
        if cached:
            return self._filter_vessel_snapshots(
                cached,
                max_age_minutes=max_age_minutes,
                require_position=require_position,
            )

        # Fallback to DB
        try:
            async with async_session_factory() as session:
                cutoff_minutes = max_age_minutes or settings.VESSEL_TIMEOUT_MINUTES
                cutoff = datetime.utcnow() - timedelta(minutes=cutoff_minutes)
                filters = [
                    Vessel.is_active.is_(True),
                    Vessel.last_updated >= cutoff,
                ]
                if require_position:
                    filters.extend([
                        Vessel.latitude.is_not(None),
                        Vessel.longitude.is_not(None),
                    ])
                result = await session.execute(select(Vessel).where(*filters))
                vessels = result.scalars().all()
                return self._filter_vessel_snapshots(
                    [self._vessel_to_dict(v) for v in vessels],
                    max_age_minutes=max_age_minutes,
                    require_position=require_position,
                )
        except Exception as e:
            logger.error("DB read error: %s", e)
            return []

    async def get_vessel(self, mmsi: int) -> Optional[dict[str, Any]]:
        """Get a single vessel by MMSI."""
        cached = await self.redis.get_vessel(mmsi)
        if cached:
            return cached

        try:
            async with async_session_factory() as session:
                result = await session.execute(select(Vessel).where(Vessel.mmsi == mmsi))
                vessel = result.scalar_one_or_none()
                return self._vessel_to_dict(vessel) if vessel else None
        except Exception as e:
            logger.error("DB read error: %s", e)
            return None

    async def search_vessels(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search active vessels by identifier, type, and maritime keywords."""
        query_text = query.strip()
        if not query_text:
            return []

        try:
            async with async_session_factory() as session:
                cutoff = datetime.utcnow() - timedelta(minutes=settings.VESSEL_TIMEOUT_MINUTES)
                result = await session.execute(
                    select(Vessel)
                    .where(
                        Vessel.is_active.is_(True),
                        Vessel.last_updated >= cutoff,
                    )
                    .order_by(Vessel.last_updated.desc())
                )
                matches = []
                for vessel in result.scalars():
                    vessel_data = self._vessel_to_dict(vessel)
                    if matches_vessel_query(vessel_data, query_text):
                        matches.append(vessel_data)
                        if len(matches) >= limit:
                            break
                return matches
        except Exception as e:
            logger.error("Search error: %s", e)
            return []

    async def mark_inactive_vessels(self):
        """Mark vessels as inactive if not updated within timeout."""
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=settings.VESSEL_TIMEOUT_MINUTES)
            async with async_session_factory() as session:
                await session.execute(
                    update(Vessel).where(
                        Vessel.is_active.is_(True),
                        Vessel.last_updated < cutoff,
                    ).values(is_active=False)
                )
                await session.commit()
        except Exception as e:
            logger.error("Inactive marking error: %s", e)

    def _vessel_to_dict(self, vessel: Vessel) -> dict[str, Any]:
        """Convert a Vessel ORM object to a dict."""
        return {
            "mmsi": vessel.mmsi,
            "imo": vessel.imo,
            "name": vessel.name,
            "call_sign": vessel.call_sign,
            "vessel_type": vessel.vessel_type,
            "vessel_type_name": vessel.vessel_type_name,
            "flag_country": vessel.flag_country,
            "flag_code": vessel.flag_code,
            "latitude": vessel.latitude,
            "longitude": vessel.longitude,
            "speed": vessel.speed,
            "heading": vessel.heading,
            "course": vessel.course,
            "rot": vessel.rot,
            "nav_status": vessel.nav_status,
            "nav_status_text": vessel.nav_status_text,
            "length": vessel.length,
            "width": vessel.width,
            "draught": vessel.draught,
            "gross_tonnage": vessel.gross_tonnage,
            "destination": vessel.destination,
            "eta": vessel.eta.isoformat() if vessel.eta else None,
            "transponder_class": vessel.transponder_class,
            "data_source": vessel.data_source,
            "last_updated": vessel.last_updated.isoformat() if vessel.last_updated else None,
            "is_active": vessel.is_active,
        }

    @staticmethod
    def _merge_vessel_state(
        existing: dict[str, Any],
        incoming: dict[str, Any],
        *,
        flag_country: Optional[str],
        flag_code: Optional[str],
        now: datetime,
    ) -> dict[str, Any]:
        """Overlay only meaningful incoming fields onto the current vessel state."""
        merged = dict(existing or {})

        for key, value in incoming.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            merged[key] = value

        if flag_country:
            merged["flag_country"] = flag_country
        if flag_code:
            merged["flag_code"] = flag_code

        merged["mmsi"] = incoming.get("mmsi", merged.get("mmsi"))
        merged["last_updated"] = now.isoformat()
        merged["is_active"] = True
        return merged

    @staticmethod
    def _as_optional_float(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @classmethod
    def _filter_vessel_snapshots(
        cls,
        vessels: list[dict[str, Any]],
        *,
        max_age_minutes: float | None = None,
        require_position: bool = False,
    ) -> list[dict[str, Any]]:
        """Filter cached vessel snapshots by freshness and position availability."""
        return [
            vessel
            for vessel in vessels
            if cls._matches_snapshot_filters(
                vessel,
                max_age_minutes=max_age_minutes,
                require_position=require_position,
            )
        ]

    @classmethod
    def _matches_snapshot_filters(
        cls,
        vessel: dict[str, Any],
        *,
        max_age_minutes: float | None = None,
        require_position: bool = False,
    ) -> bool:
        if require_position and not cls._snapshot_has_position(vessel):
            return False
        if max_age_minutes is not None and not cls._snapshot_is_fresh(vessel, max_age_minutes):
            return False
        return True

    @staticmethod
    def _snapshot_has_position(vessel: dict[str, Any]) -> bool:
        return vessel.get("latitude") is not None and vessel.get("longitude") is not None

    @staticmethod
    def _parse_snapshot_timestamp(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @classmethod
    def _snapshot_is_fresh(cls, vessel: dict[str, Any], max_age_minutes: float) -> bool:
        timestamp = cls._parse_snapshot_timestamp(vessel.get("last_updated"))
        if timestamp is None:
            return False

        if timestamp.tzinfo is None:
            now = datetime.utcnow()
        else:
            now = datetime.now(timestamp.tzinfo)

        return now - timestamp <= timedelta(minutes=max_age_minutes)

    @property
    def update_count(self) -> int:
        """Return the number of updates processed."""
        return self._update_count
