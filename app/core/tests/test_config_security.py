"""Security-related tests for application configuration.

Validates the two-layer defense around JWT secret entropy and production
secret sentinels (audit §1.2):

1. ``Field(min_length=32)`` on ``AuthConfig.jwt_secret_key`` rejects short
   secrets in any environment.
2. Root ``Settings`` ``model_validator`` refuses the default placeholder
   secret and the default demo password when ``environment == "production"``.

Tests instantiate ``Settings()`` directly via ``monkeypatch.setenv`` to bypass
the ``get_settings`` ``lru_cache``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip any inherited AUTH__* env vars so each test sets its own state."""
    monkeypatch.delenv("AUTH__JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("AUTH__DEMO_USER_PASSWORD", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_development_default_secrets_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """environment=development + default jwt_secret + default demo password -> OK."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert settings.environment == "development"
    assert settings.auth.jwt_secret_key.startswith("CHANGE-ME-IN-PRODUCTION")
    assert settings.auth.demo_user_password == "admin"


def test_production_default_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """environment=production + default jwt_secret -> ValueError."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert "AUTH__JWT_SECRET_KEY" in str(exc_info.value)


def test_production_default_demo_password_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """environment=production + custom jwt_secret + demo_password='admin' -> ValueError."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH__JWT_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("AUTH__DEMO_USER_PASSWORD", "admin")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert "AUTH__DEMO_USER_PASSWORD" in str(exc_info.value)


def test_production_with_custom_secrets_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """environment=production + custom jwt_secret + custom demo_password -> OK."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH__JWT_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("AUTH__DEMO_USER_PASSWORD", "rotated-strong-password")

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert settings.environment == "production"
    assert settings.auth.jwt_secret_key == "x" * 64
    assert settings.auth.demo_user_password == "rotated-strong-password"


def test_short_jwt_secret_rejected_any_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """jwt_secret shorter than 32 chars raises ValidationError regardless of environment."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH__JWT_SECRET_KEY", "too-short")  # 9 chars

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert "jwt_secret_key" in str(exc_info.value).lower()
