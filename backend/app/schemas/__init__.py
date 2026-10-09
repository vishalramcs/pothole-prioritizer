"""Pydantic request models. Responses are plain dicts from the repositories."""
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["Pending", "Scheduled", "In Progress", "Repaired"]
Band = Literal["Low", "Moderate", "Critical"]


class StatusChange(BaseModel):
    status: Status


class RoadUpdate(BaseModel):
    traffic_score: float = Field(ge=0, le=1)
    importance_score: float = Field(ge=0, le=1)


class ConfigUpdate(BaseModel):
    values: dict[str, float]
