"""POST /api/plan

TRD 4.7. One transaction: reset plan, recompute zones, insert orders.
"""
from fastapi import APIRouter, HTTPException

from app.core.db import Conn
from app.schemas import PlanIn
from app.services import planner

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("")
def generate_plan(conn: Conn, body: PlanIn) -> dict:
    try:
        return planner.plan(conn, body.days, body.start_date)
    except planner.PlanError as exc:
        raise HTTPException(400, str(exc))
