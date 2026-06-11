from datetime import datetime, timedelta, timezone
from typing import Any, cast

from services.ais_aggregator import AISAggregator
from services.vessel_tracker import VesselTracker


def test_merge_vessel_state_preserves_existing_position_on_identity_update():
    now = datetime(2026, 3, 18, 12, 0, 0)
    existing = {
        "mmsi": 123456789,
        "latitude": 12.34,
        "longitude": 56.78,
        "speed": 14.2,
        "data_source": "aisstream",
        "name": "OLD NAME",
    }
    incoming = {
        "mmsi": 123456789,
        "name": "NEW NAME",
    }

    merged = VesselTracker._merge_vessel_state(
        existing,
        incoming,
        flag_country=None,
        flag_code=None,
        now=now,
    )

    assert merged["name"] == "NEW NAME"
    assert merged["latitude"] == 12.34
    assert merged["longitude"] == 56.78
    assert merged["speed"] == 14.2
    assert merged["data_source"] == "aisstream"
    assert merged["last_updated"] == now.isoformat()


def test_aggregator_identity_update_does_not_claim_position_authority():
    update = AISAggregator._build_supplementary_update(
        {
            "mmsi": 123456789,
            "data_source": "gfw",
            "name": "FISHER ONE",
            "latitude": 1.0,
            "longitude": 2.0,
        }
    )

    assert update == {
        "mmsi": 123456789,
        "name": "FISHER ONE",
    }


def test_stale_source_window_expires():
    aggregator = AISAggregator(
        redis_broker=cast(Any, None),
        vessel_tracker=cast(Any, None),
    )
    aggregator._vessel_sources[123456789] = {
        "source": "aisstream",
        "last_seen": datetime.now(timezone.utc) - timedelta(seconds=400),
    }

    assert aggregator._source_is_fresh(aggregator._vessel_sources[123456789]) is False
