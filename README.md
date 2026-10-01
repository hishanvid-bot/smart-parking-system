# 🅿️ Smart Parking Finder

A terminal tool that finds parking lots near your destination and recommends the best one for you. Tell it what matters most (low cost, less traffic, high security or short distance) and it ranks every nearby lot with a clear, transparent score.

> Learning project built from a hackathon idea. All parking data is **simulated sample data**, not real prices or availability.

Built with **pure Python**, no libraries to install.

## The problem

Drivers waste time and fuel circling for parking near busy places, and it is hard to compare lots on price, traffic, distance and security. This project helps a driver choose a lot quickly instead of circling.

## Features

- **Nearby discovery**: enter a place name (like `Phoenix Marketcity`) or coordinates (`12.99,80.21`) and see lots within your chosen radius
- **Smart filtering**: lots that are closed at your arrival time, or completely full, are left out
- **Comparison engine**: scores every lot on price, traffic, distance, security, availability and travel time
- **Five preferences**: Balanced, Low Cost, Less Traffic, High Security, Short Distance
- **Best lot + reason**: shows the winner, why it won, and a Google Maps navigation link
- **Add your own lots** by editing one JSON file

## How to run

```bash
git clone https://github.com/harinisrinivasan0012-code/smart-parking-finder.git
cd smart-parking-finder
python -m parking
```

You need Python 3.8 or newer. With no options it starts an interactive session. You can also search in one line:

```bash
python -m parking -d "Phoenix Marketcity" -p low_cost
python -m parking -d "T Nagar" -p less_traffic -n 3 -t 19:30
python -m parking -d "12.99,80.21" -r 3
```

| Option | What it does |
|---|---|
| `-d`, `--destination` | Place name or `lat,lon` (leave out for interactive mode) |
| `-p`, `--preference` | `balanced` (default), `low_cost`, `less_traffic`, `high_security`, `short_distance` |
| `-r`, `--radius` | Search radius in km (default 2) |
| `-n`, `--top` | How many lots to show (default 5) |
| `-t`, `--time` | Arrival time as `HH:MM` (default: now) |

Built-in places: Phoenix Marketcity, T Nagar, Marina Beach.

## How the score works

Each lot gets a score from 0 to 100:

1. Every factor is scaled to 0 to 1, where 1 is the best lot in that search (cheapest price, least traffic, shortest distance, highest security, most free space, shortest travel time).
2. Each factor is multiplied by a **weight** that depends on your preference.
3. The results are added up.

| Preference | Heaviest weight |
|---|---|
| Low Cost | price (50%) |
| Less Traffic | traffic (45%) |
| High Security | security (55%) |
| Short Distance | distance (50%) |
| Balanced | spread evenly across all factors |

The weights live in `parking/scoring.py` and are easy to read and change. Travel time is estimated from distance at 30 km/h, slowed down by the traffic level around the lot. Scores compare lots within one search; they are not absolute grades.

## Sample run

```text
Destination : Phoenix Marketcity
Preference  : Low Cost
------------------------------------------------------------------------------
#  Lot                                   Dist   Time  Rs/hr  Free   Score
------------------------------------------------------------------------------
1  Sample Lot C - Street-side Plot     0.40km    1m     20    40    75.9
2  Sample Lot B - Metro Parking        0.34km    1m     30   120    71.2
3  Sample Lot F - Open Ground          1.66km    4m     15   300    67.0
4  Sample Lot D - Tech Park Annex      0.88km    2m     40   210    66.2
5  Sample Lot A - Mall Basement        0.07km    0m     60    35    50.3
------------------------------------------------------------------------------
BEST LOT: Sample Lot C - Street-side Plot
   0.40 km away, about 1 min, Rs 20/hr, 40/80 spaces free, security 2/5, open 24x7
   Why: it scores best on low price and good availability.
   Navigate: https://www.google.com/maps/dir/?api=1&destination=12.9935,80.216
Sample data: prices and availability are simulated.
```

Change the preference and the winner changes. Searching Marina Beach with `-p high_security` picks the guarded compound (security 5/5) even though it costs more.

## Add your own lots

Open `parking/lots.json` and add an entry to `lots`:

```json
{"name": "My Lot", "lat": 12.99, "lon": 80.22, "price_per_hr": 30,
 "total_spaces": 100, "free_spaces": 40, "traffic": 5, "security": 3,
 "hours": "08:00-22:00"}
```

- `traffic` is 1 (light) to 10 (heavy), `security` is 1 (low) to 5 (high)
- `hours` is `24x7` or `HH:MM-HH:MM` (overnight like `22:00-06:00` works too)
- add a new place under `destinations` with its `lat` and `lon`

Every lot is checked when the program starts, and it tells you if one is wrong.

## Project structure

```text
parking/
    geo.py        # distance (haversine) and travel-time estimate
    lots.py       # Lot and Candidate classes, loading, opening hours
    lots.json     # sample places and parking lots (edit me!)
    finder.py     # resolve a destination and discover nearby open lots
    scoring.py    # preference weights and the scoring engine
    __main__.py   # command line, interactive mode, output
tests/
    test_parking.py   # 34 unit tests, including full command-line runs
```

Discovery, data, scoring and display are separate modules, so sample data can later be swapped for a live parking feed without touching the scoring engine.

## Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

## Limits

- Parking data is simulated; real availability, pricing and security data would need to be sourced and verified
- Distances are straight-line, not road routes, and travel time is an estimate

## Ideas to extend it

- Connect real maps, routing and traffic APIs
- Read live availability and pricing from a data feed
- Build a map view with `tkinter` or a small web page
- Remember favourite places and preferences in a file
- Add cost for a chosen parking duration and rank by total price

## License

MIT
