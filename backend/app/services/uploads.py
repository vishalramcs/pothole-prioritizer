"""Image upload pipeline (TRD 5, POST /uploads): validate, locate, detect, store, score, save."""
import io
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import Connection

from app.core.config import get_settings
from app.repositories import config, potholes, roads, uploads
from app.services import detector, facilities, gps, matching, priority, severity, storage, video

FORMATS = {"JPEG", "PNG"}
VIDEO_TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
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

    saved = save_detections(conn, upload_id, road, lat, lng, detections, img.width, img.height, cfg)
    storage.save(path, buf.getvalue(), "image/jpeg")  # after the inserts: if storing fails, they roll back
    return {"upload_id": upload_id, "lat": lat, "lng": lng, "gps_source": gps_source,
            "image_width": img.width, "image_height": img.height, "potholes": saved}


def process_video(conn: Connection, data: bytes, road_id: int, lat: float | None, lng: float | None,
                  gps_source: str, suffix: str) -> dict:
    """TRD 4.8: one coordinate for the whole clip (videos carry no usable EXIF GPS)."""
    s = get_settings()
    bad_file = f"Use an MP4, MOV or WebM video under {s.max_video_mb} MB"
    if len(data) > s.max_video_mb * 1024 * 1024:
        raise UploadError(413, bad_file)
    road = roads.get(conn, road_id)
    if road is None:
        raise UploadError(400, "Pick a road from the list")
    if lat is None or lng is None:
        raise UploadError(400, "Videos need a location: type coordinates or click the map")
    if not gps.valid(lat, lng):
        raise UploadError(400, "Coordinates out of range")

    cfg = config.get_all(conn)
    ext = suffix.lower() if suffix.lower() in VIDEO_TYPES else ".mp4"  # never the user's filename, only a known suffix
    # OpenCV only reads videos from disk; the temp file is ours and deleted right after
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"clip{ext}"
        path.write_bytes(data)
        try:
            frames = list(video.sample_frames(str(path), cfg["FRAME_INTERVAL_S"], MAX_SIDE))
        except ValueError:
            raise UploadError(400, bad_file)
    try:
        per_frame = []
        for index, time_s, img in frames:
            dets = detector.detect(img, cfg["MIN_CONFIDENCE"])
            per_frame.append([{**d, "frame_index": index, "frame_time_s": time_s} for d in dets])
    except Exception as exc:
        raise UploadError(422, "Detection failed, try again") from exc
    kept = video.merge_tracks(per_frame, cfg["VIDEO_IOU_MIN"])

    width, height = frames[0][2].size
    stored_name = f"uploads/{uuid.uuid4().hex}{ext}"
    upload_id = uploads.insert(conn, storage_path=stored_name, media_type="video", lat=lat, lng=lng,
                               gps_source=gps_source, road_id=road_id, image_width=width, image_height=height)
    frame_images = {index: img for index, _, img in frames}
    for index in sorted({d["frame_index"] for d in kept}):  # only frames that contain a kept pothole are stored
        buf = io.BytesIO()
        frame_images[index].save(buf, "JPEG", quality=90)
        storage.save(frame_path(upload_id, index), buf.getvalue(), "image/jpeg")
    for d in kept:
        d["frame_storage_path"] = frame_path(upload_id, d["frame_index"])
    saved = save_detections(conn, upload_id, road, lat, lng, kept, width, height, cfg)
    storage.save(stored_name, data, VIDEO_TYPES[ext])
    return {"upload_id": upload_id, "media_type": "video", "lat": lat, "lng": lng, "gps_source": gps_source,
            "image_width": width, "image_height": height, "frames_sampled": len(frames), "potholes": saved}


def frame_path(upload_id: int, frame_index: int) -> str:
    return f"uploads/{upload_id}/frame_{frame_index}.jpg"  # TRD 4.8 layout


# The detection's own evidence: replaces a matched pothole's evidence when this sighting is more severe
EVIDENCE = ("upload_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "confidence", "area_ratio", "severity_score",
            "severity_level", "frame_index", "frame_time_s", "frame_storage_path")
BOX = ("bbox_x", "bbox_y", "bbox_w", "bbox_h", "confidence", "frame_index")


def save_detections(conn: Connection, upload_id: int, road: dict, lat: float, lng: float, detections: list[dict],
                    width: int, height: int, cfg: dict[str, float]) -> list[dict]:
    """Severity, repeat matching (TRD 4.4) and priority for each detection; insert or update potholes.

    Each returned row is the stored pothole plus THIS upload's box (to draw on this image) and "match".
    """
    for d in detections:
        d["area_ratio"] = severity.area_ratio(d["bbox_w"], d["bbox_h"], width, height)
        d["severity_score"], d["severity_level"] = severity.severity(d["area_ratio"], cfg)
        d["upload_id"] = upload_id
        for f in ("frame_index", "frame_time_s", "frame_storage_path"):
            d.setdefault(f, None)

    saved = []
    now = datetime.now(timezone.utc)
    place = facilities.proximity(conn, lat, lng, cfg["FACILITY_DECAY_M"])  # one point per upload
    for d, existing, kind in matching.match(conn, detections, lat, lng, cfg["DEDUP_RADIUS_M"]):
        if kind == "repeat":
            row = {**existing, "detection_count": existing["detection_count"] + 1, "last_detected_at": now}
            row.pop("image_path")  # internal Storage path, not for the response
            if d["severity_score"] > existing["severity_score"]:
                row.update({k: d[k] for k in EVIDENCE})
            changed = ("detection_count", "last_detected_at", *EVIDENCE)
        else:
            row = {**{k: d[k] for k in EVIDENCE}, **place, "road_id": road["road_id"], "lat": lat, "lng": lng,
                   "detection_count": 1, "recurrence_count": existing["recurrence_count"] + 1 if existing else 0}
            changed = tuple(row)
        scored = priority.for_pothole({**row, **{k: road[k] for k in ("traffic_score", "importance_score")}}, cfg)
        row.update({k: scored[k] for k in priority.SCORE_FIELDS})
        fields = {k: row[k] for k in (*changed, *priority.SCORE_FIELDS)}
        if kind == "repeat":
            potholes.update(conn, existing["pothole_id"], **fields)
            pothole_id = existing["pothole_id"]
        else:
            pothole_id = potholes.insert(conn, **fields)
        saved.append({**row, "pothole_id": pothole_id, **{k: d[k] for k in BOX}, "match": kind})
    return saved
