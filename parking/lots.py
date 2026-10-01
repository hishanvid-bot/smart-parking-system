"""Parking lot data: loading, checking, and opening hours."""

import json
import os
from dataclasses import dataclass, field
from typing import Dict

DATA_FILE = os.path.join(os.path.dirname(__file__), "lots.json")


@dataclass
class Lot:
    name: str
    lat: float
    lon: float
    price_per_hr: float   # rupees per hour
    total_spaces: int
    free_spaces: int
    traffic: int          # 1 (light) .. 10 (heavy) around the lot
    security: int         # 1 (low) .. 5 (high)
    hours: str            # "24x7" or "HH:MM-HH:MM"


@dataclass
class Candidate:
    """A lot found for a destination, plus its numbers and score."""
    lot: Lot
    distance_km: float
    travel_min: float
    score: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)  # points per factor


def parse_clock(text):
    """'09:30' -> 570 minutes since midnight. '24:00' is allowed (end of day)."""
    try:
        hh, mm = text.strip().split(":")
        hh, mm = int(hh), int(mm)
    except ValueError:
        raise ValueError(f"Bad time '{text}'. Use HH:MM, for example 18:30.")
    if not (0 <= hh <= 24 and 0 <= mm <= 59) or (hh == 24 and mm != 0):
        raise ValueError(f"Bad time '{text}'. Use HH:MM, for example 18:30.")
    return hh * 60 + mm


def is_open(hours, now_minutes):
    """Is a lot with these opening hours open at `now_minutes` since midnight?"""
    if hours.strip().lower() == "24x7":
        return True
    start_text, end_text = hours.split("-")
    start, end = parse_clock(start_text), parse_clock(end_text)
    if start < end:
        return start <= now_minutes < end
    return now_minutes >= start or now_minutes < end  # open past midnight


def _check_lot(lot):
    name = lot.name
    if lot.total_spaces <= 0:
        raise ValueError(f"{name}: total_spaces must be above 0")
    if not 0 <= lot.free_spaces <= lot.total_spaces:
        raise ValueError(f"{name}: free_spaces must be between 0 and total_spaces")
    if lot.price_per_hr < 0:
        raise ValueError(f"{name}: price_per_hr cannot be negative")
    if not 1 <= lot.traffic <= 10:
        raise ValueError(f"{name}: traffic must be 1-10")
    if not 1 <= lot.security <= 5:
        raise ValueError(f"{name}: security must be 1-5")
    is_open(lot.hours, 0)  # raises if the hours text is malformed


def load_data(path=DATA_FILE):
    """Read lots.json. Returns (destinations, lots) after checking every lot."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    destinations = {k.lower(): (v["lat"], v["lon"]) for k, v in raw["destinations"].items()}
    lots = [Lot(**item) for item in raw["lots"]]
    for lot in lots:
        _check_lot(lot)
    return destinations, lots
