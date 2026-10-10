"""SQL for the points_ledger table."""
from sqlalchemy import Connection, text


def rewarded_potholes(conn: Connection, user_id: int, pothole_ids: list[int]) -> set[int]:
    """Which of these potholes were already in a report that earned this user points."""
    if not pothole_ids:
        return set()
    rows = conn.execute(text("""SELECT pothole_id FROM points_ledger
        WHERE user_id = :u AND pothole_id = ANY(:ids)"""), {"u": user_id, "ids": pothole_ids})
    return {r[0] for r in rows}


def earned_today(conn: Connection, user_id: int) -> int:
    return conn.execute(text("""SELECT COALESCE(SUM(points), 0) FROM points_ledger
        WHERE user_id = :u AND created_at >= date_trunc('day', now())"""), {"u": user_id}).scalar_one()


def total(conn: Connection, user_id: int) -> int:
    return conn.execute(text("SELECT COALESCE(SUM(points), 0) FROM points_ledger WHERE user_id = :u"),
                        {"u": user_id}).scalar_one()


def insert(conn: Connection, user_id: int, user_email: str, upload_id: int, pothole_id: int | None,
           points: int, reason: str) -> None:
    conn.execute(text("""INSERT INTO points_ledger (user_id, user_email, upload_id, pothole_id, points, reason)
        VALUES (:u, :e, :up, :p, :pts, :r)"""),
        {"u": user_id, "e": user_email, "up": upload_id, "p": pothole_id, "pts": points, "r": reason})
