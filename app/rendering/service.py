"""Business logic for rendering tests."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.resilience import CircuitBreaker
from app.rendering.eoa.service import EoARenderingService
from app.rendering.exceptions import (
    RenderingProviderError,
    RenderingSubmitError,
    RenderingTestNotFoundError,
)
from app.rendering.litmus.service import LitmusRenderingService
from app.rendering.models import RenderingTest
from app.rendering.protocol import RenderingProvider
from app.rendering.repository import RenderingRepository
from app.rendering.schemas import (
    RenderingComparisonRequest,
    RenderingComparisonResponse,
    RenderingDiff,
    RenderingTestRequest,
    RenderingTestResponse,
    ScreenshotResult,
)
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)
settings = get_settings()

SUPPORTED_PROVIDERS: dict[str, type[RenderingProvider]] = {
    "litmus": LitmusRenderingService,
    "eoa": EoARenderingService,
}

_breaker = CircuitBreaker(name="rendering-api", failure_threshold=3, reset_timeout=60.0)


class RenderingService:
    """Orchestrates cross-client rendering tests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = RenderingRepository(db)
        self._providers: dict[str, RenderingProvider] = {}

    def _get_provider(self, provider_name: str | None = None) -> RenderingProvider:
        """Get or create a rendering provider instance."""
        name = provider_name or settings.rendering.provider
        if name not in self._providers:
            provider_cls = SUPPORTED_PROVIDERS.get(name)
            if provider_cls is None:
                raise RenderingProviderError(
                    f"Provider '{name}' not supported. "
                    f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
                )
            self._providers[name] = provider_cls()
        return self._providers[name]

    async def submit_test(self, data: RenderingTestRequest, user_id: int) -> RenderingTestResponse:
        """Submit HTML for cross-client rendering."""
        provider = self._get_provider()

        logger.info(
            "rendering.submit_started",
            client_count=len(data.clients),
            build_id=data.build_id,
        )

        try:
            async with _breaker:
                external_id = await provider.submit_test(data.html, data.subject, data.clients)
        except RenderingSubmitError:
            raise
        except Exception as exc:
            raise RenderingSubmitError(f"Failed to submit rendering test: {exc}") from exc

        test = await self.repository.create_test(
            external_test_id=external_id,
            provider=settings.rendering.provider,
            build_id=data.build_id,
            template_version_id=data.template_version_id,
            clients_requested=len(data.clients),
            submitted_by_id=user_id,
            client_names=data.clients,
        )

        logger.info("rendering.submit_completed", test_id=test.id, external_id=external_id)
        return self._to_response(test)

    async def get_test(self, test_id: int) -> RenderingTestResponse:
        """Get a rendering test by ID."""
        test = await self.repository.get_test(test_id)
        if not test:
            raise RenderingTestNotFoundError(f"Rendering test {test_id} not found")
        return self._to_response(test)

    async def list_tests(
        self,
        pagination: PaginationParams,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[RenderingTestResponse]:
        """List rendering tests with optional filters."""
        items = await self.repository.list_tests(
            build_id=build_id,
            template_version_id=template_version_id,
            status=status,
            offset=pagination.offset,
            limit=pagination.page_size,
        )
        total = await self.repository.count_tests(
            build_id=build_id,
            template_version_id=template_version_id,
            status=status,
        )
        return PaginatedResponse[RenderingTestResponse](
            items=[self._to_response(t) for t in items],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def compare_tests(self, data: RenderingComparisonRequest) -> RenderingComparisonResponse:
        """Compare screenshots between two rendering tests for visual regression."""
        baseline = await self.repository.get_test(data.baseline_test_id)
        current = await self.repository.get_test(data.current_test_id)

        if not baseline:
            raise RenderingTestNotFoundError(f"Baseline test {data.baseline_test_id} not found")
        if not current:
            raise RenderingTestNotFoundError(f"Current test {data.current_test_id} not found")

        baseline_map = {s.client_name: s for s in baseline.screenshots}
        current_map = {s.client_name: s for s in current.screenshots}
        common_clients = set(baseline_map) & set(current_map)

        diffs: list[RenderingDiff] = []
        regressions = 0
        for client in sorted(common_clients):
            b_url = baseline_map[client].screenshot_url
            c_url = current_map[client].screenshot_url
            # Placeholder: real implementation would download images and compute pixel diff
            diff_pct = 0.0 if b_url == c_url else 5.0  # mock diff
            has_regression = diff_pct > 2.0  # 2% threshold
            if has_regression:
                regressions += 1
            diffs.append(
                RenderingDiff(
                    client_name=client,
                    diff_percentage=diff_pct,
                    has_regression=has_regression,
                    baseline_url=b_url,
                    current_url=c_url,
                )
            )

        return RenderingComparisonResponse(
            baseline_test_id=data.baseline_test_id,
            current_test_id=data.current_test_id,
            total_clients=len(common_clients),
            regressions_found=regressions,
            diffs=diffs,
        )

    def _to_response(self, test: RenderingTest) -> RenderingTestResponse:
        """Transform a RenderingTest model to response schema."""
        return RenderingTestResponse(
            id=test.id,
            external_test_id=test.external_test_id,
            provider=test.provider,
            status=test.status,
            build_id=test.build_id,
            template_version_id=test.template_version_id,
            clients_requested=test.clients_requested,
            clients_completed=test.clients_completed,
            screenshots=[
                ScreenshotResult(
                    client_name=s.client_name,
                    screenshot_url=s.screenshot_url,
                    os=s.os,
                    category=s.category,
                    status=s.status,
                )
                for s in test.screenshots
            ],
            created_at=test.created_at,  # pyright: ignore[reportArgumentType]
        )
