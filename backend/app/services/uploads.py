"""Image upload pipeline (TRD 5, POST /uploads): validate, locate, detect, store, score, save."""
import io
import uuid

from PIL import Image, ImageOps
from sqlalchemy import Connection

from app.core.config import get_settings
from app.repositories import config, potholes, roads, uploads
from app.services import detector, gps, priority, severity, storage

FORMATS = {"JPEG", "PNG"}
MAX_SIDE = 4000  # TRD 6: longest side; bigger images are shrunk before inference


class UploadError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def process_image(conn: Connection, data: bytes, road_id: int, lat: float | None, lng: float | None,
                  gps_source: str) -> dict:
    s = get_settings()
    bad_file = f"Use a JPG or PNG under {s.max_upload_mb} MB"
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise UploadError(413, bad_file)
    try:  # content check, not the filename or the browser's content type
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise UploadError(400, bad_file)
    if img.format not in FORMATS:
        raise UploadError(400, bad_file)

    road = roads.get(conn, road_id)
    if road is None:
        raise UploadError(400, "Pick a road from the list")
    if lat is None and lng is None:
        found = gps.exif_gps(img)
        if found is None:
            raise UploadError(400, "No GPS found in the photo: type coordinates or click the map")
        (lat, lng), gps_source = found, "exif"
    elif lat is None or lng is None:
        raise UploadError(400, "Give both latitude and longitude")
    elif not gps.valid(lat, lng):
        raise UploadError(400, "Coordinates out of range")

    # Rotate as the phone intended, so boxes line up with how people see the photo
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))  # only ever shrinks
    cfg = config.get_all(conn)
    try:
        detections = detector.detect(img, cfg["MIN_CONFIDENCE"])
    except Exception as exc:
        raise UploadError(422, "Detection failed, try again") from exc

    # Store our own re-encoded copy under a generated name: boxes are in its pixels, and EXIF is dropped
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    path = f"uploads/{uuid.uuid4().hex}.jpg"
    upload_id = uploads.insert(conn, storage_path=path, media_type="image", lat=lat, lng=lng,
                               gps_source=gps_source, road_id=road_id, image_width=img.width,
                               image_height=img.height)

    saved = []
    for d in detections:
        ratio = severity.area_ratio(d["bbox_w"], d["bbox_h"], img.width, img.height)
        sev_score, sev_level = severity.severity(ratio, cfg)
        row = {**d, "upload_id": upload_id, "road_id": road_id, "lat": lat, "lng": lng, "area_ratio": ratio,
               "severity_score": sev_score, "severity_level": sev_level, "detection_count": 1, "recurrence_count": 0}
        scored = priority.for_pothole({**row, **road}, cfg)
        row.update({k: scored[k] for k in priority.SCORE_FIELDS})
        saved.append({"pothole_id": potholes.insert(conn, **row), **row})

    storage.save(path, buf.getvalue(), "image/jpeg")  # after the inserts: if storing fails, they roll back
    return {"upload_id": upload_id, "lat": lat, "lng": lng, "gps_source": gps_source,
            "image_width": img.width, "image_height": img.height, "potholes": saved}
