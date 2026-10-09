"""GET /api/repairs

Repair orders joined with pothole status; filter by status, crew_id.
Every pothole is listed (with its order, if any), so the Pending tab works before any plan exists.
"""
from fastapi import APIRouter

from app.core.db import Conn
from app.repositories import repair_orders
from app.schemas import Status

router = APIRouter(prefix="/repairs", tags=["repairs"])


@router.get("")
def list_repairs(conn: Conn, status: Status | None = None, crew_id: int | None = None) -> list[dict]:
    return repair_orders.list_repairs(conn, status, crew_id)
