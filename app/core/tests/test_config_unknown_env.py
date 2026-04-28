"""Tests for the unknown-env-var warning hook.

Pydantic's `extra="ignore"` silently drops typo'd env vars like
`AUT__JWT_SECRET_KEY`. The hook in `app.core.config` walks the model and
warns on any `*__*` env var the model does not expect.

structlog routes through `PrintLoggerFactory()` so warnings go straight to
stderr; tests assert against `capsys`, not `caplog`.
"""

from __future__ import annotations

import pytest

from app.core.config import (
    Settings,
    _walk_known_env_vars,
    _warn_unknown_nested_env_vars,
)


class TestKnownEnvVarWalk:
    def test_walks_top_level_fields(self) -> None:
        known = _walk_known_env_vars(Settings)
        assert "APP_NAME" in known
        assert "ENVIRONMENT" in known
        assert "MAIZZLE_BUILDER_URL" in known

    def test_walks_nested_via_double_underscore(self) -> None:
        known = _walk_known_env_vars(Settings)
        assert "DATABASE__URL" in known
        assert "AUTH__JWT_SECRET_KEY" in known
        assert "AI__PROVIDER" in known
        assert "DESIGN_SYNC__VLM_VERIFY_ENABLED" in known

    def test_walks_doubly_nested(self) -> None:
        # RenderingConfig has nested SandboxConfig and CalibrationConfig.
        known = _walk_known_env_vars(Settings)
        assert "RENDERING__SANDBOX__SMTP_HOST" in known
        assert "RENDERING__CALIBRATION__EMA_ALPHA" in known


class TestUnknownEnvWarning:
    def test_warns_on_typo(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("AUT__JWT_SECRET_KEY", "typo")
        _warn_unknown_nested_env_vars()
        captured = capsys.readouterr()
        combined = captured.err + captured.out
        assert "AUT__JWT_SECRET_KEY" in combined
        assert "config.unknown_env_var" in combined

    def test_silent_on_valid_nested(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("AUT__JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("AI__PROVIDER", "anthropic")
        _warn_unknown_nested_env_vars()
        captured = capsys.readouterr()
        combined = captured.err + captured.out
        assert "AI__PROVIDER" not in combined

    def test_ignores_leading_underscore_system_vars(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # macOS injects e.g. __CFBundleIdentifier; we must not warn on those.
        monkeypatch.setenv("__SYSTEM__INJECTED", "1")
        _warn_unknown_nested_env_vars()
        captured = capsys.readouterr()
        combined = captured.err + captured.out
        assert "__SYSTEM__INJECTED" not in combined
