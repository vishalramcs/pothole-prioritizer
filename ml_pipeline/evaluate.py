"""Step 7: evaluate the prioritization -> outputs/scored.csv, outputs/evaluation.json, outputs/evaluation.md.

Reference ranking = the rule-based priority_score (add_priority). There is no real-world ground truth, so
"agreement with the reference" means "how well the model reproduces the formula", nothing more.

Strategies compared under the same budget and crews (repairs taken in each strategy's order until the
budget runs out; repair day from cumulative crew hours):
  model (hybrid net), reference formula (upper bound), severity only, first come first served (longest
  waiting first, days_unrepaired is synthetic), random (seed 42).
"""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from sklearn.metrics import confusion_matrix, f1_score

import schedule
from build_real_dataset import CTX_WEIGHTS, add_priority
from hybrid import EVAL_TF, Rows, features, load_model, load_table, predict, seed_everything

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
BUDGET, CREWS, HOURS, WITHIN_DAYS, TOP_N = 200_000, 2, 8.0, 2, 10
APP_DETECTOR = HERE.parent / "backend" / "ml" / "weights" / "pothole.pt"


def ndcg_at_k(relevance: np.ndarray, scores: np.ndarray, k: int) -> float:
    order = np.argsort(-scores, kind="stable")[:k]
    ideal = np.sort(relevance)[::-1][:k]
    disc = 1 / np.log2(np.arange(2, k + 2))
    return float((relevance[order] * disc[:len(order)]).sum() / (ideal * disc[:len(ideal)]).sum())


def sev_class(s) -> np.ndarray:
    return np.digitize(np.asarray(s), [0.33, 0.66])  # 0 low, 1 medium, 2 high


def simulate(df: pd.DataFrame, scores: np.ndarray) -> dict:
    """Repairs in `scores` order while the budget lasts; day = ceil(cumulative crew hours / daily crew hours)."""
    order = np.argsort(-scores, kind="stable")
    cost = np.cumsum(df.cost_inr.to_numpy()[order])
    done = order[cost <= BUDGET]
    day = np.full(len(df), np.nan)
    day[done] = np.ceil(np.cumsum(df.crew_hours.to_numpy()[done]) / (CREWS * HOURS))
    horizon = np.nanmax(day) if len(done) else 0
    open_days = df.days_unrepaired.to_numpy() + np.nan_to_num(day, nan=horizon + 1)  # not repaired: horizon + 1
    ref = df.priority_score.to_numpy()
    high = df.severity.to_numpy() >= 0.66
    critical = ref >= np.quantile(ref, 0.75)  # top quarter by the reference
    return {
        "repaired": int(len(done)),
        "reference_priority_addressed_pct": round(100 * ref[done].sum() / ref.sum(), 1),
        f"high_severity_fixed_within_{WITHIN_DAYS}d_pct": round(100 * float((day[high] <= WITHIN_DAYS).mean()), 1),
        "avg_repair_day_critical": round(float(np.nan_to_num(day[critical], nan=horizon + 1).mean()), 2),
        "exposure": round(float((df.traffic_vehicles_per_day * df.severity * open_days).sum() / 1e6), 2),
    }


def sensitivity(df: pd.DataFrame) -> list[dict]:
    base = add_priority(df.copy()).priority_score.to_numpy()
    top = set(np.argsort(-base, kind="stable")[:TOP_N])
    rows = []
    for k in CTX_WEIGHTS:
        for f in (0.8, 1.2):
            w = {**CTX_WEIGHTS, k: CTX_WEIGHTS[k] * f}
            total = sum(w.values())
            w = {key: v / total for key, v in w.items()}  # keep the weights summing to 1
            new = add_priority(df.copy(), w).priority_score.to_numpy()
            rows.append({"weight": k, "change": f"{round((f - 1) * 100):+d}%",
                         f"top{TOP_N}_overlap_pct": round(100 * len(top & set(np.argsort(-new, kind='stable')[:TOP_N])) / TOP_N, 1),
                         "spearman": round(float(spearmanr(base, new)[0]), 3)})
    return rows


def detection_map50() -> float | None:
    """The app's detector on all 241 annotated images (none of them were used to train it, as far as we know)."""
    if not APP_DETECTOR.exists():
        return None
    from ultralytics import YOLO

    root = OUT / "yolo_eval"
    for sub, src in (("images", HERE / "pothole_images"), ("labels", HERE / "pothole_labels")):
        shutil.copytree(src, root / sub, dirs_exist_ok=True)
    # ultralytics insists on a train entry even for validation; nothing is trained here
    (root / "data.yaml").write_text(f"path: {root.as_posix()}\ntrain: images\nval: images\nnames:\n  0: pothole\n")
    res = YOLO(str(APP_DETECTOR)).val(data=str(root / "data.yaml"), split="val", imgsz=640, batch=8,
                                     plots=False, verbose=False, project=str(OUT), name="yolo_val", exist_ok=True)
    return round(float(res.box.map50), 3)


def main() -> None:
    seed_everything()
    OUT.mkdir(exist_ok=True)
    df = load_table()
    model, scaler = load_model()
    loader = torch.utils.data.DataLoader(Rows(df, scaler(features(df)), EVAL_TF), batch_size=32)
    df["pred_priority"], df["pred_severity"] = predict(model, loader)
    df = pd.concat([df, schedule.estimate(df.pred_severity)], axis=1)
    df.to_csv(OUT / "scored.csv", index=False)

    report = {"rows": int(len(df)), "budget_inr": BUDGET, "crews": CREWS, "hours_per_day": HOURS}
    # 1. agreement with the reference ranking, on unseen areas (test) vs seen (train)
    rng = np.random.default_rng(42)
    rank = []
    for split in ("train", "test"):
        part = df[df.split == split]
        ref = part.priority_score.to_numpy()
        for name, s in [("model", part.pred_priority), ("severity only", part.severity),
                        ("first come, first served", part.days_unrepaired), ("random", rng.random(len(part)))]:
            s = np.asarray(s, dtype=float)
            rank.append({"split": split, "strategy": name, "spearman": round(float(spearmanr(ref, s)[0]), 3),
                         f"ndcg@{TOP_N}": round(ndcg_at_k(ref, s, TOP_N), 3)})
        if split == "test":
            err = part.pred_priority - part.priority_score
            report["test_priority_mae"] = round(float(err.abs().mean()), 4)
            report["test_priority_rmse"] = round(float(np.sqrt((err ** 2).mean())), 4)
    report["ranking"] = rank
    # 2. the same budget, crews and costs, different orders
    sims = [{"strategy": name, **simulate(df, np.asarray(s, dtype=float))} for name, s in [
        ("model", df.pred_priority), ("reference formula (upper bound)", df.priority_score),
        ("severity only", df.severity), ("first come, first served", df.days_unrepaired),
        ("random", np.random.default_rng(42).random(len(df)))]]
    fcfs = next(s["exposure"] for s in sims if s["strategy"].startswith("first come"))
    for s in sims:
        s["exposure_vs_fcfs_pct"] = round(100 * (s["exposure"] - fcfs) / fcfs, 1)
    report["budget_simulation"] = sims
    # 3. travel saved by clustering (model's budget selection, routed with vs without clusters)
    sel = df.iloc[schedule.knapsack(df.pred_priority.to_numpy(), df.cost_inr.to_numpy(), BUDGET)].copy()
    sel["priority"] = sel.pred_priority
    depot = (float(df.lat.mean()), float(df.lon.mean()))
    sel["cluster"] = schedule.clusters(sel.lat.to_numpy(), sel.lon.to_numpy())
    with_c = schedule.daily_schedule(sel, CREWS, HOURS, depot).travel_km.sum()
    sel["cluster"] = np.arange(len(sel))  # every pothole alone = plain priority order
    without = schedule.daily_schedule(sel, CREWS, HOURS, depot).travel_km.sum()
    report["travel_km"] = {"with_clusters": round(float(with_c), 1), "priority_order_only": round(float(without), 1),
                           "saved_pct": round(100 * (without - with_c) / without, 1)}
    # 4. sensitivity of the reference ranking to its weights
    report["sensitivity"] = sensitivity(df.drop(columns=["priority_score", "priority_rank"]))
    # 5. severity head vs weak labels (test split), and the app's detector
    test = df[df.split == "test"]
    report["severity_test_mae"] = round(float((test.pred_severity - test.severity).abs().mean()), 4)
    report["severity_test_macro_f1"] = round(float(f1_score(sev_class(test.severity), sev_class(test.pred_severity),
                                                            average="macro", labels=[0, 1, 2], zero_division=0)), 3)
    report["severity_test_confusion"] = confusion_matrix(sev_class(test.severity), sev_class(test.pred_severity),
                                                         labels=[0, 1, 2]).tolist()
    report["app_detector_map50"] = detection_map50()
    (OUT / "evaluation.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
