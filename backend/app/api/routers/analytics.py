"""GET /api/analytics/summary

See docs/05-backend-schema.md, section 7 for the queries.
"""
from fastapi import APIRouter

from app.core.db import Conn
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(conn: Conn) -> dict:
    return analytics.summary(conn)
