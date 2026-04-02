"""Pydantic schemas for the scheduling engine."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# Shared Redis key prefixes (used by engine.py and service.py)
JOBS_PREFIX = "scheduling:jobs"
RUNS_PREFIX = "scheduling:runs"
LEADER_KEY = "scheduling:leader"


class JobStatus(StrEnum):
    """Status of a scheduled job or run."""

    idle = "idle"
    running = "running"
    success = "success"
    failed = "failed"


class JobDefinitionResponse(BaseModel):
    """Response schema for a registered scheduled job."""

    name: str
    cron_expr: str
    callable_name: str
    enabled: bool
    last_run: datetime | None = None
    last_status: JobStatus | None = None
    next_run: datetime | None = None
    run_count: int = 0


class JobUpdateRequest(BaseModel):
    """Request schema for updating a scheduled job."""

    enabled: bool | None = Field(default=None, description="Enable or disable the job")
    cron_expr: str | None = Field(default=None, description="New cron expression")


class JobRunResponse(BaseModel):
    """Response schema for a job run record."""

    job_name: str
    started_at: datetime
    ended_at: datetime | None = None
    status: JobStatus
    error: str | None = None
    duration_ms: int | None = None
