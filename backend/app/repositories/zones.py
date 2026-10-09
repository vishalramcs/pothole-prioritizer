"""SQL for the zones table. Zones are derived data: rebuilt in one transaction (TRD 4.6)."""
from sqlalchemy import Connection, text


def delete_all(conn: Connection) -> None:
    conn.execute(text("DELETE FROM zones"))  # ON DELETE SET NULL clears every potholes.zone_id


def insert(conn: Connection, centroid_lat: float, centroid_lng: float, pothole_count: int, avg_priority: float) -> int:
    return conn.execute(
        text("INSERT INTO zones (centroid_lat, centroid_lng, pothole_count, avg_priority) "
             "VALUES (:lat, :lng, :n, :avg) RETURNING zone_id"),
        {"lat": centroid_lat, "lng": centroid_lng, "n": pothole_count, "avg": avg_priority},
    ).scalar_one()


def list_all(conn: Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(text("SELECT * FROM zones ORDER BY avg_priority DESC")).mappings()]
