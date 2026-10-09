"""SQL for the config table. Every value is numeric (weights, thresholds, radii)."""
from sqlalchemy import Connection, text


def get_all(conn: Connection) -> dict[str, float]:
    return {k: float(v) for k, v in conn.execute(text("SELECT key, value FROM config"))}


def set_many(conn: Connection, values: dict[str, float]) -> None:
    conn.execute(text("UPDATE config SET value = :value WHERE key = :key"),
                 [{"key": k, "value": str(v)} for k, v in values.items()])
