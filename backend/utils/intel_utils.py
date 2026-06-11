"""
Shared intelligence helper functions.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any


EARTH_RADIUS_NM = 3440.065
MILITARY_KEYWORDS = {
    "military",
    "navy",
    "naval",
    "warship",
    "submarine",
    "patrol",
    "coast guard",
    "coastguard",
    "law enforcement",
    "destroyer",
    "frigate",
}
COMMERCIAL_KEYWORDS = {
    "cargo",
    "container",
    "bulk",
    "tanker",
    "lng",
    "lpg",
    "fishing",
    "passenger",
    "ro-ro",
}
MILITARY_TYPE_CODES = {35, 55}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(*parts: Any) -> str:
    return " ".join(str(part or "").strip().lower() for part in parts if part is not None)


def get_vessel_category(vessel: dict) -> str:
    vessel_type = vessel.get("vessel_type")
    vessel_type_name = _normalize_text(vessel.get("vessel_type_name"), vessel.get("name"))
    if vessel_type in MILITARY_TYPE_CODES or any(keyword in vessel_type_name for keyword in MILITARY_KEYWORDS):
        return "military"
    if any(keyword in vessel_type_name for keyword in COMMERCIAL_KEYWORDS):
        return "commercial"
    if "fishing" in vessel_type_name:
        return "fishing"
    if "passenger" in vessel_type_name or "cruise" in vessel_type_name:
        return "passenger"
    if "tanker" in vessel_type_name:
        return "tanker"
    if "cargo" in vessel_type_name or "container" in vessel_type_name:
        return "cargo"
    return "general"


def is_military_vessel(vessel: dict) -> bool:
    return get_vessel_category(vessel) == "military"


def is_commercial_vessel(vessel: dict) -> bool:
    return get_vessel_category(vessel) in {"commercial", "cargo", "tanker", "passenger", "fishing"}


def _to_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def get_last_seen_minutes(vessel: dict, now: datetime | None = None) -> float | None:
    last_seen = _to_datetime(vessel.get("last_updated"))
    if not last_seen:
        return None
    current_time = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    delta = current_time - last_seen
    return max(0.0, delta.total_seconds() / 60.0)


def is_dark_vessel(vessel: dict, threshold_minutes: float = 60.0, now: datetime | None = None) -> bool:
    last_seen_minutes = get_last_seen_minutes(vessel, now=now)
    if last_seen_minutes is None:
        return False
    return last_seen_minutes >= threshold_minutes and bool(vessel.get("latitude") and vessel.get("longitude"))


def get_weather_impact_score(vessel: dict, weather_point: dict | None = None) -> float:
    if not weather_point:
        return 0.0
    wind_speed = to_float(weather_point.get("wind_speed"), 0.0) or 0.0
    wave_height = to_float(weather_point.get("wave_height"), 0.0) or 0.0
    current_speed = to_float(weather_point.get("current_speed"), 0.0) or 0.0
    vessel_speed = to_float(vessel.get("speed"), 0.0) or 0.0
    impact = wind_speed * 0.8 + wave_height * 12.0 + current_speed * 8.0
    if vessel_speed < 2.0:
        impact *= 0.75
    return round(clamp(impact, 0.0, 100.0), 2)


def get_risk_assessment(
    vessel: dict,
    *,
    weather_point: dict | None = None,
    restricted_zone_hits: int = 0,
    ais_gap_minutes: float | None = None,
) -> dict:
    speed = to_float(vessel.get("speed"), 0.0) or 0.0
    draught = to_float(vessel.get("draught"), 0.0) or 0.0
    last_seen_minutes = ais_gap_minutes
    if last_seen_minutes is None:
        last_seen_minutes = get_last_seen_minutes(vessel) or 0.0

    factors: list[dict[str, Any]] = []
    score = 0.0

    if speed >= 22.0:
        score += 18.0
        factors.append({"factor": "high_speed", "weight": 18})
    elif speed >= 15.0:
        score += 10.0
        factors.append({"factor": "elevated_speed", "weight": 10})

    if last_seen_minutes >= 180.0:
        score += 28.0
        factors.append({"factor": "long_ais_gap", "weight": 28})
    elif last_seen_minutes >= 60.0:
        score += 16.0
        factors.append({"factor": "ais_gap", "weight": 16})

    if is_military_vessel(vessel):
        score += 14.0
        factors.append({"factor": "military_presence", "weight": 14})

    if draught >= 12.0:
        score += 8.0
        factors.append({"factor": "deep_draught", "weight": 8})

    if restricted_zone_hits > 0:
        zone_weight = min(20.0, restricted_zone_hits * 8.0)
        score += zone_weight
        factors.append({"factor": "restricted_zone", "weight": zone_weight})

    weather_impact = get_weather_impact_score(vessel, weather_point)
    if weather_impact >= 70.0:
        score += 18.0
        factors.append({"factor": "severe_weather", "weight": 18})
    elif weather_impact >= 40.0:
        score += 10.0
        factors.append({"factor": "weather_pressure", "weight": 10})

    if not vessel.get("destination") and is_commercial_vessel(vessel):
        score += 8.0
        factors.append({"factor": "missing_destination", "weight": 8})

    normalized_score = round(clamp(score, 0.0, 100.0), 2)
    if normalized_score >= 75:
        level = "critical"
    elif normalized_score >= 50:
        level = "high"
    elif normalized_score >= 25:
        level = "medium"
    else:
        level = "low"

    return {
        "score": normalized_score,
        "level": level,
        "weather_impact_score": weather_impact,
        "last_seen_minutes": round(last_seen_minutes, 2),
        "category": get_vessel_category(vessel),
        "factors": factors,
    }


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    return EARTH_RADIUS_NM * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def destination_point(lat: float, lon: float, bearing_degrees: float, distance_nm: float) -> tuple[float, float]:
    angular_distance = distance_nm / EARTH_RADIUS_NM
    bearing = math.radians(bearing_degrees)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    lon_deg = ((math.degrees(lon2) + 540.0) % 360.0) - 180.0
    return round(math.degrees(lat2), 6), round(lon_deg, 6)


def get_projected_route(vessel: dict, hours: int = 6, step_minutes: int = 30) -> list[dict]:
    lat = to_float(vessel.get("latitude"))
    lon = to_float(vessel.get("longitude"))
    speed = max(0.0, to_float(vessel.get("speed"), 0.0) or 0.0)
    heading = to_float(vessel.get("heading"))
    if heading is None:
        heading = to_float(vessel.get("course"), 0.0) or 0.0
    if lat is None or lon is None:
        return []

    route = []
    current_lat = lat
    current_lon = lon
    total_steps = max(1, math.ceil((hours * 60) / step_minutes))
    for step in range(1, total_steps + 1):
        distance_nm = speed * (step_minutes / 60.0)
        current_lat, current_lon = destination_point(current_lat, current_lon, heading, distance_nm)
        route.append(
            {
                "step": step,
                "minutes_ahead": step * step_minutes,
                "latitude": current_lat,
                "longitude": current_lon,
                "speed": speed,
                "heading": heading,
            }
        )
    return route


def build_playback_events(history_points: list[dict]) -> list[dict]:
    if not history_points:
        return []

    points = sorted(history_points, key=lambda point: _to_datetime(point.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))
    events = []
    previous = None
    for point in points:
        timestamp = _to_datetime(point.get("timestamp"))
        if not timestamp:
            continue
        event_type = None
        details: dict[str, Any] = {}

        if previous is None:
            event_type = "track_start"
        else:
            prev_timestamp = _to_datetime(previous.get("timestamp"))
            prev_speed = to_float(previous.get("speed"), 0.0) or 0.0
            speed = to_float(point.get("speed"), 0.0) or 0.0
            if prev_timestamp:
                gap_minutes = (timestamp - prev_timestamp).total_seconds() / 60.0
                if gap_minutes >= 60.0:
                    event_type = "ais_gap"
                    details["gap_minutes"] = round(gap_minutes, 2)
            if event_type is None and abs(speed - prev_speed) >= 10.0:
                event_type = "speed_change"
                details["from_speed"] = prev_speed
                details["to_speed"] = speed
            prev_heading = to_float(previous.get("heading"), to_float(previous.get("course"), 0.0) or 0.0) or 0.0
            heading = to_float(point.get("heading"), to_float(point.get("course"), 0.0) or 0.0) or 0.0
            turn_amount = abs(((heading - prev_heading + 180.0) % 360.0) - 180.0)
            if event_type is None and turn_amount >= 45.0:
                event_type = "course_change"
                details["turn_degrees"] = round(turn_amount, 2)

        if event_type:
            events.append(
                {
                    "type": event_type,
                    "timestamp": timestamp.isoformat(),
                    "latitude": point.get("latitude"),
                    "longitude": point.get("longitude"),
                    "details": details,
                }
            )
        previous = point

    if events:
        last_point = points[-1]
        last_timestamp = _to_datetime(last_point.get("timestamp"))
        if last_timestamp:
            events.append(
                {
                    "type": "track_end",
                    "timestamp": last_timestamp.isoformat(),
                    "latitude": last_point.get("latitude"),
                    "longitude": last_point.get("longitude"),
                    "details": {},
                }
            )
    return events


def get_traffic_corridors(vessels: list[dict], min_vessels: int = 3, precision: float = 2.5) -> list[dict]:
    corridor_map: dict[tuple[float, float], dict[str, Any]] = {}
    for vessel in vessels:
        lat = to_float(vessel.get("latitude"))
        lon = to_float(vessel.get("longitude"))
        if lat is None or lon is None:
            continue
        cell = (
            round(lat / precision) * precision,
            round(lon / precision) * precision,
        )
        bucket = corridor_map.setdefault(
            cell,
            {
                "latitude": cell[0],
                "longitude": cell[1],
                "vessel_count": 0,
                "categories": {},
            },
        )
        bucket["vessel_count"] += 1
        category = get_vessel_category(vessel)
        bucket["categories"][category] = bucket["categories"].get(category, 0) + 1

    corridors = [value for value in corridor_map.values() if value["vessel_count"] >= min_vessels]
    corridors.sort(key=lambda item: item["vessel_count"], reverse=True)
    return corridors


def get_port_congestion(ports: list[dict], vessels: list[dict], radius_nm: float = 12.0) -> list[dict]:
    congestion = []
    for port in ports:
        port_lat = to_float(port.get("latitude"))
        port_lon = to_float(port.get("longitude"))
        if port_lat is None or port_lon is None:
            continue

        nearby = []
        queued = 0
        arrivals = 0
        for vessel in vessels:
            vessel_lat = to_float(vessel.get("latitude"))
            vessel_lon = to_float(vessel.get("longitude"))
            if vessel_lat is None or vessel_lon is None:
                continue
            distance = haversine_nm(port_lat, port_lon, vessel_lat, vessel_lon)
            if distance > radius_nm:
                continue
            nearby.append(vessel)
            speed = to_float(vessel.get("speed"), 0.0) or 0.0
            if speed < 1.5:
                queued += 1
            if speed >= 6.0:
                arrivals += 1

        if not nearby:
            continue

        congestion_score = clamp(len(nearby) * 5.0 + queued * 8.0 + arrivals * 3.0, 0.0, 100.0)
        congestion.append(
            {
                "port_id": port.get("id"),
                "port_name": port.get("name"),
                "country": port.get("country"),
                "latitude": port_lat,
                "longitude": port_lon,
                "nearby_vessels": len(nearby),
                "queued_vessels": queued,
                "arrivals_per_hour": arrivals,
                "congestion_score": round(congestion_score, 2),
            }
        )

    congestion.sort(key=lambda item: item["congestion_score"], reverse=True)
    return congestion


def nearest_point(latitude: float, longitude: float, points: list[dict]) -> dict | None:
    best_point = None
    best_distance = None
    for point in points:
        point_lat = to_float(point.get("lat"))
        point_lon = to_float(point.get("lon"))
        if point_lat is None or point_lon is None:
            continue
        distance = haversine_nm(latitude, longitude, point_lat, point_lon)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_point = point
    return best_point


def destination_eta_hours(
    vessel: dict,
    destination_lat: float | None,
    destination_lon: float | None,
) -> float | None:
    speed = to_float(vessel.get("speed"), 0.0) or 0.0
    origin_lat = to_float(vessel.get("latitude"))
    origin_lon = to_float(vessel.get("longitude"))
    if speed <= 0.1 or origin_lat is None or origin_lon is None:
        return None
    if destination_lat is None or destination_lon is None:
        return None
    distance = haversine_nm(origin_lat, origin_lon, destination_lat, destination_lon)
    return round(distance / speed, 2)
