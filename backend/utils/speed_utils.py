"""
Speed conversion utilities.
"""


def knots_to_kmh(knots: float) -> float:
    """Convert speed from knots to km/h."""
    return knots * 1.852


def knots_to_mph(knots: float) -> float:
    """Convert speed from knots to mph."""
    return knots * 1.15078


def kmh_to_knots(kmh: float) -> float:
    """Convert speed from km/h to knots."""
    return kmh / 1.852


def is_speed_anomaly(current_speed: float, previous_speed: float, threshold: float = 25.0) -> bool:
    """
    Detect a speed anomaly — e.g. sudden stop from high speed or impossible spike.
    threshold: max change in knots between consecutive updates.
    """
    if current_speed is None or previous_speed is None:
        return False
    return abs(current_speed - previous_speed) > threshold


def speed_category(speed: float) -> str:
    """Categorize vessel speed for analytics."""
    if speed is None or speed < 0:
        return "unknown"
    if speed < 0.5:
        return "stationary"
    if speed < 5:
        return "slow"
    if speed < 15:
        return "moderate"
    if speed < 25:
        return "fast"
    return "very_fast"
