"""The ONE place that applies status changes and side effects (TRD 4.9)."""
from datetime import date, datetime, timezone

from sqlalchemy import Connection

from app.repositories import potholes, repair_orders

# (from, to) changes a user may make. Pending -> Scheduled needs a crew and date, so only the planner does it.
USER_CHANGES = {
    ("Scheduled", "Pending"),
    ("Pending", "In Progress"), ("Scheduled", "In Progress"),
    ("Pending", "Repaired"), ("Scheduled", "Repaired"), ("In Progress", "Repaired"),
}


class InvalidStatusChange(Exception):
    pass


def change_status(conn: Connection, pothole_id: int, new: str) -> None:
    """User action (Start / Mark repaired / Unschedule). LookupError if missing, InvalidStatusChange if not allowed."""
    p = potholes.get(conn, pothole_id, for_update=True)
    if p is None:
        raise LookupError(pothole_id)
    if (p["status"], new) not in USER_CHANGES:
        raise InvalidStatusChange(f"{p['status']} -> {new}")
    if new == "Pending":  # unschedule
        repair_orders.delete_for_pothole(conn, pothole_id)
        potholes.update(conn, pothole_id, status="Pending")
    elif new == "In Progress":  # keep the order if there is one
        potholes.update(conn, pothole_id, status="In Progress")
    else:  # Repaired: final; repaired potholes leave their zone (zones only hold open potholes)
        potholes.update(conn, pothole_id, status="Repaired", repaired_at=datetime.now(timezone.utc), zone_id=None)
        repair_orders.complete_for_pothole(conn, pothole_id)


def schedule(conn: Connection, pothole_id: int, crew_id: int, sequence_no: int, planned_date: date) -> None:
    """Planner only: Pending -> Scheduled with its repair order."""
    p = potholes.get(conn, pothole_id, for_update=True)
    if p is None or p["status"] != "Pending":
        raise InvalidStatusChange(f"cannot schedule pothole {pothole_id}")
    repair_orders.insert(conn, pothole_id, crew_id, sequence_no, planned_date)
    potholes.update(conn, pothole_id, status="Scheduled")
