"""Collects every router under the /api prefix."""
from fastapi import APIRouter, Depends

from app.api.routers import (
    analytics, auth, config, crews, evaluation, health, plan, potholes, repairs, roads, uploads, zones,
)
from app.core.auth import require_official

api_router = APIRouter(prefix="/api")
# public, or checked per route (uploads: any logged-in user; roads: reading is open to logged-in users)
for module in (health, auth, uploads, roads):
    api_router.include_router(module.router)
# officials only: every route in these
for module in (potholes, crews, zones, plan, repairs, analytics, config, evaluation):
    api_router.include_router(module.router, dependencies=[Depends(require_official)])
