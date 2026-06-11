"""Unit tests for coverage diagnostics messaging."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.analytics_service import build_coverage_warnings


class CoverageDiagnosticsTestCase(unittest.TestCase):
    def test_build_coverage_warnings_flags_single_source_bias(self):
        warnings = build_coverage_warnings(
            active_vessels=12000,
            active_source_count=1,
            top_source_share=0.97,
            unique_flag_countries=117,
            unknown_flag_count=18,
        )
        self.assertTrue(any("one free AIS feed" in warning for warning in warnings))

    def test_build_coverage_warnings_returns_baseline_notice_for_healthy_case(self):
        warnings = build_coverage_warnings(
            active_vessels=18000,
            active_source_count=3,
            top_source_share=0.55,
            unique_flag_countries=140,
            unknown_flag_count=5,
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("not complete worldwide", warnings[0])


if __name__ == "__main__":
    unittest.main()
