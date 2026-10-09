"""Import hospitals, clinics, schools and fire stations from OpenStreetMap, then rescore every pothole.

Run from backend/:  python scripts/import_facilities.py [south west north east]
Default box: central Bengaluru, around the demo data. Needs internet once; afterwards everything is local.
Data (c) OpenStreetMap contributors, ODbL. Re-running updates existing rows (matched by OSM id).
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_engine  # noqa: E402
from app.repositories import facilities as repo  # noqa: E402
from app.services import facilities, priority  # noqa: E402

OVERPASS = "https://overpass-api.de/api/interpreter"
DEFAULT_BOX = (12.90, 77.53, 13.02, 77.68)


def fetch(box: tuple[float, ...]) -> dict:
    s, w, n, e = box
    query = (f'[out:json][timeout:90];nwr["amenity"~"^({"|".join(facilities.KINDS)})$"]({s},{w},{n},{e});'
             "out center tags;")
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": query}).encode(),
                                 headers={"User-Agent": "SRPPS hackathon project (facility import)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    box = tuple(float(x) for x in sys.argv[1:5]) if len(sys.argv) >= 5 else DEFAULT_BOX
    rows = facilities.parse_overpass(fetch(box))
    print(f"OpenStreetMap returned {len(rows)} facilities in {box}")
    with get_engine().begin() as conn:
        repo.upsert_many(conn, rows)
        priority.rescore_all(conn, refresh_facilities=True)
        print(f"{repo.count(conn)} facilities stored; every pothole rescored")


if __name__ == "__main__":
    main()
