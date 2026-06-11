"""Unit tests for core utility helpers with deterministic behavior."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import sys
import unittest
from typing import Any, cast
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.ais_codes import get_nav_status_text, get_vessel_category, get_vessel_type_name
from utils.geo_utils import bearing, bbox_from_center, cpa_tcpa, haversine_nm, is_valid_coordinate, point_in_bbox
from utils.speed_utils import is_speed_anomaly, kmh_to_knots, knots_to_kmh, knots_to_mph, speed_category
from utils.time_utils import format_duration_hours, format_eta, parse_ais_eta, time_ago, utcnow


class CoreUtilsTestCase(unittest.TestCase):
    def test_haversine_and_bearing_handle_basic_routes(self):
        self.assertAlmostEqual(haversine_nm(0.0, 0.0, 0.0, 1.0), 60.04, places=1)
        self.assertAlmostEqual(bearing(0.0, 0.0, 1.0, 0.0), 0.0, places=1)
        self.assertAlmostEqual(bearing(0.0, 0.0, 0.0, 1.0), 90.0, places=1)

    def test_bbox_helpers_cover_center_point_and_expected_span(self):
        bbox = bbox_from_center(12.0, 34.0, 60.0)
        self.assertTrue(point_in_bbox(12.0, 34.0, bbox))
        self.assertFalse(point_in_bbox(20.0, 34.0, bbox))
        self.assertAlmostEqual(bbox[0], 11.0, places=5)
        self.assertAlmostEqual(bbox[2], 13.0, places=5)

    def test_cpa_tcpa_handles_parallel_and_intercept_cases(self):
        parallel_cpa, parallel_tcpa = cpa_tcpa(0.0, 0.0, 12.0, 90.0, 0.1, 0.0, 12.0, 90.0)
        self.assertGreater(parallel_cpa, 5.0)
        self.assertEqual(parallel_tcpa, 0.0)

        intercept_cpa, intercept_tcpa = cpa_tcpa(0.0, 0.0, 12.0, 90.0, 0.0, 0.2, 12.0, 270.0)
        self.assertLess(intercept_cpa, 0.1)
        self.assertGreater(intercept_tcpa, 0.0)

    def test_coordinate_validation_rejects_out_of_range_values(self):
        self.assertTrue(is_valid_coordinate(0.0, 0.0))
        self.assertFalse(is_valid_coordinate(-91.0, 0.0))
        self.assertFalse(is_valid_coordinate(0.0, 181.0))

    def test_speed_conversions_and_categories_cover_boundaries(self):
        self.assertAlmostEqual(knots_to_kmh(10.0), 18.52, places=2)
        self.assertAlmostEqual(knots_to_mph(10.0), 11.5078, places=4)
        self.assertAlmostEqual(kmh_to_knots(18.52), 10.0, places=2)
        self.assertFalse(is_speed_anomaly(cast(Any, None), 12.0))
        self.assertTrue(is_speed_anomaly(30.0, 1.0))
        self.assertEqual(speed_category(cast(Any, None)), "unknown")
        self.assertEqual(speed_category(-1.0), "unknown")
        self.assertEqual(speed_category(0.1), "stationary")
        self.assertEqual(speed_category(4.0), "slow")
        self.assertEqual(speed_category(10.0), "moderate")
        self.assertEqual(speed_category(20.0), "fast")
        self.assertEqual(speed_category(30.0), "very_fast")

    def test_time_helpers_format_common_cases(self):
        aware_eta = datetime(2026, 3, 18, 12, 30, tzinfo=timezone.utc)
        self.assertEqual(format_eta(aware_eta), "2026-03-18 12:30 UTC")
        self.assertIsNone(format_eta(None))

        self.assertEqual(format_duration_hours(None), "N/A")
        self.assertEqual(format_duration_hours(0.5), "30m")
        self.assertEqual(format_duration_hours(6.25), "6.2h")
        self.assertEqual(format_duration_hours(48.0), "2.0d")

    def test_time_ago_handles_naive_aware_and_future_values(self):
        self.assertEqual(time_ago(None), "N/A")

        naive_past = datetime.now() - timedelta(seconds=45)
        result = time_ago(naive_past)
        self.assertTrue(result.endswith("s ago"))

        aware_past = utcnow() - timedelta(minutes=90)
        self.assertEqual(time_ago(aware_past), "1h ago")

        aware_future = utcnow() + timedelta(minutes=5)
        self.assertEqual(time_ago(aware_future), "just now")

    def test_parse_ais_eta_handles_invalid_and_rollover_cases(self):
        fixed_now = datetime(2026, 12, 31, 23, 0, tzinfo=timezone.utc)
        with patch("utils.time_utils.utcnow", return_value=fixed_now):
            parsed = parse_ais_eta(1, 1, 1, 30)
            assert parsed is not None
            self.assertEqual(parsed.year, 2027)
            self.assertEqual(parsed.month, 1)
            self.assertEqual(parsed.day, 1)

        self.assertIsNone(parse_ais_eta(0, 1, 1, 1))
        self.assertIsNone(parse_ais_eta(2, 31, 1, 1))

    def test_ais_code_helpers_return_named_and_unknown_values(self):
        self.assertEqual(get_vessel_type_name(70), "Cargo ship")
        self.assertEqual(get_nav_status_text(5), "Moored")
        self.assertEqual(get_vessel_category(35), "military")
        self.assertEqual(get_vessel_type_name(999), "Unknown (999)")
        self.assertEqual(get_nav_status_text(999), "Unknown (999)")
        self.assertEqual(get_vessel_category(999), "other")


if __name__ == "__main__":
    unittest.main()
