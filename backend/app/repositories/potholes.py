"""SQL for the potholes table. Column names in insert/update come from our code, never from requests."""
from math import cos, radians

from sqlalchemy import Connection, text

# Pothole plus what the map and detail panel need from its road and upload.
_SELECT = """
SELECT p.*, r.name AS road_name, r.road_type, r.traffic_score, r.importance_score,
       r.data_source AS road_data_source, u.image_width, u.image_height, u.media_type, u.is_demo,
       COALESCE(p.frame_storage_path, u.storage_path) AS image_path
FROM potholes p
JOIN uploads u ON u.upload_id = p.upload_id
LEFT JOIN roads r ON r.road_id = p.road_id
"""


def insert(conn: Connection, **row) -> int:
    cols = ", ".join(row)
    vals = ", ".join(f":{c}" for c in row)
    return conn.execute(text(f"INSERT INTO potholes ({cols}) VALUES ({vals}) RETURNING pothole_id"), row).scalar_one()


def list_filtered(conn: Connection, status: str | None = None, band: str | None = None,
                  zone_id: int | None = None) -> list[dict]:
    where, params = [], {}
    for col, val in (("p.status", status), ("p.priority_band", band), ("p.zone_id", zone_id)):
        if val is not None:
            key = col.split(".")[1]
            where.append(f"{col} = :{key}")
            params[key] = val
    sql = _SELECT + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY p.priority_score DESC"
    return [dict(r) for r in conn.execute(text(sql), params).mappings()]


def get(conn: Connection, pothole_id: int, for_update: bool = False) -> dict | None:
    # FOR UPDATE OF p: two status clicks at once must not both pass the transition check
    sql = _SELECT + " WHERE p.pothole_id = :id" + (" FOR UPDATE OF p" if for_update else "")
    row = conn.execute(text(sql), {"id": pothole_id}).mappings().first()
    return dict(row) if row else None


def near(conn: Connection, lat: float, lng: float, radius_m: float) -> list[dict]:
    """Potholes inside a lat/lng box around the point (callers refine with haversine)."""
    dlat = radius_m / 111_320
    dlng = dlat / max(cos(radians(lat)), 0.01)
    sql = _SELECT + " WHERE p.lat BETWEEN :lat0 AND :lat1 AND p.lng BETWEEN :lng0 AND :lng1 FOR UPDATE OF p"
    rows = conn.execute(text(sql), {"lat0": lat - dlat, "lat1": lat + dlat, "lng0": lng - dlng, "lng1": lng + dlng})
    return [dict(r) for r in rows.mappings()]


def open_rows(conn: Connection) -> list[dict]:
    """Pending, Scheduled and In Progress potholes, highest priority first, locked for the zone/plan rebuild."""
    sql = _SELECT + " WHERE p.status <> 'Repaired' ORDER BY p.priority_score DESC, p.pothole_id FOR UPDATE OF p"
    return [dict(r) for r in conn.execute(text(sql)).mappings()]


def set_zone(conn: Connection, pothole_ids: list[int], zone_id: int) -> None:
    conn.execute(text("UPDATE potholes SET zone_id = :z WHERE pothole_id = ANY(:ids)"), {"z": zone_id, "ids": pothole_ids})


def update(conn: Connection, pothole_id: int, **fields) -> None:
    sets = ", ".join(f"{c} = :{c}" for c in fields)
    conn.execute(text(f"UPDATE potholes SET {sets} WHERE pothole_id = :pothole_id"), {**fields, "pothole_id": pothole_id})
