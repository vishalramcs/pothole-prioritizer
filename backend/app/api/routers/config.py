"""GET/PUT /api/config

Reject weights that do not sum to 1.0 (tolerance 0.001).
Not implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])
