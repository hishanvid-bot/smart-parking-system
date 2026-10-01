"""Run with:  python -m parking   (or:  python -m parking -d "Phoenix Marketcity")"""

import argparse
import datetime
import sys

from .finder import discover, resolve_destination
from .lots import load_data, parse_clock
from .scoring import PREFERENCES, score_candidates

BANNER = r"""
==============================================
         SMART  PARKING  FINDER
==============================================
"""

LABELS = {
    "price": "low price",
    "traffic": "light traffic",
    "distance": "short distance",
    "security": "high security",
    "availability": "good availability",
    "time": "short travel time",
}


def pretty(preference):
    return preference.replace("_", " ").title()


def render(destination, preference, ranked, top, say):
    """Print the ranked table and the best lot's details."""
    say("")
    say(f"Destination : {destination}")
    say(f"Preference  : {pretty(preference)}")
    say("-" * 78)
    say(f"{'#':<3}{'Lot':<34}{'Dist':>8}{'Time':>7}{'Rs/hr':>7}{'Free':>6}{'Score':>8}")
    say("-" * 78)
    for i, c in enumerate(ranked[:top], start=1):
        say(f"{i:<3}{c.lot.name:<34}{c.distance_km:>6.2f}km{c.travel_min:>5.0f}m"
            f"{c.lot.price_per_hr:>7.0f}{c.lot.free_spaces:>6}{c.score:>8}")
    say("-" * 78)

    best = ranked[0]
    lot = best.lot
    strongest = sorted(best.breakdown, key=best.breakdown.get, reverse=True)[:2]
    say(f"BEST LOT: {lot.name}")
    say(f"   {best.distance_km:.2f} km away, about {best.travel_min:.0f} min, "
        f"Rs {lot.price_per_hr:.0f}/hr, {lot.free_spaces}/{lot.total_spaces} spaces free, "
        f"security {lot.security}/5, open {lot.hours}")
    say(f"   Why: it scores best on {LABELS[strongest[0]]} and {LABELS[strongest[1]]}.")
    say(f"   Navigate: https://www.google.com/maps/dir/?api=1&destination={lot.lat},{lot.lon}")
    say("Sample data: prices and availability are simulated.")


def search(destinations, lots, text, preference, now_minutes, radius, top, say):
    """One full search. Returns True if something was found."""
    try:
        point = resolve_destination(destinations, text)
    except ValueError as err:
        say(str(err))
        return False
    candidates = discover(lots, point, now_minutes, radius)
    if not candidates:
        say(f"No open lots with free spaces within {radius:g} km. Try a bigger radius (-r).")
        return False
    render(text.strip().title(), preference, score_candidates(candidates, preference), top, say)
    return True


def build_parser():
    ap = argparse.ArgumentParser(prog="parking", description="Find and rank nearby parking lots.")
    ap.add_argument("-d", "--destination", help="place name or 'lat,lon'. Leave out for interactive mode.")
    ap.add_argument("-p", "--preference", choices=list(PREFERENCES), default="balanced")
    ap.add_argument("-r", "--radius", type=float, default=2.0, help="search radius in km (default 2)")
    ap.add_argument("-n", "--top", type=int, default=5, help="how many lots to show (default 5)")
    ap.add_argument("-t", "--time", help="time of arrival as HH:MM (default: now)")
    return ap


def choose_preference(ask, say):
    names = list(PREFERENCES)
    for i, name in enumerate(names, start=1):
        say(f"   {i}. {pretty(name)}")
    reply = ask(f"Choose a preference [1-{len(names)}, Enter = Balanced]: ").strip()
    if reply.isdigit() and 1 <= int(reply) <= len(names):
        return names[int(reply) - 1]
    return "balanced"


def main(argv=None, ask=input, say=print):
    args = build_parser().parse_args(argv)
    try:
        destinations, lots = load_data()
        if args.time:
            now = parse_clock(args.time)
        else:
            clock = datetime.datetime.now()
            now = clock.hour * 60 + clock.minute
    except (ValueError, OSError) as err:
        say(f"Error: {err}")
        return 1

    if args.destination:  # one-shot mode
        ok = search(destinations, lots, args.destination, args.preference,
                    now, args.radius, args.top, say)
        return 0 if ok else 1

    say(BANNER)
    say("Known places: " + ", ".join(name.title() for name in destinations))
    while True:
        text = ask("\nWhere are you going? (place name or lat,lon): ")
        if text.strip():
            try:
                resolve_destination(destinations, text)  # check the place before asking more
            except ValueError as err:
                say(str(err))
            else:
                preference = choose_preference(ask, say)
                search(destinations, lots, text, preference, now, args.radius, args.top, say)
        if ask("\nSearch again? (y/n) ").strip().lower() != "y":
            say("Happy parking!")
            return 0


if __name__ == "__main__":
    sys.exit(main())
