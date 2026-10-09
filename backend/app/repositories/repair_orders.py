"""SQL for the repair_orders table. No status column: an order is done when completed_at is set."""
from sqlalchemy import Connection, text


def insert(conn: Connection, pothole_id: int, crew_id: int, sequence_no: int, planned_date) -> None:
    conn.execute(text("INSERT INTO repair_orders (pothole_id, crew_id, sequence_no, planned_date) "
                      "VALUES (:p, :c, :s, :d)"), {"p": pothole_id, "c": crew_id, "s": sequence_no, "d": planned_date})


def delete_for_pothole(conn: Connection, pothole_id: int) -> None:
    conn.execute(text("DELETE FROM repair_orders WHERE pothole_id = :id"), {"id": pothole_id})


def complete_for_pothole(conn: Connection, pothole_id: int) -> None:
    conn.execute(text("UPDATE repair_orders SET completed_at = now() WHERE pothole_id = :id"), {"id": pothole_id})


def list_repairs(conn: Connection, status: str | None = None, crew_id: int | None = None) -> list[dict]:
    """Every pothole with its order (if any), for the Repairs page. Open orders sort by date, then sequence."""
    where, params = [], {}
    if status is not None:
        where.append("p.status = :status")
        params["status"] = status
    if crew_id is not None:
        where.append("o.crew_id = :crew_id")
        params["crew_id"] = crew_id
    sql = """
    SELECT p.pothole_id, p.status, p.priority_band, p.priority_score, p.severity_level, p.zone_id,
           p.repaired_at, r.name AS road_name, o.order_id, o.crew_id, c.name AS crew_name,
           o.sequence_no, o.planned_date, o.completed_at
    FROM potholes p
    LEFT JOIN roads r ON r.road_id = p.road_id
    LEFT JOIN repair_orders o ON o.pothole_id = p.pothole_id
    LEFT JOIN crews c ON c.crew_id = o.crew_id
    """ + (" WHERE " + " AND ".join(where) if where else "") + """
    ORDER BY o.planned_date NULLS LAST, o.sequence_no NULLS LAST, p.priority_score DESC
    """
    return [dict(r) for r in conn.execute(text(sql), params).mappings()]
