"""GET /api/potholes; GET /api/potholes/{id}; GET /api/potholes/{id}/image; PATCH /api/potholes/{id}/status

TRD 5 and 4.9. Status changes go through services.status only.
"""
from fastapi import APIRouter, HTTPException, Response

from app.core.db import Conn
from app.repositories import config
from app.repositories import potholes as repo
from app.schemas import Band, Status, StatusChange
from app.services import priority, status, storage

router = APIRouter(prefix="/potholes", tags=["potholes"])


def _public(p: dict) -> dict:
    p.pop("image_path", None)  # internal Storage path; the browser uses the /image endpoint
    return p


def _get_or_404(conn, pothole_id: int) -> dict:
    p = repo.get(conn, pothole_id)
    if p is None:
        raise HTTPException(404, "Pothole not found")
    return p


@router.get("")
def list_potholes(conn: Conn, status: Status | None = None, band: Band | None = None,
                  zone_id: int | None = None) -> list[dict]:
    return [_public(p) for p in repo.list_filtered(conn, status, band, zone_id)]


@router.get("/{pothole_id}")
def get_pothole(conn: Conn, pothole_id: int) -> dict:
    p = _get_or_404(conn, pothole_id)
    # Same inputs as the stored score, so the bars always add up to priority_score
    p["breakdown"] = priority.for_pothole(p, config.get_all(conn))["breakdown"]
    return _public(p)


@router.get("/{pothole_id}/image")
def pothole_image(conn: Conn, pothole_id: int) -> Response:
    return Response(storage.load(_get_or_404(conn, pothole_id)["image_path"]), media_type="image/jpeg")


@router.patch("/{pothole_id}/status")
def set_status(conn: Conn, pothole_id: int, body: StatusChange) -> dict:
    try:
        status.change_status(conn, pothole_id, body.status)
    except LookupError:
        raise HTTPException(404, "Pothole not found")
    except status.InvalidStatusChange:
        raise HTTPException(409, "Invalid status change")
    return _public(repo.get(conn, pothole_id))
