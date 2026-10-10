"""POST /api/uploads; GET /api/uploads/{id}/image; GET /api/uploads/{id}/frames/{n}

TRD 5. Validate file (type, size, content), read GPS, run detection via services, save potholes.
Videos (TRD 4.8, P2) use the same endpoint; their content is checked by actually decoding frames.
"""
from pathlib import PurePath
from typing import Annotated, Literal

import logging

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Response, UploadFile

from app.core.auth import User
from app.core.config import get_settings
from app.core.db import Conn
from app.repositories import roads
from app.repositories import uploads as uploads_repo
from app.services import mailer, points, storage
from app.services.uploads import UploadError, frame_path, process_image, process_video

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("")
def create_upload(
    conn: Conn,
    user: User,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    road_id: Annotated[int | None, Form()] = None,  # none: found on OpenStreetMap from the location
    lat: Annotated[float | None, Form()] = None,
    lng: Annotated[float | None, Form()] = None,
    gps_source: Annotated[Literal["manual", "map_click"], Form()] = "manual",
    description: Annotated[str, Form(max_length=1000)] = "",  # what the reporter saw, in their words
) -> dict:
    s = get_settings()
    is_video = (file.content_type or "").startswith("video/")
    limit = (s.max_video_mb if is_video else s.max_upload_mb) * 1024 * 1024
    data = file.file.read(limit + 1)  # never read more than one byte past the limit
    reporter = {"user_id": user["user_id"], "description": description.strip() or None}
    try:
        if is_video:
            result = process_video(conn, data, road_id, lat, lng, gps_source, PurePath(file.filename or "").suffix,
                                   **reporter)
        else:
            result = process_image(conn, data, road_id, lat, lng, gps_source, **reporter)
    except UploadError as exc:
        raise HTTPException(exc.status_code, str(exc))
    result["points"] = points.award(conn, user, result, data)  # citizens only; never raises
    if result["points"]:
        result["points"]["email"] = _queue_points_email(conn, user, result, background)
    return result


def _queue_points_email(conn, user: dict, result: dict, background: BackgroundTasks) -> dict:
    """Sends after the response, so it never slows the upload. Only says "sending" when SMTP is configured."""
    try:
        status = mailer.email_status(user["email"])
        if status == "sending":
            road = roads.get(conn, uploads_repo.get(conn, result["upload_id"])["road_id"])
            p = result["points"]
            body = mailer.points_summary(p, str(p["total"]) if p["total"] is not None else "not available",
                                         road["name"] if road else "unknown", result["upload_id"])
            background.add_task(mailer.send, user["email"], f"SRPPS: +{p['earned']} points for your report", body)
        return {"status": status, "to": user["email"]}
    except Exception:
        logging.getLogger(__name__).exception("points email not queued")
        return {"status": "not_configured", "to": user["email"]}


def _upload_or_404(conn, upload_id: int, user: dict) -> dict:
    """Officials see every upload; a citizen only their own (404, not 403: don't reveal that it exists)."""
    u = uploads_repo.get(conn, upload_id)
    if u is None or (user["role"] != "official" and u["user_id"] != user["user_id"]):
        raise HTTPException(404, "Upload not found")
    return u


@router.get("/{upload_id}/image")
def upload_image(conn: Conn, user: User, upload_id: int) -> Response:
    u = _upload_or_404(conn, upload_id, user)
    if u["media_type"] != "image":
        raise HTTPException(404, "This upload is a video; use its frames")
    return Response(storage.load(u["storage_path"]), media_type="image/jpeg")


@router.get("/{upload_id}/frames/{frame_index}")
def upload_frame(conn: Conn, user: User, upload_id: int, frame_index: int) -> Response:
    _upload_or_404(conn, upload_id, user)
    try:
        return Response(storage.load(frame_path(upload_id, frame_index)), media_type="image/jpeg")
    except Exception:  # only frames that contained a pothole are stored
        raise HTTPException(404, "Frame not stored")
