"""Maizzle Build deterministic node — compiles email HTML via sidecar service."""

from typing import cast

import httpx

from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.ai.shared import sanitize_html_xss
from app.ai.templates.precompiler import CSS_PREOPTIMIZED_MARKER
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MaizzleBuildNode:
    """Deterministic node that compiles HTML through the Maizzle builder sidecar.

    Pipeline: sidecar PostCSS optimize → Lightning CSS minify → Maizzle build (Juice inlines) → sanitize.
    """

    @property
    def name(self) -> str:
        return "maizzle_build"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """POST to Maizzle builder with CSS optimization, sanitize output."""
        if not context.html:
            return NodeResult(status="failed", error="No HTML to build")

        settings = get_settings()
        source_html = context.html

        skip_css = CSS_PREOPTIMIZED_MARKER in source_html
        if skip_css:
            source_html = source_html.replace(CSS_PREOPTIMIZED_MARKER, "", 1)
            logger.info("blueprint.maizzle_build.css_skipped_preoptimized")

        url = f"{settings.maizzle_builder_url}/build"
        payload: dict[str, object] = {"source": source_html, "config": {}, "production": False}

        if not skip_css:
            raw_clients = context.metadata.get("target_clients")
            if isinstance(raw_clients, list):
                payload["target_clients"] = list(cast("list[str]", raw_clients))

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                compiled_html = str(result["html"])

                optimization = result.get("optimization")
                if optimization:
                    logger.info(
                        "blueprint.maizzle_build.css_optimized",
                        removed_count=len(optimization.get("removed_properties", [])),
                        conversion_count=len(optimization.get("conversions", [])),
                        original_css_size=optimization.get("original_css_size", 0),
                        optimized_css_size=optimization.get("optimized_css_size", 0),
                    )
        except httpx.ConnectError:
            logger.warning("blueprint.maizzle_build.unavailable", url=url)
            return NodeResult(status="failed", error="Maizzle builder unavailable")
        except httpx.HTTPStatusError as exc:
            logger.error("blueprint.maizzle_build.http_error", status=exc.response.status_code)
            return NodeResult(status="failed", error=f"Builder returned {exc.response.status_code}")
        except Exception as exc:
            logger.error("blueprint.maizzle_build.failed", error=str(exc))
            return NodeResult(status="failed", error=f"Build failed: {exc}")

        compiled_html = sanitize_html_xss(compiled_html)
        logger.info(
            "blueprint.maizzle_build.completed",
            input_length=len(context.html),
            output_length=len(compiled_html),
        )
        return NodeResult(
            status="success", html=compiled_html, details=f"Compiled {len(compiled_html)} chars"
        )
