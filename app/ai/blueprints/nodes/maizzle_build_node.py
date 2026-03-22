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

    Pipeline: optimize CSS (stages 1-5) → Maizzle build (Juice inlines) → sanitize.
    """

    @property
    def name(self) -> str:
        return "maizzle_build"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Optimize CSS, POST to Maizzle builder, sanitize output."""
        if not context.html:
            return NodeResult(
                status="failed",
                error="No HTML to build",
            )

        settings = get_settings()
        source_html = context.html

        # Skip CSS optimization if template was pre-optimized (26.3)
        skip_css = CSS_PREOPTIMIZED_MARKER in source_html
        if skip_css:
            source_html = source_html.replace(CSS_PREOPTIMIZED_MARKER, "", 1)
            logger.info("blueprint.maizzle_build.css_skipped_preoptimized")
        else:
            # CSS optimization: run ontology-driven stages 1-5 before Maizzle inlines
            raw_clients = context.metadata.get("target_clients")
            target_clients_list: list[str] | None = None
            if isinstance(raw_clients, list):
                target_clients_list = list(cast("list[str]", raw_clients))

            try:
                from app.email_engine.css_compiler.compiler import EmailCSSCompiler

                compiler = EmailCSSCompiler(target_clients=target_clients_list)
                optimized = compiler.optimize_css(source_html)
                source_html = optimized.html

                logger.info(
                    "blueprint.maizzle_build.css_optimized",
                    removed_count=len(optimized.removed_properties),
                    conversion_count=len(optimized.conversions),
                    optimize_time_ms=optimized.optimize_time_ms,
                )
            except Exception as exc:
                # CSS optimization is best-effort — proceed with unoptimized HTML
                logger.warning("blueprint.maizzle_build.css_optimize_failed", error=str(exc))

        url = f"{settings.maizzle_builder_url}/build"
        payload: dict[str, object] = {
            "source": source_html,
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

        # Sanitize final output (stage 7 equivalent)
        compiled_html = sanitize_html_xss(compiled_html)

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
