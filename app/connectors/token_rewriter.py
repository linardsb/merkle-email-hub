"""Token rewriter service — orchestrates cross-ESP token migration."""

from __future__ import annotations

from dataclasses import dataclass

from app.connectors.token_ir import (
    ESPPlatform,
    detect_and_parse,
    emit_tokens,
    parse_tokens,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TokenRewriteResult:
    html: str
    source_esp: str
    target_esp: str
    tokens_rewritten: int
    warnings: tuple[str, ...]


class TokenRewriterService:
    """Orchestrate cross-ESP token migration: detect source, parse, emit target."""

    async def rewrite(
        self,
        html: str,
        target_esp: ESPPlatform,
        source_esp: ESPPlatform | None = None,
    ) -> TokenRewriteResult:
        """Rewrite ESP tokens in HTML from source to target format.

        If source_esp is None, auto-detects the source platform.
        """
        if source_esp is not None:
            ir = parse_tokens(html, source_esp)
            detected_source = source_esp
        else:
            ir, detected_source = detect_and_parse(html)

        # Same ESP → passthrough
        if detected_source == target_esp:
            logger.info(
                "connectors.token_rewrite.passthrough",
                source_esp=detected_source,
                target_esp=target_esp,
            )
            return TokenRewriteResult(
                html=html,
                source_esp=detected_source,
                target_esp=target_esp,
                tokens_rewritten=0,
                warnings=(),
            )

        new_html, warnings = emit_tokens(ir, html, target_esp)
        tokens_rewritten = len(ir.variables) + len(ir.conditionals) + len(ir.loops)

        logger.info(
            "connectors.token_rewrite.completed",
            source_esp=detected_source,
            target_esp=target_esp,
            tokens_rewritten=tokens_rewritten,
            warnings_count=len(warnings),
        )

        return TokenRewriteResult(
            html=new_html,
            source_esp=detected_source,
            target_esp=target_esp,
            tokens_rewritten=tokens_rewritten,
            warnings=tuple(warnings),
        )
