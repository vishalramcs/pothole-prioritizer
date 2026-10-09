"""Crew assignment, greedy sequencing, overflow reporting (TRD 4.7).

Not optimal like a full travelling-salesman solution, but fast and explainable:
zones by average Pending priority -> crew with most capacity left -> greedy stop order inside the zone.
"""
from datetime import date, timedelta

from sqlalchemy import Connection

from app.repositories import crews as crews_repo
from app.repositories import potholes
from app.services import geo, status, zones


class PlanError(Exception):
    pass


def greedy_order(stops: list[dict]) -> list[dict]:
    """Start at the highest priority, then keep taking the best priority / (1 + km from the last stop)."""
    left = sorted(stops, key=lambda p: (-p["priority_score"], p["pothole_id"]))
    if not left:
        return []
    route = [left.pop(0)]
    while left:
        last = route[-1]
        best = max(left, key=lambda p: (
            p["priority_score"] / (1 + geo.distance_m(last["lat"], last["lng"], p["lat"], p["lng"]) / 1000),
            -p["pothole_id"],
        ))
        left.remove(best)
        route.append(best)
    return route


def plan(conn: Connection, days: int, start_date: date | None = None) -> dict:
    """Runs in the request's single transaction: reset, recompute zones, schedule. Any error rolls it all back."""
    start_date = start_date or date.today()
    crews = crews_repo.list_all(conn)
    if not crews:
        raise PlanError("Add at least one crew first")

    status.unschedule_all(conn)  # 1. reset the earlier plan (In Progress is left alone)
    zones.recompute(conn)  # 2. fresh zones
    pending = [p for p in potholes.open_rows(conn) if p["status"] == "Pending"]
    if not pending:
        return {"message": "No pending potholes to schedule", "scheduled": [], "unscheduled_count": 0,
                "unscheduled_ids": []}

    by_zone: dict[int, list[dict]] = {}
    for p in pending:
        by_zone.setdefault(p["zone_id"], []).append(p)
    avg = lambda ps: sum(p["priority_score"] for p in ps) / len(ps)  # noqa: E731
    # 3. zones by average Pending priority; ties by lowest pothole id so replanning gives the same result
    zone_order = sorted(by_zone.values(), key=lambda ps: (-avg(ps), min(p["pothole_id"] for p in ps)))

    left = {c["crew_id"]: c["capacity_per_day"] * days for c in crews}
    seq = {c["crew_id"]: 0 for c in crews}
    by_id = {c["crew_id"]: c for c in crews}
    scheduled, unscheduled = [], []
    for members in zone_order:
        crew_id = max(left, key=lambda c: (left[c], -c))  # 4. most capacity left; ties: lowest crew id
        for p in greedy_order(members):
            if left[crew_id] == 0:  # doesn't fit: stays Pending and is reported
                unscheduled.append(p["pothole_id"])
                continue
            left[crew_id] -= 1
            seq[crew_id] += 1
            planned = start_date + timedelta(days=(seq[crew_id] - 1) // by_id[crew_id]["capacity_per_day"])
            status.schedule(conn, p["pothole_id"], crew_id, seq[crew_id], planned)  # 5-6.
            scheduled.append({
                "pothole_id": p["pothole_id"], "crew_id": crew_id, "crew_name": by_id[crew_id]["name"],
                "sequence_no": seq[crew_id], "planned_date": planned.isoformat(), "zone_id": p["zone_id"],
                "road_name": p["road_name"], "priority_score": p["priority_score"], "priority_band": p["priority_band"],
            })
    return {
        "message": f"Scheduled {len(scheduled)} pothole(s)" + (f"; {len(unscheduled)} did not fit" if unscheduled else ""),
        "scheduled": scheduled, "unscheduled_count": len(unscheduled), "unscheduled_ids": unscheduled,
    }
