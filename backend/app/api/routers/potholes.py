"""GET /api/potholes; GET /api/potholes/{id}; GET /api/potholes/{id}/image; PATCH /api/potholes/{id}/status

TRD 5 and 4.9. Status changes go through services.status only.
Not implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/potholes", tags=["potholes"])
