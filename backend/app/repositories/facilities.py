"""SQL for the facilities table (critical places from OpenStreetMap)."""
from math import cos, radians

from sqlalchemy import Connection, text


def near(conn: Connection, lat: float, lng: float, radius_m: float) -> list[dict]:
    """Facilities inside a lat/lng box around the point (callers refine with haversine)."""
    dlat = radius_m / 111_320
    dlng = dlat / max(cos(radians(lat)), 0.01)
    rows = conn.execute(text("SELECT * FROM facilities WHERE lat BETWEEN :a AND :b AND lng BETWEEN :c AND :d"),
                        {"a": lat - dlat, "b": lat + dlat, "c": lng - dlng, "d": lng + dlng})
    return [dict(r) for r in rows.mappings()]


def upsert_many(conn: Connection, rows: list[dict]) -> None:
    if rows:
        conn.execute(text("""
            INSERT INTO facilities (osm_id, name, kind, lat, lng) VALUES (:osm_id, :name, :kind, :lat, :lng)
            ON CONFLICT (osm_id) DO UPDATE SET name = EXCLUDED.name, kind = EXCLUDED.kind,
                                              lat = EXCLUDED.lat, lng = EXCLUDED.lng"""), rows)


def count(conn: Connection) -> int:
    return conn.execute(text("SELECT count(*) FROM facilities")).scalar_one()
