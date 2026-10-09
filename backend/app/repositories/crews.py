"""SQL for the crews table."""
from sqlalchemy import Connection, text


def list_all(conn: Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(text("SELECT * FROM crews ORDER BY crew_id")).mappings()]


def get(conn: Connection, crew_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM crews WHERE crew_id = :id"), {"id": crew_id}).mappings().first()
    return dict(row) if row else None


def insert(conn: Connection, name: str, capacity_per_day: int) -> int:
    return conn.execute(text("INSERT INTO crews (name, capacity_per_day) VALUES (:n, :c) RETURNING crew_id"),
                        {"n": name, "c": capacity_per_day}).scalar_one()


def update(conn: Connection, crew_id: int, name: str, capacity_per_day: int) -> None:
    conn.execute(text("UPDATE crews SET name = :n, capacity_per_day = :c WHERE crew_id = :id"),
                 {"n": name, "c": capacity_per_day, "id": crew_id})


def delete(conn: Connection, crew_id: int) -> None:
    conn.execute(text("DELETE FROM crews WHERE crew_id = :id"), {"id": crew_id})


def order_counts(conn: Connection, crew_id: int) -> tuple[int, int]:
    """(open orders, finished orders) for a crew."""
    row = conn.execute(text("SELECT count(*) FILTER (WHERE completed_at IS NULL), count(*) FILTER (WHERE completed_at IS NOT NULL) "
                            "FROM repair_orders WHERE crew_id = :id"), {"id": crew_id}).one()
    return row[0], row[1]
