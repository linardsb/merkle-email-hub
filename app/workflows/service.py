"""Business logic for workflow orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from app.auth.models import User
from app.core.config import get_settings
from app.core.logging import get_logger
from app.workflows.exceptions import (
    InvalidFlowDefinitionError,
    KestraUnavailableError,
    WorkflowTriggerError,
    WorkflowValidationError,
)
from app.workflows.kestra_client import KestraClient
from app.workflows.schemas import (
    ExecutionLogsResponse,
    Flow,
    FlowCreateRequest,
    FlowSummary,
    WorkflowListResponse,
    WorkflowStatusResponse,
    WorkflowTriggerRequest,
)
from app.workflows.tasks import ALLOWED_TASK_TYPES

logger = get_logger(__name__)

FLOW_TEMPLATES_DIR = Path(__file__).parent / "flow_templates"

KESTRA_BUILTIN_TASK_TYPES: frozenset[str] = frozenset(
    {
        "io.kestra.core.tasks.flows.Parallel",
        "io.kestra.core.tasks.flows.Sequential",
        "io.kestra.core.tasks.flows.Switch",
        "io.kestra.core.tasks.flows.If",
        "io.kestra.core.tasks.flows.Pause",
        "io.kestra.core.tasks.flows.ForEach",
        "io.kestra.core.tasks.log.Log",
    }
)


class WorkflowService:
    """Orchestrates Kestra workflow management."""

    def __init__(self) -> None:
        self._client = KestraClient()

    # --- Flow management ---

    async def list_workflows(self) -> WorkflowListResponse:
        """List available flows (Kestra flows + bundled templates)."""
        flows = await self._client.list_flows()
        templates = self._list_bundled_templates()

        summaries: list[FlowSummary] = []
        # Remote flows
        for f in flows:
            summaries.append(
                FlowSummary(
                    id=f.id,
                    namespace=f.namespace,
                    description=f.description,
                    revision=f.revision,
                    has_schedule=any(t.get("type", "").endswith("Schedule") for t in f.triggers),
                )
            )
        # Bundled templates not yet synced
        remote_ids = {f.id for f in flows}
        for tmpl in templates:
            if tmpl["id"] not in remote_ids:
                summaries.append(
                    FlowSummary(
                        id=tmpl["id"],
                        namespace=tmpl["namespace"],
                        description=tmpl.get("description", ""),
                        is_template=True,
                    )
                )

        return WorkflowListResponse(flows=summaries)

    async def get_flow(self, flow_id: str) -> Flow:
        """Get a flow definition."""
        return await self._client.get_flow(flow_id)

    async def create_custom_flow(self, data: FlowCreateRequest, user: User) -> Flow:
        """Create a custom flow from YAML. Admin only — validated against allowlist."""
        logger.info("workflow.flow.create_requested", flow_id=data.flow_id, user_id=user.id)

        definition = self._parse_and_validate_yaml(data.yaml_definition)
        if data.description:
            definition["description"] = data.description

        flow = await self._client.create_flow(data.flow_id, definition)
        logger.info("workflow.flow.created", flow_id=flow.id, revision=flow.revision)
        return flow

    # --- Execution management ---

    async def trigger(self, data: WorkflowTriggerRequest, user: User) -> WorkflowStatusResponse:
        """Trigger a workflow execution."""
        logger.info(
            "workflow.execution.trigger_requested",
            flow_id=data.flow_id,
            user_id=user.id,
        )

        # Inject user context into inputs
        inputs = {**data.inputs, "_user_id": user.id}
        if data.project_id is not None:
            inputs["project_id"] = data.project_id

        execution = await self._client.trigger_execution(data.flow_id, inputs)

        return WorkflowStatusResponse(
            execution_id=execution.id,
            flow_id=execution.flow_id,
            status=execution.status,
            started=execution.started,
            ended=execution.ended,
            inputs=execution.inputs,
            outputs=execution.outputs,
            task_runs=execution.task_runs,
        )

    async def get_status(self, execution_id: str) -> WorkflowStatusResponse:
        """Get execution status."""
        execution = await self._client.get_execution(execution_id)
        return WorkflowStatusResponse(
            execution_id=execution.id,
            flow_id=execution.flow_id,
            status=execution.status,
            started=execution.started,
            ended=execution.ended,
            inputs=execution.inputs,
            outputs=execution.outputs,
            task_runs=execution.task_runs,
        )

    async def get_logs(self, execution_id: str) -> ExecutionLogsResponse:
        """Get execution logs."""
        logs = await self._client.get_logs(execution_id)
        return ExecutionLogsResponse(execution_id=execution_id, logs=logs)

    async def health_check(self) -> bool:
        """Check if the Kestra API is reachable."""
        return await self._client.health_check()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

    # --- Sync bundled templates to Kestra ---

    async def sync_flow_templates(self) -> int:
        """Sync bundled YAML flow templates to Kestra. Returns count synced."""
        templates = self._list_bundled_templates()
        synced = 0
        for tmpl in templates:
            try:
                await self._client.create_flow(tmpl["id"], tmpl)
                synced += 1
                logger.info("workflow.template.synced", flow_id=tmpl["id"])
            except (KestraUnavailableError, WorkflowTriggerError):
                logger.warning(
                    "workflow.template.sync_failed",
                    flow_id=tmpl.get("id", "unknown"),
                    exc_info=True,
                )
        return synced

    # --- Validation ---

    def _parse_and_validate_yaml(self, yaml_source: str) -> dict[str, Any]:
        """Parse YAML and validate only Hub task types are used."""
        try:
            definition = yaml.safe_load(yaml_source)
        except yaml.YAMLError as exc:
            raise WorkflowValidationError(f"Invalid YAML: {exc}") from exc

        if not isinstance(definition, dict):
            raise WorkflowValidationError("YAML must be a mapping")

        result = cast(dict[str, Any], definition)
        # Validate task types against allowlist
        self._validate_task_types(result.get("tasks", []))
        return result

    def _validate_task_types(self, tasks: list[Any]) -> None:
        """Recursively check all task types are in the Hub allowlist or Kestra built-ins."""
        for task in tasks:
            if not isinstance(task, dict):
                continue
            task_type = cast(str, cast(dict[str, Any], task).get("type", ""))
            if (
                task_type
                and task_type not in KESTRA_BUILTIN_TASK_TYPES
                and task_type not in ALLOWED_TASK_TYPES
            ):
                raise InvalidFlowDefinitionError(
                    f"Disallowed task type: '{task_type}'. "
                    f"Allowed Hub tasks: {', '.join(sorted(ALLOWED_TASK_TYPES))}"
                )
            # Recurse into sub-tasks (Parallel, Sequential, etc.)
            for sub_key in ("tasks", "errors"):
                if sub_key in task:
                    self._validate_task_types(cast(list[Any], task[sub_key]))

    @staticmethod
    def _list_bundled_templates() -> list[dict[str, Any]]:
        """Load all YAML flow templates from the bundled directory."""
        templates: list[dict[str, Any]] = []
        if not FLOW_TEMPLATES_DIR.is_dir():
            return templates
        settings = get_settings()
        for path in sorted(FLOW_TEMPLATES_DIR.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text())
                if isinstance(raw, dict):
                    data = cast(dict[str, Any], raw)
                    data.setdefault("namespace", settings.kestra.namespace)
                    data.setdefault("id", path.stem.replace("_", "-"))
                    templates.append(data)
            except yaml.YAMLError:
                logger.warning("workflow.template.load_failed", path=str(path))
        return templates


# --- Singleton ---

_service: WorkflowService | None = None


def get_workflow_service() -> WorkflowService:
    global _service
    if _service is None:
        _service = WorkflowService()
    return _service
