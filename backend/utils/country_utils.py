"""Country normalization helpers for vessel and port metadata."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.prepared import prep

from utils.flag_utils import MID_TABLE


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


COUNTRY_NAME_OVERRIDES = {
    "AE": "United Arab Emirates",
    "BA": "Bosnia and Herzegovina",
    "CI": "Ivory Coast",
    "CD": "Democratic Republic of the Congo",
    "CG": "Republic of the Congo",
    "CZ": "Czech Republic",
    "FK": "Falkland Islands",
    "FM": "Micronesia",
    "GB": "United Kingdom",
    "IR": "Iran",
    "KP": "North Korea",
    "KR": "South Korea",
    "LA": "Laos",
    "MD": "Moldova",
    "MK": "North Macedonia",
    "PS": "Palestine",
    "RE": "Reunion",
    "RU": "Russia",
    "ST": "Sao Tome and Principe",
    "SY": "Syria",
    "TF": "French Southern Territories",
    "TW": "Taiwan",
    "TZ": "Tanzania",
    "US": "United States",
    "VA": "Vatican City",
    "VE": "Venezuela",
    "VN": "Vietnam",
}

ISO2_TO_COUNTRY = {
    iso.upper(): COUNTRY_NAME_OVERRIDES.get(iso.upper(), country)
    for country, iso in {entry for entry in MID_TABLE.values() if entry[1] != "XX"}
}

ALIAS_TO_COUNTRY = {
    "uae": "United Arab Emirates",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "usa": "United States",
    "united states of america": "United States",
    "cote d'ivoire": "Ivory Coast",
    "cote d’ivoire": "Ivory Coast",
    "cote divoire": "Ivory Coast",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "dr congo": "Democratic Republic of the Congo",
    "congo kinshasa": "Democratic Republic of the Congo",
    "congo brazzaville": "Republic of the Congo",
    "korea, south": "South Korea",
    "korea, north": "North Korea",
    "russian federation": "Russia",
    "viet nam": "Vietnam",
}

for iso_code, country_name in ISO2_TO_COUNTRY.items():
    ALIAS_TO_COUNTRY[_normalize_text(country_name)] = country_name
    ALIAS_TO_COUNTRY[_normalize_text(iso_code)] = country_name

COUNTRY_TO_ISO2 = {
    _normalize_text(country_name): iso_code
    for iso_code, country_name in ISO2_TO_COUNTRY.items()
}

COUNTRY_TO_ISO2.update({
    _normalize_text(alias): COUNTRY_TO_ISO2[_normalize_text(country_name)]
    for alias, country_name in ALIAS_TO_COUNTRY.items()
    if _normalize_text(country_name) in COUNTRY_TO_ISO2
})


def normalize_country_name(value: str | None) -> str | None:
    """Return a human-readable country name from an ISO code or alias."""
    normalized = _normalize_text(value)
    if not normalized:
        return None

    if len(normalized) == 2 and normalized.upper() in ISO2_TO_COUNTRY:
        return ISO2_TO_COUNTRY[normalized.upper()]

    if normalized in ALIAS_TO_COUNTRY:
        return ALIAS_TO_COUNTRY[normalized]

    return " ".join(part.capitalize() for part in normalized.split())


def normalize_country_code(value: str | None) -> str | None:
    """Return an ISO alpha-2 code when one is known."""
    normalized = _normalize_text(value)
    if not normalized:
        return None

    if len(normalized) == 2 and normalized.upper() in ISO2_TO_COUNTRY:
        return normalized.upper()

    return COUNTRY_TO_ISO2.get(normalized)


def normalize_country_identity(
    country: str | None = None,
    country_code: str | None = None,
) -> tuple[str | None, str | None]:
    """Normalize a country label and alpha-2 code together."""
    normalized_name = normalize_country_name(country) or normalize_country_name(country_code)
    normalized_code = normalize_country_code(country_code) or normalize_country_code(country)

    if normalized_name is None and normalized_code is not None:
        normalized_name = ISO2_TO_COUNTRY.get(normalized_code)
    if normalized_code is None and normalized_name is not None:
        normalized_code = normalize_country_code(normalized_name)

    return normalized_name, normalized_code


@lru_cache(maxsize=1)
def list_country_catalog() -> list[dict]:
    """Return a stable catalog of normalized country names and aliases."""
    catalog: dict[str, dict] = {}

    for iso_code, country_name in ISO2_TO_COUNTRY.items():
        key = _normalize_text(country_name)
        catalog[key] = {
            "name": country_name,
            "code": iso_code,
            "aliases": {key, _normalize_text(iso_code)},
        }

    for alias, country_name in ALIAS_TO_COUNTRY.items():
        canonical_name = normalize_country_name(country_name) or country_name
        key = _normalize_text(canonical_name)
        entry = catalog.setdefault(
            key,
            {
                "name": canonical_name,
                "code": normalize_country_code(canonical_name),
                "aliases": {key},
            },
        )
        entry["aliases"].add(_normalize_text(alias))

    return [
        {
            "name": entry["name"],
            "code": entry["code"],
            "aliases": sorted(alias for alias in entry["aliases"] if alias),
        }
        for entry in sorted(catalog.values(), key=lambda item: item["name"])
    ]


def _country_name_from_properties(properties: dict) -> str | None:
    territory = str(properties.get("territory1") or "").strip()
    sovereign = str(properties.get("sovereign1") or "").strip()
    geoname = str(properties.get("geoname") or "").strip()
    common_name = str(
        properties.get("name")
        or properties.get("NAME")
        or properties.get("admin")
        or properties.get("ADMIN")
        or ""
    ).strip()
    if territory and sovereign and _normalize_text(territory) != _normalize_text(sovereign):
        return territory
    return territory or sovereign or geoname or common_name or None


class PolygonCountryResolver:
    """Resolve countries from a local polygon GeoJSON dataset."""

    def __init__(
        self,
        geojson_path: Path,
        *,
        default_nearest_tolerance_degrees: float = 0.0,
    ):
        self.geojson_path = geojson_path
        self.default_nearest_tolerance_degrees = default_nearest_tolerance_degrees
        self._regions = self._load_regions()

    def _load_regions(self) -> list[dict]:
        if not self.geojson_path.exists():
            return []

        payload = json.loads(self.geojson_path.read_text(encoding="utf-8"))
        regions = []
        for feature in payload.get("features", []):
            geometry = feature.get("geometry")
            country_name = _country_name_from_properties(feature.get("properties") or {})
            if not geometry or not country_name:
                continue

            polygon = shape(geometry)
            if polygon.is_empty:
                continue

            min_lon, min_lat, max_lon, max_lat = polygon.bounds
            regions.append({
                "country": normalize_country_name(country_name) or country_name,
                "bounds": (min_lat, min_lon, max_lat, max_lon),
                "polygon": polygon,
                "geometry": prep(polygon),
            })
        return regions

    def resolve(
        self,
        latitude: float | None,
        longitude: float | None,
        *,
        nearest_tolerance_degrees: float | None = None,
    ) -> str | None:
        if latitude is None or longitude is None or not self._regions:
            return None

        tolerance = (
            self.default_nearest_tolerance_degrees
            if nearest_tolerance_degrees is None
            else nearest_tolerance_degrees
        )
        point = Point(longitude, latitude)
        nearest_country = None
        nearest_distance = None
        for region in self._regions:
            min_lat, min_lon, max_lat, max_lon = region["bounds"]
            if latitude < min_lat or latitude > max_lat or longitude < min_lon or longitude > max_lon:
                if (
                    latitude < min_lat - tolerance
                    or latitude > max_lat + tolerance
                    or longitude < min_lon - tolerance
                    or longitude > max_lon + tolerance
                ):
                    continue
            if region["geometry"].intersects(point):
                return region["country"]

            distance = region["polygon"].distance(point)
            if distance <= tolerance and (
                nearest_distance is None or distance < nearest_distance
            ):
                nearest_country = region["country"]
                nearest_distance = distance
        return nearest_country


class EEZCountryResolver(PolygonCountryResolver):
    """Resolve a coastal country from the bundled EEZ dataset."""

    def __init__(self, geojson_path: Path | None = None):
        default_path = Path(__file__).resolve().parent.parent / "static" / "eez_boundaries.geojson"
        super().__init__(
            geojson_path or default_path,
            default_nearest_tolerance_degrees=1.5,
        )


class LandCountryResolver(PolygonCountryResolver):
    """Resolve a sovereign country from the bundled land-boundary dataset."""

    def __init__(self, geojson_path: Path | None = None):
        default_path = Path(__file__).resolve().parent.parent / "static" / "countries.geojson"
        super().__init__(
            geojson_path or default_path,
            default_nearest_tolerance_degrees=0.25,
        )


@lru_cache(maxsize=1)
def get_eez_country_resolver() -> EEZCountryResolver:
    """Return a cached EEZ-based country resolver."""
    return EEZCountryResolver()


@lru_cache(maxsize=1)
def get_land_country_resolver() -> LandCountryResolver:
    """Return a cached land-boundary country resolver."""
    return LandCountryResolver()
