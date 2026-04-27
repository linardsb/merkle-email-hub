"""Hook registry for pipeline execution events."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.ai.hooks.profiles import HookProfile, profile_includes
from app.ai.pipeline.artifacts import ArtifactStore
from app.core.logging import get_logger

logger = get_logger(__name__)


class HookEvent(StrEnum):
    """Pipeline execution events that hooks can subscribe to."""

    PRE_AGENT = "pre_agent"
    POST_AGENT = "post_agent"
    PRE_PIPELINE = "pre_pipeline"
    POST_PIPELINE = "post_pipeline"
    PRE_LEVEL = "pre_level"
    POST_LEVEL = "post_level"
    CONTRACT_FAILED = "contract_failed"
    ARTIFACT_STORED = "artifact_stored"


@dataclass(frozen=True, slots=True)
class HookContext:
    """Context passed to hook functions on each event."""

    run_id: str
    pipeline_name: str
    event: HookEvent
    agent_name: str | None = None
    level: int | None = None
    artifacts: ArtifactStore | None = None
    node_trace: Any | None = None  # NodeTrace (avoid circular import)
    cost_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


@dataclass(frozen=True, slots=True)
class HookResult:
    """Result of a single hook invocation."""

    hook_name: str
    duration_ms: int
    output: Any | None = None
    error: str | None = None


# Callable type for hooks
HookFn = Callable[[HookContext], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class _RegisteredHook:
    name: str
    event: HookEvent
    fn: HookFn
    profile: HookProfile


class HookRegistry:
    """Registry for pipeline execution hooks with profile-based filtering."""

    def __init__(
        self,
        active_profile: HookProfile = "standard",
        disabled: frozenset[str] = frozenset(),
    ) -> None:
        self._hooks: list[_RegisteredHook] = []
        self._profile: HookProfile = active_profile
        self._disabled = disabled

    @property
    def active_profile(self) -> HookProfile:
        return self._profile

    def register(
        self,
        event: HookEvent,
        fn: HookFn,
        *,
        name: str,
        profile: HookProfile = "standard",
    ) -> None:
        """Register a hook function for a specific event and profile level."""
        if name in self._disabled:
            return
        self._hooks.append(_RegisteredHook(name=name, event=event, fn=fn, profile=profile))

    async def fire(self, event: HookEvent, context: HookContext) -> list[HookResult]:
        """Fire all registered hooks for an event, respecting profile filtering.

        HookAbortError propagates immediately. All other hook errors are
        logged and captured in the result without stopping execution.
        """
        from app.core.exceptions import HookAbortError

        results: list[HookResult] = []
        for hook in self._hooks:
            if hook.event != event:
                continue
            if not profile_includes(self._profile, hook.profile):
                continue
            start = time.monotonic()
            try:
                output = await hook.fn(context)
                elapsed = int((time.monotonic() - start) * 1000)
                results.append(HookResult(hook_name=hook.name, duration_ms=elapsed, output=output))
            except HookAbortError:
                raise
            except Exception as exc:
                elapsed = int((time.monotonic() - start) * 1000)
                logger.warning(
                    "hooks.fire.error",
                    extra={
                        "hook": hook.name,
                        "event": event,
                        "error": str(exc),
                    },
                )
                results.append(
                    HookResult(
                        hook_name=hook.name,
                        duration_ms=elapsed,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results
