"""Step 1: raw Roboflow export -> pothole_images/ + pothole_labels/ (one image per source photo).

Source: huggingface.co/datasets/Ryukijano/Pothole-detection-Yolov8, a Roboflow export of
"Potholes Detection" (universe.roboflow.com/project-ssayl/potholes-detection-d4rma), CC BY 4.0.
Roboflow added a horizontally flipped copy of many training images (same name before ".rf.<hash>");
keeping both would put near-duplicates on both sides of a train/test split, so only the first is kept.
Download first:  python -c "from huggingface_hub import snapshot_download as s; s('Ryukijano/Pothole-detection-Yolov8', repo_type='dataset', local_dir='raw/ryukijano')"
"""
import csv
import re
import shutil
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "ryukijano"


def source_name(filename: str) -> str:
    return re.sub(r"\.rf\.[0-9a-f]+\.jpg$", "", filename)


def main() -> None:
    images, labels = HERE / "pothole_images", HERE / "pothole_labels"
    images.mkdir(exist_ok=True)
    labels.mkdir(exist_ok=True)
    seen, rows = set(), []
    for split in ("train", "valid", "test"):
        for img in sorted((RAW / split / "images").glob("*.jpg")):
            src = source_name(img.name)
            if src in seen:
                continue
            seen.add(src)
            with Image.open(img) as im:
                im.verify()  # raises if the file is not a readable image
            lab = RAW / split / "labels" / (img.stem + ".txt")
            boxes = [line for line in lab.read_text().splitlines() if line.strip()]
            name = f"{src}.jpg"
            shutil.copyfile(img, images / name)
            (labels / f"{src}.txt").write_text("\n".join(boxes) + "\n")
            rows.append({"image_file": name, "roboflow_split": split, "n_boxes": len(boxes)})
    with open(HERE / "pothole_images_manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image_file", "roboflow_split", "n_boxes"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} unique images -> {images}  (boxes per image: "
          f"{sum(r['n_boxes'] for r in rows) / len(rows):.2f} on average)")


if __name__ == "__main__":
    main()
