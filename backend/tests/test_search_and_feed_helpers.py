"""Unit tests for search helpers, flag utilities, and feed parser helpers."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.sources.global_fishing_watch import GlobalFishingWatchClient
from services.sources.kystverket import KystverketClient
from services.sources.noaa_ais import NOAAAISClient
from utils.flag_utils import get_flag_emoji, get_flag_from_mmsi
from utils.vessel_search import get_vessel_search_text, matches_vessel_query, normalize_vessel_query


async def _noop(_: dict) -> None:
    return None


class SearchAndFeedHelpersTestCase(unittest.TestCase):
    def test_vessel_search_helpers_match_name_identifiers_and_type_keywords(self):
        vessel = {
            "name": "Mercury Tide",
            "mmsi": 419123456,
            "call_sign": "VT1234",
            "imo": 9876543,
            "destination": "Singapore",
            "flag_country": "India",
            "vessel_type": 70,
        }

        self.assertEqual(normalize_vessel_query("  MERCURY  "), "mercury")
        haystack = get_vessel_search_text(vessel)
        self.assertIn("cargo ship", haystack)
        self.assertIn("merchant ship", haystack)
        self.assertTrue(matches_vessel_query(vessel, "mercury"))
        self.assertTrue(matches_vessel_query(vessel, "9876543"))
        self.assertTrue(matches_vessel_query(vessel, "merchant"))
        self.assertFalse(matches_vessel_query(vessel, "m"))

    def test_flag_helpers_cover_known_unknown_and_invalid_codes(self):
        self.assertEqual(get_flag_from_mmsi(419123456), ("India", "IN"))
        self.assertEqual(get_flag_from_mmsi(999123456), ("Unknown", "XX"))
        self.assertEqual(get_flag_emoji("IN"), "🇮🇳")
        self.assertEqual(get_flag_emoji(""), "🏳️")
        self.assertEqual(get_flag_emoji("IND"), "🏳️")

    def test_noaa_first_data_row_handles_valid_and_invalid_payloads(self):
        self.assertEqual(
            NOAAAISClient._first_data_row({"data": [{"v": "1.2"}]}),
            {"v": "1.2"},
        )
        self.assertIsNone(NOAAAISClient._first_data_row({"data": []}))
        self.assertIsNone(NOAAAISClient._first_data_row({"data": [None]}))
        self.assertIsNone(NOAAAISClient._first_data_row([]))

    def test_kystverket_helper_parsers_and_barentswatch_normalization(self):
        client = KystverketClient(_noop)

        self.assertEqual(client._as_float("12.5"), 12.5)
        self.assertIsNone(client._as_float("bad"))
        self.assertEqual(client._as_int("42"), 42)
        self.assertIsNone(client._as_int("bad"))
        self.assertEqual(client._as_text("  abc  "), "abc")
        self.assertIsNone(client._as_text(42))

        vessel = client._parse_barentswatch(
            {
                "mmsi": "257123456",
                "latitude": 60.0,
                "longitude": 5.0,
                "speedOverGround": "12.4",
                "courseOverGround": "180.0",
                "trueHeading": 180,
                "navigationalStatus": 5,
                "name": "  NORDIC STAR ",
                "shipType": 70,
            }
        )
        assert vessel is not None
        self.assertEqual(vessel["mmsi"], 257123456)
        self.assertEqual(vessel["name"], "NORDIC STAR")
        self.assertEqual(vessel["flag_country"], "Norway")
        self.assertEqual(vessel["vessel_type_name"], "Cargo ship")

        self.assertIsNone(client._parse_barentswatch({"mmsi": "bad"}))
        self.assertIsNone(client._parse_barentswatch({"mmsi": "257123456"}))

    def test_gfw_parser_prefers_registry_identity_and_falls_back_to_mid_flag(self):
        client = GlobalFishingWatchClient(_noop)

        vessel = client._parse_vessel(
            {
                "ssvid": "419123456",
                "combinedSourcesInfo": [
                    {"shipsname": "FISH MASTER", "imo": "1234567", "callsign": "VTAA"}
                ],
                "registryInfo": [
                    {"shipname": "REGISTRY NAME", "flag": "IN"}
                ],
            }
        )
        assert vessel is not None
        self.assertEqual(vessel["name"], "FISH MASTER")
        self.assertEqual(vessel["imo"], 1234567)
        self.assertEqual(vessel["call_sign"], "VTAA")
        self.assertEqual(vessel["flag_country"], "India")
        self.assertEqual(vessel["flag_code"], "IN")

        fallback = client._parse_vessel({"ssvid": "257123456"})
        assert fallback is not None
        self.assertEqual(fallback["flag_country"], "Norway")
        self.assertIsNone(client._parse_vessel({"ssvid": "bad"}))


if __name__ == "__main__":
    unittest.main()
