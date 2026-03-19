"""Pydantic schemas for workflow orchestration."""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --- Kestra domain models ---


class TaskRun(BaseModel):
    """A single task execution within a workflow."""

    task_id: str
    status: str  # CREATED, RUNNING, SUCCESS, FAILED, WARNING, KILLED
    started: datetime.datetime | None = None
    ended: datetime.datetime | None = None
    outputs: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class Execution(BaseModel):
    """A Kestra workflow execution."""

    id: str
    namespace: str
    flow_id: str
    status: str  # CREATED, RUNNING, SUCCESS, FAILED, WARNING, PAUSED, KILLED
    started: datetime.datetime
    ended: datetime.datetime | None = None
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    task_runs: list[TaskRun] = []

    model_config = ConfigDict(from_attributes=True)


class LogEntry(BaseModel):
    """A Kestra execution log line."""

    timestamp: datetime.datetime
    level: str
    message: str
    task_id: str | None = None


class Flow(BaseModel):
    """A Kestra flow definition summary."""

    id: str
    namespace: str
    revision: int = 1
    description: str | None = None
    inputs: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []


# --- API request/response schemas ---


class FlowSummary(BaseModel):
    """Summary of a flow for listing."""

    id: str
    namespace: str
    description: str | None = None
    is_template: bool = False
    revision: int = 1
    has_schedule: bool = False


class WorkflowTriggerRequest(BaseModel):
    """Request to trigger a workflow execution."""

    flow_id: str = Field(max_length=200)
    inputs: dict[str, Any] = Field(default_factory=dict)
    project_id: int | None = None


class WorkflowStatusResponse(BaseModel):
    """Workflow execution status."""

    execution_id: str
    flow_id: str
    status: str
    started: datetime.datetime
    ended: datetime.datetime | None = None
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    task_runs: list[TaskRun] = []


class WorkflowListResponse(BaseModel):
    """List of available workflows."""

    flows: list[FlowSummary]


class FlowCreateRequest(BaseModel):
    """Request to create a custom workflow from YAML."""

    flow_id: str = Field(max_length=200, pattern=r"^[a-z0-9_-]+$")
    description: str = Field(default="", max_length=500)
    yaml_definition: str = Field(max_length=50_000)


class ExecutionLogsResponse(BaseModel):
    """Execution log entries."""

    execution_id: str
    logs: list[LogEntry]
