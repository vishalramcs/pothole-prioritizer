"""Collects every router under the /api prefix."""
from fastapi import APIRouter

from app.api.routers import (
    analytics, config, crews, health, plan, potholes, repairs, roads, uploads, zones,
)

api_router = APIRouter(prefix="/api")
for module in (health, uploads, potholes, roads, crews, zones, plan, repairs, analytics, config):
    api_router.include_router(module.router)
