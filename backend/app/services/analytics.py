"""Summary numbers for the Analytics page. Fills in zero counts so every chart always shows every category."""
from sqlalchemy import Connection

from app.repositories import analytics

STATUSES = ("Pending", "Scheduled", "In Progress", "Repaired")
SEVERITIES = ("High", "Medium", "Low")


def summary(conn: Connection) -> dict:
    s = analytics.summary(conn)
    by_status = {r["status"]: r["n"] for r in s["by_status"]}
    by_severity = {r["severity_level"]: r["n"] for r in s["by_severity"]}
    s["by_status"] = [{"status": k, "n": by_status.get(k, 0)} for k in STATUSES]
    s["by_severity"] = [{"severity_level": k, "n": by_severity.get(k, 0)} for k in SEVERITIES]
    return s
