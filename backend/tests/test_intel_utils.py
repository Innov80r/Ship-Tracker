"""Unit tests for backend intelligence helper functions."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.intel_utils import (
    build_playback_events,
    get_port_congestion,
    get_projected_route,
    get_risk_assessment,
    is_military_vessel,
)


class IntelUtilsTestCase(unittest.TestCase):
    def test_get_risk_assessment_flags_high_risk_dark_military_vessel(self):
        vessel = {
            "mmsi": 123456789,
            "name": "Test Navy Patrol",
            "vessel_type": 35,
            "vessel_type_name": "Navy patrol vessel",
            "speed": 24.0,
            "draught": 13.0,
            "destination": "",
            "last_updated": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
        }
        risk = get_risk_assessment(vessel, restricted_zone_hits=1)
        self.assertGreaterEqual(risk["score"], 60.0)
        self.assertIn(risk["level"], {"high", "critical"})
        self.assertTrue(any(factor["factor"] == "military_presence" for factor in risk["factors"]))

    def test_get_projected_route_returns_multiple_forward_points(self):
        vessel = {
            "latitude": 12.5,
            "longitude": 80.3,
            "speed": 12.0,
            "heading": 90.0,
        }
        route = get_projected_route(vessel, hours=2, step_minutes=30)
        self.assertEqual(len(route), 4)
        self.assertTrue(all(point["minutes_ahead"] > 0 for point in route))
        self.assertGreater(route[-1]["longitude"], route[0]["longitude"])

    def test_is_military_vessel_treats_law_enforcement_as_security_contact(self):
        vessel = {
            "mmsi": 555000111,
            "name": "Harbor Patrol",
            "vessel_type": 55,
            "vessel_type_name": "Law enforcement",
        }
        self.assertTrue(is_military_vessel(vessel))

    def test_get_port_congestion_scores_busy_port_above_quiet_port(self):
        ports = [
            {"id": 1, "name": "Busy Port", "country": "IN", "latitude": 10.0, "longitude": 70.0},
            {"id": 2, "name": "Quiet Port", "country": "IN", "latitude": 25.0, "longitude": 75.0},
        ]
        vessels = [
            {"mmsi": 1, "latitude": 10.01, "longitude": 70.01, "speed": 0.5},
            {"mmsi": 2, "latitude": 10.04, "longitude": 70.02, "speed": 0.4},
            {"mmsi": 3, "latitude": 10.10, "longitude": 70.05, "speed": 7.0},
            {"mmsi": 4, "latitude": 25.20, "longitude": 75.20, "speed": 8.0},
        ]
        congestion = get_port_congestion(ports, vessels, radius_nm=20.0)
        self.assertGreaterEqual(len(congestion), 2)
        self.assertEqual(congestion[0]["port_name"], "Busy Port")
        self.assertGreater(congestion[0]["congestion_score"], congestion[1]["congestion_score"])

    def test_build_playback_events_detects_gap_and_course_change(self):
        points = [
            {
                "latitude": 10.0,
                "longitude": 20.0,
                "speed": 8.0,
                "heading": 90.0,
                "course": 90.0,
                "timestamp": "2026-03-17T00:00:00+00:00",
            },
            {
                "latitude": 10.2,
                "longitude": 20.3,
                "speed": 8.5,
                "heading": 150.0,
                "course": 150.0,
                "timestamp": "2026-03-17T00:30:00+00:00",
            },
            {
                "latitude": 10.6,
                "longitude": 20.7,
                "speed": 9.0,
                "heading": 150.0,
                "course": 150.0,
                "timestamp": "2026-03-17T02:15:00+00:00",
            },
        ]
        events = build_playback_events(points)
        event_types = [event["type"] for event in events]
        self.assertIn("track_start", event_types)
        self.assertIn("course_change", event_types)
        self.assertIn("ais_gap", event_types)
        self.assertEqual(event_types[-1], "track_end")


if __name__ == "__main__":
    unittest.main()
