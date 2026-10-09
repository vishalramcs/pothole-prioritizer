"""GET /api/health (app is up) and GET /api/health/db (database reachable)."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.db import get_engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict:
    return {"status": "ok"}


@router.get("/db")
def health_db() -> dict:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # do not leak connection details to the client
        raise HTTPException(status_code=503, detail="Database not reachable") from exc
    return {"status": "ok", "database": "reachable"}
