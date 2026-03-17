"""Tests for BIMI readiness checker (Phase 20.4)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import limiter
from app.main import app
from app.qa_engine.bimi.checker import BIMIReadinessChecker
from app.qa_engine.bimi.types import BIMIStatus
from app.qa_engine.service import QAEngineService

# --- Fixtures ---

VALID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" baseProfile="tiny-ps" '
    'viewBox="0 0 100 100"><title>Logo</title><rect width="100" height="100"/></svg>'
)

DMARC_REJECT = "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
DMARC_QUARANTINE = "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
DMARC_NONE = "v=DMARC1; p=none; rua=mailto:dmarc@example.com"
DMARC_PCT_50 = "v=DMARC1; p=reject; pct=50; rua=mailto:dmarc@example.com"

BIMI_FULL = "v=BIMI1; l=https://example.com/logo.svg; a=https://example.com/cert.pem"
BIMI_NO_AUTH = "v=BIMI1; l=https://example.com/logo.svg"
BIMI_NO_LOGO = "v=BIMI1"
BIMI_INVALID = "some random txt record"


def _mock_settings(enabled: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.qa_bimi.enabled = enabled
    settings.qa_bimi.dns_timeout_seconds = 5.0
    settings.qa_bimi.svg_fetch_timeout_seconds = 10.0
    settings.qa_bimi.svg_max_size_bytes = 32_768
    return settings


def _make_dns_result(txt: str) -> MagicMock:
    """Create a mock DNS answer with a single TXT record."""
    rdata = MagicMock()
    rdata.strings = [txt.encode()]
    answer = MagicMock()
    answer.__iter__ = lambda _self: iter([rdata])
    return answer


# --- Unit Tests: BIMIReadinessChecker ---


@pytest.mark.asyncio
async def test_invalid_domain() -> None:
    """Invalid domain format returns error."""
    checker = BIMIReadinessChecker()
    result = await checker.check_domain("not a domain!")
    assert result.dmarc_policy == "invalid_domain"
    assert not result.dmarc_ready
    assert "Invalid domain format" in result.issues


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_dmarc_reject_is_ready(mock_settings: MagicMock) -> None:
    """Domain with p=reject → dmarc_ready=True."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=None),
    ):
        result = await checker.check_domain("example.com")

    assert result.dmarc_ready is True
    assert result.dmarc_policy == "reject"


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_dmarc_quarantine_is_ready(mock_settings: MagicMock) -> None:
    """p=quarantine → dmarc_ready=True."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_QUARANTINE),
        patch.object(checker, "_lookup_bimi", return_value=None),
    ):
        result = await checker.check_domain("example.com")

    assert result.dmarc_ready is True
    assert result.dmarc_policy == "quarantine"


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_dmarc_none_not_ready(mock_settings: MagicMock) -> None:
    """p=none → dmarc_ready=False with issue message."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_NONE),
        patch.object(checker, "_lookup_bimi", return_value=None),
    ):
        result = await checker.check_domain("example.com")

    assert result.dmarc_ready is False
    assert result.dmarc_policy == "none"
    assert any("must be 'quarantine' or 'reject'" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_dmarc_missing(mock_settings: MagicMock) -> None:
    """No TXT record → dmarc_policy='missing'."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=None),
        patch.object(checker, "_lookup_bimi", return_value=None),
    ):
        result = await checker.check_domain("example.com")

    assert result.dmarc_policy == "missing"
    assert any("No DMARC record found" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_dmarc_pct_warning(mock_settings: MagicMock) -> None:
    """pct=50 → warning about 100%."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_PCT_50),
        patch.object(checker, "_lookup_bimi", return_value=None),
    ):
        result = await checker.check_domain("example.com")

    assert result.dmarc_ready is True
    assert any("pct=50" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_bimi_record_parsed(mock_settings: MagicMock) -> None:
    """Valid v=BIMI1; l=...; a=... parsed correctly."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=BIMI_FULL),
        patch.object(
            checker,
            "_validate_svg",
            return_value=MagicMock(valid=True, issues=[]),
        ),
    ):
        result = await checker.check_domain("example.com")

    assert result.bimi_record_exists is True
    assert result.bimi_svg_url == "https://example.com/logo.svg"
    assert result.bimi_authority_url == "https://example.com/cert.pem"


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_bimi_record_missing(mock_settings: MagicMock) -> None:
    """No BIMI record → bimi_record_exists=False."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=None),
    ):
        result = await checker.check_domain("example.com")

    assert result.bimi_record_exists is False
    assert any("No BIMI record found" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_bimi_no_logo_url(mock_settings: MagicMock) -> None:
    """BIMI record without l= → issue."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=BIMI_NO_LOGO),
    ):
        result = await checker.check_domain("example.com")

    assert result.bimi_record_exists is True
    assert result.bimi_svg_url is None
    assert any("no l=" in i for i in result.issues)


def test_svg_valid_tiny_ps() -> None:
    """Valid square SVG with baseProfile='tiny-ps' → no issues."""
    checker = BIMIReadinessChecker()
    issues = checker._check_svg_tiny_ps(VALID_SVG)
    assert issues == []


def test_svg_not_square() -> None:
    """Non-square viewBox → issue."""
    svg = '<svg viewBox="0 0 200 100"><title>X</title></svg>'
    checker = BIMIReadinessChecker()
    issues = checker._check_svg_tiny_ps(svg)
    assert any("not square" in i for i in issues)


def test_svg_forbidden_script() -> None:
    """SVG with <script> → issue."""
    svg = '<svg baseProfile="tiny-ps" viewBox="0 0 100 100"><title>X</title><script>alert(1)</script></svg>'
    checker = BIMIReadinessChecker()
    issues = checker._check_svg_tiny_ps(svg)
    assert any("<script>" in i for i in issues)


def test_svg_external_refs() -> None:
    """SVG with external href → issue."""
    svg = '<svg baseProfile="tiny-ps" viewBox="0 0 100 100"><title>X</title><rect href="https://evil.com"/></svg>'
    checker = BIMIReadinessChecker()
    issues = checker._check_svg_tiny_ps(svg)
    assert any("external references" in i for i in issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_svg_too_large(mock_settings: MagicMock) -> None:
    """SVG over 32KB → issue."""
    mock_settings.return_value = _mock_settings()
    mock_settings.return_value.qa_bimi.svg_max_size_bytes = 100  # tiny limit

    checker = BIMIReadinessChecker()

    mock_response = MagicMock()
    mock_response.content = b"x" * 200
    mock_response.text = VALID_SVG
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.qa_engine.bimi.checker.httpx.AsyncClient", return_value=mock_client):
        result = await checker._validate_svg("https://example.com/logo.svg")

    assert result.valid is False
    assert any("200 bytes" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_svg_https_required(mock_settings: MagicMock) -> None:
    """HTTP URL → svg_valid=False."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()
    result = await checker._validate_svg("http://example.com/logo.svg")
    assert result.valid is False
    assert any("HTTPS" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_svg_fetch_timeout(mock_settings: MagicMock) -> None:
    """Timeout → svg_valid=False."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.qa_engine.bimi.checker.httpx.AsyncClient", return_value=mock_client):
        result = await checker._validate_svg("https://example.com/logo.svg")

    assert result.valid is False
    assert any("timed out" in i for i in result.issues)


def test_svg_missing_title() -> None:
    """No <title> → issue."""
    svg = '<svg baseProfile="tiny-ps" viewBox="0 0 100 100"><rect/></svg>'
    checker = BIMIReadinessChecker()
    issues = checker._check_svg_tiny_ps(svg)
    assert any("<title>" in i for i in issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_cmc_present(mock_settings: MagicMock) -> None:
    """Authority URL in BIMI → cmc_status='present'."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=BIMI_FULL),
        patch.object(
            checker,
            "_validate_svg",
            return_value=MagicMock(valid=True, issues=[]),
        ),
    ):
        result = await checker.check_domain("example.com")

    assert result.cmc_status == "present"


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_cmc_missing(mock_settings: MagicMock) -> None:
    """No a= tag → cmc_status='missing' with issue."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=BIMI_NO_AUTH),
        patch.object(
            checker,
            "_validate_svg",
            return_value=MagicMock(valid=True, issues=[]),
        ),
    ):
        result = await checker.check_domain("example.com")

    assert result.cmc_status == "missing"
    assert any("CMC" in i for i in result.issues)


@pytest.mark.asyncio
@patch("app.qa_engine.bimi.checker.get_settings")
async def test_fully_ready(mock_settings: MagicMock) -> None:
    """All checks pass → ready=True."""
    mock_settings.return_value = _mock_settings()
    checker = BIMIReadinessChecker()

    with (
        patch.object(checker, "_lookup_dmarc", return_value=DMARC_REJECT),
        patch.object(checker, "_lookup_bimi", return_value=BIMI_FULL),
        patch.object(
            checker,
            "_validate_svg",
            return_value=MagicMock(valid=True, issues=[]),
        ),
    ):
        result = await checker.check_domain("example.com")

    assert result.ready is True
    assert result.dmarc_ready is True
    assert result.bimi_record_exists is True
    assert result.svg_valid is True
    assert result.cmc_status == "present"


def test_generate_record() -> None:
    """Record generation with SVG and CMC URLs."""
    checker = BIMIReadinessChecker()
    record = checker._generate_record(
        "example.com",
        svg_url="https://example.com/logo.svg",
        authority_url="https://example.com/cert.pem",
    )
    assert "default._bimi.example.com" in record
    assert "v=BIMI1" in record
    assert "l=https://example.com/logo.svg" in record
    assert "a=https://example.com/cert.pem" in record


def test_generate_record_placeholder() -> None:
    """Record generation without URLs uses placeholder."""
    checker = BIMIReadinessChecker()
    record = checker._generate_record("example.com")
    assert "example.com/bimi/logo.svg" in record


# --- Route tests ---

BASE = "/api/v1/qa"


def _make_user(role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = role
    return user


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestRoutes:
    def test_bimi_check_requires_auth(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/bimi-check", json={"domain": "example.com"})
        assert resp.status_code == 401

    @pytest.mark.usefixtures("_auth_developer")
    def test_bimi_check_disabled(self, client: TestClient) -> None:
        with patch.object(
            QAEngineService,
            "run_bimi_check",
            new_callable=AsyncMock,
            side_effect=ForbiddenError("BIMI readiness check is not enabled"),
        ):
            resp = client.post(f"{BASE}/bimi-check", json={"domain": "example.com"})
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_bimi_check_success(self, client: TestClient) -> None:
        from app.qa_engine.schemas import BIMICheckResponse

        mock_response = BIMICheckResponse(
            domain="example.com",
            ready=True,
            dmarc_ready=True,
            dmarc_policy="reject",
            bimi_record_exists=True,
            svg_valid=True,
            cmc_status="present",
            generated_record="test",
        )
        with patch.object(
            QAEngineService,
            "run_bimi_check",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = client.post(f"{BASE}/bimi-check", json={"domain": "example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain"] == "example.com"
        assert data["ready"] is True
        assert data["dmarc_ready"] is True

    @pytest.mark.usefixtures("_auth_developer")
    def test_bimi_check_invalid_domain(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/bimi-check", json={"domain": "x"})
        assert resp.status_code == 422


# --- Service tests ---


@pytest.mark.asyncio
async def test_service_delegates_to_checker() -> None:
    """Service calls checker and maps response."""
    from app.qa_engine.schemas import BIMICheckRequest
    from app.qa_engine.service import QAEngineService

    service = QAEngineService.__new__(QAEngineService)
    request = BIMICheckRequest(domain="example.com")

    mock_status = BIMIStatus(
        domain="example.com",
        dmarc_ready=True,
        dmarc_policy="reject",
        bimi_record_exists=True,
        svg_valid=True,
        cmc_status="present",
        generated_record="test",
    )

    with (
        patch(
            "app.qa_engine.service.get_settings",
            return_value=_mock_settings(enabled=True),
        ),
        patch(
            "app.qa_engine.bimi.checker.BIMIReadinessChecker.check_domain",
            return_value=mock_status,
        ),
    ):
        result = await service.run_bimi_check(request)

    assert result.domain == "example.com"
    assert result.ready is True
    assert result.dmarc_policy == "reject"


@pytest.mark.asyncio
async def test_service_disabled_raises() -> None:
    """ForbiddenError when disabled."""
    from app.core.exceptions import ForbiddenError
    from app.qa_engine.schemas import BIMICheckRequest
    from app.qa_engine.service import QAEngineService

    service = QAEngineService.__new__(QAEngineService)
    request = BIMICheckRequest(domain="example.com")

    with (
        patch(
            "app.qa_engine.service.get_settings",
            return_value=_mock_settings(enabled=False),
        ),
        pytest.raises(ForbiddenError),
    ):
        await service.run_bimi_check(request)
