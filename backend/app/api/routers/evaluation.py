"""GET /api/evaluation: SRPPS vs baselines on the current open potholes, plus weight sensitivity. Read-only."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.core.db import Conn
from app.services import evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("")
def evaluate(conn: Conn, days: Annotated[int, Query(ge=1, le=60)] = 5,
             critical_within: Annotated[int, Query(ge=1, le=60)] = 2,
             top_n: Annotated[int, Query(ge=1, le=100)] = 10) -> dict:
    try:
        return evaluation.evaluate(conn, days, critical_within, top_n)
    except evaluation.EvaluationError as exc:
        raise HTTPException(400, str(exc))
