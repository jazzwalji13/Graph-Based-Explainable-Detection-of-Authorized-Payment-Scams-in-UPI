from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    seed: Optional[int] = None
    users: Optional[int] = Field(default=None, ge=50, le=5000)
    days: Optional[int] = Field(default=None, ge=30, le=365)
    scam_rate: Optional[float] = Field(default=None, gt=0, lt=0.2)
    flag_threshold: Optional[float] = Field(default=None, gt=0, lt=1)
    drift_start_day: Optional[int] = None


class CheckinRequest(BaseModel):
    answer: Literal["confirm", "deny", "unsure"]


class BudgetSimulateRequest(BaseModel):
    c0: Optional[float] = Field(default=None, gt=0, le=10)
    alpha: Optional[float] = Field(default=None, ge=0, le=10)
    window_minutes: Optional[int] = Field(default=None, ge=1, le=10080)
    decay: Optional[float] = Field(default=None, gt=0, le=1)
    latency_minutes: Optional[float] = Field(default=None, ge=0, le=120)
    cooldown_minutes: Optional[int] = Field(default=None, ge=0, le=10080)


class HealthResponse(BaseModel):
    status: str
    version: str
    time: str
    seeded: bool
