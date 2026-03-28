# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Route tests for MJML import endpoint (Phase 36.4)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.main import app

BASE = "/api/v1/design-sync"

_MINIMAL_MJML = (
    "<mjml><mj-body>"
    "<mj-section><mj-column>"
    "<mj-text>Hello World</mj-text>"
    "</mj-column></mj-section>"
    "</mj-body></mjml>"
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    saved = dict(app.dependency_overrides)
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    saved = dict(app.dependency_overrides)
    user = _make_user("viewer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("_auth_developer")
def test_import_mjml_success(client: TestClient) -> None:
    """POST /import/mjml returns 200 with document JSON."""
    resp = client.post(f"{BASE}/import/mjml", json={"mjml_source": _MINIMAL_MJML})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sections_count"] == 1
    assert "document" in body
    assert body["document"]["source"]["provider"] == "mjml"
    assert isinstance(body["warnings"], list)


@pytest.mark.usefixtures("_auth_developer")
def test_import_mjml_malformed_xml(client: TestClient) -> None:
    """POST /import/mjml returns 422 for malformed XML."""
    resp = client.post(f"{BASE}/import/mjml", json={"mjml_source": "<mjml><unclosed>"})
    assert resp.status_code == 422


def test_import_mjml_no_auth(client: TestClient) -> None:
    """POST /import/mjml returns 401 without auth."""
    resp = client.post(f"{BASE}/import/mjml", json={"mjml_source": _MINIMAL_MJML})
    assert resp.status_code == 401


@pytest.mark.usefixtures("_auth_viewer")
def test_import_mjml_viewer_forbidden(client: TestClient) -> None:
    """POST /import/mjml returns 403 for viewer role."""
    resp = client.post(f"{BASE}/import/mjml", json={"mjml_source": _MINIMAL_MJML})
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_developer")
def test_import_mjml_disabled(client: TestClient) -> None:
    """POST /import/mjml returns 503 when disabled."""
    from unittest.mock import MagicMock, patch

    mock_cfg = MagicMock()
    mock_cfg.design_sync.mjml_import_enabled = False
    with patch("app.core.config.get_settings", return_value=mock_cfg):
        resp = client.post(f"{BASE}/import/mjml", json={"mjml_source": _MINIMAL_MJML})
    assert resp.status_code == 503


@pytest.mark.usefixtures("_auth_developer")
def test_import_mjml_oversized(client: TestClient) -> None:
    """POST /import/mjml returns 413 or 422 for oversized input."""
    huge = "<mjml><mj-body>" + "x" * (2 * 1024 * 1024) + "</mj-body></mjml>"
    resp = client.post(f"{BASE}/import/mjml", json={"mjml_source": huge})
    # Middleware may reject at 413 before adapter's 422
    assert resp.status_code in (413, 422)
