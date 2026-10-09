"""POST /api/plan

TRD 4.7. One transaction: reset plan, recompute zones, insert orders.
Not implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/plan", tags=["plan"])
