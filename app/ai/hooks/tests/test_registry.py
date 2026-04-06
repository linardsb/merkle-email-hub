"""Tests for HookRegistry."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.core.exceptions import HookAbortError


def _make_context(
    run_id: str = "test-run",
    event: HookEvent = HookEvent.PRE_AGENT,
) -> HookContext:
    return HookContext(
        run_id=run_id,
        pipeline_name="test-pipeline",
        event=event,
    )


class TestHookRegistry:
    @pytest.mark.asyncio
    async def test_register_and_fire(self, hook_registry: HookRegistry) -> None:
        fn = AsyncMock(return_value={"ok": True})
        hook_registry.register(HookEvent.PRE_AGENT, fn, name="test_hook", profile="standard")

        ctx = _make_context(event=HookEvent.PRE_AGENT)
        results = await hook_registry.fire(HookEvent.PRE_AGENT, ctx)

        assert len(results) == 1
        assert results[0].hook_name == "test_hook"
        assert results[0].output == {"ok": True}
        assert results[0].error is None
        fn.assert_awaited_once_with(ctx)

    @pytest.mark.asyncio
    async def test_profile_filtering(self) -> None:
        registry = HookRegistry(active_profile="standard")
        fn = AsyncMock(return_value=None)
        registry.register(HookEvent.PRE_AGENT, fn, name="strict_hook", profile="strict")

        ctx = _make_context(event=HookEvent.PRE_AGENT)
        results = await registry.fire(HookEvent.PRE_AGENT, ctx)

        assert len(results) == 0
        fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disabled_hook_skipped(self) -> None:
        registry = HookRegistry(active_profile="strict", disabled=frozenset({"disabled_hook"}))
        fn = AsyncMock(return_value=None)
        registry.register(HookEvent.PRE_AGENT, fn, name="disabled_hook", profile="minimal")

        ctx = _make_context(event=HookEvent.PRE_AGENT)
        results = await registry.fire(HookEvent.PRE_AGENT, ctx)

        assert len(results) == 0
        fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_hook_error_captured(self, hook_registry: HookRegistry) -> None:
        fn = AsyncMock(side_effect=RuntimeError("boom"))
        hook_registry.register(HookEvent.PRE_AGENT, fn, name="failing_hook", profile="standard")

        ctx = _make_context(event=HookEvent.PRE_AGENT)
        results = await hook_registry.fire(HookEvent.PRE_AGENT, ctx)

        assert len(results) == 1
        assert results[0].hook_name == "failing_hook"
        assert results[0].error == "RuntimeError: boom"
        assert results[0].output is None

    @pytest.mark.asyncio
    async def test_hook_abort_propagates(self, hook_registry: HookRegistry) -> None:
        async def aborting_hook(ctx: HookContext) -> None:
            raise HookAbortError("gate", "rejected")

        hook_registry.register(HookEvent.POST_AGENT, aborting_hook, name="gate", profile="standard")

        ctx = _make_context(event=HookEvent.POST_AGENT)
        with pytest.raises(HookAbortError, match="rejected"):
            await hook_registry.fire(HookEvent.POST_AGENT, ctx)
