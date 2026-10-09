"""POST /api/uploads; GET /api/uploads/{id}/image

TRD 5. Validate file (type, size, content), read GPS, run detection via services, save potholes.
Not implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/uploads", tags=["uploads"])
