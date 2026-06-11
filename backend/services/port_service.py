"""
Port Service — fetches world port data from OpenStreetMap Overpass API.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import async_session_factory
from models.port import Port
from utils.country_utils import (
    get_eez_country_resolver,
    get_land_country_resolver,
    normalize_country_identity,
)

logger = logging.getLogger("port_service")


class PortService:
    """Fetches and caches world port data from Overpass API."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    MINIMUM_EXPECTED_PORTS = 12000
    OVERPASS_MAX_ATTEMPTS = 4
    OVERPASS_BASE_RETRY_SECONDS = 6.0
    OVERPASS_SHARD_PAUSE_SECONDS = 1.5
    OVERPASS_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    OVERPASS_BBOXES = (
        (-90, -180, 0, -90),
        (-90, -90, 0, 0),
        (-90, 0, 0, 90),
        (-90, 90, 0, 180),
        (0, -180, 90, -90),
        (0, -90, 90, 0),
        (0, 0, 90, 90),
        (0, 90, 90, 180),
    )

    def __init__(self):
        self.country_resolver = get_eez_country_resolver()
        self.land_country_resolver = get_land_country_resolver()

    @classmethod
    def should_rebuild_catalog(
        cls,
        *,
        requested: bool,
        fetched_count: int,
        failed_shards: int,
    ) -> bool:
        """Only rebuild on a complete-enough fetch so partial runs never erase good data."""
        if not requested:
            return False
        if failed_shards:
            return False
        return fetched_count >= cls.MINIMUM_EXPECTED_PORTS

    @classmethod
    def _get_retry_delay_seconds(cls, response: httpx.Response | None, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After") if response else None
        if retry_after:
            try:
                return max(float(retry_after), cls.OVERPASS_BASE_RETRY_SECONDS)
            except ValueError:
                pass
        return cls.OVERPASS_BASE_RETRY_SECONDS * attempt

    async def _fetch_shard_elements(
        self,
        client: httpx.AsyncClient,
        bbox: tuple[float, float, float, float],
        shard_index: int,
    ) -> list[dict] | None:
        query = self._build_query(bbox)

        for attempt in range(1, self.OVERPASS_MAX_ATTEMPTS + 1):
            try:
                resp = await client.post(self.OVERPASS_URL, data={"data": query})
            except httpx.HTTPError as exc:
                if attempt >= self.OVERPASS_MAX_ATTEMPTS:
                    logger.warning(
                        "Overpass shard %s/%s failed after %s attempts: %s",
                        shard_index,
                        len(self.OVERPASS_BBOXES),
                        attempt,
                        exc,
                    )
                    return None

                delay = self._get_retry_delay_seconds(None, attempt)
                logger.warning(
                    "Overpass shard %s/%s request error on attempt %s/%s: %s; retrying in %.1fs",
                    shard_index,
                    len(self.OVERPASS_BBOXES),
                    attempt,
                    self.OVERPASS_MAX_ATTEMPTS,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                logger.info(
                    "Overpass shard %s/%s returned %s raw elements",
                    shard_index,
                    len(self.OVERPASS_BBOXES),
                    len(elements),
                )
                return elements

            if resp.status_code not in self.OVERPASS_RETRYABLE_STATUS_CODES:
                logger.warning(
                    "Overpass shard %s/%s returned non-retryable %s",
                    shard_index,
                    len(self.OVERPASS_BBOXES),
                    resp.status_code,
                )
                return None

            if attempt >= self.OVERPASS_MAX_ATTEMPTS:
                logger.warning(
                    "Overpass shard %s/%s returned %s after %s attempts",
                    shard_index,
                    len(self.OVERPASS_BBOXES),
                    resp.status_code,
                    attempt,
                )
                return None

            delay = self._get_retry_delay_seconds(resp, attempt)
            logger.warning(
                "Overpass shard %s/%s returned %s on attempt %s/%s; retrying in %.1fs",
                shard_index,
                len(self.OVERPASS_BBOXES),
                resp.status_code,
                attempt,
                self.OVERPASS_MAX_ATTEMPTS,
                delay,
            )
            await asyncio.sleep(delay)

        return None

    async def fetch_ports(self, rebuild: bool = False) -> int:
        """Fetch all ports, terminals, and anchorages from OSM Overpass API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                parsed_ports: dict[str, dict] = {}
                failed_shards: list[int] = []
                for shard_index, bbox in enumerate(self.OVERPASS_BBOXES, start=1):
                    elements = await self._fetch_shard_elements(client, bbox, shard_index)
                    if elements is None:
                        failed_shards.append(shard_index)
                        continue

                    for el in elements:
                        port_data = self._parse_element(el)
                        if port_data and port_data.get("name"):
                            parsed_ports[port_data["osm_id"]] = port_data

                    if shard_index < len(self.OVERPASS_BBOXES):
                        await asyncio.sleep(self.OVERPASS_SHARD_PAUSE_SECONDS)

                if not parsed_ports:
                    logger.warning("Overpass returned no usable port elements")
                    return 0

                if failed_shards:
                    logger.warning(
                        "Overpass fetch incomplete: %s/%s shards failed (%s)",
                        len(failed_shards),
                        len(self.OVERPASS_BBOXES),
                        ",".join(str(shard) for shard in failed_shards),
                    )

                async with async_session_factory() as session:
                    should_rebuild = self.should_rebuild_catalog(
                        requested=rebuild,
                        fetched_count=len(parsed_ports),
                        failed_shards=len(failed_shards),
                    )
                    if rebuild and not should_rebuild:
                        logger.warning(
                            "Skipping destructive port catalog rebuild because the fetch was incomplete "
                            "(ports=%s, failed_shards=%s)",
                            len(parsed_ports),
                            len(failed_shards),
                        )

                    if should_rebuild:
                        await session.execute(delete(Port))

                    for port_data in parsed_ports.values():
                        stmt = pg_insert(Port).values(**port_data)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["osm_id"],
                            set_={k: v for k, v in port_data.items() if k != "osm_id"},
                        )
                        await session.execute(stmt)
                    await session.commit()

                count = len(parsed_ports)
                logger.info("Loaded %s ports from Overpass API", count)
                return count

        except Exception as e:
            logger.error("Port fetch error: %s", e)
            return 0

    @staticmethod
    def _build_query(bbox: tuple[float, float, float, float]) -> str:
        """Build a sharded Overpass query for a world-region bounding box."""
        south, west, north, east = bbox
        bbox_expr = f"({south},{west},{north},{east})"
        selectors = [
            'node["harbour"="yes"]',
            'node["harbour:category"~"^(port|terminal|anchorage|cargo|container)$", i]',
            'node["seamark:type"~"^(harbour|anchorage|harbour_basin|terminal|berth|dock|marina|pier|quay)$", i]',
            'node["port"="yes"]',
            'node["landuse"="port"]',
            'node["industrial"="port"]',
            'way["harbour"="yes"]',
            'way["harbour:category"~"^(port|terminal|anchorage|cargo|container)$", i]',
            'way["seamark:type"~"^(harbour|anchorage|harbour_basin|terminal|berth|dock|marina|pier|quay)$", i]',
            'way["port"="yes"]',
            'way["landuse"="port"]',
            'way["industrial"="port"]',
            'relation["harbour"="yes"]',
            'relation["harbour:category"~"^(port|terminal|anchorage|cargo|container)$", i]',
            'relation["seamark:type"~"^(harbour|anchorage|harbour_basin|terminal|berth|dock|marina|pier|quay)$", i]',
            'relation["port"="yes"]',
            'relation["landuse"="port"]',
            'relation["industrial"="port"]',
        ]
        lines = [f"  {selector}{bbox_expr};" for selector in selectors]
        joined = "\n".join(lines)
        return f"[out:json][timeout:120];\n(\n{joined}\n);\nout tags center;"

    def _normalize_or_resolve_country(
        self,
        *,
        country: str | None,
        country_code: str | None = None,
        latitude: float,
        longitude: float,
    ) -> tuple[str | None, str | None]:
        """Prefer canonical names and use EEZ lookup when tag text is not a real country."""
        normalized_country, normalized_code = normalize_country_identity(country, country_code)

        resolved_country = self.country_resolver.resolve(float(latitude), float(longitude))
        if not resolved_country:
            resolved_country = self.land_country_resolver.resolve(float(latitude), float(longitude))
        resolved_country, resolved_code = normalize_country_identity(resolved_country)

        if resolved_country and (not normalized_code or not normalized_country):
            return resolved_country, resolved_code
        return normalized_country, normalized_code

    def _parse_element(self, el: dict) -> Optional[dict]:
        """Parse an Overpass element into a port dict."""
        tags = el.get("tags", {})
        lat = el.get("lat") if el.get("lat") is not None else el.get("center", {}).get("lat")
        lon = el.get("lon") if el.get("lon") is not None else el.get("center", {}).get("lon")

        if lat is None or lon is None:
            return None

        name = tags.get("name", tags.get("seamark:name", ""))
        if not name:
            return None

        normalized_country, _ = self._normalize_or_resolve_country(
            country=(
                tags.get("addr:country")
                or tags.get("country")
                or tags.get("is_in:country")
            ),
            country_code=(
                tags.get("addr:country")
                or tags.get("is_in:country_code")
                or tags.get("ISO3166-1:alpha2")
                or tags.get("ISO3166-1")
            ),
            latitude=float(lat),
            longitude=float(lon),
        )

        osm_type = str(el.get("type") or "node").strip().lower()
        osm_id = el.get("id")
        if not osm_id:
            return None

        return {
            "name": name.strip(),
            "country": normalized_country,
            "latitude": float(lat),
            "longitude": float(lon),
            "port_type": (
                tags.get("harbour:category")
                or tags.get("seamark:type")
                or ("port" if tags.get("port") == "yes" else None)
                or "port"
            ),
            "un_locode": tags.get("ref:locode", tags.get("un_locode", "")),
            "osm_id": f"{osm_type}/{osm_id}",
            "description": tags.get("description"),
            "last_refreshed": datetime.now(timezone.utc).replace(tzinfo=None),
        }

    async def count_ports(self) -> int:
        """Return the total number of cached ports."""
        try:
            async with async_session_factory() as session:
                return await session.scalar(select(func.count()).select_from(Port)) or 0
        except Exception as e:
            logger.error("Port count error: %s", e)
            return 0

    async def backfill_port_countries(self) -> int:
        """Normalize or infer countries for existing cached ports."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(Port))
                ports = result.scalars().all()
                updated = 0
                for port in ports:
                    normalized_country, normalized_code = normalize_country_identity(port.country)
                    needs_resolution = (
                        port.country is None
                        or port.country == ""
                        or len((port.country or "").strip()) <= 3
                        or normalized_country != port.country
                        or normalized_code is None
                    )
                    if not needs_resolution:
                        continue

                    resolved_country, _ = self._normalize_or_resolve_country(
                        country=port.country,
                        latitude=port.latitude,
                        longitude=port.longitude,
                    )
                    if resolved_country and resolved_country != port.country:
                        port.country = resolved_country
                        updated += 1
                await session.commit()
                return updated
        except Exception as e:
            logger.error("Port country backfill error: %s", e)
            return 0

    async def ensure_port_catalog(self) -> dict:
        """Refresh incomplete catalogs and normalize country fields."""
        existing_count = await self.count_ports()
        refreshed = 0

        if existing_count < self.MINIMUM_EXPECTED_PORTS:
            logger.info(
                "Refreshing world port catalog because only %s cached ports were found",
                existing_count,
            )
            refreshed = await self.fetch_ports(rebuild=False)
            if refreshed:
                existing_count = await self.count_ports()

        normalized = await self.backfill_port_countries()
        return {
            "count": existing_count,
            "refreshed": refreshed,
            "normalized": normalized,
        }

    async def get_all_ports(
        self,
        *,
        search: str | None = None,
        country: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Get cached ports from the database, optionally filtered."""
        try:
            async with async_session_factory() as session:
                query = select(Port).order_by(Port.name.asc())

                if search:
                    query = query.where(
                        Port.name.ilike(f"%{search}%") | Port.country.ilike(f"%{search}%")
                    )

                normalized_country, _ = normalize_country_identity(country)
                if normalized_country:
                    query = query.where(Port.country.ilike(normalized_country))

                if limit is not None:
                    query = query.limit(limit)

                result = await session.execute(query)
                ports = result.scalars().all()
                return [
                    {
                        "id": p.id,
                        "name": p.name,
                        "country": normalize_country_identity(p.country)[0] or p.country,
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "port_type": p.port_type,
                        "un_locode": p.un_locode,
                        "geofence_radius_nm": p.geofence_radius_nm,
                        "description": p.description,
                    }
                    for p in ports
                ]
        except Exception as e:
            logger.error("Get ports error: %s", e)
            return []

    async def search_ports(self, query: str, limit: int = 20) -> list[dict]:
        """Search ports by name or country."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Port).where(
                        Port.name.ilike(f"%{query}%") | Port.country.ilike(f"%{query}%")
                    ).limit(limit)
                )
                ports = result.scalars().all()
                return [
                    {
                        "id": p.id,
                        "name": p.name,
                        "country": normalize_country_identity(p.country)[0] or p.country,
                        "latitude": p.latitude, "longitude": p.longitude,
                        "port_type": p.port_type,
                        "un_locode": p.un_locode,
                    }
                    for p in ports
                ]
        except Exception as e:
            logger.error("Port search error: %s", e)
            return []
