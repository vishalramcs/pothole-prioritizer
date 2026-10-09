"""SQL for the uploads table."""
from sqlalchemy import Connection, text


def insert(conn: Connection, **row) -> int:
    cols = ", ".join(row)
    vals = ", ".join(f":{c}" for c in row)
    return conn.execute(text(f"INSERT INTO uploads ({cols}) VALUES ({vals}) RETURNING upload_id"), row).scalar_one()


def get(conn: Connection, upload_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM uploads WHERE upload_id = :id"), {"id": upload_id}).mappings().first()
    return dict(row) if row else None
