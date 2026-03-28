# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Unit tests for TokenRewriterService, rewrite-tokens endpoint, and push auto-rewrite."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.connectors.sync_service import ConnectorSyncService
from app.connectors.token_rewriter import TokenRewriterService
from app.core.exceptions import DomainValidationError
from app.core.rate_limit import limiter
from app.main import app

BASE = "/api/v1/connectors/sync"


# ── Helpers ──


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_connection(
    id: int = 1,
    esp_type: str = "braze",
    project_id: int = 1,
    encrypted_credentials: str = "",
    status: str = "connected",
) -> MagicMock:
    conn = MagicMock()
    conn.id = id
    conn.esp_type = esp_type
    conn.name = "Test Connection"
    conn.encrypted_credentials = encrypted_credentials
    conn.credentials_hint = "****1234"
    conn.status = status
    conn.error_message = None
    conn.project_id = project_id
    conn.created_by_id = 1
    conn.last_synced_at = None
    conn.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    conn.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return conn


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Rewrite Service tests
# ---------------------------------------------------------------------------


class TestTokenRewriterService:
    @pytest.mark.asyncio
    async def test_klaviyo_to_sfmc(self) -> None:
        rewriter = TokenRewriterService()
        html = '<td>{{ person.first_name | default: "Friend" }}</td>'
        result = await rewriter.rewrite(html, "sfmc", "klaviyo")
        assert "%%=" in result.html
        assert result.source_esp == "klaviyo"
        assert result.target_esp == "sfmc"
        assert result.tokens_rewritten >= 1

    @pytest.mark.asyncio
    async def test_braze_to_hubspot(self) -> None:
        rewriter = TokenRewriterService()
        html = "{{ first_name }}"
        result = await rewriter.rewrite(html, "hubspot", "braze")
        assert "contact.first_name" in result.html
        assert result.tokens_rewritten == 1

    @pytest.mark.asyncio
    async def test_no_tokens_raises_validation_error(self) -> None:
        """HTML without tokens raises DomainValidationError when auto-detecting."""
        rewriter = TokenRewriterService()
        html = "<table><tr><td>Plain text</td></tr></table>"
        with pytest.raises(DomainValidationError, match="Could not detect"):
            await rewriter.rewrite(html, "sfmc")

    @pytest.mark.asyncio
    async def test_same_esp_passthrough(self) -> None:
        rewriter = TokenRewriterService()
        html = "{{ first_name }}"
        result = await rewriter.rewrite(html, "braze", "braze")
        assert result.html == html
        assert result.tokens_rewritten == 0

    @pytest.mark.asyncio
    async def test_auto_detect_source(self) -> None:
        rewriter = TokenRewriterService()
        html = '{% connected_content https://api.example.com %}{{ first_name | default: "there" }}'
        result = await rewriter.rewrite(html, "klaviyo")
        assert result.source_esp == "braze"
        assert "person." in result.html


# ---------------------------------------------------------------------------
# 2. Endpoint tests
# ---------------------------------------------------------------------------


class TestRewriteTokensEndpoint:
    @pytest.mark.usefixtures("_auth_developer")
    def test_valid_rewrite_200(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/rewrite-tokens",
            json={
                "html": "{{ first_name }}",
                "target_esp": "sfmc",
                "source_esp": "braze",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "%%=" in body["html"]
        assert body["source_esp"] == "braze"
        assert body["target_esp"] == "sfmc"
        assert body["tokens_rewritten"] >= 1

    @pytest.mark.usefixtures("_auth_developer")
    def test_missing_html_422(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/rewrite-tokens",
            json={"target_esp": "sfmc"},
        )
        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_invalid_target_esp_422(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/rewrite-tokens",
            json={"html": "{{ x }}", "target_esp": "invalid_platform"},
        )
        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_no_tokens_auto_detect_422(self, client: TestClient) -> None:
        """Auto-detect with no ESP tokens returns 422 (DomainValidationError)."""
        resp = client.post(
            f"{BASE}/rewrite-tokens",
            json={
                "html": "<table><tr><td>Plain</td></tr></table>",
                "target_esp": "sfmc",
            },
        )
        assert resp.status_code == 422

    def test_unauthenticated_401(self, client: TestClient) -> None:
        app.dependency_overrides.clear()
        resp = client.post(
            f"{BASE}/rewrite-tokens",
            json={"html": "{{ x }}", "target_esp": "braze"},
        )
        assert resp.status_code == 401

    def test_viewer_forbidden_403(self, client: TestClient) -> None:
        user = _make_user("viewer")
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.post(
            f"{BASE}/rewrite-tokens",
            json={"html": "{{ x }}", "target_esp": "braze"},
        )
        app.dependency_overrides.clear()
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. Push auto-rewrite integration tests
# ---------------------------------------------------------------------------


class TestPushAutoRewrite:
    @pytest.mark.asyncio
    async def test_push_auto_rewrites_when_source_differs(self) -> None:
        """Push detects Braze tokens and rewrites to target SFMC connection."""
        db = AsyncMock()
        service = ConnectorSyncService(db)
        user = MagicMock()
        user.id = 1
        user.role = "developer"

        conn = _make_connection(esp_type="sfmc")
        local_tpl = MagicMock()
        local_tpl.name = "Test Email"
        local_tpl.latest_version = 1
        version = MagicMock()
        # HTML with Braze connected_content for reliable detection
        version.html_source = '{% connected_content https://api.example.com %}Hello {{ first_name | default: "there" }}'
        remote_tpl = MagicMock()
        remote_tpl.id = "remote_1"
        remote_tpl.name = "Test Email"
        remote_tpl.html = "..."
        remote_tpl.esp_type = "sfmc"
        remote_tpl.created_at = "2026-01-01"
        remote_tpl.updated_at = "2026-01-01"

        with (
            patch.object(
                service,
                "_get_connection_with_bola",
                new_callable=AsyncMock,
                return_value=(conn, {"api_key": "k"}),
            ),
            patch.object(service, "_get_provider") as mock_get_provider,
            patch.object(
                service._template_service,
                "get_template",
                new_callable=AsyncMock,
                return_value=local_tpl,
            ),
            patch.object(
                service._template_service,
                "get_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch.object(service._repo, "update_status", new_callable=AsyncMock),
        ):
            mock_provider = AsyncMock()
            mock_provider.create_template = AsyncMock(return_value=remote_tpl)
            mock_get_provider.return_value = mock_provider

            result = await service.push_template(1, 10, user)
            # Verify the HTML sent to provider was rewritten to SFMC syntax
            call_args = mock_provider.create_template.call_args
            pushed_html = call_args[0][1]
            assert "%%=" in pushed_html  # SFMC tokens present
            assert result is not None

    @pytest.mark.asyncio
    async def test_push_skips_rewrite_when_same_esp(self) -> None:
        """Push with same source/target ESP doesn't rewrite."""
        db = AsyncMock()
        service = ConnectorSyncService(db)
        user = MagicMock()
        user.id = 1

        conn = _make_connection(esp_type="braze")
        local_tpl = MagicMock()
        local_tpl.name = "Test"
        local_tpl.latest_version = 1
        version = MagicMock()
        version.html_source = (
            '{% connected_content https://api.com %}{{ first_name | default: "hi" }}'
        )
        remote_tpl = MagicMock()
        remote_tpl.id = "r1"
        remote_tpl.name = "Test"
        remote_tpl.html = ""
        remote_tpl.esp_type = "braze"
        remote_tpl.created_at = "2026-01-01"
        remote_tpl.updated_at = "2026-01-01"

        with (
            patch.object(
                service,
                "_get_connection_with_bola",
                new_callable=AsyncMock,
                return_value=(conn, {"api_key": "k"}),
            ),
            patch.object(service, "_get_provider") as mock_get_provider,
            patch.object(
                service._template_service,
                "get_template",
                new_callable=AsyncMock,
                return_value=local_tpl,
            ),
            patch.object(
                service._template_service,
                "get_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch.object(service._repo, "update_status", new_callable=AsyncMock),
        ):
            mock_provider = AsyncMock()
            mock_provider.create_template = AsyncMock(return_value=remote_tpl)
            mock_get_provider.return_value = mock_provider

            await service.push_template(1, 10, user)
            call_args = mock_provider.create_template.call_args
            pushed_html = call_args[0][1]
            # Original Braze syntax preserved
            assert "{{" in pushed_html
            assert "%%=" not in pushed_html

    @pytest.mark.asyncio
    async def test_push_preserves_no_token_html(self) -> None:
        """Push with plain HTML (no tokens) passes through unchanged."""
        db = AsyncMock()
        service = ConnectorSyncService(db)
        user = MagicMock()
        user.id = 1

        conn = _make_connection(esp_type="sfmc")
        local_tpl = MagicMock()
        local_tpl.name = "Plain"
        local_tpl.latest_version = 1
        version = MagicMock()
        original_html = "<table><tr><td>No tokens here</td></tr></table>"
        version.html_source = original_html
        remote_tpl = MagicMock()
        remote_tpl.id = "r1"
        remote_tpl.name = "Plain"
        remote_tpl.html = ""
        remote_tpl.esp_type = "sfmc"
        remote_tpl.created_at = "2026-01-01"
        remote_tpl.updated_at = "2026-01-01"

        with (
            patch.object(
                service,
                "_get_connection_with_bola",
                new_callable=AsyncMock,
                return_value=(conn, {"api_key": "k"}),
            ),
            patch.object(service, "_get_provider") as mock_get_provider,
            patch.object(
                service._template_service,
                "get_template",
                new_callable=AsyncMock,
                return_value=local_tpl,
            ),
            patch.object(
                service._template_service,
                "get_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch.object(service._repo, "update_status", new_callable=AsyncMock),
        ):
            mock_provider = AsyncMock()
            mock_provider.create_template = AsyncMock(return_value=remote_tpl)
            mock_get_provider.return_value = mock_provider

            await service.push_template(1, 10, user)
            call_args = mock_provider.create_template.call_args
            pushed_html = call_args[0][1]
            assert pushed_html == original_html
