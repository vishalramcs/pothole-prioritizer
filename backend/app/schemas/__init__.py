"""Pydantic request models. Responses are plain dicts from the repositories."""
from datetime import date
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


class CrewIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    capacity_per_day: int = Field(ge=1, le=100)


class PlanIn(BaseModel):
    days: int = Field(ge=1, le=60)
    start_date: date | None = None


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
    role: Literal["citizen", "official"]


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=200)
