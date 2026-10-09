"""Duplicate matching and repeat damage across uploads (TRD 4.4).

All detections from one upload share its point, so every candidate is the same distance from each of them.
1. Detections from the same upload are never merged with each other.
2. Pair with OPEN potholes from earlier uploads inside DEDUP_RADIUS_M, one-to-one, both sides sorted by
   severity (high first): same pothole seen again.
3. Pair leftovers with REPAIRED potholes the same way: the damage came back (new record, recurrence + 1).
4. Anything left is a brand-new pothole.
"""
from sqlalchemy import Connection

from app.repositories import potholes
from app.services import geo

by_severity = lambda p: -p["severity_score"]  # noqa: E731


def match(conn: Connection, detections: list[dict], lat: float, lng: float,
          radius_m: float) -> list[tuple[dict, dict | None, str]]:
    """[(detection, matched existing pothole or None, kind)] with kind "repeat", "recurrence" or "new"."""
    nearby = [p for p in potholes.near(conn, lat, lng, radius_m)
              if geo.distance_m(lat, lng, p["lat"], p["lng"]) <= radius_m]
    open_ = sorted((p for p in nearby if p["status"] != "Repaired"), key=by_severity)
    # Repaired candidates: newest link in a repeat chain first (highest recurrence), so counts keep climbing
    repaired = sorted((p for p in nearby if p["status"] == "Repaired"),
                      key=lambda p: (-p["recurrence_count"], -p["severity_score"]))

    left = sorted(detections, key=by_severity)
    out = [(d, p, "repeat") for d, p in zip(left, open_)]
    left = left[len(out):]
    recurred = [(d, p, "recurrence") for d, p in zip(left, repaired)]
    out += recurred
    out += [(d, None, "new") for d in left[len(recurred):]]
    return out
