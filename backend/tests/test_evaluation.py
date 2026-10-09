"""Evaluation: simulation metrics on hand-made pools, sensitivity, and the API."""
import pytest

from app.services import evaluation
from tests.test_planning import add, board, crew  # noqa: F401 (board is a fixture)
from tests.test_scoring import CFG

M = 1 / 111_320
CREWS = [{"crew_id": 1, "name": "A", "capacity_per_day": 1}]


def pothole(pid, lat, lng, prio, sev, traffic, band="Moderate", age=0, zone=0):
    return {"pothole_id": pid, "lat": lat, "lng": lng, "priority_score": prio, "severity_score": sev,
            "traffic_score": traffic, "importance_score": 0.5, "detection_count": 1, "recurrence_count": 0,
            "facility_score": 0.0, "priority_band": band, "first_detected_at": f"2026-01-0{age + 1}",
            "zone_id": zone, "road_name": "r"}


def by_name(result, prefix):
    return next(r for r in result["strategies"] if r["strategy"].startswith(prefix))


def test_priority_first_beats_fcfs_on_exposure_and_critical():
    pool = [
        pothole(1, 10.0, 10.0, 0.30, 0.2, 0.2, age=0),                      # oldest, harmless
        pothole(2, 10.0, 10.0 + 50 * M, 0.35, 0.3, 0.2, age=1),
        pothole(3, 10.0, 10.0 + 90 * M, 0.90, 1.0, 0.9, band="Critical", age=2),  # newest, dangerous
    ]
    r = evaluation.simulate(pool, CREWS, days=2, critical_within=1, cfg=CFG)
    srpps, fcfs = by_name(r, "SRPPS"), by_name(r, "First come")
    assert srpps["critical_fixed_pct"] == 100.0 and fcfs["critical_fixed_pct"] == 0.0
    assert srpps["avg_days_critical"] == 1 and fcfs["avg_days_critical"] == 3  # not repaired in 2 days -> 3
    assert srpps["exposure"] < fcfs["exposure"]
    assert srpps["exposure_reduction_vs_fcfs_pct"] > 0
    assert srpps["repaired"] == fcfs["repaired"] == 2  # same capacity for everyone


def test_zones_save_travel_over_priority_only():
    # two clusters 5 km apart, priorities interleaved so a pure priority order zig-zags between them
    west = [pothole(i, 10.0, 10.0 + i * 20 * M, p, 0.5, 0.5, zone=0) for i, p in [(1, 0.9), (3, 0.7)]]
    east = [pothole(i, 10.0, 10.05 + i * 20 * M, p, 0.5, 0.5, zone=1) for i, p in [(2, 0.8), (4, 0.6)]]
    crews = [{"crew_id": 1, "name": "A", "capacity_per_day": 4}]
    r = evaluation.simulate(west + east, crews, days=1, critical_within=1, cfg=CFG)
    assert by_name(r, "SRPPS")["travel_km"] < by_name(r, "Priority only")["travel_km"]


def test_metrics_with_no_critical_potholes():
    r = evaluation.simulate([pothole(1, 10.0, 10.0, 0.3, 0.2, 0.2)], CREWS, days=1, critical_within=1, cfg=CFG)
    assert by_name(r, "SRPPS")["critical_fixed_pct"] is None and r["critical_potholes"] == 0


def test_sensitivity_covers_every_weight_both_ways():
    pool = [pothole(i, 10.0, 10.0, 0.0, s, t) for i, (s, t) in enumerate([(0.9, 0.1), (0.5, 0.5), (0.1, 0.9)], 1)]
    rows = evaluation.sensitivity(pool, CFG, top_n=2)
    assert len(rows) == 10 and {r["change"] for r in rows} == {"-20%", "+20%"}
    assert all(0 <= r["top_n_overlap_pct"] <= 100 and -1 <= r["spearman"] <= 1 for r in rows)


def test_evaluation_api(client, board):  # noqa: F811
    assert client.get("/api/evaluation").status_code == 400  # no crews on the empty board
    crew(client, "Crew A", 2)
    assert client.get("/api/evaluation").json() == {"error": "No open potholes to evaluate"}
    for i, s in enumerate([0.9, 0.2, 0.6]):
        add(board, 30.0 + i * 30 * M, 30.0, s)
    r = client.get("/api/evaluation", params={"days": 1, "critical_within": 1})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["open_potholes"] == 3 and body["capacity_per_day"] == 2
    assert len(body["strategies"]) == 5 and all(s["repaired"] == 2 for s in body["strategies"])
    assert client.get("/api/evaluation", params={"days": 0}).status_code == 400
    # read-only: nothing got scheduled
    assert client.get("/api/potholes", params={"status": "Scheduled"}).json() == []


@pytest.mark.parametrize("days", [1, 3])
def test_fill_never_exceeds_capacity(days):
    crews = [{"crew_id": 1, "name": "A", "capacity_per_day": 2}, {"crew_id": 2, "name": "B", "capacity_per_day": 1}]
    pool = [pothole(i, 10.0, 10.0, 0.5, 0.5, 0.5) for i in range(20)]
    plan = evaluation.fill(pool, crews, days)
    assert all(len(plan[1][d]) <= 2 and len(plan[2][d]) <= 1 for d in range(days))
    assert sum(len(s) for c in plan.values() for s in c) == 3 * days
