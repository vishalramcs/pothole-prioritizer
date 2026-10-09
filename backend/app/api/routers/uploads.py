"""POST /api/uploads; GET /api/uploads/{id}/image

TRD 5. Validate file (type, size, content), read GPS, run detection via services, save potholes.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.core.config import get_settings
from app.core.db import Conn
from app.repositories import uploads as uploads_repo
from app.services import storage
from app.services.uploads import UploadError, process_image

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
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # never read more than one byte past the limit
    try:
        return process_image(conn, data, road_id, lat, lng, gps_source)
    except UploadError as exc:
        raise HTTPException(exc.status_code, str(exc))


@router.get("/{upload_id}/image")
def upload_image(conn: Conn, upload_id: int) -> Response:
    u = uploads_repo.get(conn, upload_id)
    if u is None:
        raise HTTPException(404, "Upload not found")
    return Response(storage.load(u["storage_path"]), media_type="image/jpeg")
