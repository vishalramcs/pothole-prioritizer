"""Load the YOLO model once; run it on an image; return boxes + confidence (TRD 4.1).

Confidence only filters detections (>= MIN_CONFIDENCE); it never changes severity.
"""
import functools
import threading
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
_lock = threading.Lock()  # FastAPI runs sync routes in a thread pool; a YOLO model is not thread-safe


class DetectorError(Exception):
    pass


@functools.cache
def _model():
    path = Path(get_settings().model_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    if not path.exists():
        raise DetectorError(f"Model weights not found at {path}. Run: python scripts/download_model.py")
    from ultralytics import YOLO  # imported here: slow to import, and tests without the model never need it

    return YOLO(str(path))


def detect(img: Image.Image, min_confidence: float) -> list[dict]:
    """Pixel boxes (top-left x, y, width, height) and confidence for every pothole in an RGB image."""
    with _lock:
        model = _model()
        r = model.predict(img, conf=min_confidence, verbose=False)[0]
    pothole_classes = {i for i, name in model.names.items() if name.lower() == "pothole"}
    return [
        {"bbox_x": x1, "bbox_y": y1, "bbox_w": x2 - x1, "bbox_h": y2 - y1, "confidence": conf}
        for (x1, y1, x2, y2), conf, cls in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist())
        if int(cls) in pothole_classes
    ]
