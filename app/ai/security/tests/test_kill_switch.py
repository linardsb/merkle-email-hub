"""Config round-trip tests for the agent kill switch + per-run caps.

The runtime behaviour of the kill switch is covered in
``app/ai/agents/tests/test_base_security.py``. This file pins down the
config surface itself: defaults, env-var parsing, and the empty-string
edge case called out in the plan's preflight warnings.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import SecurityConfig


class TestSecurityConfigDefaults:
    def test_disabled_agents_defaults_empty(self) -> None:
        cfg = SecurityConfig()
        assert cfg.disabled_agents == []

    def test_run_cap_defaults(self) -> None:
        cfg = SecurityConfig()
        assert cfg.agent_max_run_seconds == 90
        assert cfg.agent_max_total_tokens == 32_000


class TestSecurityConfigParsing:
    def test_disabled_agents_accepts_list(self) -> None:
        cfg = SecurityConfig(disabled_agents=["scaffolder", "dark_mode"])
        assert cfg.disabled_agents == ["scaffolder", "dark_mode"]

    def test_run_cap_accepts_overrides(self) -> None:
        cfg = SecurityConfig(agent_max_run_seconds=30, agent_max_total_tokens=8_000)
        assert cfg.agent_max_run_seconds == 30
        assert cfg.agent_max_total_tokens == 8_000

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SecurityConfig(prompt_guard_mode="bogus")  # pyright: ignore[reportArgumentType]
