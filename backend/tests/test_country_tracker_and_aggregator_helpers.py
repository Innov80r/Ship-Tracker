"""Focused coverage for country helpers, tracker helpers, and aggregator branches."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, cast

import pytest
from shapely.geometry import Polygon
from shapely.prepared import prep

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ais_aggregator import AISAggregator
from services.vessel_tracker import VesselTracker
from utils.country_utils import (
    EEZCountryResolver,
    _country_name_from_properties,
    get_eez_country_resolver,
    list_country_catalog,
    normalize_country_code,
    normalize_country_identity,
    normalize_country_name,
)


class _TrackerStub:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    async def update_vessel(self, data: dict) -> None:
        self.updates.append(data)


def test_country_name_and_code_normalization_cover_aliases_and_fallbacks():
    assert normalize_country_name("uk") == "United Kingdom"
    assert normalize_country_name("  russian federation ") == "Russia"
    assert normalize_country_name("marshall islands") == "Marshall Islands"
    assert normalize_country_name(None) is None

    assert normalize_country_code("United States of America") == "US"
    assert normalize_country_code("gb") == "GB"
    assert normalize_country_code("unknown place") is None


def test_country_identity_fills_missing_name_or_code():
    assert normalize_country_identity(country=None, country_code="KR") == ("South Korea", "KR")
    assert normalize_country_identity(country="cote divoire", country_code=None) == ("Ivory Coast", "CI")


def test_country_name_from_properties_prefers_territory_then_fallbacks():
    assert _country_name_from_properties(
        {"territory1": "Greenland", "sovereign1": "Denmark", "geoname": "Ignored"}
    ) == "Greenland"
    assert _country_name_from_properties(
        {"territory1": "", "sovereign1": "France", "geoname": "Ignored"}
    ) == "France"
    assert _country_name_from_properties(
        {"territory1": "", "sovereign1": "", "geoname": "Atlantic"}
    ) == "Atlantic"


def test_country_catalog_keeps_aliases_for_common_countries():
    catalog = list_country_catalog()
    united_kingdom = next(country for country in catalog if country["name"] == "United Kingdom")

    assert united_kingdom["code"] == "GB"
    assert "uk" in united_kingdom["aliases"]
    assert "great britain" in united_kingdom["aliases"]


def test_eez_country_resolver_resolves_intersection_and_nearest_country():
    resolver = EEZCountryResolver(geojson_path=Path("does-not-matter.geojson"))
    polygon = Polygon([(10, 10), (10, 12), (12, 12), (12, 10)])
    resolver._regions = [
        {
            "country": "Greenland",
            "bounds": (10.0, 10.0, 12.0, 12.0),
            "polygon": polygon,
            "geometry": prep(polygon),
        }
    ]

    assert resolver.resolve(11.0, 11.0) == "Greenland"
    assert resolver.resolve(12.4, 11.0, nearest_tolerance_degrees=0.5) == "Greenland"
    assert resolver.resolve(20.0, 20.0, nearest_tolerance_degrees=0.5) is None
    assert resolver.resolve(None, 11.0) is None


def test_get_eez_country_resolver_is_cached_singleton():
    get_eez_country_resolver.cache_clear()
    first = get_eez_country_resolver()
    second = get_eez_country_resolver()

    assert first is second


def test_tracker_merge_state_ignores_blank_fields_and_applies_flags():
    now = datetime(2026, 3, 18, 18, 0, 0)
    merged = VesselTracker._merge_vessel_state(
        {
            "mmsi": 123456789,
            "name": "ORIGINAL",
            "destination": "Mumbai",
            "latitude": 19.0,
        },
        {
            "mmsi": 123456789,
            "name": " ",
            "destination": None,
            "call_sign": "VT99",
        },
        flag_country="India",
        flag_code="IN",
        now=now,
    )

    assert merged["name"] == "ORIGINAL"
    assert merged["destination"] == "Mumbai"
    assert merged["call_sign"] == "VT99"
    assert merged["flag_country"] == "India"
    assert merged["flag_code"] == "IN"
    assert merged["last_updated"] == now.isoformat()
    assert merged["is_active"] is True


def test_tracker_optional_float_and_vessel_to_dict_cover_basic_conversions():
    tracker = VesselTracker(redis_broker=cast(Any, SimpleNamespace()))
    eta = datetime(2026, 3, 19, 1, 30, 0)
    updated = datetime(2026, 3, 18, 20, 15, 0)
    vessel = SimpleNamespace(
        mmsi=123456789,
        imo=9876543,
        name="SEA BIRD",
        call_sign="VTAA",
        vessel_type=70,
        vessel_type_name="Cargo ship",
        flag_country="India",
        flag_code="IN",
        latitude=18.9,
        longitude=72.8,
        speed=12.4,
        heading=180.0,
        course=181.0,
        rot=0.0,
        nav_status=0,
        nav_status_text="Under way",
        length=120.0,
        width=20.0,
        draught=7.5,
        gross_tonnage=9000.0,
        destination="Mumbai",
        eta=eta,
        transponder_class="A",
        data_source="aisstream",
        last_updated=updated,
        is_active=True,
    )

    assert VesselTracker._as_optional_float(7) == 7.0
    assert VesselTracker._as_optional_float(7.5) == 7.5
    assert VesselTracker._as_optional_float("7.5") is None

    vessel_dict = tracker._vessel_to_dict(cast(Any, vessel))
    assert vessel_dict["eta"] == eta.isoformat()
    assert vessel_dict["last_updated"] == updated.isoformat()
    assert vessel_dict["gross_tonnage"] == 9000.0


def test_tracker_snapshot_filters_keep_only_fresh_positioned_vessels():
    now = datetime.utcnow()
    fresh = {
        "mmsi": 111000111,
        "latitude": 12.0,
        "longitude": 72.0,
        "last_updated": now.isoformat(),
    }
    stale = {
        "mmsi": 222000222,
        "latitude": 13.0,
        "longitude": 73.0,
        "last_updated": (now - timedelta(minutes=12)).isoformat(),
    }
    no_position = {
        "mmsi": 333000333,
        "last_updated": now.isoformat(),
    }

    filtered = VesselTracker._filter_vessel_snapshots(
        [fresh, stale, no_position],
        max_age_minutes=5,
        require_position=True,
    )

    assert filtered == [fresh]


@pytest.mark.asyncio
async def test_aggregator_identity_update_forwards_supplementary_only():
    tracker = _TrackerStub()
    aggregator = AISAggregator(
        redis_broker=cast(Any, SimpleNamespace()),
        vessel_tracker=cast(Any, tracker),
    )

    await aggregator._on_vessel_update(
        {
            "mmsi": 111000111,
            "data_source": "gfw",
            "name": "IDENTITY ONLY",
            "latitude": None,
            "longitude": None,
            "call_sign": "CALL1",
        }
    )

    assert tracker.updates == [
        {
            "mmsi": 111000111,
            "name": "IDENTITY ONLY",
            "call_sign": "CALL1",
        }
    ]
    assert aggregator.message_count == 1
    assert aggregator.active_sources == []


@pytest.mark.asyncio
async def test_aggregator_blocks_fresh_lower_priority_position_but_keeps_supplementary_data():
    tracker = _TrackerStub()
    aggregator = AISAggregator(
        redis_broker=cast(Any, SimpleNamespace()),
        vessel_tracker=cast(Any, tracker),
    )

    await aggregator._on_vessel_update(
        {
            "mmsi": 222000222,
            "data_source": "aisstream",
            "latitude": 10.0,
            "longitude": 20.0,
            "speed": 14.0,
            "name": "PRIMARY",
        }
    )
    await aggregator._on_vessel_update(
        {
            "mmsi": 222000222,
            "data_source": "noaa",
            "latitude": 11.0,
            "longitude": 21.0,
            "speed": 8.0,
            "destination": "Boston",
        }
    )

    assert tracker.updates[0]["latitude"] == 10.0
    assert tracker.updates[1] == {
        "mmsi": 222000222,
        "destination": "Boston",
    }
    assert aggregator._vessel_sources[222000222]["source"] == "aisstream"
    assert set(aggregator.active_sources) == {"aisstream"}
    assert aggregator.message_count == 2


@pytest.mark.asyncio
async def test_aggregator_accepts_lower_priority_position_after_source_stales():
    tracker = _TrackerStub()
    aggregator = AISAggregator(
        redis_broker=cast(Any, SimpleNamespace()),
        vessel_tracker=cast(Any, tracker),
    )
    aggregator._vessel_sources[333000333] = {
        "source": "aisstream",
        "last_seen": datetime.now(timezone.utc) - timedelta(seconds=400),
    }

    await aggregator._on_vessel_update(
        {
            "mmsi": 333000333,
            "data_source": "noaa",
            "latitude": 30.0,
            "longitude": 40.0,
            "speed": 9.5,
        }
    )

    assert tracker.updates == [
        {
            "mmsi": 333000333,
            "data_source": "noaa",
            "latitude": 30.0,
            "longitude": 40.0,
            "speed": 9.5,
        }
    ]
    assert aggregator._vessel_sources[333000333]["source"] == "noaa"
    assert aggregator.message_count == 1


def test_aggregator_helpers_cover_position_and_invalid_source_state():
    assert AISAggregator._has_position({"latitude": 1.0, "longitude": 2.0}) is True
    assert AISAggregator._has_position({"latitude": 1.0, "longitude": None}) is False
    assert AISAggregator._build_supplementary_update({"name": "missing mmsi"}) == {}

    aggregator = AISAggregator(
        redis_broker=cast(Any, SimpleNamespace()),
        vessel_tracker=cast(Any, SimpleNamespace()),
    )
    assert aggregator._source_is_fresh({"source": "aisstream", "last_seen": "invalid"}) is False
