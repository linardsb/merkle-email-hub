"""Workflow orchestration HTTP endpoints."""

# pyright: reportUntypedFunctionDecorator=false

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.workflows.schemas import (
    ExecutionLogsResponse,
    FlowCreateRequest,
    WorkflowListResponse,
    WorkflowStatusResponse,
    WorkflowTriggerRequest,
)
from app.workflows.service import WorkflowService, get_workflow_service

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


def get_service() -> WorkflowService:
    return get_workflow_service()


@router.get("/", response_model=WorkflowListResponse)
@limiter.limit("30/minute")
async def list_workflows(
    request: Request,
    service: WorkflowService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> WorkflowListResponse:
    """List available workflow templates and custom workflows."""
    _ = request
    return await service.list_workflows()


@router.post(
    "/trigger",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def trigger_workflow(
    request: Request,
    data: WorkflowTriggerRequest,
    service: WorkflowService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> WorkflowStatusResponse:
    """Trigger a workflow execution with inputs."""
    _ = request
    return await service.trigger(data, current_user)


@router.get("/flows/{flow_id}")
@limiter.limit("30/minute")
async def get_flow_definition(
    request: Request,
    flow_id: str,
    service: WorkflowService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a workflow definition."""
    _ = request
    flow = await service.get_flow(flow_id)
    return flow.model_dump()


@router.post(
    "/flows",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def create_custom_flow(
    request: Request,
    data: FlowCreateRequest,
    service: WorkflowService = Depends(get_service),
    current_user: User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create a custom workflow from YAML definition. Admin only."""
    _ = request
    flow = await service.create_custom_flow(data, current_user)
    return {"id": flow.id, "namespace": flow.namespace, "revision": flow.revision}


@router.get("/{execution_id}", response_model=WorkflowStatusResponse)
@limiter.limit("30/minute")
async def get_execution_status(
    request: Request,
    execution_id: str,
    service: WorkflowService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> WorkflowStatusResponse:
    """Get workflow execution status and task run details."""
    _ = request
    return await service.get_status(execution_id)


@router.get("/{execution_id}/logs", response_model=ExecutionLogsResponse)
@limiter.limit("15/minute")
async def get_execution_logs(
    request: Request,
    execution_id: str,
    service: WorkflowService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> ExecutionLogsResponse:
    """Get execution log entries."""
    _ = request
    return await service.get_logs(execution_id)
