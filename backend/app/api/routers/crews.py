"""GET/POST /api/crews; PUT/DELETE /api/crews/{id}

DELETE returns 409 if the crew still has open orders. A crew with finished orders cannot be deleted either:
those orders are repair history (analytics counts them), and the foreign key keeps them pointing at the crew.
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.db import Conn
from app.repositories import crews
from app.schemas import CrewIn

router = APIRouter(prefix="/crews", tags=["crews"])
DUPLICATE = "A crew with that name already exists"


@router.get("")
def list_crews(conn: Conn) -> list[dict]:
    return crews.list_all(conn)


@router.post("")
def create_crew(conn: Conn, body: CrewIn) -> dict:
    try:
        crew_id = crews.insert(conn, body.name.strip(), body.capacity_per_day)
    except IntegrityError:
        raise HTTPException(409, DUPLICATE)
    return crews.get(conn, crew_id)


@router.put("/{crew_id}")
def update_crew(conn: Conn, crew_id: int, body: CrewIn) -> dict:
    if crews.get(conn, crew_id) is None:
        raise HTTPException(404, "Crew not found")
    try:
        crews.update(conn, crew_id, body.name.strip(), body.capacity_per_day)
    except IntegrityError:
        raise HTTPException(409, DUPLICATE)
    return crews.get(conn, crew_id)


@router.delete("/{crew_id}")
def delete_crew(conn: Conn, crew_id: int) -> dict:
    if crews.get(conn, crew_id) is None:
        raise HTTPException(404, "Crew not found")
    open_orders, finished = crews.order_counts(conn, crew_id)
    if open_orders:
        raise HTTPException(409, "This crew still has open repair orders")
    if finished:
        raise HTTPException(409, "This crew has finished repairs on record and cannot be deleted")
    crews.delete(conn, crew_id)
    return {"deleted": crew_id}
