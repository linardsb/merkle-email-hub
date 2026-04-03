# pyright: reportUnknownMemberType=false
"""Tests for credential health API endpoint."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.credentials import CredentialPool, _hash_key
from app.core.rate_limit import limiter


def _mock_config(
    *,
    cooldown_initial_seconds: int = 30,
    cooldown_max_seconds: int = 300,
    failure_threshold: int = 3,
    unhealthy_ttl_seconds: int = 3600,
) -> MagicMock:
    cfg = MagicMock()
    cfg.cooldown_initial_seconds = cooldown_initial_seconds
    cfg.cooldown_max_seconds = cooldown_max_seconds
    cfg.failure_threshold = failure_threshold
    cfg.unhealthy_ttl_seconds = unhealthy_ttl_seconds
    return cfg


def _mock_redis_with_state() -> tuple[AsyncMock, dict[str, str]]:
    store: dict[str, str] = {}
    redis = AsyncMock()

    async def _get(key: str) -> str | None:
        return store.get(key)

    async def _setex(key: str, ttl: int, value: str) -> None:
        store[key] = value

    redis.get = AsyncMock(side_effect=_get)
    redis.setex = AsyncMock(side_effect=_setex)
    return redis, store


def _admin_user() -> MagicMock:
    user = MagicMock()
    user.role = "admin"
    user.id = 1
    user.is_active = True
    return user


def _viewer_user() -> MagicMock:
    user = MagicMock()
    user.role = "viewer"
    user.id = 2
    user.is_active = True
    return user


@pytest.fixture
def admin_client() -> Generator[TestClient]:
    from app.core.credentials_routes import router

    app = FastAPI()
    app.include_router(router)
    limiter.enabled = False
    app.dependency_overrides[get_current_user] = _admin_user
    yield TestClient(app)
    limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client() -> Generator[TestClient]:
    from app.core.credentials_routes import router

    app = FastAPI()
    app.include_router(router)
    limiter.enabled = False
    app.dependency_overrides[get_current_user] = _viewer_user
    yield TestClient(app)
    limiter.enabled = True
    app.dependency_overrides.clear()


class TestCredentialHealth:
    def test_health_returns_empty_when_no_pools(self, admin_client: TestClient) -> None:
        with patch("app.core.credentials_routes.get_all_pools", return_value={}):
            resp = admin_client.get("/api/v1/credentials/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["services"] == []
        assert data["total_keys"] == 0
        assert data["healthy_total"] == 0

    def test_health_returns_pool_status(self, admin_client: TestClient) -> None:
        redis, _store = _mock_redis_with_state()
        config = _mock_config()

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool_a = CredentialPool("anthropic", ["key-1", "key-2"], config)
            pool_b = CredentialPool("openai", ["key-3"], config)

        pools = {"anthropic": pool_a, "openai": pool_b}
        with (
            patch("app.core.credentials_routes.get_all_pools", return_value=pools),
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
        ):
            resp = admin_client.get("/api/v1/credentials/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_keys"] == 3
        assert data["healthy_total"] == 3
        assert len(data["services"]) == 2
        svc_names = [s["service"] for s in data["services"]]
        assert "anthropic" in svc_names
        assert "openai" in svc_names

    def test_health_shows_cooled_down_keys(self, admin_client: TestClient) -> None:
        redis, store = _mock_redis_with_state()
        config = _mock_config()

        key_hash = _hash_key("key-a")
        store[f"credentials:svc:{key_hash}"] = json.dumps(
            {
                "healthy": True,
                "cooldown_until": 9999999999.0,
                "failure_count": 1,
                "last_failure_code": 429,
            }
        )

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("svc", ["key-a"], config)

        with (
            patch("app.core.credentials_routes.get_all_pools", return_value={"svc": pool}),
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 1000.0
            resp = admin_client.get("/api/v1/credentials/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["cooled_down_total"] == 1
        key_report = data["services"][0]["keys"][0]
        assert key_report["status"] == "cooled_down"
        assert key_report["cooldown_remaining_s"] > 0

    def test_health_shows_unhealthy_keys(self, admin_client: TestClient) -> None:
        redis, store = _mock_redis_with_state()
        config = _mock_config()

        key_hash = _hash_key("key-a")
        store[f"credentials:svc:{key_hash}"] = json.dumps(
            {
                "healthy": False,
                "cooldown_until": 0.0,
                "failure_count": 5,
                "last_failure_code": 401,
            }
        )

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("svc", ["key-a"], config)

        with (
            patch("app.core.credentials_routes.get_all_pools", return_value={"svc": pool}),
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 1000.0
            resp = admin_client.get("/api/v1/credentials/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["unhealthy_total"] == 1
        key_report = data["services"][0]["keys"][0]
        assert key_report["status"] == "unhealthy"
        assert key_report["failure_count"] == 5

    def test_health_forbidden_for_non_admin(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/v1/credentials/health")
        assert resp.status_code == 403

    def test_key_values_never_exposed(self, admin_client: TestClient) -> None:
        redis, _store = _mock_redis_with_state()
        config = _mock_config()
        raw_keys = ["sk-secret-key-abc123", "sk-another-secret-xyz"]

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("svc", raw_keys, config)

        with (
            patch("app.core.credentials_routes.get_all_pools", return_value={"svc": pool}),
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
        ):
            resp = admin_client.get("/api/v1/credentials/health")

        assert resp.status_code == 200
        body = resp.text
        for raw_key in raw_keys:
            assert raw_key not in body, f"Raw key {raw_key!r} leaked in response"
        # Verify hashes are present instead
        data = resp.json()
        for key_report in data["services"][0]["keys"]:
            assert len(key_report["key_hash"]) == 12
