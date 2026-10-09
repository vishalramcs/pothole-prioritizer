"""Step 2: WEAK severity labels from the annotated boxes -> cnn_severity.csv.

These are not measured severity: there is no depth or ground-truth severity in the dataset. They are a formula
on the hand-drawn boxes:
    area term  = clip(pothole_area_ratio / 0.3, 0, 1)   pothole_area_ratio = summed box area / image area (max 1)
    count term = clip(pothole_count / 8, 0, 1)
    depth term = not available
    severity   = (0.5 * area + 0.2 * count) / 0.7     # weights 0.5 / 0.2 / 0.3, renormalised without depth
"""
import argparse
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
W_AREA, W_COUNT = 0.5, 0.2


def clip01(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def weak_severity(boxes: list[tuple[float, float]]) -> dict:
    """boxes: (width, height) as fractions of the image (YOLO format)."""
    ratio = min(sum(w * h for w, h in boxes), 1.0)  # overlapping boxes could exceed 1
    count = len(boxes)
    sev = (W_AREA * clip01(ratio / 0.3) + W_COUNT * clip01(count / 8)) / (W_AREA + W_COUNT)
    return {"severity": round(sev, 4), "pothole_area_ratio": round(ratio, 4), "pothole_count": count}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="pothole_labels")
    ap.add_argument("--out", default="cnn_severity.csv")
    a = ap.parse_args()
    rows = []
    for lab in sorted((HERE / a.labels).glob("*.txt")):
        boxes = [(float(p[3]), float(p[4])) for p in (line.split() for line in lab.read_text().splitlines()) if len(p) == 5]
        rows.append({"image_file": lab.stem + ".jpg", **weak_severity(boxes)})
    with open(HERE / a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image_file", "severity", "pothole_area_ratio", "pothole_count"])
        w.writeheader()
        w.writerows(rows)
    sev = sorted(r["severity"] for r in rows)
    print(f"{len(rows)} images -> {a.out} | severity min {sev[0]} median {sev[len(sev) // 2]} max {sev[-1]}")
    for lo, hi, name in [(0, 0.33, "low"), (0.33, 0.66, "medium"), (0.66, 1.01, "high")]:
        print(f"  {name:6} {sum(lo <= s < hi for s in sev)}")


if __name__ == "__main__":
    main()
