"""GET/POST /api/crews; PUT/DELETE /api/crews/{id}

DELETE returns 409 if the crew still has open orders.
Not implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/crews", tags=["crews"])
