"""Tests for component extraction from design connections."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.component_extractor import (
    ComponentExtractor,
    build_component_brief,
    detect_category,
    slugify,
)
from app.design_sync.protocol import DesignComponent, ExportedImage


class TestDetectCategory:
    def test_button_maps_to_cta(self) -> None:
        assert detect_category("Primary Button") == "cta"
        assert detect_category("cta-block") == "cta"

    def test_header_maps_to_header(self) -> None:
        assert detect_category("Email Header") == "header"
        assert detect_category("Navigation Bar") == "header"

    def test_footer_maps_to_footer(self) -> None:
        assert detect_category("Footer Section") == "footer"

    def test_hero_maps_to_hero(self) -> None:
        assert detect_category("Hero Banner") == "hero"

    def test_card_maps_to_content(self) -> None:
        assert detect_category("Product Card") == "content"
        assert detect_category("Feature Tile") == "content"

    def test_unknown_maps_to_general(self) -> None:
        assert detect_category("Divider") == "general"
        assert detect_category("Spacer") == "general"


class TestSlugify:
    def test_basic_slugify(self) -> None:
        assert slugify("Primary Button") == "primary-button"

    def test_special_chars_removed(self) -> None:
        assert slugify("CTA (v2)") == "cta-v2"

    def test_truncates_at_100(self) -> None:
        assert len(slugify("a" * 200)) <= 100


class TestBuildComponentBrief:
    def test_includes_name_and_category(self) -> None:
        comp = DesignComponent(component_id="1", name="Hero Banner", description="")
        brief = build_component_brief(comp, "hero")
        assert "Hero Banner" in brief
        assert "hero" in brief

    def test_includes_description_when_present(self) -> None:
        comp = DesignComponent(component_id="1", name="CTA", description="Call to action button")
        brief = build_component_brief(comp, "cta")
        assert "Call to action button" in brief


class TestComponentExtractor:
    """Integration-style tests with mocked dependencies."""

    @pytest.fixture
    def mock_provider(self) -> AsyncMock:
        provider = AsyncMock()
        provider.list_components.return_value = [
            DesignComponent(
                component_id="comp-1",
                name="Hero Banner",
                description="Main hero section",
            ),
            DesignComponent(
                component_id="comp-2",
                name="CTA Button",
                description="Primary action button",
            ),
        ]
        provider.export_images.return_value = [
            ExportedImage(node_id="comp-1", url="https://cdn.figma.com/hero.png", format="png"),
            ExportedImage(node_id="comp-2", url="https://cdn.figma.com/cta.png", format="png"),
        ]
        return provider

    @pytest.fixture
    def mock_design_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.update_import_status = AsyncMock()
        repo.create_import_asset = AsyncMock()
        mock_import = MagicMock()
        mock_import.id = 42
        repo.get_import = AsyncMock(return_value=mock_import)
        return repo

    @pytest.fixture
    def mock_component_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.get_by_slug = AsyncMock(return_value=None)
        mock_component = MagicMock()
        mock_component.id = 1
        mock_component.versions = [MagicMock(version_number=1, compatibility=None)]
        repo.create = AsyncMock(return_value=mock_component)
        return repo

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        # execute() returns a sync Result — use MagicMock so scalar_one_or_none() is sync
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_extract_creates_components(
        self,
        mock_provider: AsyncMock,
        mock_design_repo: AsyncMock,
        mock_component_repo: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """Verify extraction creates components with correct categories."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        extractor = ComponentExtractor(
            provider=mock_provider,
            design_repo=mock_design_repo,
            component_repo=mock_component_repo,
            db=mock_db,
        )

        with patch.object(extractor, "_generate_html", return_value="<div>Mock</div>"):
            await extractor.extract(
                import_id=42,
                file_ref="abc123",
                access_token="token",
                user_id=1,
            )

        assert mock_component_repo.create.call_count == 2

        final_status_call = mock_design_repo.update_import_status.call_args_list[-1]
        assert final_status_call[0][1] == "completed"

    @pytest.mark.asyncio
    async def test_extract_with_component_filter(
        self,
        mock_provider: AsyncMock,
        mock_design_repo: AsyncMock,
        mock_component_repo: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """Verify component_ids filter limits extraction."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        extractor = ComponentExtractor(
            provider=mock_provider,
            design_repo=mock_design_repo,
            component_repo=mock_component_repo,
            db=mock_db,
        )

        with patch.object(extractor, "_generate_html", return_value="<div>Mock</div>"):
            await extractor.extract(
                import_id=42,
                file_ref="abc123",
                access_token="token",
                user_id=1,
                component_ids=["comp-1"],
            )

        assert mock_component_repo.create.call_count == 1

    @pytest.mark.asyncio
    async def test_extract_creates_new_version_for_existing(
        self,
        mock_provider: AsyncMock,
        mock_design_repo: AsyncMock,
        mock_component_repo: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """When a Figma component was previously extracted, create new version."""
        mock_provider.list_components.return_value = [
            DesignComponent(component_id="comp-1", name="Hero Banner"),
        ]
        mock_provider.export_images.return_value = [
            ExportedImage(node_id="comp-1", url="https://cdn.figma.com/hero.png", format="png"),
        ]

        existing = MagicMock()
        existing.id = 99
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing

        new_version = MagicMock()
        new_version.version_number = 2
        mock_component_repo.create_version = AsyncMock(return_value=new_version)

        extractor = ComponentExtractor(
            provider=mock_provider,
            design_repo=mock_design_repo,
            component_repo=mock_component_repo,
            db=mock_db,
        )

        with patch.object(extractor, "_generate_html", return_value="<div>V2</div>"):
            await extractor.extract(
                import_id=42,
                file_ref="abc123",
                access_token="token",
                user_id=1,
            )

        assert mock_component_repo.create.call_count == 0
        assert mock_component_repo.create_version.call_count == 1

    @pytest.mark.asyncio
    async def test_extract_handles_scaffolder_failure_gracefully(
        self,
        mock_provider: AsyncMock,
        mock_design_repo: AsyncMock,
        mock_component_repo: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """If Scaffolder fails for one component, others still proceed."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        extractor = ComponentExtractor(
            provider=mock_provider,
            design_repo=mock_design_repo,
            component_repo=mock_component_repo,
            db=mock_db,
        )

        call_count = 0

        async def flaky_generate(comp: object, cat: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM timeout")
            return "<div>OK</div>"

        with patch.object(extractor, "_generate_html", side_effect=flaky_generate):
            await extractor.extract(
                import_id=42,
                file_ref="abc123",
                access_token="token",
                user_id=1,
            )

        final_call = mock_design_repo.update_import_status.call_args_list[-1]
        status = final_call[0][1]
        assert status == "completed"
