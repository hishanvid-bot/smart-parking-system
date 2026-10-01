"""Distance and travel-time maths."""

import math

EARTH_RADIUS_KM = 6371.0
AVG_SPEED_KMPH = 30  # free-flow city driving speed


def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line (great-circle) distance between two points, in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def travel_minutes(distance_km, traffic):
    """Estimated drive time. `traffic` runs 1 (light) to 10 (heavy).

    Heavy traffic slows the trip: at traffic 10 the drive takes twice as long.
    """
    return distance_km / AVG_SPEED_KMPH * 60 * (1 + traffic / 10)
