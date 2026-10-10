"""GET /api/roads; PUT /api/roads/{id}

Edit mock traffic/importance; recompute priority after an edit.
"""
from fastapi import APIRouter, HTTPException

from app.core.auth import Official, User
from app.core.db import Conn
from app.repositories import roads
from app.schemas import RoadUpdate
from app.services import priority

router = APIRouter(prefix="/roads", tags=["roads"])


@router.get("")
def list_roads(conn: Conn, _: User) -> list[dict]:
    return roads.list_all(conn)


@router.put("/{road_id}")
def update_road(conn: Conn, _: Official, road_id: int, body: RoadUpdate) -> dict:
    if roads.get(conn, road_id) is None:
        raise HTTPException(404, "Road not found")
    roads.update_scores(conn, road_id, body.traffic_score, body.importance_score)
    priority.rescore_all(conn)
    return roads.get(conn, road_id)
