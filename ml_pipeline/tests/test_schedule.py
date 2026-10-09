from itertools import combinations

import numpy as np
import pandas as pd

from schedule import clusters, daily_schedule, estimate, greedy, knapsack, nn_route, with_cluster_bonus


def brute_force(values, costs, budget):
    best = (0.0, ())
    for r in range(len(values) + 1):
        for combo in combinations(range(len(values)), r):
            if costs[list(combo)].sum() <= budget:
                best = max(best, (values[list(combo)].sum(), combo))
    return best[0]


def test_knapsack_is_optimal_and_within_budget():
    rng = np.random.default_rng(0)
    for _ in range(20):
        values = rng.random(9)
        costs = rng.integers(1, 30, 9) * 100.0  # whole hundreds, so rounding is exact
        budget = float(rng.integers(5, 120) * 100)
        idx = knapsack(values, costs, budget)
        assert costs[idx].sum() <= budget
        assert np.isclose(values[idx].sum(), brute_force(values, costs, budget))
        assert values[greedy(values, costs, budget)].sum() <= values[idx].sum() + 1e-9


def test_knapsack_beats_greedy_on_classic_case():
    # greedy takes the dense small item and then cannot fit the big one
    values, costs = np.array([0.6, 1.0]), np.array([100.0, 1000.0])
    assert greedy(values, costs, 1000) == [0] and knapsack(values, costs, 1000) == [1]


def test_cost_grows_with_severity():
    e = estimate(np.array([0.0, 1.0]))
    assert e.cost_inr[1] > e.cost_inr[0] and e.crew_hours[1] > e.crew_hours[0]


def test_clusters_and_bonus():
    lat = np.array([11.0, 11.0005, 11.05])  # ~55 m apart, and one ~5.5 km away
    lon = np.array([77.0, 77.0, 77.0])
    lab = clusters(lat, lon)
    assert lab[0] == lab[1] != lab[2] and (lab >= 0).all()
    v = with_cluster_bonus(np.ones(3), lab)
    assert v[0] == v[1] > v[2] == 1.0


def test_nn_route_visits_all_nearest_first():
    pts = [(11.0, 77.10), (11.0, 77.01), (11.0, 77.05)]
    assert nn_route(pts, (11.0, 77.0)) == [1, 2, 0]


def test_daily_schedule_respects_hours():
    sel = pd.DataFrame({"pothole_id": [f"P{i}" for i in range(6)], "lat": [11.0] * 6, "lon": [77.0 + i * 1e-4 for i in range(6)],
                        "cluster": [0] * 6, "priority": np.linspace(0.9, 0.4, 6), "cost_inr": [3000] * 6, "crew_hours": [3.0] * 6})
    plan = daily_schedule(sel, crews=1, hours=8, depot=(11.0, 77.0))
    assert len(plan) == 6 and plan.day.max() == 3  # 2 sites of 3 h fit in an 8 h day
    assert plan.groupby(["day", "crew"]).crew_hours.sum().max() <= 8
