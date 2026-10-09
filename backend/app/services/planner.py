"""Crew assignment, greedy sequencing, overflow reporting (TRD 4.7, revised after evaluation).

Priority decides WHAT is repaired, location decides HOW crews drive:
1. Each day takes the next highest-priority potholes, as many as all crews can repair that day.
2. That day's potholes are grouped by zone; zones go (most urgent first) to the crew with the most capacity
   left that day, split only when a zone doesn't fit; stops inside a zone are ordered greedily.
The first version ranked whole zones by average priority, which let one big zone of minor potholes delay a
Critical one elsewhere; the Evaluation page measured it (fewer Critical fixed, more travel), so it was replaced.
Not optimal like a full travelling-salesman solution, but fast and explainable.
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


def build_plan(pending: list[dict], crews: list[dict], days: int, start_date: date) -> tuple[list[dict], list[int]]:
    """Without touching the database (the evaluation simulates with it too).
    pending: potholes carrying zone_id. Returns (scheduled stops, unscheduled pothole ids)."""
    ranked = sorted(pending, key=lambda p: (-p["priority_score"], p["pothole_id"]))
    per_day = sum(c["capacity_per_day"] for c in crews)
    seq = {c["crew_id"]: 0 for c in crews}
    scheduled = []
    for day in range(days):
        today = ranked[day * per_day:(day + 1) * per_day]
        by_zone: dict[int, list[dict]] = {}
        for p in today:
            by_zone.setdefault(p["zone_id"], []).append(p)
        # most urgent zone first; ties by lowest pothole id so replanning gives the same result
        zone_order = sorted(by_zone.values(), key=lambda ps: (-ps[0]["priority_score"], ps[0]["pothole_id"]))
        left = {c["crew_id"]: c["capacity_per_day"] for c in crews}
        for members in zone_order:
            route = greedy_order(members)
            while route:
                crew = max(crews, key=lambda c: (left[c["crew_id"]], -c["crew_id"]))
                take, route = route[:left[crew["crew_id"]]], route[left[crew["crew_id"]]:]
                left[crew["crew_id"]] -= len(take)
                for p in take:
                    seq[crew["crew_id"]] += 1
                    scheduled.append({
                        "pothole_id": p["pothole_id"], "crew_id": crew["crew_id"], "crew_name": crew["name"],
                        "sequence_no": seq[crew["crew_id"]], "planned_date": (start_date + timedelta(days=day)).isoformat(),
                        "zone_id": p["zone_id"], "road_name": p["road_name"], "priority_score": p["priority_score"],
                        "priority_band": p["priority_band"],
                    })
    return scheduled, [p["pothole_id"] for p in ranked[days * per_day:]]


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

    scheduled, unscheduled = build_plan(pending, crews, days, start_date)
    for s in scheduled:  # 5-6.
        status.schedule(conn, s["pothole_id"], s["crew_id"], s["sequence_no"], date.fromisoformat(s["planned_date"]))
    return {
        "message": f"Scheduled {len(scheduled)} pothole(s)" + (f"; {len(unscheduled)} did not fit" if unscheduled else ""),
        "scheduled": scheduled, "unscheduled_count": len(unscheduled), "unscheduled_ids": unscheduled,
    }
