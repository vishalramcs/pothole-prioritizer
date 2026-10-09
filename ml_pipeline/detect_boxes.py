"""Boxes for images that have none: run the web app's pothole detector and write YOLO-format labels.

Used for the Outerview photos, whose "pothole" labels come from Outerview's own AI and are noisy (spot checks
found playgrounds and manhole covers). Images where our detector finds nothing at --conf get no label file,
so later steps drop them. The boxes are therefore MODEL boxes, not hand-drawn ones.

Run:  python detect_boxes.py --images pothole_images_mumbai --labels pothole_labels_mumbai --conf 0.4
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parent / "backend" / "ml" / "weights" / "pothole.pt"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--conf", type=float, default=0.4)
    a = ap.parse_args()
    out = HERE / a.labels
    out.mkdir(exist_ok=True)
    model = YOLO(str(DETECTOR))
    files = sorted((HERE / a.images).glob("*.jpg"))
    hit = 0
    for f in files:
        r = model.predict(str(f), conf=a.conf, verbose=False)[0]
        rows = [f"0 {x:.6f} {y:.6f} {w:.6f} {h:.6f}" for x, y, w, h in r.boxes.xywhn.tolist()]
        label = out / (f.stem + ".txt")
        if rows:
            label.write_text("\n".join(rows) + "\n")
            hit += 1
        elif label.exists():
            label.unlink()  # stale label from an earlier run with another threshold
    print(f"{hit} of {len(files)} images have a pothole at conf >= {a.conf} -> {out}")


if __name__ == "__main__":
    main()
