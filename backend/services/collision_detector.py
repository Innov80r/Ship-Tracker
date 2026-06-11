"""
Collision Detector — checks pairs of vessels for CPA/TCPA collision risk.
"""

import logging
from typing import Optional

from utils.geo_utils import cpa_tcpa, haversine_nm
from services.alert_engine import AlertEngine
from config import get_settings

logger = logging.getLogger("collision_detector")
settings = get_settings()


class CollisionDetector:
    """
    Monitors vessel pairs for potential collision risk.
    Uses CPA (Closest Point of Approach) and TCPA (Time to CPA) analysis.
    """

    def __init__(self, alert_engine: AlertEngine):
        self.alert_engine = alert_engine
        self._checked_pairs: set = set()  # avoid duplicate alerts

    async def check_collision_risk(self, vessels: list[dict]):
        """Check all pairs of nearby moving vessels for collision risk."""
        moving = [
            v for v in vessels
            if v.get("speed", 0) and v["speed"] > 0.5
            and v.get("latitude") and v.get("longitude")
            and v.get("course") is not None
        ]

        # Only check vessels within potential range (pre-filter)
        for i, v1 in enumerate(moving):
            for v2 in moving[i + 1:]:
                dist = haversine_nm(
                    v1["latitude"], v1["longitude"],
                    v2["latitude"], v2["longitude"],
                )
                # Only check vessels within 10 NM of each other
                if dist < 10:
                    await self._check_pair(v1, v2)

    async def _check_pair(self, v1: dict, v2: dict):
        """Check a single pair for collision risk."""
        pair_key = tuple(sorted([v1["mmsi"], v2["mmsi"]]))
        if pair_key in self._checked_pairs:
            return

        cpa_dist, tcpa_min = cpa_tcpa(
            v1["latitude"], v1["longitude"], v1.get("speed", 0), v1.get("course", 0),
            v2["latitude"], v2["longitude"], v2.get("speed", 0), v2.get("course", 0),
        )

        # Alert if CPA < configured distance and TCPA is positive (converging)
        if cpa_dist < settings.COLLISION_ALERT_DISTANCE_NM and 0 < tcpa_min < 30:
            self._checked_pairs.add(pair_key)
            await self.alert_engine.create_alert(
                alert_type="COLLISION_RISK",
                title=f"Collision risk: {v1.get('name', v1['mmsi'])} ↔ {v2.get('name', v2['mmsi'])}",
                message=f"CPA: {cpa_dist:.2f} NM in {tcpa_min:.1f} min",
                severity="critical",
                mmsi=v1["mmsi"],
                vessel_name=v1.get("name"),
                latitude=v1["latitude"],
                longitude=v1["longitude"],
            )
            logger.warning(f"Collision risk: MMSI {v1['mmsi']} ↔ {v2['mmsi']}, CPA={cpa_dist:.2f}NM, TCPA={tcpa_min:.1f}min")

    def clear_checked(self):
        """Clear checked pairs to allow re-alerting after cooldown."""
        self._checked_pairs.clear()
