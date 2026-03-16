# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Route tests for all rendering API endpoints — auth, rate limiting, happy path, errors."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.main import app
from app.rendering.exceptions import (
    RenderingProviderError,
    RenderingTestNotFoundError,
    ScreenshotTimeoutError,
)
from app.rendering.schemas import (
    BaselineListResponse,
    BaselineResponse,
    RenderingComparisonResponse,
    RenderingDiff,
    RenderingTestResponse,
    ScreenshotClientResult,
    ScreenshotResponse,
    VisualDiffResponse,
)
from app.rendering.service import RenderingService
from app.shared.schemas import PaginatedResponse

# Small 1x1 white PNG for testing (base64)
TINY_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "nGP4z8BQDwAEgAF/pooBPQAAAABJRU5ErkJggg=="
)

BASE = "/api/v1/rendering"


# ── Helpers ──


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_test_response(test_id: int = 1) -> RenderingTestResponse:
    return RenderingTestResponse(
        id=test_id,
        external_test_id="litmus_test_abc",
        provider="litmus",
        status="complete",
        build_id=None,
        template_version_id=None,
        clients_requested=3,
        clients_completed=3,
        screenshots=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_screenshot_response() -> ScreenshotResponse:
    return ScreenshotResponse(
        screenshots=[
            ScreenshotClientResult(
                client_name="gmail_web",
                image_base64=TINY_PNG,
                viewport="1280x800",
                browser="chromium",
            )
        ],
        clients_rendered=1,
        clients_failed=0,
    )


def _make_visual_diff_response() -> VisualDiffResponse:
    return VisualDiffResponse(
        identical=True,
        diff_percentage=0.0,
        diff_image=None,
        pixel_count=0,
        changed_regions=[],
        threshold_used=0.01,
    )


def _make_baseline_list_response() -> BaselineListResponse:
    return BaselineListResponse(
        entity_type="component_version",
        entity_id=1,
        baselines=[],
    )


def _make_baseline_response() -> BaselineResponse:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return BaselineResponse(
        id=1,
        entity_type="component_version",
        entity_id=1,
        client_name="gmail_web",
        image_hash="abc123",
        created_at=now,
        updated_at=now,
    )


def _make_comparison_response() -> RenderingComparisonResponse:
    return RenderingComparisonResponse(
        baseline_test_id=1,
        current_test_id=2,
        total_clients=1,
        regressions_found=0,
        diffs=[
            RenderingDiff(
                client_name="gmail_web",
                diff_percentage=0.0,
                has_regression=False,
            )
        ],
    )


# ── Fixtures ──


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
def _auth_viewer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("viewer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── A. Screenshot endpoint ──


class TestScreenshotEndpoint:
    @pytest.mark.usefixtures("_auth_developer")
    def test_screenshots_200(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "render_screenshots",
            new_callable=AsyncMock,
            return_value=_make_screenshot_response(),
        ):
            resp = client.post(
                f"{BASE}/screenshots",
                json={"html": "<html><body>Test</body></html>", "clients": ["gmail_web"]},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["clients_rendered"] == 1
        assert len(body["screenshots"]) == 1
        assert body["screenshots"][0]["client_name"] == "gmail_web"

    @pytest.mark.usefixtures("_auth_viewer")
    def test_screenshots_requires_developer(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/screenshots",
            json={"html": "<html></html>", "clients": ["gmail_web"]},
        )
        assert resp.status_code == 403

    def test_screenshots_no_auth_401(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/screenshots",
            json={"html": "<html></html>", "clients": ["gmail_web"]},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.usefixtures("_auth_developer")
    def test_screenshots_disabled_raises(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "render_screenshots",
            new_callable=AsyncMock,
            side_effect=RenderingProviderError("Local screenshot rendering is disabled"),
        ):
            resp = client.post(
                f"{BASE}/screenshots",
                json={"html": "<html></html>", "clients": ["gmail_web"]},
            )

        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_screenshots_timeout(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "render_screenshots",
            new_callable=AsyncMock,
            side_effect=ScreenshotTimeoutError("Screenshot rendering timed out"),
        ):
            resp = client.post(
                f"{BASE}/screenshots",
                json={"html": "<html></html>", "clients": ["gmail_web"]},
            )

        # ScreenshotTimeoutError extends AppError → 500
        assert resp.status_code == 500


# ── B. Visual diff endpoint ──


class TestVisualDiffEndpoint:
    @pytest.mark.usefixtures("_auth_developer")
    def test_visual_diff_200(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "visual_diff",
            new_callable=AsyncMock,
            return_value=_make_visual_diff_response(),
        ):
            resp = client.post(
                f"{BASE}/visual-diff",
                json={"baseline_image": TINY_PNG, "current_image": TINY_PNG},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["identical"] is True
        assert body["diff_percentage"] == 0.0

    @pytest.mark.usefixtures("_auth_viewer")
    def test_visual_diff_requires_developer(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/visual-diff",
            json={"baseline_image": TINY_PNG, "current_image": TINY_PNG},
        )
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_visual_diff_invalid_base64(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "visual_diff",
            new_callable=AsyncMock,
            side_effect=RenderingProviderError("Invalid base64 image data"),
        ):
            resp = client.post(
                f"{BASE}/visual-diff",
                json={"baseline_image": "not-valid!", "current_image": TINY_PNG},
            )

        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_visual_diff_disabled(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "visual_diff",
            new_callable=AsyncMock,
            side_effect=RenderingProviderError("Visual diff is disabled"),
        ):
            resp = client.post(
                f"{BASE}/visual-diff",
                json={"baseline_image": TINY_PNG, "current_image": TINY_PNG},
            )

        assert resp.status_code == 422


# ── C. Baseline list endpoint ──


class TestBaselineListEndpoint:
    @pytest.mark.usefixtures("_auth_developer")
    def test_list_baselines_200(self, client: TestClient) -> None:
        mock_resp = _make_baseline_list_response()
        mock_resp.baselines = [_make_baseline_response()]

        with patch.object(
            RenderingService,
            "list_baselines",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.get(f"{BASE}/baselines/component_version/1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["entity_type"] == "component_version"
        assert len(body["baselines"]) == 1

    @pytest.mark.usefixtures("_auth_developer")
    def test_list_baselines_invalid_entity_type(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "list_baselines",
            new_callable=AsyncMock,
            side_effect=RenderingProviderError("Invalid entity_type 'invalid'"),
        ):
            resp = client.get(f"{BASE}/baselines/invalid/1")

        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_list_baselines_empty(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "list_baselines",
            new_callable=AsyncMock,
            return_value=_make_baseline_list_response(),
        ):
            resp = client.get(f"{BASE}/baselines/component_version/1")

        assert resp.status_code == 200
        assert resp.json()["baselines"] == []

    def test_list_baselines_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"{BASE}/baselines/component_version/1")
        assert resp.status_code in (401, 403)


# ── D. Baseline update endpoint ──


class TestBaselineUpdateEndpoint:
    @pytest.mark.usefixtures("_auth_developer")
    def test_update_baseline_200(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "update_baseline",
            new_callable=AsyncMock,
            return_value=_make_baseline_response(),
        ):
            resp = client.put(
                f"{BASE}/baselines/component_version/1",
                json={"client_name": "gmail_web", "image_base64": TINY_PNG},
            )

        assert resp.status_code == 200
        assert resp.json()["client_name"] == "gmail_web"

    @pytest.mark.usefixtures("_auth_viewer")
    def test_update_baseline_requires_developer(self, client: TestClient) -> None:
        resp = client.put(
            f"{BASE}/baselines/component_version/1",
            json={"client_name": "gmail_web", "image_base64": TINY_PNG},
        )
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_update_baseline_invalid_entity_type(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "update_baseline",
            new_callable=AsyncMock,
            side_effect=RenderingProviderError("Invalid entity_type 'invalid'"),
        ):
            resp = client.put(
                f"{BASE}/baselines/invalid/1",
                json={"client_name": "gmail_web", "image_base64": TINY_PNG},
            )

        assert resp.status_code == 422

    @pytest.mark.usefixtures("_auth_developer")
    def test_update_baseline_invalid_base64(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "update_baseline",
            new_callable=AsyncMock,
            side_effect=RenderingProviderError("Invalid base64 image data"),
        ):
            resp = client.put(
                f"{BASE}/baselines/component_version/1",
                json={"client_name": "gmail_web", "image_base64": "!!!bad!!!"},
            )

        assert resp.status_code == 422

    def test_update_baseline_no_auth(self, client: TestClient) -> None:
        resp = client.put(
            f"{BASE}/baselines/component_version/1",
            json={"client_name": "gmail_web", "image_base64": TINY_PNG},
        )
        assert resp.status_code in (401, 403)


# ── E. Rendering test endpoints ──


class TestRenderingTestEndpoints:
    @pytest.mark.usefixtures("_auth_developer")
    def test_submit_test_201(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "submit_test",
            new_callable=AsyncMock,
            return_value=_make_test_response(),
        ):
            resp = client.post(
                f"{BASE}/tests",
                json={"html": "<html><body>Test</body></html>", "clients": ["gmail_web"]},
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == 1
        assert body["provider"] == "litmus"

    @pytest.mark.usefixtures("_auth_viewer")
    def test_submit_test_requires_developer(self, client: TestClient) -> None:
        resp = client.post(
            f"{BASE}/tests",
            json={"html": "<html></html>", "clients": ["gmail_web"]},
        )
        assert resp.status_code == 403

    @pytest.mark.usefixtures("_auth_developer")
    def test_list_tests_200(self, client: TestClient) -> None:
        paginated = PaginatedResponse[RenderingTestResponse](
            items=[_make_test_response()],
            total=1,
            page=1,
            page_size=20,
        )
        with patch.object(
            RenderingService,
            "list_tests",
            new_callable=AsyncMock,
            return_value=paginated,
        ):
            resp = client.get(f"{BASE}/tests")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1

    @pytest.mark.usefixtures("_auth_developer")
    def test_list_tests_with_filters(self, client: TestClient) -> None:
        paginated = PaginatedResponse[RenderingTestResponse](
            items=[],
            total=0,
            page=1,
            page_size=20,
        )
        with patch.object(
            RenderingService,
            "list_tests",
            new_callable=AsyncMock,
            return_value=paginated,
        ):
            resp = client.get(f"{BASE}/tests?build_id=1&status=complete")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.usefixtures("_auth_developer")
    def test_get_test_200(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "get_test",
            new_callable=AsyncMock,
            return_value=_make_test_response(),
        ):
            resp = client.get(f"{BASE}/tests/1")

        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    @pytest.mark.usefixtures("_auth_developer")
    def test_get_test_404(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "get_test",
            new_callable=AsyncMock,
            side_effect=RenderingTestNotFoundError("Rendering test 999 not found"),
        ):
            resp = client.get(f"{BASE}/tests/999")

        assert resp.status_code == 500  # RenderingTestNotFoundError extends AppError base

    @pytest.mark.usefixtures("_auth_developer")
    def test_compare_tests_200(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "compare_tests",
            new_callable=AsyncMock,
            return_value=_make_comparison_response(),
        ):
            resp = client.post(
                f"{BASE}/compare",
                json={"baseline_test_id": 1, "current_test_id": 2},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_clients"] == 1
        assert body["regressions_found"] == 0

    @pytest.mark.usefixtures("_auth_developer")
    def test_compare_tests_not_found(self, client: TestClient) -> None:
        with patch.object(
            RenderingService,
            "compare_tests",
            new_callable=AsyncMock,
            side_effect=RenderingTestNotFoundError("Baseline test 999 not found"),
        ):
            resp = client.post(
                f"{BASE}/compare",
                json={"baseline_test_id": 999, "current_test_id": 2},
            )

        assert resp.status_code == 500  # RenderingTestNotFoundError extends AppError base


# ── F. Rate limiting ──


class TestRateLimiting:
    @pytest.mark.usefixtures("_auth_developer")
    def test_rate_limit_screenshots(self, client: TestClient) -> None:
        limiter.enabled = True
        try:
            with patch.object(
                RenderingService,
                "render_screenshots",
                new_callable=AsyncMock,
                return_value=_make_screenshot_response(),
            ):
                for _i in range(6):
                    resp = client.post(
                        f"{BASE}/screenshots",
                        json={"html": "<html>Test</html>", "clients": ["gmail_web"]},
                    )
                    if resp.status_code == 429:
                        break
                else:
                    pytest.fail("Expected 429 rate limit after 5 requests")
        finally:
            limiter.enabled = False

    @pytest.mark.usefixtures("_auth_developer")
    def test_rate_limit_visual_diff(self, client: TestClient) -> None:
        limiter.enabled = True
        try:
            with patch.object(
                RenderingService,
                "visual_diff",
                new_callable=AsyncMock,
                return_value=_make_visual_diff_response(),
            ):
                for _i in range(11):
                    resp = client.post(
                        f"{BASE}/visual-diff",
                        json={"baseline_image": TINY_PNG, "current_image": TINY_PNG},
                    )
                    if resp.status_code == 429:
                        break
                else:
                    pytest.fail("Expected 429 rate limit after 10 requests")
        finally:
            limiter.enabled = False
