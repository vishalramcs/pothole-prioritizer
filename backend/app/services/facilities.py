"""Location factor: how close a pothole is to an important building (OpenStreetMap): hospitals, clinics,
fire stations, schools, colleges, universities, police stations, bus stations, railway stations.

facility_score = exp(-distance_m / FACILITY_DECAY_M) to the nearest one: 1 next door, 0.37 at 500 m, ~0 beyond 2.5 km.
Facilities come from OpenStreetMap (scripts/import_facilities.py), so coverage is only as good as OSM's.
"""
from math import exp

from sqlalchemy import Connection

from app.repositories import facilities
from app.services import geo

AMENITIES = ("hospital", "clinic", "fire_station", "school", "college", "university", "police", "bus_station")
KINDS = AMENITIES + ("railway_station",)  # railway stations are tagged railway=station, not amenity
NONE = {"facility_score": 0.0, "nearest_facility": None, "nearest_facility_m": None}


def proximity(conn: Connection, lat: float, lng: float, decay_m: float) -> dict:
    radius = 5 * decay_m  # beyond this the score is below 0.007, so treat it as none
    best = None
    for f in facilities.near(conn, lat, lng, radius):
        d = geo.distance_m(lat, lng, f["lat"], f["lng"])
        if d <= radius and (best is None or d < best[0]):
            best = (d, f)
    if best is None:
        return dict(NONE)
    d, f = best
    label = f"{f['name'] or 'Unnamed'} ({f['kind'].replace('_', ' ')})"
    return {"facility_score": exp(-d / decay_m), "nearest_facility": label, "nearest_facility_m": round(d, 1)}


def parse_overpass(data: dict) -> list[dict]:
    """Overpass JSON (nodes, and ways/relations with `out center`) -> facility rows."""
    rows = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        kind = tags.get("amenity") if tags.get("amenity") in AMENITIES else (
            "railway_station" if tags.get("railway") == "station" else None)
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lng = el.get("lon", el.get("center", {}).get("lon"))
        if kind in KINDS and lat is not None and lng is not None:
            rows.append({"osm_id": f"{el['type']}/{el['id']}", "name": tags.get("name"),
                         "kind": kind, "lat": lat, "lng": lng})
    return rows
