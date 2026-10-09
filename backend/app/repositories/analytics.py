"""Read-only analytics SQL across tables (docs/05-backend-schema.md, section 7)."""
from sqlalchemy import Connection, text


def _rows(conn: Connection, sql: str) -> list[dict]:
    return [dict(r) for r in conn.execute(text(sql)).mappings()]


def summary(conn: Connection) -> dict:
    return {
        "by_status": _rows(conn, "SELECT status, COUNT(*) AS n FROM potholes GROUP BY status"),
        "by_severity": _rows(conn, "SELECT severity_level, COUNT(*) AS n FROM potholes "
                                   "WHERE status <> 'Repaired' GROUP BY severity_level"),
        "top_roads": _rows(conn, """
            SELECT r.name, COUNT(*) AS pending, ROUND(SUM(p.priority_score)::numeric, 2)::float AS total_priority
            FROM potholes p JOIN roads r ON r.road_id = p.road_id
            WHERE p.status <> 'Repaired'
            GROUP BY r.road_id, r.name ORDER BY total_priority DESC LIMIT 5"""),
        "hotspots": _rows(conn, """
            SELECT p.pothole_id, p.lat, p.lng, r.name AS road_name, p.detection_count, p.recurrence_count,
                   (p.detection_count - 1) + p.recurrence_count AS repeat_count
            FROM potholes p LEFT JOIN roads r ON r.road_id = p.road_id
            WHERE (p.detection_count - 1) + p.recurrence_count >= 1
            ORDER BY repeat_count DESC, p.pothole_id LIMIT 10"""),
        "avg_days_to_repair": conn.execute(text("""
            SELECT ROUND(AVG(EXTRACT(EPOCH FROM (repaired_at - first_detected_at)) / 86400)::numeric, 1)::float
            FROM potholes WHERE status = 'Repaired'""")).scalar(),
        "done_by_crew": _rows(conn, """
            SELECT c.name, COUNT(*) AS done
            FROM repair_orders o JOIN crews c ON c.crew_id = o.crew_id
            WHERE o.completed_at IS NOT NULL
            GROUP BY c.crew_id, c.name ORDER BY done DESC"""),
    }
