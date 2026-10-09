"""Step 5: which potholes to repair under a budget, and in what order (daily crew schedule).

1. Cost and crew hours per pothole from its predicted severity (ASSUMED rates, see constants).
2. Select repairs: 0/1 knapsack (exact, maximises total priority within the budget) vs greedy by
   priority per rupee (the usual baseline).
3. DBSCAN groups potholes within CLUSTER_EPS_M; each pothole's value gets a small bonus for sharing a
   trip with others, so cheap neighbouring repairs are picked together.
4. Clusters in order of total priority, nearest-neighbour route inside each, packed into crew-days by
   hours (repair + travel) -> outputs/daily_schedule.csv.

Run:  python schedule.py [--budget 200000] [--crews 2] [--hours 8]
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

HERE = Path(__file__).resolve().parent
# shortcut: assumed rates, not from a road authority; replace with real tender rates before trusting rupees
AREA_M2_MIN, AREA_M2_PER_SEV = 0.2, 2.8      # severity 0 -> 0.2 m2 patch, severity 1 -> 3.0 m2
COST_FIXED, COST_PER_M2 = 1500, 1200         # INR: mobilisation per site + cold-mix patch per m2
HOURS_FIXED, HOURS_PER_M2 = 0.5, 0.8         # crew hours per site
CLUSTER_EPS_M, CLUSTER_BONUS = 300, 0.15     # up to +15% value when 3+ neighbours share the trip
SPEED_KMH = 20                               # city driving between sites
EARTH_R = 6_371_000


def estimate(severity: np.ndarray) -> pd.DataFrame:
    area = AREA_M2_MIN + AREA_M2_PER_SEV * np.asarray(severity)
    return pd.DataFrame({"repair_area_m2": area.round(2), "cost_inr": (COST_FIXED + COST_PER_M2 * area).round(0),
                         "crew_hours": (HOURS_FIXED + HOURS_PER_M2 * area).round(2)})


def knapsack(values: np.ndarray, costs: np.ndarray, budget: float, unit: int = 100) -> list[int]:
    """Exact 0/1 knapsack by dynamic programming over cost rounded UP to `unit` (never exceeds the budget)."""
    w = np.ceil(np.asarray(costs) / unit).astype(int)
    cap = int(budget // unit)
    best = np.zeros(cap + 1)
    take = np.zeros((len(w), cap + 1), dtype=bool)
    for i, (wi, vi) in enumerate(zip(w, values)):
        if wi > cap:
            continue
        cand = best[:cap + 1 - wi] + vi
        better = cand > best[wi:]
        take[i, wi:] = better
        best[wi:] = np.where(better, cand, best[wi:])
    chosen, c = [], cap
    for i in range(len(w) - 1, -1, -1):
        if take[i, c]:
            chosen.append(i)
            c -= w[i]
    return sorted(chosen)


def greedy(values: np.ndarray, costs: np.ndarray, budget: float) -> list[int]:
    order = np.argsort(-np.asarray(values) / np.asarray(costs), kind="stable")
    chosen, spent = [], 0.0
    for i in order:
        if spent + costs[i] <= budget:
            chosen.append(int(i))
            spent += costs[i]
    return sorted(chosen)


def clusters(lat: np.ndarray, lon: np.ndarray, eps_m: float = CLUSTER_EPS_M) -> np.ndarray:
    """DBSCAN (haversine); lone points get their own cluster id instead of -1."""
    labels = DBSCAN(eps=eps_m / EARTH_R, min_samples=2, metric="haversine").fit(np.radians(np.c_[lat, lon])).labels_
    nxt = labels.max() + 1
    for i in np.where(labels == -1)[0]:
        labels[i], nxt = nxt, nxt + 1
    return labels


def with_cluster_bonus(values: np.ndarray, labels: np.ndarray) -> np.ndarray:
    size = pd.Series(labels).map(pd.Series(labels).value_counts()).to_numpy()
    return values * (1 + CLUSTER_BONUS * np.minimum(size - 1, 3) / 3)


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h)) / 1000


def nn_route(points: list[tuple[float, float]], start: tuple[float, float]) -> list[int]:
    """Nearest-neighbour order of `points` starting from `start`."""
    left, order, here = list(range(len(points))), [], start
    while left:
        j = min(left, key=lambda k: km(here, points[k]))
        order.append(j)
        left.remove(j)
        here = points[j]
    return order


def daily_schedule(sel: pd.DataFrame, crews: int, hours: float, depot: tuple[float, float]) -> pd.DataFrame:
    """Clusters by total priority, NN route inside each, packed into crew-days by repair + travel hours."""
    rows, day, crew, used, here = [], 1, 1, 0.0, depot
    for _, grp in sorted(sel.groupby("cluster"), key=lambda g: -g[1].priority.sum()):
        pts = list(zip(grp.lat, grp.lon))
        for j in nn_route(pts, here):
            r = grp.iloc[j]
            travel = km(here, pts[j])
            need = r.crew_hours + travel / SPEED_KMH
            if used + need > hours and used > 0:  # next crew, or next day when all crews are full
                crew, used = (crew + 1, 0.0) if crew < crews else (1, 0.0)
                day += crew == 1
                here, travel = depot, km(depot, pts[j])
                need = r.crew_hours + travel / SPEED_KMH
            rows.append({"day": day, "crew": crew, "pothole_id": r.pothole_id, "cluster": int(r.cluster),
                         "lat": r.lat, "lon": r.lon, "priority": round(r.priority, 4), "cost_inr": r.cost_inr,
                         "crew_hours": r.crew_hours, "travel_km": round(travel, 2)})
            used += need
            here = pts[j]
    out = pd.DataFrame(rows)
    out.insert(2, "stop", out.groupby(["day", "crew"]).cumcount() + 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=200_000)
    ap.add_argument("--crews", type=int, default=2)
    ap.add_argument("--hours", type=float, default=8)
    a = ap.parse_args()
    df = pd.read_csv(HERE / "outputs" / "scored.csv")  # from evaluate.py (model predictions for every row)
    df = pd.concat([df, estimate(df.pred_severity)], axis=1)
    df["priority"] = df.pred_priority
    df["cluster"] = clusters(df.lat.to_numpy(), df.lon.to_numpy())
    values, costs = df.priority.to_numpy(), df.cost_inr.to_numpy()

    picks = {"knapsack": knapsack(values, costs, a.budget), "greedy (priority per rupee)": greedy(values, costs, a.budget),
             "knapsack + cluster bonus": knapsack(with_cluster_bonus(values, df.cluster.to_numpy()), costs, a.budget)}
    print(f"{len(df)} potholes, total cost {costs.sum():,.0f} INR, budget {a.budget:,.0f} INR")
    for name, idx in picks.items():
        print(f"  {name:28} repairs {len(idx):3}  priority {values[idx].sum():6.2f}  cost {costs[idx].sum():9,.0f}")
    sel = df.iloc[picks["knapsack + cluster bonus"]]
    depot = (float(df.lat.mean()), float(df.lon.mean()))
    plan = daily_schedule(sel, a.crews, a.hours, depot)
    plan.to_csv(HERE / "outputs" / "daily_schedule.csv", index=False)
    print(f"daily_schedule.csv: {len(plan)} stops over {plan.day.max()} day(s), {plan.travel_km.sum():.1f} km travel")


if __name__ == "__main__":
    main()
