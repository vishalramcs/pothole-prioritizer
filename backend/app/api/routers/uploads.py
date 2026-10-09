"""POST /api/uploads; GET /api/uploads/{id}/image; GET /api/uploads/{id}/frames/{n}

TRD 5. Validate file (type, size, content), read GPS, run detection via services, save potholes.
Videos (TRD 4.8, P2) use the same endpoint; their content is checked by actually decoding frames.
"""
from pathlib import PurePath
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.core.config import get_settings
from app.core.db import Conn
from app.repositories import uploads as uploads_repo
from app.services import storage
from app.services.uploads import UploadError, frame_path, process_image, process_video

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("")
def create_upload(
    conn: Conn,
    file: Annotated[UploadFile, File()],
    road_id: Annotated[int, Form()],
    lat: Annotated[float | None, Form()] = None,
    lng: Annotated[float | None, Form()] = None,
    gps_source: Annotated[Literal["manual", "map_click"], Form()] = "manual",
) -> dict:
    s = get_settings()
    is_video = (file.content_type or "").startswith("video/")
    limit = (s.max_video_mb if is_video else s.max_upload_mb) * 1024 * 1024
    data = file.file.read(limit + 1)  # never read more than one byte past the limit
    try:
        if is_video:
            return process_video(conn, data, road_id, lat, lng, gps_source, PurePath(file.filename or "").suffix)
        return process_image(conn, data, road_id, lat, lng, gps_source)
    except UploadError as exc:
        raise HTTPException(exc.status_code, str(exc))


def _upload_or_404(conn, upload_id: int) -> dict:
    u = uploads_repo.get(conn, upload_id)
    if u is None:
        raise HTTPException(404, "Upload not found")
    return u


@router.get("/{upload_id}/image")
def upload_image(conn: Conn, upload_id: int) -> Response:
    u = _upload_or_404(conn, upload_id)
    if u["media_type"] != "image":
        raise HTTPException(404, "This upload is a video; use its frames")
    return Response(storage.load(u["storage_path"]), media_type="image/jpeg")


@router.get("/{upload_id}/frames/{frame_index}")
def upload_frame(conn: Conn, upload_id: int, frame_index: int) -> Response:
    _upload_or_404(conn, upload_id)
    try:
        return Response(storage.load(frame_path(upload_id, frame_index)), media_type="image/jpeg")
    except Exception:  # only frames that contained a pothole are stored
        raise HTTPException(404, "Frame not stored")
