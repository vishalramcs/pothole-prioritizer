"""DBSCAN clustering and zone rebuild (TRD 4.6).

Straight-line (haversine) distance, not driving distance: a river or divided road can make close points far
apart in practice. That limitation is listed in the README.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import Connection

from app.repositories import config, potholes
from app.repositories import zones as zones_repo
from app.services import geo


def cluster(points: list[tuple[float, float]], eps_m: float) -> list[int]:
    """One label per point. Points with no neighbour within eps_m get a zone of their own (no -1 noise)."""
    if not points:
        return []
    rad = np.radians(np.array(points))
    labels = DBSCAN(eps=eps_m / geo.EARTH_RADIUS_M, min_samples=2, metric="haversine",
                    algorithm="ball_tree").fit(rad).labels_
    next_label = labels.max() + 1
    out = []
    for label in labels:
        if label == -1:
            label, next_label = next_label, next_label + 1
        out.append(int(label))
    return out


def recompute(conn: Connection) -> None:
    """Rebuild every zone from the open potholes, inside the request's transaction."""
    eps_m = config.get_all(conn)["ZONE_EPS_M"]
    zones_repo.delete_all(conn)
    open_ = potholes.open_rows(conn)
    groups: dict[int, list[dict]] = {}
    for p, label in zip(open_, cluster([(p["lat"], p["lng"]) for p in open_], eps_m)):
        groups.setdefault(label, []).append(p)
    for members in groups.values():
        zone_id = zones_repo.insert(
            conn,
            centroid_lat=sum(p["lat"] for p in members) / len(members),
            centroid_lng=sum(p["lng"] for p in members) / len(members),
            pothole_count=len(members),
            avg_priority=sum(p["priority_score"] for p in members) / len(members),
        )
        potholes.set_zone(conn, [p["pothole_id"] for p in members], zone_id)


def list_with_radius(conn: Connection) -> list[dict]:
    """Zones plus radius_m (farthest member from the centroid), so the map can draw a circle around them."""
    members: dict[int, list[dict]] = {}
    for p in potholes.open_rows(conn):
        if p["zone_id"] is not None:
            members.setdefault(p["zone_id"], []).append(p)
    out = []
    for z in zones_repo.list_all(conn):
        pts = members.get(z["zone_id"], [])
        z["radius_m"] = max((geo.distance_m(z["centroid_lat"], z["centroid_lng"], p["lat"], p["lng"]) for p in pts),
                            default=0.0)
        out.append(z)
    return out

