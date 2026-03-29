"""Pre-compile CSS for golden templates at registration time."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.ai.templates.models import GoldenTemplate
from app.core.config import get_settings
from app.core.logging import get_logger
from app.email_engine.css_compiler.compiler import EmailCSSCompiler

logger = get_logger(__name__)

CSS_PREOPTIMIZED_MARKER = "<!-- css-preoptimized -->"

_DEFAULT_TARGETS = ("gmail", "outlook", "apple_mail", "yahoo_mail")


@dataclass(frozen=True)
class PrecompilationReport:
    """Result of batch precompilation."""

    total: int
    succeeded: int
    failed: int
    total_size_reduction_bytes: int
    avg_compile_time_ms: float
    errors: dict[str, str]


class TemplatePrecompiler:
    """Pre-compiles CSS optimization for golden templates.

    Uses EmailCSSCompiler.optimize_css() (from 26.1) on template HTML.
    Result is stored in GoldenTemplate.optimized_html via dataclasses.replace().
    """

    def __init__(self, target_clients: tuple[str, ...] | None = None) -> None:
        settings = get_settings()
        configured = settings.email_engine.css_compiler_target_clients
        self._target_clients = target_clients or tuple(configured) or _DEFAULT_TARGETS

    def precompile(self, template: GoldenTemplate) -> GoldenTemplate:
        """Pre-compile CSS for a single template.

        Returns a new GoldenTemplate with optimized_html populated.
        Preserves slot placeholders, ESP tokens, builder annotations.
        """
        compiler = EmailCSSCompiler(target_clients=list(self._target_clients))
        start = time.monotonic()

        try:
            optimized = compiler.optimize_css(template.html)
        except Exception:
            logger.warning(
                "templates.precompile_failed",
                template=template.metadata.name,
                exc_info=True,
            )
            raise

        compile_time_ms = round((time.monotonic() - start) * 1000, 2)
        original_size = len(template.html.encode("utf-8"))
        optimized_size = len(optimized.html.encode("utf-8"))

        metadata: dict[str, object] = {
            "removed_properties": optimized.removed_properties,
            "conversions": len(optimized.conversions),
            "compile_time_ms": compile_time_ms,
            "original_size": original_size,
            "optimized_size": optimized_size,
        }

        optimized_html = CSS_PREOPTIMIZED_MARKER + optimized.html

        result = replace(
            template,
            optimized_html=optimized_html,
            optimized_at=datetime.now(UTC),
            optimized_for_clients=self._target_clients,
            optimization_metadata=metadata,
        )

        logger.info(
            "templates.precompiled",
            template=template.metadata.name,
            original_size=original_size,
            optimized_size=optimized_size,
            reduction_bytes=original_size - optimized_size,
            compile_time_ms=compile_time_ms,
        )

        return result

    def precompile_all(
        self,
        templates: dict[str, GoldenTemplate],
    ) -> tuple[dict[str, GoldenTemplate], PrecompilationReport]:
        """Batch precompile all templates.

        Returns updated templates dict and a report.
        """
        succeeded = 0
        failed = 0
        total_reduction = 0
        total_time = 0.0
        errors: dict[str, str] = {}
        updated: dict[str, GoldenTemplate] = {}

        for name, template in templates.items():
            try:
                compiled = self.precompile(template)
                updated[name] = compiled
                succeeded += 1
                meta = compiled.optimization_metadata
                orig = meta.get("original_size", 0)
                opt = meta.get("optimized_size", 0)
                total_reduction += int(str(orig)) - int(str(opt))
                total_time += float(str(meta.get("compile_time_ms", 0)))
            except Exception as exc:
                updated[name] = template  # keep original
                failed += 1
                errors[name] = str(exc)

        total = succeeded + failed
        report = PrecompilationReport(
            total=total,
            succeeded=succeeded,
            failed=failed,
            total_size_reduction_bytes=total_reduction,
            avg_compile_time_ms=round(total_time / max(succeeded, 1), 2),
            errors=errors,
        )

        logger.info(
            "templates.precompile_all_completed",
            total=total,
            succeeded=succeeded,
            failed=failed,
            total_reduction_bytes=total_reduction,
        )

        return updated, report

    @staticmethod
    def is_stale(template: GoldenTemplate, target_clients: tuple[str, ...]) -> bool:
        """Check if precompiled CSS is stale.

        Returns True if:
        - optimized_at is None (never precompiled)
        - optimized_for_clients differs from target_clients
        """
        if template.optimized_at is None:
            return True
        return set(template.optimized_for_clients) != set(target_clients)
