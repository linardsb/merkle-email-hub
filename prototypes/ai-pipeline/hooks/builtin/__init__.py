"""Built-in pipeline execution hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.hooks.registry import HookRegistry


def register_builtin_hooks(registry: HookRegistry) -> None:
    """Register all built-in hooks with the given registry."""
    from app.ai.hooks.builtin import (
        adversarial_gate,
        cost_tracker,
        pattern_extractor,
        progress_reporter,
        structured_logger,
    )

    cost_tracker.register(registry)
    structured_logger.register(registry)
    progress_reporter.register(registry)
    adversarial_gate.register(registry)
    pattern_extractor.register(registry)
