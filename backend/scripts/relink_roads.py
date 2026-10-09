"""Move existing uploads and potholes from the old demo (mock) roads to their real OpenStreetMap road, then
delete the mock roads and rescore everything. Safe to re-run.

Run from backend/:  python scripts/relink_roads.py
One Overpass query per ~1 km tile that has potholes. Uploads with no mapped road within osm_roads.SEARCH_M keep
no road (road_id NULL; scored like the quietest road) and are listed, so they can be fixed by hand.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine  # noqa: E402
from app.services import osm_roads, priority  # noqa: E402

def main() -> None:
    with get_engine().connect() as conn:
        ups = conn.execute(text("SELECT upload_id, lat, lng FROM uploads")).mappings().all()
    tiles = defaultdict(list)
    for u in ups:
        tiles[(int(u["lat"] // osm_roads.TILE), int(u["lng"] // osm_roads.TILE))].append(u)
    ways = {}
    for key, members in tiles.items():  # 1. download every tile first (cached), so a failure loses nothing
        ways[key] = osm_roads.tile_ways(*key, attempts=4, wait_s=20)  # cached in backend/.osm_cache
        print(f"tile {key[0] * osm_roads.TILE:.2f},{key[1] * osm_roads.TILE:.2f}: {len(ways[key])} roads, {len(members)} uploads")
    with get_engine().begin() as conn:  # 2. then update the database in one transaction
        unmatched = []
        for key, members in tiles.items():
            for u in members:
                way = osm_roads.nearest_way(ways[key], u["lat"], u["lng"])
                road_id = osm_roads.road_for_way(conn, way)["road_id"] if way else None
                if road_id is None:
                    unmatched.append(u["upload_id"])
                conn.execute(text("UPDATE uploads SET road_id = :r WHERE upload_id = :u"), {"r": road_id, "u": u["upload_id"]})
                conn.execute(text("UPDATE potholes SET road_id = :r WHERE upload_id = :u"), {"r": road_id, "u": u["upload_id"]})
        gone = conn.execute(text("DELETE FROM roads WHERE data_source = 'mock' RETURNING name")).scalars().all()
        priority.rescore_all(conn, refresh_facilities=True)
        print(f"relinked {len(ups) - len(unmatched)} uploads to OSM roads; deleted mock roads: {gone or 'none'}")
        if unmatched:
            print(f"no mapped road within {osm_roads.SEARCH_M} m for uploads {unmatched} (road left empty)")


if __name__ == "__main__":
    main()
