"""Discovery: turn a destination into a list of usable nearby lots."""

from .geo import haversine_km, travel_minutes
from .lots import Candidate, is_open


def resolve_destination(destinations, text):
    """Turn what the user typed into (lat, lon).

    Accepts a known place name ('Phoenix Marketcity') or coordinates ('12.99,80.21').
    """
    key = text.strip().lower()
    if key in destinations:
        return destinations[key]
    parts = key.split(",")
    if len(parts) == 2:
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except ValueError:
            lat = lon = None
        if lat is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    known = ", ".join(name.title() for name in destinations)
    raise ValueError(f"Unknown destination '{text}'. Try one of: {known} (or 'lat,lon').")


def discover(lots, point, now_minutes, radius_km=2.0):
    """Find lots near `point` that are within range, open, and not full.

    Returns a list of Candidate objects (not scored yet).
    """
    lat, lon = point
    found = []
    for lot in lots:
        distance = haversine_km(lat, lon, lot.lat, lot.lon)
        if distance > radius_km:
            continue
        if lot.free_spaces == 0 or not is_open(lot.hours, now_minutes):
            continue
        found.append(Candidate(lot, distance, travel_minutes(distance, lot.traffic)))
    return found
