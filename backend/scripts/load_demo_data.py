"""Load demo potholes for the judges' walkthrough (docs/05, section 8).

Run from backend/ after the migrations and seed:  python scripts/load_demo_data.py

Honest by construction: every demo pothole is a REAL detection by the model, run through the normal upload
pipeline on a licensed sample photo (sample_data/images, licences in sample_data/README.md). Only the
locations and roads are made up. The uploads are flagged is_demo = true (migration 0003) and the UI labels
them "demo data". It includes three close clusters (zones), one spot photographed twice (repeat), and one
spot that is repaired and then damaged again (recurrence).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine  # noqa: E402
from app.repositories import roads as roads_repo  # noqa: E402
from app.services import status  # noqa: E402
from app.services.uploads import process_image  # noqa: E402

PHOTOS = sorted((Path(__file__).resolve().parents[2] / "sample_data" / "images").glob("pothole_*.jpg"))

# (road, lat, lng, status after upload). Made-up spots around central Bengaluru.
SPOTS = [
    ("Demo Highway", 12.95000, 77.64000, None),        # cluster 1
    ("Demo Highway", 12.95060, 77.64050, None),
    ("Demo Highway", 12.95110, 77.63980, None),
    ("Demo Highway", 12.95040, 77.64110, None),
    ("Demo Highway", 12.95000, 77.64000, None),        # same spot again: repeat
    ("Demo Main Road", 12.96000, 77.60000, None),      # cluster 2
    ("Demo Main Road", 12.96050, 77.60080, "In Progress"),
    ("Demo Main Road", 12.95980, 77.60120, None),
    ("Demo Main Road", 12.96100, 77.59950, None),
    ("Demo Market Street", 12.97500, 77.58000, None),  # cluster 3
    ("Demo Market Street", 12.97550, 77.58060, "Repaired"),
    ("Demo Market Street", 12.97480, 77.58090, None),
    ("Demo Lane", 12.99000, 77.57000, None),           # lone potholes
    ("Demo Lane", 12.99500, 77.62000, None),
    ("Demo Lane", 12.94000, 77.59000, None),
    ("Demo Lane", 12.98500, 77.56500, "Repaired"),     # repaired ...
    ("Demo Lane", 12.98500, 77.56500, None),           # ... and back: recurrence
]


def main() -> None:
    if not PHOTOS:
        sys.exit("No sample photos found in sample_data/images")
    with get_engine().begin() as conn:  # all or nothing
        if conn.execute(text("SELECT count(*) FROM uploads WHERE is_demo")).scalar_one():
            sys.exit("Demo data is already loaded.")
        road_ids = {r["name"]: r["road_id"] for r in roads_repo.list_all(conn)}
        for i, (road, lat, lng, after) in enumerate(SPOTS):
            res = process_image(conn, PHOTOS[i % len(PHOTOS)].read_bytes(), road_ids[road], lat, lng, "manual")
            conn.execute(text("UPDATE uploads SET is_demo = true WHERE upload_id = :id"), {"id": res["upload_id"]})
            for p in res["potholes"]:
                if after:
                    status.change_status(conn, p["pothole_id"], after)
                print(f"{road:18} {lat:.5f},{lng:.5f}  pothole #{p['pothole_id']} {p['match']:10} "
                      f"{p['priority_band']} {p['priority_score']:.2f}{'  -> ' + after if after else ''}")
    print("Demo data loaded. Open Zones and Plan and click Recompute zones.")


if __name__ == "__main__":
    main()
