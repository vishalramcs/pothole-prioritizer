"""POST /api/zones/recompute; GET /api/zones

TRD 4.6.
"""
from fastapi import APIRouter

from app.core.db import Conn
from app.services import zones

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("")
def list_zones(conn: Conn) -> list[dict]:
    return zones.list_with_radius(conn)


@router.post("/recompute")
def recompute_zones(conn: Conn) -> list[dict]:
    zones.recompute(conn)
    return zones.list_with_radius(conn)
