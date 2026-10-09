"""Zones (TRD 4.6), crews and the planner (TRD 4.7). Each test starts from an empty board and is rolled back."""
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.repositories import potholes
from app.services import planner, zones
from tests.test_api_core import make_pothole

M = 1 / 111_320  # one metre of latitude in degrees
TODAY = date.today()


@pytest.fixture
def board(conn):
    """No open potholes, no orders, no crews (inside the rolled-back test transaction)."""
    conn.execute(text("DELETE FROM repair_orders"))
    conn.execute(text("DELETE FROM crews"))
    conn.execute(text("DELETE FROM zones"))
    conn.execute(text("UPDATE potholes SET status = 'Repaired'"))
    return conn


def add(conn, lat, lng, score, status="Pending") -> int:
    pid = make_pothole(conn, "Pending", lat=lat, lng=lng)
    potholes.update(conn, pid, priority_score=score)
    if status != "Pending":
        potholes.update(conn, pid, status=status)
    return pid


def crew(client, name, cap) -> int:
    r = client.post("/api/crews", json={"name": name, "capacity_per_day": cap})
    assert r.status_code == 200, r.json()
    return r.json()["crew_id"]


# ---------- zones ----------

def test_cluster_close_points_together_far_point_alone():
    pts = [(12.0, 77.0), (12.0 + 50 * M, 77.0), (12.0 + 5000 * M, 77.0)]
    a, b, far = zones.cluster(pts, eps_m=200)
    assert a == b and far != a


def test_cluster_two_lone_points_get_different_zones():
    a, b = zones.cluster([(10.0, 10.0), (11.0, 11.0)], eps_m=200)
    assert a != b


def test_recompute_zones_api(client, board):
    near1, near2 = add(board, 20.0, 70.0, 0.5), add(board, 20.0 + 100 * M, 70.0, 0.7)
    far = add(board, 20.5, 70.0, 0.3)
    done = add(board, 20.0, 70.0, 0.9, status="Repaired")
    zs = client.post("/api/zones/recompute").json()
    assert sorted(z["pothole_count"] for z in zs) == [1, 2]
    pair = next(z for z in zs if z["pothole_count"] == 2)
    assert pair["avg_priority"] == pytest.approx(0.6)
    assert 40 < pair["radius_m"] < 60
    get = lambda i: potholes.get(board, i)["zone_id"]  # noqa: E731
    assert get(near1) == get(near2) != get(far)
    assert get(done) is None  # repaired potholes are not zoned


# ---------- crews ----------

def test_crew_crud_and_delete_rules(client, board):
    cid = crew(client, "Crew X", 3)
    assert client.put(f"/api/crews/{cid}", json={"name": "Crew X", "capacity_per_day": 4}).json()["capacity_per_day"] == 4
    assert client.post("/api/crews", json={"name": "Crew Y", "capacity_per_day": 0}).status_code == 400
    pid = add(board, 30.0, 30.0, 0.5)
    client.post("/api/plan", json={"days": 1})
    assert client.delete(f"/api/crews/{cid}").status_code == 409  # open order
    client.patch(f"/api/potholes/{pid}/status", json={"status": "Repaired"})
    assert client.delete(f"/api/crews/{cid}").status_code == 409  # finished order is history
    other = crew(client, "Crew Z", 2)
    assert client.delete(f"/api/crews/{other}").status_code == 200
    # last: a duplicate name aborts the (shared test) transaction
    assert client.post("/api/crews", json={"name": "Crew X", "capacity_per_day": 2}).status_code == 409


# ---------- planner ----------

def test_no_crews_is_400(client, board):
    add(board, 30.0, 30.0, 0.5)
    r = client.post("/api/plan", json={"days": 3})
    assert r.status_code == 400 and r.json()["error"] == "Add at least one crew first"


def test_nothing_to_plan(client, board):
    crew(client, "Crew A", 5)
    r = client.post("/api/plan", json={"days": 3})
    assert r.status_code == 200 and r.json()["scheduled"] == [] and "No pending" in r.json()["message"]


def test_bad_days_is_400(client, board):
    assert client.post("/api/plan", json={"days": 0}).status_code == 400


def test_one_crew_orders_by_priority_and_dates_follow_capacity(client, board):
    crew(client, "Crew A", 2)
    ids = [add(board, 30.0 + i * 20 * M, 30.0, s) for i, s in enumerate([0.3, 0.9, 0.6])]
    body = client.post("/api/plan", json={"days": 2, "start_date": TODAY.isoformat()}).json()
    stops = body["scheduled"]
    assert stops[0]["pothole_id"] == ids[1]  # highest priority first
    assert [s["sequence_no"] for s in stops] == [1, 2, 3]
    assert [s["planned_date"] for s in stops] == [TODAY.isoformat()] * 2 + [(TODAY + timedelta(days=1)).isoformat()]
    assert all(potholes.get(board, i)["status"] == "Scheduled" for i in ids)
    assert body["unscheduled_count"] == 0


def test_two_crews_share_two_zones(client, board):
    a, b = crew(client, "Crew A", 5), crew(client, "Crew B", 5)
    add(board, 30.0, 30.0, 0.9)
    add(board, 30.0 + 50 * M, 30.0, 0.8)
    add(board, 31.0, 30.0, 0.5)  # far away: second zone
    stops = client.post("/api/plan", json={"days": 1}).json()["scheduled"]
    assert {s["crew_id"] for s in stops} == {a, b}
    assert len({s["zone_id"] for s in stops if s["crew_id"] == a}) == 1  # a zone stays with one crew


def test_capacity_too_small_reports_unscheduled(client, board):
    crew(client, "Crew A", 1)
    ids = [add(board, 30.0 + i * 20 * M, 30.0, s) for i, s in enumerate([0.9, 0.5, 0.2])]
    body = client.post("/api/plan", json={"days": 2}).json()
    assert len(body["scheduled"]) == 2
    assert body["unscheduled_count"] == 1 and body["unscheduled_ids"] == [ids[2]]
    assert potholes.get(board, ids[2])["status"] == "Pending"
    assert "did not fit" in body["message"]


def test_replanning_twice_gives_same_result_and_leaves_in_progress(client, board):
    crew(client, "Crew A", 2)
    crew(client, "Crew B", 2)
    for i, s in enumerate([0.9, 0.4, 0.7, 0.2, 0.6]):
        add(board, 30.0 + (i % 2) * 0.5 + i * 30 * M, 30.0, s)
    busy = add(board, 30.0, 30.0, 0.95, status="In Progress")
    strip = lambda r: [(s["pothole_id"], s["crew_name"], s["sequence_no"], s["planned_date"]) for s in r["scheduled"]]  # noqa: E731
    first = client.post("/api/plan", json={"days": 2}).json()
    second = client.post("/api/plan", json={"days": 2}).json()
    assert strip(first) == strip(second)
    assert busy not in [s["pothole_id"] for s in first["scheduled"]]
    assert potholes.get(board, busy)["status"] == "In Progress"
    orders = board.execute(text("SELECT count(*) FROM repair_orders")).scalar_one()
    assert orders == len(second["scheduled"])  # old orders were replaced, not duplicated


def test_plan_recomputes_zones_first(client, board):
    crew(client, "Crew A", 5)
    pid = add(board, 30.0, 30.0, 0.5)
    assert potholes.get(board, pid)["zone_id"] is None
    client.post("/api/plan", json={"days": 1})
    assert potholes.get(board, pid)["zone_id"] is not None


def test_greedy_order_prefers_close_stops():
    start = {"pothole_id": 1, "priority_score": 0.9, "lat": 0.0, "lng": 0.0}
    near = {"pothole_id": 2, "priority_score": 0.5, "lat": 0.0, "lng": 100 * M}
    far = {"pothole_id": 3, "priority_score": 0.6, "lat": 0.0, "lng": 20_000 * M}
    assert [p["pothole_id"] for p in planner.greedy_order([far, near, start])] == [1, 2, 3]


# ---------- analytics ----------

def test_analytics_summary(client, board):
    a = add(board, 40.0, 40.0, 0.5)
    b = add(board, 40.0, 40.0, 0.7)
    potholes.update(board, b, detection_count=3)
    crew(client, "Crew A", 5)
    client.post("/api/plan", json={"days": 1})
    client.patch(f"/api/potholes/{a}/status", json={"status": "Repaired"})
    s = client.get("/api/analytics/summary").json()
    status = {r["status"]: r["n"] for r in s["by_status"]}
    assert status["Scheduled"] == 1 and status["Pending"] == 0  # zero counts are filled in
    assert s["top_roads"][0]["pending"] == 1 and s["top_roads"][0]["total_priority"] == 0.7
    assert s["hotspots"][0]["pothole_id"] == b and s["hotspots"][0]["repeat_count"] == 2
    assert s["avg_days_to_repair"] == 0.0
    assert s["done_by_crew"] == [{"name": "Crew A", "done": 1}]
