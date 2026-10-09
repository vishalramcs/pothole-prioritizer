"""Download the pothole detection weights to ml/weights/pothole.pt (the MODEL_PATH default).

Run from backend/:  python scripts/download_model.py
Model: Samdutse/pothole-yolov8 on Hugging Face (YOLOv8s fine-tuned on the Smartathon pothole set).
Its model card states no licence: ask the author before relying on it for anything public, or switch
MODEL_URL to tahaUgan/pothole-yolo11n (CC-BY-4.0, file pothole2v.pt). The detector keeps only classes
named "pothole", so either works without code changes.
"""
import urllib.request
from pathlib import Path

MODEL_URL = "https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt"
DEST = Path(__file__).resolve().parents[1] / "ml" / "weights" / "pothole.pt"

if __name__ == "__main__":
    DEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEST.with_suffix(".part")
    urllib.request.urlretrieve(MODEL_URL, tmp)
    tmp.replace(DEST)  # only replace once the download finished
    print(f"Saved {DEST} ({DEST.stat().st_size // 1024} KB)")
