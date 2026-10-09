"""The real road at a pothole's location, from OpenStreetMap.

Importance comes from the road's OSM class. Traffic is ESTIMATED from class and lane count: there is no free source
of real traffic counts for these roads, so the app labels it "estimated from road type", never as measured.
Needs the Overpass API (internet); if it is unreachable, uploads fall back to a road picked from the list.
"""
import json
import urllib.parse
import urllib.request
from math import cos, hypot, radians

from sqlalchemy import Connection

from app.repositories import roads

OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
SEARCH_M = 60  # a photo's GPS is often 5 to 10 m off; a road farther than this is probably not the one

# OSM highway tag -> (app road type, importance, base traffic estimate)
# shortcut: traffic per class is our estimate (busier classes carry more vehicles); replace with counts if a city publishes them
CLASSES = {
    "motorway": ("highway", 1.0, 0.95), "trunk": ("highway", 1.0, 0.9),
    "primary": ("arterial", 0.8, 0.75), "secondary": ("arterial", 0.7, 0.6),
    "tertiary": ("collector", 0.5, 0.45), "unclassified": ("collector", 0.4, 0.3),
    "residential": ("local", 0.3, 0.2), "living_street": ("local", 0.2, 0.1), "service": ("local", 0.2, 0.1),
}


class RoadLookupError(Exception):
    pass


def road_values(highway: str, lanes: int | None) -> dict:
    """Road type, importance and estimated traffic for an OSM highway tag (links count as their road)."""
    road_type, importance, traffic = CLASSES[highway.removesuffix("_link")]
    if lanes:  # more lanes than the usual two carry more vehicles
        traffic = min(max(traffic + 0.05 * (lanes - 2), 0.0), 1.0)
    return {"road_type": road_type, "importance_score": importance, "traffic_score": round(traffic, 3)}


def _segment_m(lat: float, lng: float, a: dict, b: dict) -> float:
    """Distance in metres from a point to segment a-b (flat approximation, fine at this scale)."""
    k = cos(radians(lat))
    ax, ay = (a["lon"] - lng) * 111_320 * k, (a["lat"] - lat) * 110_540
    bx, by = (b["lon"] - lng) * 111_320 * k, (b["lat"] - lat) * 110_540
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return hypot(ax + t * dx, ay + t * dy)


TIE_M = 10  # GPS is 5 to 10 m off, so roads this much farther than the nearest are equally likely


def nearest_way(ways: list[dict], lat: float, lng: float, max_m: float = SEARCH_M) -> dict | None:
    """The road the point is on, from an Overpass `out geom` answer: among ways within TIE_M of the nearest
    (and within max_m), the most important one, so a driveway beside a main road does not win."""
    dist = {}
    for i, w in enumerate(ways):
        g = w.get("geometry") or []
        d = min((_segment_m(lat, lng, a, b) for a, b in zip(g, g[1:])), default=None)
        if d is not None and d <= max_m:
            dist[i] = d
    if not dist:
        return None
    closest = min(dist.values())
    near = [i for i, d in dist.items() if d <= closest + TIE_M]
    best = max(near, key=lambda i: (CLASSES[ways[i]["tags"]["highway"].removesuffix("_link")][1], -dist[i]))
    return ways[best]


def fetch_ways(south: float, west: float, north: float, east: float) -> list[dict]:
    tags = "|".join(f"{k}(_link)?" if k in ("motorway", "trunk", "primary", "secondary", "tertiary") else k for k in CLASSES)
    query = f'[out:json][timeout:60];way["highway"~"^({tags})$"]({south},{west},{north},{east});out tags geom;'
    body = urllib.parse.urlencode({"data": query}).encode()
    for url in OVERPASS:
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": "SRPPS hackathon project (road lookup)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return [e for e in json.load(r).get("elements", []) if e.get("type") == "way"]
        except OSError:  # HTTP errors and timeouts: try the next server
            continue
    raise RoadLookupError("OpenStreetMap could not be reached")


def road_for_way(conn: Connection, way: dict) -> dict:
    """Find or create the road row for an OSM way."""
    osm_id = f"way/{way['id']}"
    existing = roads.get_by_osm_id(conn, osm_id)
    if existing:
        return existing
    t = way.get("tags", {})
    try:
        lanes = int(str(t.get("lanes", "")).split(";")[0]) if t.get("lanes") else None
    except ValueError:
        lanes = None
    values = road_values(t["highway"], lanes)
    name = t.get("name") or t.get("ref") or f"Unnamed {t['highway'].replace('_', ' ')} road"
    return roads.get(conn, roads.insert(conn, name=name, osm_way_id=osm_id, osm_highway=t["highway"], lanes=lanes,
                                        data_source="osm_estimate", **values))


def road_at(conn: Connection, lat: float, lng: float) -> dict:
    """The real road at a point; RoadLookupError if OSM is unreachable or no road is within SEARCH_M."""
    pad = SEARCH_M / 111_000
    way = nearest_way(fetch_ways(lat - pad, lng - pad / max(cos(radians(lat)), 0.01), lat + pad,
                                 lng + pad / max(cos(radians(lat)), 0.01)), lat, lng)
    if way is None:
        raise RoadLookupError(f"No mapped road within {SEARCH_M} m of this location")
    return road_for_way(conn, way)
