"""
AIS code lookups — vessel type names, navigation status text.
Reference: ITU-R M.1371-5  §  Table 53 (ship type) and Table 15.2 (nav status).
"""

# AIS ship type code → human-readable name
VESSEL_TYPES = {
    0: "Not available",
    20: "Wing in ground",
    21: "Wing in ground - Hazardous A",
    22: "Wing in ground - Hazardous B",
    23: "Wing in ground - Hazardous C",
    24: "Wing in ground - Hazardous D",
    29: "Wing in ground - No info",
    30: "Fishing vessel",
    31: "Towing",
    32: "Towing (large)",
    33: "Dredger",
    34: "Diving support vessel",
    35: "Military warship",
    36: "Sailing vessel",
    37: "Pleasure craft",
    40: "High speed craft",
    41: "High speed craft - Hazardous A",
    42: "High speed craft - Hazardous B",
    43: "High speed craft - Hazardous C",
    44: "High speed craft - Hazardous D",
    49: "High speed craft - No info",
    50: "Pilot boat",
    51: "Search and rescue vessel",
    52: "Tugboat",
    53: "Port tender",
    54: "Anti-pollution vessel",
    55: "Law enforcement",
    56: "Spare - Local 1",
    57: "Spare - Local 2",
    58: "Medical transport",
    59: "Resolution No.18 ship",
    60: "Passenger ship",
    61: "Passenger ship - Hazardous A",
    62: "Passenger ship - Hazardous B",
    63: "Passenger ship - Hazardous C",
    64: "Passenger ship - Hazardous D",
    69: "Passenger ship - No info",
    70: "Cargo ship",
    71: "Cargo ship - Hazardous A",
    72: "Cargo ship - Hazardous B",
    73: "Cargo ship - Hazardous C",
    74: "Cargo ship - Hazardous D",
    79: "Cargo ship - No info",
    80: "Tanker",
    81: "Tanker - Hazardous A",
    82: "Tanker - Hazardous B",
    83: "Tanker - Hazardous C",
    84: "Tanker - Hazardous D",
    89: "Tanker - No info",
    90: "Other",
    91: "Other - Hazardous A",
    92: "Other - Hazardous B",
    93: "Other - Hazardous C",
    94: "Other - Hazardous D",
    99: "Other - No info",
}

# Navigation status code → text
NAV_STATUS = {
    0: "Under way using engine",
    1: "At anchor",
    2: "Not under command",
    3: "Restricted manoeuvrability",
    4: "Constrained by draught",
    5: "Moored",
    6: "Aground",
    7: "Engaged in fishing",
    8: "Under way sailing",
    9: "Reserved (HSC)",
    10: "Reserved (WIG)",
    11: "Power-driven vessel towing astern",
    12: "Power-driven vessel pushing ahead",
    13: "Reserved",
    14: "AIS-SART / MOB / EPIRB",
    15: "Default / Not defined",
}

# Broader vessel category for frontend icon/color mapping
VESSEL_CATEGORY_MAP = {
    30: "fishing",
    31: "tug",
    32: "tug",
    33: "dredger",
    34: "diving_support",
    35: "military",
    36: "sailing",
    37: "pleasure",
    40: "high_speed",
    41: "high_speed",
    42: "high_speed",
    43: "high_speed",
    44: "high_speed",
    49: "high_speed",
    50: "pilot",
    51: "sar",
    52: "tug",
    53: "port_tender",
    54: "anti_pollution",
    55: "law_enforcement",
    58: "medical",
    60: "passenger",
    61: "passenger",
    62: "passenger",
    63: "passenger",
    64: "passenger",
    69: "passenger",
    70: "cargo",
    71: "cargo",
    72: "cargo",
    73: "cargo",
    74: "cargo",
    79: "cargo",
    80: "tanker",
    81: "tanker",
    82: "tanker",
    83: "tanker",
    84: "tanker",
    89: "tanker",
    90: "other",
    91: "other",
    92: "other",
    93: "other",
    94: "other",
    99: "other",
}


def get_vessel_type_name(code: int) -> str:
    """Return human-readable vessel type name from AIS type code."""
    return VESSEL_TYPES.get(code, f"Unknown ({code})")


def get_nav_status_text(code: int) -> str:
    """Return navigation status text from AIS nav status code."""
    return NAV_STATUS.get(code, f"Unknown ({code})")


def get_vessel_category(code: int) -> str:
    """Return broad vessel category for frontend rendering."""
    return VESSEL_CATEGORY_MAP.get(code, "other")
