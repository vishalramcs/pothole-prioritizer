"""SQL for the roads table."""
from sqlalchemy import Connection, text


def list_all(conn: Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(text("SELECT * FROM roads ORDER BY importance_score DESC, name")).mappings()]


def get(conn: Connection, road_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM roads WHERE road_id = :id"), {"id": road_id}).mappings().first()
    return dict(row) if row else None


def get_by_osm_id(conn: Connection, osm_way_id: str) -> dict | None:
    row = conn.execute(text("SELECT * FROM roads WHERE osm_way_id = :id"), {"id": osm_way_id}).mappings().first()
    return dict(row) if row else None


def insert(conn: Connection, **row) -> int:
    cols = ", ".join(row)  # column names come from our code, never from requests
    vals = ", ".join(f":{c}" for c in row)
    return conn.execute(text(f"INSERT INTO roads ({cols}) VALUES ({vals}) RETURNING road_id"), row).scalar_one()


def update_scores(conn: Connection, road_id: int, traffic_score: float, importance_score: float) -> None:
    conn.execute(text("UPDATE roads SET traffic_score = :t, importance_score = :i WHERE road_id = :id"),
                 {"t": traffic_score, "i": importance_score, "id": road_id})
