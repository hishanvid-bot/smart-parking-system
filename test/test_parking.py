import json
import os
import tempfile
import unittest

from parking.__main__ import main
from parking.finder import discover, resolve_destination
from parking.geo import haversine_km, travel_minutes
from parking.lots import Candidate, Lot, is_open, load_data, parse_clock
from parking.scoring import FACTORS, PREFERENCES, score_candidates

PHOENIX = (12.9908, 80.2185)


def make_lot(name="Lot", price=30, total=100, free=50, traffic=5, security=3, hours="24x7",
             lat=PHOENIX[0], lon=PHOENIX[1]):
    return Lot(name, lat, lon, price, total, free, traffic, security, hours)


def make_candidate(distance=1.0, **kwargs):
    lot = make_lot(**kwargs)
    return Candidate(lot, distance, travel_minutes(distance, lot.traffic))


def run_cli(argv, replies=()):
    """Run main() with captured output and scripted replies."""
    out = []
    it = iter(replies)
    code = main(argv, ask=lambda prompt: next(it), say=out.append)
    return code, "\n".join(out)


class TestGeo(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(haversine_km(12.99, 80.21, 12.99, 80.21), 0.0)

    def test_known_distance(self):
        # One degree of latitude is about 111 km.
        self.assertAlmostEqual(haversine_km(0, 0, 1, 0), 111.2, delta=0.5)

    def test_traffic_slows_travel(self):
        self.assertGreater(travel_minutes(2, 9), travel_minutes(2, 1))
        self.assertAlmostEqual(travel_minutes(30, 10), 120.0)


class TestHours(unittest.TestCase):
    def test_parse_clock(self):
        self.assertEqual(parse_clock("09:30"), 570)
        self.assertEqual(parse_clock("24:00"), 1440)
        for bad in ("25:00", "9", "ab:cd", "10:75", "24:30"):
            with self.assertRaises(ValueError):
                parse_clock(bad)

    def test_always_open(self):
        self.assertTrue(is_open("24x7", 0))
        self.assertTrue(is_open("24X7", 1000))

    def test_normal_hours(self):
        self.assertTrue(is_open("10:00-23:00", parse_clock("10:00")))
        self.assertTrue(is_open("10:00-23:00", parse_clock("22:59")))
        self.assertFalse(is_open("10:00-23:00", parse_clock("23:00")))
        self.assertFalse(is_open("10:00-23:00", parse_clock("09:59")))

    def test_open_until_midnight(self):
        self.assertTrue(is_open("09:00-24:00", parse_clock("23:59")))
        self.assertFalse(is_open("09:00-24:00", parse_clock("02:00")))

    def test_overnight_hours(self):
        self.assertTrue(is_open("22:00-06:00", parse_clock("23:30")))
        self.assertTrue(is_open("22:00-06:00", parse_clock("03:00")))
        self.assertFalse(is_open("22:00-06:00", parse_clock("12:00")))


class TestData(unittest.TestCase):
    def test_bundled_data_is_valid(self):
        destinations, lots = load_data()
        self.assertGreaterEqual(len(destinations), 3)
        self.assertGreaterEqual(len(lots), 10)

    def test_every_destination_has_nearby_lots(self):
        destinations, lots = load_data()
        for name, point in destinations.items():
            self.assertTrue(discover(lots, point, parse_clock("12:00")), name)

    def _load_with(self, **changes):
        lot = {"name": "X", "lat": 1, "lon": 1, "price_per_hr": 10, "total_spaces": 10,
               "free_spaces": 5, "traffic": 3, "security": 3, "hours": "24x7"}
        lot.update(changes)
        data = {"destinations": {"Here": {"lat": 1, "lon": 1}}, "lots": [lot]}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "lots.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return load_data(path)

    def test_good_lot_loads(self):
        self._load_with()

    def test_bad_lots_are_rejected(self):
        for bad in ({"free_spaces": 11}, {"total_spaces": 0}, {"price_per_hr": -1},
                    {"traffic": 11}, {"security": 0}, {"hours": "late"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                self._load_with(**bad)


class TestDiscovery(unittest.TestCase):
    NOON = parse_clock("12:00")

    def test_resolve_known_and_coordinates(self):
        known = {"phoenix marketcity": PHOENIX}
        self.assertEqual(resolve_destination(known, "  Phoenix Marketcity "), PHOENIX)
        self.assertEqual(resolve_destination(known, "12.5, 80.25"), (12.5, 80.25))

    def test_resolve_rejects_nonsense(self):
        known = {"phoenix marketcity": PHOENIX}
        for bad in ("Mars", "1,2,3", "abc,def", "95,10"):
            with self.assertRaises(ValueError):
                resolve_destination(known, bad)

    def test_radius_filters_far_lots(self):
        near = make_lot("near")
        far = make_lot("far", lat=PHOENIX[0] + 0.1)  # about 11 km away
        found = discover([near, far], PHOENIX, self.NOON, radius_km=2)
        self.assertEqual([c.lot.name for c in found], ["near"])

    def test_full_and_closed_lots_are_skipped(self):
        full = make_lot("full", free=0)
        closed = make_lot("closed", hours="18:00-22:00")
        ok = make_lot("ok")
        found = discover([full, closed, ok], PHOENIX, self.NOON)
        self.assertEqual([c.lot.name for c in found], ["ok"])

    def test_lot_opens_later_in_the_day(self):
        evening = make_lot("evening", hours="18:00-22:00")
        self.assertEqual(discover([evening], PHOENIX, self.NOON), [])
        self.assertEqual(len(discover([evening], PHOENIX, parse_clock("19:00"))), 1)


class TestScoring(unittest.TestCase):
    def test_every_preference_weights_add_to_one(self):
        for name, weights in PREFERENCES.items():
            self.assertEqual(set(weights), set(FACTORS), name)
            self.assertAlmostEqual(sum(weights.values()), 1.0, msg=name)

    def test_scores_are_between_0_and_100(self):
        cands = [make_candidate(d, price=p, security=s) for d, p, s in ((0.2, 90, 5), (1.5, 15, 2), (0.9, 40, 3))]
        for pref in PREFERENCES:
            for c in score_candidates([Candidate(x.lot, x.distance_km, x.travel_min) for x in cands], pref):
                self.assertTrue(0 <= c.score <= 100, (pref, c.score))

    def test_sorted_best_first(self):
        cands = [make_candidate(d, price=p) for d, p in ((1.8, 80), (0.5, 20), (1.0, 50))]
        scores = [c.score for c in score_candidates(cands)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_low_cost_prefers_cheap(self):
        cheap = make_candidate(1.0, price=10, security=1)
        pricey = make_candidate(1.0, price=100, security=5)
        self.assertIs(score_candidates([pricey, cheap], "low_cost")[0], cheap)

    def test_high_security_prefers_secure(self):
        cheap = make_candidate(1.0, price=10, security=1)
        pricey = make_candidate(1.0, price=100, security=5)
        self.assertIs(score_candidates([cheap, pricey], "high_security")[0], pricey)

    def test_less_traffic_prefers_calm_roads(self):
        calm = make_candidate(1.0, traffic=1)
        busy = make_candidate(1.0, traffic=10)
        self.assertIs(score_candidates([busy, calm], "less_traffic")[0], calm)

    def test_short_distance_prefers_close(self):
        close = make_candidate(0.1)
        far = make_candidate(1.9)
        self.assertIs(score_candidates([far, close], "short_distance")[0], close)

    def test_breakdown_matches_score(self):
        ranked = score_candidates([make_candidate(0.3, price=20), make_candidate(1.2, price=60)], "balanced")
        for c in ranked:
            self.assertAlmostEqual(sum(c.breakdown.values()), c.score, delta=0.3)

    def test_single_candidate_and_empty(self):
        self.assertEqual(score_candidates([], "balanced"), [])
        only = score_candidates([make_candidate()], "balanced")
        self.assertEqual(len(only), 1)

    def test_unknown_preference(self):
        with self.assertRaises(ValueError):
            score_candidates([make_candidate()], "cheapest_ever")


class TestCommandLine(unittest.TestCase):
    def test_one_shot_search(self):
        code, text = run_cli(["-d", "Phoenix Marketcity", "-p", "low_cost", "-t", "12:00"])
        self.assertEqual(code, 0)
        self.assertIn("BEST LOT: Sample Lot", text)
        self.assertIn("Preference  : Low Cost", text)
        self.assertIn("google.com/maps", text)

    def test_preference_changes_the_winner(self):
        _, cheap = run_cli(["-d", "Phoenix Marketcity", "-p", "low_cost", "-t", "12:00"])
        _, safe = run_cli(["-d", "Phoenix Marketcity", "-p", "high_security", "-t", "12:00"])
        self.assertNotEqual(cheap.split("BEST LOT:")[1].splitlines()[0],
                            safe.split("BEST LOT:")[1].splitlines()[0])

    def test_top_option_limits_rows(self):
        _, text = run_cli(["-d", "Phoenix Marketcity", "-n", "2", "-t", "12:00"])
        self.assertEqual(text.count("Sample Lot"), 3)  # 2 table rows + the BEST LOT line

    def test_closed_at_night_lots_are_left_out(self):
        _, text = run_cli(["-d", "Phoenix Marketcity", "-n", "10", "-t", "03:00"])
        self.assertNotIn("Mall Basement", text)  # opens at 10:00
        self.assertIn("Street-side Plot", text)  # open 24x7

    def test_unknown_place_and_bad_time(self):
        code, text = run_cli(["-d", "Atlantis", "-t", "12:00"])
        self.assertEqual(code, 1)
        self.assertIn("Unknown destination", text)
        code, text = run_cli(["-d", "T Nagar", "-t", "99:99"])
        self.assertEqual(code, 1)
        self.assertIn("Bad time", text)

    def test_nothing_in_range(self):
        code, text = run_cli(["-d", "0,0", "-t", "12:00"])
        self.assertEqual(code, 1)
        self.assertIn("No open lots", text)

    def test_interactive_session(self):
        replies = ["Marina Beach", "3", "y",       # search 1, pick 'Less Traffic'
                   "Mars", "n"]                    # search 2 fails, then quit
        code, text = run_cli(["-t", "12:00"], replies)
        self.assertEqual(code, 0)
        self.assertIn("Preference  : Less Traffic", text)
        self.assertIn("Unknown destination 'Mars'", text)
        self.assertIn("Happy parking!", text)


if __name__ == "__main__":
    unittest.main()
