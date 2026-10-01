"""Preference-weighted scoring. Every weight is visible and easy to change."""

FACTORS = ("price", "traffic", "distance", "security", "availability", "time")

# How much each factor matters for each preference. Each row adds up to 1.0.
PREFERENCES = {
    "balanced":       {"price": 0.20, "traffic": 0.15, "distance": 0.20, "security": 0.15, "availability": 0.15, "time": 0.15},
    "low_cost":       {"price": 0.50, "traffic": 0.05, "distance": 0.10, "security": 0.05, "availability": 0.20, "time": 0.10},
    "less_traffic":   {"price": 0.10, "traffic": 0.45, "distance": 0.10, "security": 0.05, "availability": 0.10, "time": 0.20},
    "high_security":  {"price": 0.05, "traffic": 0.05, "distance": 0.10, "security": 0.55, "availability": 0.15, "time": 0.10},
    "short_distance": {"price": 0.05, "traffic": 0.10, "distance": 0.50, "security": 0.05, "availability": 0.10, "time": 0.20},
}


def _norm(value, low, high, higher_is_better):
    """Scale a value to 0..1 where 1 is always the best in the group."""
    if high == low:
        return 1.0
    x = (value - low) / (high - low)
    return x if higher_is_better else 1 - x


def score_candidates(candidates, preference="balanced"):
    """Give each candidate a 0-100 score and return them best first.

    Each factor is scaled to 0..1 (1 = best of the group), multiplied by its
    weight, and added up. `breakdown` holds the points each factor contributed.
    Scores compare lots within one search; they are not absolute grades.
    """
    if preference not in PREFERENCES:
        raise ValueError(f"Unknown preference '{preference}'. Choose from: {', '.join(PREFERENCES)}")
    if not candidates:
        return []
    weights = PREFERENCES[preference]

    def span(get):
        values = [get(c) for c in candidates]
        return min(values), max(values)

    price = span(lambda c: c.lot.price_per_hr)
    traffic = span(lambda c: c.lot.traffic)
    distance = span(lambda c: c.distance_km)
    security = span(lambda c: c.lot.security)
    time = span(lambda c: c.travel_min)

    for c in candidates:
        scaled = {
            "price": _norm(c.lot.price_per_hr, *price, False),
            "traffic": _norm(c.lot.traffic, *traffic, False),
            "distance": _norm(c.distance_km, *distance, False),
            "security": _norm(c.lot.security, *security, True),
            "availability": c.lot.free_spaces / c.lot.total_spaces,
            "time": _norm(c.travel_min, *time, False),
        }
        points = {f: 100 * weights[f] * scaled[f] for f in FACTORS}
        c.score = round(sum(points.values()), 1)
        c.breakdown = {f: round(p, 1) for f, p in points.items()}
    return sorted(candidates, key=lambda c: c.score, reverse=True)
