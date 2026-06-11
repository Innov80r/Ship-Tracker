"""
Shared helpers for matching vessel search queries.
"""

from utils.ais_codes import get_vessel_type_name

GENERIC_VESSEL_TERMS = (
    "ship",
    "ships",
    "vessel",
    "vessels",
    "boat",
    "boats",
    "sea",
    "marine",
    "maritime",
    "ocean",
)

TYPE_KEYWORDS = {
    30: ("fishing", "trawler", "trawlers"),
    31: ("towing", "tug", "tugboat", "tugboats"),
    32: ("towing", "tug", "tugboat", "tugboats"),
    33: ("dredger", "dredging"),
    34: ("diving", "support vessel", "offshore support"),
    35: ("military", "navy", "naval", "warship", "warships", "submarine", "submarines"),
    36: ("sailing", "sailboat", "sailboats", "yacht"),
    37: ("pleasure", "recreational", "yacht", "yachts"),
    40: ("high speed", "fast craft", "patrol craft"),
    50: ("pilot", "pilot boat"),
    51: ("sar", "search and rescue", "rescue"),
    52: ("tug", "tugboat", "harbor tug", "harbour tug"),
    53: ("port tender", "harbor service", "harbour service"),
    54: ("anti pollution", "pollution response"),
    55: ("law enforcement", "coast guard", "patrol", "police"),
    58: ("medical", "hospital ship"),
    60: ("passenger", "ferry", "cruise", "liner"),
    70: ("cargo", "freighter", "merchant", "merchant ship"),
    80: ("tanker", "oil tanker", "chemical tanker", "gas carrier"),
    90: ("service vessel",),
}


def normalize_vessel_query(query: str) -> str:
    """Normalize a free-text vessel search query."""
    return query.strip().casefold()


def _keywords_for_type(code: object) -> tuple[str, ...]:
    if not isinstance(code, int):
        return ()
    if code in TYPE_KEYWORDS:
        return TYPE_KEYWORDS[code]
    return TYPE_KEYWORDS.get((code // 10) * 10, ())


def get_vessel_search_text(vessel: dict) -> str:
    """Build a normalized search haystack for one vessel."""
    vessel_type = vessel.get("vessel_type")
    vessel_type_name = vessel.get("vessel_type_name")

    if not vessel_type_name and isinstance(vessel_type, int):
        vessel_type_name = get_vessel_type_name(vessel_type)

    parts = [
        vessel.get("name"),
        vessel.get("mmsi"),
        vessel.get("call_sign"),
        vessel.get("imo"),
        vessel.get("destination"),
        vessel.get("flag_country"),
        vessel_type_name,
        *GENERIC_VESSEL_TERMS,
        *_keywords_for_type(vessel_type),
    ]

    return " ".join(str(value) for value in parts if value not in (None, "")).casefold()


def matches_vessel_query(vessel: dict, query: str) -> bool:
    """Return True when a vessel should match the given free-text query."""
    normalized_query = normalize_vessel_query(query)
    if len(normalized_query) < 2:
        return False
    return normalized_query in get_vessel_search_text(vessel)
