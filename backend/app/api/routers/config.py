"""GET/PUT /api/config

Reject weights that do not sum to 1.0 (tolerance 0.001).
"""
from fastapi import APIRouter, HTTPException

from app.core.db import Conn
from app.repositories import config
from app.schemas import ConfigUpdate
from app.services import priority

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(conn: Conn) -> dict[str, float]:
    return config.get_all(conn)


@router.put("")
def update_config(conn: Conn, body: ConfigUpdate) -> dict[str, float]:
    current = config.get_all(conn)
    unknown = set(body.values) - set(current)
    if unknown:
        raise HTTPException(400, f"Unknown config keys: {', '.join(sorted(unknown))}")
    try:
        priority.check_weights({**current, **body.values})
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    config.set_many(conn, body.values)
    priority.rescore_all(conn)
    return config.get_all(conn)
