"""SQL for the roads table."""
from sqlalchemy import Connection, text


def list_all(conn: Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(text("SELECT * FROM roads ORDER BY importance_score DESC, name")).mappings()]


def get(conn: Connection, road_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM roads WHERE road_id = :id"), {"id": road_id}).mappings().first()
    return dict(row) if row else None


def update_scores(conn: Connection, road_id: int, traffic_score: float, importance_score: float) -> None:
    conn.execute(text("UPDATE roads SET traffic_score = :t, importance_score = :i WHERE road_id = :id"),
                 {"t": traffic_score, "i": importance_score, "id": road_id})
