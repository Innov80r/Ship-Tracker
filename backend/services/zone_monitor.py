"""
Zone Monitor — tracks vessel entry/exit from user-defined zones.
"""

import logging
from typing import Set, Dict

from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from sqlalchemy import select

from database import async_session_factory
from models.zone import Zone
from services.alert_engine import AlertEngine

logger = logging.getLogger("zone_monitor")


class ZoneMonitor:
    """Monitors vessels against user-defined geographic zones."""

    def __init__(self, alert_engine: AlertEngine):
        self.alert_engine = alert_engine
        self._zones: list[dict] = []
        self._vessel_zone_state: dict[int, set[int]] = {}  # mmsi → set of zone_ids

    async def load_zones(self):
        """Load active zones from DB."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Zone).where(Zone.is_active.is_(True))
                )
                zones = result.scalars().all()
                self._zones = []
                for z in zones:
                    geo = None
                    if z.geometry:
                        geo = to_shape(z.geometry)
                    self._zones.append({
                        "id": z.id,
                        "name": z.name,
                        "zone_type": z.zone_type,
                        "shape": geo,
                        "alert_on_entry": z.alert_on_entry,
                        "alert_on_exit": z.alert_on_exit,
                    })
                logger.info("Loaded %d zones", len(self._zones))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Zone load error: %s", e)

    async def check_vessel(self, vessel_data: dict):
        """Check a vessel against all zones for entry/exit."""
        mmsi_raw = vessel_data.get("mmsi")
        lat = vessel_data.get("latitude")
        lon = vessel_data.get("longitude")
        if not mmsi_raw or lat is None or lon is None:
            return

        mmsi = int(str(mmsi_raw))
        point = Point(lon, lat)
        current_zones = set()

        for zone in self._zones:
            if zone["shape"] and zone["shape"].contains(point):
                current_zones.add(zone["id"])

        prev_zones = self._vessel_zone_state.get(int(mmsi), set())

        # Check entries
        entered = current_zones - prev_zones
        for zone_id in entered:
            zone = next((z for z in self._zones if z["id"] == zone_id), None)
            if zone and zone["alert_on_entry"]:
                await self.alert_engine.create_alert(
                    alert_type="ZONE_ENTRY",
                    title=f"{vessel_data.get('name', 'Unknown')} entered {zone['name']}",
                    message=f"Vessel MMSI {mmsi} entered {zone['zone_type']} zone",
                    severity="warning" if zone["zone_type"] == "restricted" else "info",
                    mmsi=mmsi,
                    vessel_name=vessel_data.get("name"),
                    latitude=lat,
                    longitude=lon,
                    zone_id=zone_id,
                )

        # Check exits
        exited = prev_zones - current_zones
        for zone_id in exited:
            zone = next((z for z in self._zones if z["id"] == zone_id), None)
            if zone and zone["alert_on_exit"]:
                await self.alert_engine.create_alert(
                    alert_type="ZONE_EXIT",
                    title=f"{vessel_data.get('name', 'Unknown')} exited {zone['name']}",
                    message=f"Vessel MMSI {mmsi} exited {zone['zone_type']} zone",
                    severity="info",
                    mmsi=mmsi,
                    vessel_name=vessel_data.get("name"),
                    latitude=lat,
                    longitude=lon,
                    zone_id=zone_id,
                )

        self._vessel_zone_state[int(mmsi)] = current_zones
