"""GET /api/roads; PUT /api/roads/{id}

Edit mock traffic/importance; recompute priority after an edit.
Not implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/roads", tags=["roads"])
