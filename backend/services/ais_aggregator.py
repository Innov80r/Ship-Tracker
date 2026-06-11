"""
AIS Aggregator — merges vessel data from all sources by MMSI.
Priority: aisstream > kystverket > noaa > gfw.
Deduplicates and feeds unified vessel state to Redis and the database.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from config import get_settings
from services.redis_broker import RedisBroker
from services.vessel_tracker import VesselTracker
from services.sources.aisstream import AISStreamClient
from services.sources.kystverket import KystverketClient
from services.sources.noaa_ais import NOAAAISClient
from services.sources.global_fishing_watch import GlobalFishingWatchClient

logger = logging.getLogger("aggregator")
settings = get_settings()

# Source priority — lower = higher priority
SOURCE_PRIORITY = {
    "aisstream": 1,
    "kystverket": 2,
    "noaa": 3,
    "gfw": 4,
}

POSITION_FIELDS = {
    "latitude",
    "longitude",
    "speed",
    "heading",
    "course",
    "rot",
    "nav_status",
    "nav_status_text",
    "data_source",
}


class AISAggregator:
    """
    Centralized aggregator that runs all source clients,
    merges updates by MMSI, and forwards to the tracker.
    """

    def __init__(self, redis_broker: RedisBroker, vessel_tracker: VesselTracker):
        self.redis = redis_broker
        self.tracker = vessel_tracker
        self._vessel_sources: dict[int, dict[str, datetime | str]] = {}
        self._message_count = 0

        # Create source clients with our callback
        self.aisstream = AISStreamClient(on_message=self._on_vessel_update)
        self.kystverket = KystverketClient(on_message=self._on_vessel_update)
        self.noaa = NOAAAISClient(on_message=self._on_vessel_update)
        self.gfw = GlobalFishingWatchClient(on_message=self._on_vessel_update)

    async def start(self):
        """Start all source clients concurrently."""
        logger.info("AIS Aggregator starting all sources...")
        tasks = [
            asyncio.create_task(self.aisstream.start(), name="aisstream"),
            asyncio.create_task(self.kystverket.start(), name="kystverket"),
            asyncio.create_task(self.noaa.start(), name="noaa"),
            asyncio.create_task(self.gfw.start(), name="gfw"),
        ]
        # Don't await — let them run in background
        self._tasks = tasks
        logger.info("All AIS sources started")

    async def _on_vessel_update(self, vessel_data: dict):
        """
        Callback from any source. Deduplicates and forwards to tracker.
        Lower-priority sources are ignored if we recently got data from a higher-priority source.
        """
        mmsi = vessel_data.get("mmsi")
        if not mmsi:
            return

        source = vessel_data.get("data_source", "unknown")
        received_at = datetime.now(timezone.utc)
        current_source = self._vessel_sources.get(mmsi)
        has_position = self._has_position(vessel_data)

        # Identity-only updates should enrich the vessel without claiming position authority.
        if not has_position:
            supplementary = self._build_supplementary_update(vessel_data)
            if supplementary:
                await self.tracker.update_vessel(supplementary)
                self._message_count += 1
            return

        # If this vessel is being tracked by a fresher higher-priority source, skip lower-priority positions
        if current_source and current_source["source"] != source:
            current_source_name = str(current_source["source"])
            if SOURCE_PRIORITY.get(source, 99) > SOURCE_PRIORITY.get(current_source_name, 99):
                if self._source_is_fresh(current_source):
                    supplementary = self._build_supplementary_update(vessel_data)
                    if supplementary:
                        await self.tracker.update_vessel(supplementary)
                        self._message_count += 1
                    return

        self._vessel_sources[mmsi] = {
            "source": source,
            "last_seen": received_at,
        }
        self._message_count += 1

        # Forward to tracker (handles DB + Redis + WebSocket)
        await self.tracker.update_vessel(vessel_data)

    def _source_is_fresh(self, source_state: dict[str, datetime | str]) -> bool:
        """Treat a source as authoritative only for a short grace window."""
        last_seen = source_state.get("last_seen")
        if not isinstance(last_seen, datetime):
            return False
        age = datetime.now(timezone.utc) - last_seen
        return age.total_seconds() < settings.SOURCE_STALE_SECONDS

    @staticmethod
    def _has_position(vessel_data: dict) -> bool:
        """Only coordinate-bearing updates should own vessel position."""
        return (
            vessel_data.get("latitude") is not None
            and vessel_data.get("longitude") is not None
        )

    @staticmethod
    def _build_supplementary_update(vessel_data: dict) -> dict:
        """Strip motion/source fields so supplementary updates can't erase live positions."""
        supplementary = {
            k: v for k, v in vessel_data.items()
            if k not in POSITION_FIELDS
        }
        if supplementary.get("mmsi"):
            return supplementary
        return {}

    @property
    def message_count(self) -> int:
        return self._message_count

    @property
    def active_sources(self) -> list[str]:
        """Return list of sources that have provided data."""
        return list({str(source["source"]) for source in self._vessel_sources.values()})

    async def stop(self):
        """Stop all source clients."""
        logger.info("AIS Aggregator stopping all sources...")
        await asyncio.gather(
            self.aisstream.stop(),
            self.kystverket.stop(),
            self.noaa.stop(),
            self.gfw.stop(),
            return_exceptions=True,
        )
        for task in getattr(self, "_tasks", []):
            task.cancel()
        logger.info("AIS Aggregator stopped")
