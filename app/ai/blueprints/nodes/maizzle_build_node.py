"""Maizzle Build deterministic node — compiles email HTML via sidecar service."""

import httpx

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MaizzleBuildNode:
    """Deterministic node that compiles HTML through the Maizzle builder sidecar.

    Uses the same httpx pattern as EmailEngineService._call_builder().
    No database persistence — just compile and return.
    """

    @property
    def name(self) -> str:
        return "maizzle_build"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """POST HTML to Maizzle builder and return compiled output."""
        if not context.html:
            return NodeResult(
                status="failed",
                error="No HTML to build",
            )

        settings = get_settings()
        url = f"{settings.maizzle_builder_url}/build"
        payload: dict[str, object] = {
            "source": context.html,
            "config": {},
            "production": False,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                compiled_html = str(result["html"])
        except httpx.ConnectError:
            logger.warning("blueprint.maizzle_build.unavailable", url=url)
            return NodeResult(
                status="failed",
                error="Maizzle builder unavailable",
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "blueprint.maizzle_build.http_error",
                status=exc.response.status_code,
            )
            return NodeResult(
                status="failed",
                error=f"Builder returned {exc.response.status_code}",
            )
        except Exception as exc:
            logger.error("blueprint.maizzle_build.failed", error=str(exc))
            return NodeResult(
                status="failed",
                error=f"Build failed: {exc}",
            )

        logger.info(
            "blueprint.maizzle_build.completed",
            input_length=len(context.html),
            output_length=len(compiled_html),
        )

        return NodeResult(
            status="success",
            html=compiled_html,
            details=f"Compiled {len(compiled_html)} chars",
        )
