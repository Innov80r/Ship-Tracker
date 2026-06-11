"""Unit tests for country normalization and port parsing helpers."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.port_service import PortService
from utils.country_utils import LandCountryResolver, list_country_catalog, normalize_country_identity


class CountryAndPortUtilsTestCase(unittest.TestCase):
    def test_normalize_country_identity_expands_common_iso_codes(self):
        country, code = normalize_country_identity("AE", "AE")
        self.assertEqual(country, "United Arab Emirates")
        self.assertEqual(code, "AE")

    def test_port_parser_keeps_zero_coordinates_and_prefixes_osm_type(self):
        service = PortService()
        parsed = service._parse_element({
            "type": "node",
            "id": 123,
            "lat": 0.0,
            "lon": 0.0,
            "tags": {
                "name": "Null Island Anchorage",
                "addr:country": "US",
                "seamark:type": "anchorage",
            },
        })

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["osm_id"], "node/123")
        self.assertEqual(parsed["country"], "United States")
        self.assertEqual(parsed["latitude"], 0.0)
        self.assertEqual(parsed["longitude"], 0.0)

    def test_country_catalog_includes_common_aliases(self):
        catalog = list_country_catalog()
        united_states = next((country for country in catalog if country["name"] == "United States"), None)

        self.assertIsNotNone(united_states)
        assert united_states is not None
        self.assertEqual(united_states["code"], "US")
        self.assertIn("usa", united_states["aliases"])
        self.assertIn("united states of america", united_states["aliases"])

    def test_port_parser_prefers_eez_resolution_for_non_country_territory_labels(self):
        service = PortService()

        class _Resolver:
            @staticmethod
            def resolve(_latitude, _longitude):
                return "India"

        service.country_resolver = _Resolver()
        parsed = service._parse_element({
            "type": "node",
            "id": 456,
            "lat": 11.0,
            "lon": 92.7,
            "tags": {
                "name": "Port Blair",
                "country": "Andaman And Nicobar",
                "seamark:type": "harbour",
            },
        })

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["country"], "India")

    def test_rebuild_only_happens_for_complete_fetches(self):
        self.assertFalse(
            PortService.should_rebuild_catalog(
                requested=True,
                fetched_count=1506,
                failed_shards=5,
            )
        )
        self.assertTrue(
            PortService.should_rebuild_catalog(
                requested=True,
                fetched_count=PortService.MINIMUM_EXPECTED_PORTS,
                failed_shards=0,
            )
        )

    def test_land_country_resolver_supports_name_property_geojson(self):
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Paraguay", "ISO3166-1-Alpha-2": "PY"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-58.5, -27.5],
                            [-54.5, -27.5],
                            [-54.5, -19.0],
                            [-58.5, -19.0],
                            [-58.5, -27.5],
                        ]],
                    },
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            geojson_path = Path(tmpdir) / "countries.geojson"
            geojson_path.write_text(json.dumps(payload), encoding="utf-8")
            resolver = LandCountryResolver(geojson_path)
            self.assertEqual(resolver.resolve(-25.28, -57.64), "Paraguay")

    def test_port_parser_falls_back_to_land_country_resolution(self):
        service = PortService()

        class _NoEEZResolver:
            @staticmethod
            def resolve(_latitude, _longitude):
                return None

        class _LandResolver:
            @staticmethod
            def resolve(_latitude, _longitude):
                return "Paraguay"

        service.country_resolver = _NoEEZResolver()
        service.land_country_resolver = _LandResolver()
        parsed = service._parse_element({
            "type": "node",
            "id": 789,
            "lat": -25.28,
            "lon": -57.64,
            "tags": {
                "name": "Asuncion Port",
                "seamark:type": "harbour",
            },
        })

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["country"], "Paraguay")


if __name__ == "__main__":
    unittest.main()
