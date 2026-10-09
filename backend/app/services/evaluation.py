"""How good is the prioritization? Read-only simulation against simple baselines, plus weight sensitivity.

Every strategy repairs the same open potholes with the same crews (repairs per day) over the same days:
- SRPPS: the real planner (zones by priority, crew with most capacity left, greedy stop order)
- Priority only: same priority ranking, no zones (isolates what clustering saves in travel)
- First come, first served; Severity only; Random (fixed seed)

Metrics (what the problem statement asks to measure):
- priority_addressed_pct: share of total priority repaired within the horizon
- critical_fixed_pct: share of Critical potholes repaired within `critical_within` days
- avg_days_critical: average repair day of Critical potholes (not repaired = days + 1)
- exposure: sum of traffic x severity x days the pothole stays open (lower = less risk to road users)
- travel_km: crews' straight-line travel between stops, per day (no depot)

Honest caveat: exposure uses traffic and severity, which are also priority inputs, so a priority strategy is
expected to do well on it. The evaluation shows how much, and what it costs in travel and fairness (FCFS).
"""
import random
from datetime import date

from scipy.stats import spearmanr
from sqlalchemy import Connection

from app.repositories import config
from app.repositories import crews as crews_repo
from app.repositories import potholes
from app.services import geo, planner, priority, zones


class EvaluationError(Exception):
    pass


def fill(order: list[dict], crews: list[dict], days: int) -> dict[int, list[list[dict]]]:
    """Baseline schedule: each day every crew takes the next `capacity` potholes in the given order.
    Returns {crew_id: [stops on day 1, stops on day 2, ...]}."""
    plan = {c["crew_id"]: [[] for _ in range(days)] for c in crews}
    it = iter(order)
    for day in range(days):
        for c in crews:
            for _ in range(c["capacity_per_day"]):
                p = next(it, None)
                if p is None:
                    return plan
                plan[c["crew_id"]][day].append(p)
    return plan


def srpps(pool: list[dict], crews: list[dict], days: int) -> dict[int, list[list[dict]]]:
    start = date.today()
    stops, _ = planner.build_plan(pool, crews, days, start)
    by_id = {p["pothole_id"]: p for p in pool}
    plan = {c["crew_id"]: [[] for _ in range(days)] for c in crews}
    for s in sorted(stops, key=lambda s: (s["crew_id"], s["sequence_no"])):
        plan[s["crew_id"]][(date.fromisoformat(s["planned_date"]) - start).days].append(by_id[s["pothole_id"]])
    return plan


def metrics(plan: dict[int, list[list[dict]]], pool: list[dict], days: int, critical_within: int) -> dict:
    repair_day = {p["pothole_id"]: d + 1 for crew_days in plan.values() for d, stops in enumerate(crew_days)
                  for p in stops}
    total_priority = sum(p["priority_score"] for p in pool) or 1.0
    critical = [p for p in pool if p["priority_band"] == "Critical"]
    travel_m = sum(geo.distance_m(a["lat"], a["lng"], b["lat"], b["lng"])
                   for crew_days in plan.values() for stops in crew_days for a, b in zip(stops, stops[1:]))
    return {
        "repaired": len(repair_day),
        "priority_addressed_pct": round(100 * sum(p["priority_score"] for p in pool if p["pothole_id"] in repair_day)
                                        / total_priority, 1),
        "critical_fixed_pct": round(100 * sum(repair_day.get(p["pothole_id"], days + 1) <= critical_within
                                              for p in critical) / len(critical), 1) if critical else None,
        "avg_days_critical": round(sum(repair_day.get(p["pothole_id"], days + 1) for p in critical) / len(critical), 2)
        if critical else None,
        "exposure": round(sum((p.get("traffic_score") or 0) * p["severity_score"] * repair_day.get(p["pothole_id"], days)
                              for p in pool), 2),
        "travel_km": round(travel_m / 1000, 2),
    }


def sensitivity(pool: list[dict], cfg: dict[str, float], top_n: int) -> list[dict]:
    """Change one weight by -20% / +20% (then rescale all weights to sum to 1) and compare the rankings."""
    def ranking(c):
        return sorted(pool, key=lambda p: (-priority.for_pothole(p, c)["priority_score"], p["pothole_id"]))

    base = ranking(cfg)
    n = min(top_n, len(pool))
    base_top = {p["pothole_id"] for p in base[:n]}
    base_pos = {p["pothole_id"]: i for i, p in enumerate(base)}
    rows = []
    for w in priority.WEIGHTS:
        for factor in (0.8, 1.2):
            changed = {**cfg, w: cfg[w] * factor}
            total = sum(changed[k] for k in priority.WEIGHTS)
            changed.update({k: changed[k] / total for k in priority.WEIGHTS})
            new = ranking(changed)
            rho = spearmanr([base_pos[p["pothole_id"]] for p in new], range(len(new)))[0] if len(new) > 1 else 1.0
            rows.append({"weight": w, "change": f"{round((factor - 1) * 100):+d}%",
                         "top_n_overlap_pct": round(100 * len(base_top & {p["pothole_id"] for p in new[:n]}) / n, 1)
                         if n else None,
                         "spearman": round(float(rho), 3)})
    return rows


def simulate(pool: list[dict], crews: list[dict], days: int, critical_within: int, cfg: dict[str, float],
             top_n: int = 10, seed: int = 42) -> dict:
    """Pure core of the evaluation (pool rows need zone_id; the caller assigns fresh zones)."""
    shuffled = pool[:]
    random.Random(seed).shuffle(shuffled)
    strategies = {
        "SRPPS (priority + zones)": srpps(pool, crews, days),
        "Priority only (no zones)": fill(sorted(pool, key=lambda p: (-p["priority_score"], p["pothole_id"])), crews, days),
        "First come, first served": fill(sorted(pool, key=lambda p: (p["first_detected_at"], p["pothole_id"])), crews, days),
        "Severity only": fill(sorted(pool, key=lambda p: (-p["severity_score"], p["pothole_id"])), crews, days),
        f"Random (seed {seed})": fill(shuffled, crews, days),
    }
    results = [{"strategy": name, **metrics(plan, pool, days, critical_within)} for name, plan in strategies.items()]
    fcfs = next(r for r in results if r["strategy"].startswith("First come"))["exposure"]
    for r in results:
        r["exposure_reduction_vs_fcfs_pct"] = round(100 * (fcfs - r["exposure"]) / fcfs, 1) if fcfs else None
    return {
        "open_potholes": len(pool),
        "critical_potholes": sum(p["priority_band"] == "Critical" for p in pool),
        "capacity_per_day": sum(c["capacity_per_day"] for c in crews),
        "days": days, "critical_within": critical_within,
        "strategies": results,
        "sensitivity": sensitivity(pool, cfg, top_n), "top_n": min(top_n, len(pool)),
    }


def evaluate(conn: Connection, days: int, critical_within: int, top_n: int = 10) -> dict:
    """Read-only: simulates on the open potholes a new plan would schedule (Pending and Scheduled)."""
    crews = crews_repo.list_all(conn)
    if not crews:
        raise EvaluationError("Add at least one crew first")
    pool = [dict(p) for p in potholes.open_rows(conn) if p["status"] in ("Pending", "Scheduled")]
    if not pool:
        raise EvaluationError("No open potholes to evaluate")
    cfg = config.get_all(conn)
    for p, label in zip(pool, zones.cluster([(p["lat"], p["lng"]) for p in pool], cfg["ZONE_EPS_M"])):
        p["zone_id"] = label  # temporary zones for the simulation; stored zones are not touched
    return simulate(pool, crews, days, critical_within, cfg, top_n)
