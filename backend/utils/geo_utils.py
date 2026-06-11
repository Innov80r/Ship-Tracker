"""
Geospatial utility functions — distance, bearing, bounding boxes.
"""

import math
from typing import Tuple

# Earth radius in nautical miles
EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in nautical miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_NM * c


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial bearing from point 1 to point 2 in degrees."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    initial_bearing = math.atan2(x, y)
    return (math.degrees(initial_bearing) + 360) % 360


def point_in_bbox(lat: float, lon: float, bbox: Tuple[float, float, float, float]) -> bool:
    """Check if a point is within a bounding box (min_lat, min_lon, max_lat, max_lon)."""
    return bbox[0] <= lat <= bbox[2] and bbox[1] <= lon <= bbox[3]


def bbox_from_center(lat: float, lon: float, radius_nm: float) -> Tuple[float, float, float, float]:
    """Create a bounding box from a center point and radius in nautical miles."""
    dlat = radius_nm / 60.0
    dlon = radius_nm / (60.0 * math.cos(math.radians(lat)))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def cpa_tcpa(
    lat1: float, lon1: float, sog1: float, cog1: float,
    lat2: float, lon2: float, sog2: float, cog2: float,
) -> Tuple[float, float]:
    """
    Calculate Closest Point of Approach (CPA) distance in NM and
    Time to CPA (TCPA) in minutes between two moving vessels.
    Returns (cpa_nm, tcpa_minutes). Negative TCPA means vessels are diverging.
    """
    # Convert COG to radians
    cog1_r, cog2_r = math.radians(cog1), math.radians(cog2)

    # Velocity components in NM/min
    vx1 = (sog1 / 60.0) * math.sin(cog1_r)
    vy1 = (sog1 / 60.0) * math.cos(cog1_r)
    vx2 = (sog2 / 60.0) * math.sin(cog2_r)
    vy2 = (sog2 / 60.0) * math.cos(cog2_r)

    # Relative velocity
    dvx = vx2 - vx1
    dvy = vy2 - vy1

    # Relative position (approximate in NM using flat earth near point 1)
    dx = (lon2 - lon1) * 60.0 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 60.0

    # Relative speed squared
    dv2 = dvx ** 2 + dvy ** 2
    if dv2 < 1e-10:
        # Vessels moving at same speed and direction
        return haversine_nm(lat1, lon1, lat2, lon2), 0.0

    # TCPA
    tcpa = -(dx * dvx + dy * dvy) / dv2

    # CPA distance
    cpa_x = dx + dvx * tcpa
    cpa_y = dy + dvy * tcpa
    cpa_dist = math.sqrt(cpa_x ** 2 + cpa_y ** 2)

    return cpa_dist, tcpa


def is_valid_coordinate(lat: float, lon: float) -> bool:
    """Validate latitude and longitude ranges."""
    return -90 <= lat <= 90 and -180 <= lon <= 180
