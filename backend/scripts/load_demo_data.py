"""Load demo potholes for the judges' walkthrough (docs/05, section 8).

Run from backend/ after the migrations and seed:  python scripts/load_demo_data.py   (needs internet for OSM)

Honest by construction: every demo pothole is a REAL detection by the model, run through the normal upload
pipeline on a licensed sample photo (sample_data/images, licences in sample_data/README.md). Only the locations
are made up; each one's road is the real OpenStreetMap road there. The uploads are flagged is_demo = true
(migration 0003) and the UI labels them "demo data". It includes three close clusters (zones), one spot
photographed twice (repeat), and one spot that is repaired and then damaged again (recurrence).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine  # noqa: E402
from app.services import status  # noqa: E402
from app.services.uploads import UploadError, process_image  # noqa: E402

PHOTOS = sorted((Path(__file__).resolve().parents[2] / "sample_data" / "images").glob("pothole_*.jpg"))

# (lat, lng, status after upload). Made-up spots around central Bengaluru.
SPOTS = [
    (12.95000, 77.64000, None),        # cluster 1
    (12.95060, 77.64050, None),
    (12.95110, 77.63980, None),
    (12.95040, 77.64110, None),
    (12.95000, 77.64000, None),        # same spot again: repeat
    (12.96000, 77.60000, None),        # cluster 2
    (12.96050, 77.60080, "In Progress"),
    (12.95980, 77.60120, None),
    (12.96100, 77.59950, None),
    (12.97500, 77.58000, None),        # cluster 3
    (12.97550, 77.58060, "Repaired"),
    (12.97480, 77.58090, None),
    (12.99000, 77.57000, None),        # lone potholes
    (12.99500, 77.62000, None),
    (12.94000, 77.59000, None),
    (12.98500, 77.56500, "Repaired"),  # repaired ...
    (12.98500, 77.56500, None),        # ... and back: recurrence
]


def main() -> None:
    if not PHOTOS:
        sys.exit("No sample photos found in sample_data/images")
    with get_engine().begin() as conn:  # all or nothing
        if conn.execute(text("SELECT count(*) FROM uploads WHERE is_demo")).scalar_one():
            sys.exit("Demo data is already loaded.")
        for i, (lat, lng, after) in enumerate(SPOTS):
            try:
                res = process_image(conn, PHOTOS[i % len(PHOTOS)].read_bytes(), None, lat, lng, "manual")
            except UploadError as exc:  # e.g. no mapped road near this made-up spot, or OSM unreachable
                print(f"skipped {lat:.5f},{lng:.5f}: {exc}")
                continue
            conn.execute(text("UPDATE uploads SET is_demo = true WHERE upload_id = :id"), {"id": res["upload_id"]})
            for p in res["potholes"]:
                if after:
                    status.change_status(conn, p["pothole_id"], after)
                print(f"{lat:.5f},{lng:.5f}  pothole #{p['pothole_id']} {p['match']:10} "
                      f"{p['priority_band']} {p['priority_score']:.2f}{'  -> ' + after if after else ''}")
    print("Demo data loaded. Open Zones and Plan and click Recompute zones.")


if __name__ == "__main__":
    main()
