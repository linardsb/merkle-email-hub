"""Business logic for rendering tests."""

from __future__ import annotations

import base64
import binascii
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.resilience import CircuitBreaker
from app.email_engine.models import EmailBuild
from app.projects.service import ProjectService
from app.rendering.calibration.calibrator import EmulatorCalibrator
from app.rendering.calibration.repository import CalibrationRepository
from app.rendering.calibration.schemas import (
    CalibrationHistoryResponse,
    CalibrationRecordResponse,
    CalibrationSummaryListResponse,
    CalibrationSummaryResponse,
    CalibrationTriggerRequest,
    CalibrationTriggerResponse,
)
from app.rendering.eoa.service import EoARenderingService
from app.rendering.exceptions import (
    CalibrationError,
    ClientNotFoundError,
    RenderingProviderError,
    RenderingSubmitError,
    RenderingTestNotFoundError,
)
from app.rendering.gate import RenderingSendGate
from app.rendering.gate_schemas import (
    GateConfigUpdateRequest,
    GateEvaluateRequest,
    GateResult,
    RenderingGateConfigSchema,
)
from app.rendering.litmus.service import LitmusRenderingService
from app.rendering.local.service import LocalRenderingProvider
from app.rendering.models import RenderingTest
from app.rendering.protocol import RenderingProvider
from app.rendering.repository import RenderingRepository, ScreenshotBaselineRepository
from app.rendering.schemas import (
    VALID_ENTITY_TYPES,
    BaselineListResponse,
    BaselineResponse,
    BaselineUpdateRequest,
    ClientConfidenceResponse,
    Region,
    RenderingComparisonRequest,
    RenderingComparisonResponse,
    RenderingDiff,
    RenderingTestRequest,
    RenderingTestResponse,
    ScreenshotClientResult,
    ScreenshotRequest,
    ScreenshotResponse,
    ScreenshotResult,
    VisualDiffRequest,
    VisualDiffResponse,
)
from app.rendering.visual_diff import compare_images
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)
settings = get_settings()

SUPPORTED_PROVIDERS: dict[str, type[RenderingProvider]] = {
    "litmus": LitmusRenderingService,
    "eoa": EoARenderingService,
    "local": LocalRenderingProvider,
}

_breaker = CircuitBreaker(name="rendering-api", failure_threshold=3, reset_timeout=60.0)


class RenderingService:
    """Orchestrates cross-client rendering tests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = RenderingRepository(db)
        self.baseline_repo = ScreenshotBaselineRepository(db)
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

    async def _resolve_test_project_id(self, test: RenderingTest) -> int | None:
        """Resolve project_id from a rendering test via build link."""
        if test.build_id:
            result = await self.db.execute(
                select(EmailBuild.project_id).where(EmailBuild.id == test.build_id)
            )
            project_id = result.scalar_one_or_none()
            if project_id:
                return int(project_id)
        return None

    async def compare_tests(
        self, data: RenderingComparisonRequest, user: User
    ) -> RenderingComparisonResponse:
        """Compare screenshots between two rendering tests for visual regression."""
        baseline = await self.repository.get_test(data.baseline_test_id)
        current = await self.repository.get_test(data.current_test_id)

        if not baseline:
            raise RenderingTestNotFoundError(f"Baseline test {data.baseline_test_id} not found")
        if not current:
            raise RenderingTestNotFoundError(f"Current test {data.current_test_id} not found")

        # BOLA: verify user has access to both tests' projects
        project_service = ProjectService(self.db)
        for render_test in [baseline, current]:
            project_id = await self._resolve_test_project_id(render_test)
            if project_id:
                await project_service.verify_project_access(project_id, user)

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

    async def render_screenshots(self, data: ScreenshotRequest) -> ScreenshotResponse:
        """Render email HTML locally across simulated email clients."""
        if not settings.rendering.screenshots_enabled:
            raise RenderingProviderError("Local screenshot rendering is disabled")

        provider = LocalRenderingProvider()
        raw_results = await provider.render_screenshots(data.html, data.clients)

        screenshots = [
            ScreenshotClientResult(
                client_name=str(r["client_name"]),
                image_base64=base64.b64encode(r["image_bytes"]).decode("ascii"),
                viewport=str(r["viewport"]),
                browser=str(r["browser"]),
                confidence_score=r.get("confidence_score"),
                confidence_breakdown=r.get("confidence_breakdown"),
                confidence_recommendations=r.get("confidence_recommendations"),
            )
            for r in raw_results
        ]

        return ScreenshotResponse(
            screenshots=screenshots,
            clients_rendered=len(screenshots),
            clients_failed=len(data.clients) - len(screenshots),
        )

    async def get_client_confidence(self, client_id: str) -> ClientConfidenceResponse:
        """Get current confidence calibration data for an email client."""
        from app.rendering.local.confidence import RenderingConfidenceScorer
        from app.rendering.local.emulators import _EMULATORS
        from app.rendering.local.profiles import CLIENT_PROFILES

        emulator = _EMULATORS.get(client_id)
        profiles = [name for name, p in CLIENT_PROFILES.items() if p.emulator_id == client_id]

        if not emulator and not profiles:
            raise ClientNotFoundError(f"Unknown rendering client: {client_id}")

        scorer = RenderingConfidenceScorer()
        seed = await scorer.get_seed_with_db(client_id, self.db)
        rule_count = len(emulator.rules) if emulator else 0

        return ClientConfidenceResponse(
            client_id=client_id,
            accuracy=seed.get("accuracy", 0.5),
            sample_count=seed.get("sample_count", 0),
            last_calibrated=seed.get("last_calibrated", ""),
            known_blind_spots=seed.get("known_blind_spots", []),
            emulator_rule_count=rule_count,
            profiles=profiles,
        )

    async def get_calibration_summary(self) -> CalibrationSummaryListResponse:
        """List calibration state for all clients."""
        repo = CalibrationRepository(self.db)
        summaries = await repo.list_summaries()
        return CalibrationSummaryListResponse(
            summaries=[
                CalibrationSummaryResponse(
                    client_id=s.client_id,
                    current_accuracy=s.current_accuracy,
                    sample_count=s.sample_count,
                    accuracy_trend=list(s.accuracy_trend or []),
                    known_blind_spots=list(s.known_blind_spots or []),
                    last_provider=s.last_provider,
                    last_calibrated=s.updated_at,  # pyright: ignore[reportArgumentType]
                )
                for s in summaries
            ]
        )

    async def get_calibration_history(
        self, client_id: str, *, limit: int = 20
    ) -> CalibrationHistoryResponse:
        """Get calibration record history for a client."""
        repo = CalibrationRepository(self.db)
        records = await repo.list_records(client_id, limit=limit)
        total = await repo.count_records(client_id)
        return CalibrationHistoryResponse(
            client_id=client_id,
            records=[
                CalibrationRecordResponse(
                    id=r.id,
                    client_id=r.client_id,
                    html_hash=r.html_hash,
                    diff_percentage=r.diff_percentage,
                    accuracy_score=r.accuracy_score,
                    pixel_count=r.pixel_count,
                    external_provider=r.external_provider,
                    emulator_version=r.emulator_version,
                    created_at=r.created_at,  # pyright: ignore[reportArgumentType]
                )
                for r in records
            ],
            total=total,
        )

    async def trigger_calibration(
        self, data: CalibrationTriggerRequest
    ) -> CalibrationTriggerResponse:
        """Trigger a calibration run: render locally + capture externally + compare."""
        logger.info(
            "calibration.trigger_started",
            client_ids=data.client_ids,
            provider=data.external_provider,
        )

        try:
            provider = LocalRenderingProvider()
            raw_results = await provider.render_screenshots(data.html, data.client_ids)
        except Exception as exc:
            raise CalibrationError(f"Local screenshot rendering failed: {exc}") from exc

        local_map: dict[str, bytes] = {str(r["client_name"]): r["image_bytes"] for r in raw_results}

        external_map: dict[str, bytes] = {}
        if data.external_provider == "sandbox":
            try:
                from app.rendering.sandbox.sandbox import send_and_capture

                _, captures = await send_and_capture(
                    html=data.html,
                    subject="Calibration test",
                    profile_names=data.client_ids,
                )
                for profile_name, _html, screenshot, _diff in captures:
                    if screenshot:
                        external_map[profile_name] = screenshot
            except CalibrationError:
                raise
            except Exception as exc:
                raise CalibrationError(f"Sandbox capture failed: {exc}") from exc
        else:
            logger.info(
                "calibration.external_provider_not_implemented",
                provider=data.external_provider,
            )

        calibrator = EmulatorCalibrator(self.db)
        results = await calibrator.calibrate_batch(
            html=data.html,
            local_screenshots=local_map,
            external_screenshots=external_map,
            external_provider=data.external_provider,
        )
        await calibrator.update_seeds(results, external_provider=data.external_provider)

        logger.info(
            "calibration.trigger_completed",
            records_created=len(results),
            client_ids=data.client_ids,
        )

        return CalibrationTriggerResponse(
            results=results,
            records_created=len(results),
        )

    async def visual_diff(self, data: VisualDiffRequest) -> VisualDiffResponse:
        """Compare two base64 images using ODiff."""
        if not settings.rendering.visual_diff_enabled:
            raise RenderingProviderError("Visual diff is disabled")

        try:
            baseline_bytes = base64.b64decode(data.baseline_image)
            current_bytes = base64.b64decode(data.current_image)
        except binascii.Error as exc:
            raise RenderingProviderError(f"Invalid base64 image data: {exc}") from exc

        result = await compare_images(baseline_bytes, current_bytes, threshold=data.threshold)

        diff_b64 = (
            base64.b64encode(result.diff_image).decode("ascii") if result.diff_image else None
        )
        threshold_used = (
            data.threshold
            if data.threshold is not None
            else settings.rendering.visual_diff_threshold
        )

        return VisualDiffResponse(
            identical=result.identical,
            diff_percentage=result.diff_percentage,
            diff_image=diff_b64,
            pixel_count=result.pixel_count,
            changed_regions=[
                Region(x=r[0], y=r[1], width=r[2], height=r[3]) for r in result.changed_regions
            ],
            threshold_used=threshold_used,
        )

    async def list_baselines(self, entity_type: str, entity_id: int) -> BaselineListResponse:
        """List all baselines for a given entity."""
        if entity_type not in VALID_ENTITY_TYPES:
            raise RenderingProviderError(
                f"Invalid entity_type '{entity_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"
            )
        baselines = await self.baseline_repo.list_by_entity(entity_type, entity_id)
        return BaselineListResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            baselines=[
                BaselineResponse(
                    id=b.id,
                    entity_type=b.entity_type,
                    entity_id=b.entity_id,
                    client_name=b.client_name,
                    image_hash=b.image_hash,
                    created_at=b.created_at,  # pyright: ignore[reportArgumentType]
                    updated_at=b.updated_at,  # pyright: ignore[reportArgumentType]
                )
                for b in baselines
            ],
        )

    async def update_baseline(
        self,
        entity_type: str,
        entity_id: int,
        data: BaselineUpdateRequest,
        user_id: int,
    ) -> BaselineResponse:
        """Create or update a baseline screenshot for an entity + client."""
        if entity_type not in VALID_ENTITY_TYPES:
            raise RenderingProviderError(
                f"Invalid entity_type '{entity_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"
            )

        try:
            image_bytes = base64.b64decode(data.image_base64)
        except binascii.Error as exc:
            raise RenderingProviderError(f"Invalid base64 image data: {exc}") from exc
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        baseline = await self.baseline_repo.upsert(
            entity_type=entity_type,
            entity_id=entity_id,
            client_name=data.client_name,
            image_data=image_bytes,
            image_hash=image_hash,
            created_by_id=user_id,
        )

        logger.info(
            "baseline.updated",
            entity_type=entity_type,
            entity_id=entity_id,
            client_name=data.client_name,
            image_hash=image_hash,
        )

        return BaselineResponse(
            id=baseline.id,
            entity_type=baseline.entity_type,
            entity_id=baseline.entity_id,
            client_name=baseline.client_name,
            image_hash=baseline.image_hash,
            created_at=baseline.created_at,  # pyright: ignore[reportArgumentType]
            updated_at=baseline.updated_at,  # pyright: ignore[reportArgumentType]
        )

    async def evaluate_gate(self, request: GateEvaluateRequest) -> GateResult:
        """Evaluate rendering gate for given HTML."""
        gate = RenderingSendGate(self.db)
        return await gate.evaluate(request)

    async def get_gate_config(self, project_id: int) -> RenderingGateConfigSchema:
        """Get project-level gate configuration."""
        gate = RenderingSendGate(self.db)
        return await gate.resolve_config(project_id)

    async def update_gate_config(
        self,
        project_id: int,
        update: GateConfigUpdateRequest,
    ) -> RenderingGateConfigSchema:
        """Update project-level gate configuration (partial merge)."""
        from app.projects.models import Project

        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError(f"Project {project_id} not found")

        # Resolve current config from the already-loaded project (no second query)
        gate = RenderingSendGate(self.db)
        current = await gate.resolve_config(None)  # global defaults
        if project.rendering_gate_config:
            try:
                current = RenderingGateConfigSchema.model_validate(project.rendering_gate_config)
            except Exception:
                logger.warning("gate.invalid_project_config", project_id=project_id)

        # Merge update into current config
        merged = current.model_dump()
        update_data = update.model_dump(exclude_none=True)
        merged.update(update_data)

        # Validate merged config
        validated = RenderingGateConfigSchema.model_validate(merged)
        project.rendering_gate_config = validated.model_dump()
        await self.db.commit()
        return validated

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
