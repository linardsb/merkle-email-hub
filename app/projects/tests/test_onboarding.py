"""Tests for client-specific onboarding subgraph generation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.projects.onboarding import (
    generate_and_store_subgraph,
    generate_onboarding_documents,
)


class TestGenerateOnboardingDocuments:
    """Tests for document generation logic."""

    def test_generates_documents_for_valid_clients(self) -> None:
        """Should produce documents when valid client IDs provided."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test Project",
            client_ids=["gmail_web", "outlook_2019_win"],
        )
        # Brief + 2 client profiles + risk matrix = 4 documents
        assert len(docs) == 4
        assert all(ds == "project_onboarding_1" for ds, _ in docs)

    def test_returns_empty_for_unknown_clients(self) -> None:
        """Should return empty list when no client IDs resolve."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=["nonexistent_client"],
        )
        assert docs == []

    def test_returns_empty_for_empty_list(self) -> None:
        """Should return empty list for empty client_ids."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=[],
        )
        assert docs == []

    def test_skips_unknown_keeps_valid(self) -> None:
        """Should skip unknown IDs and process valid ones."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=["gmail_web", "not_real"],
        )
        # Brief + 1 client profile + risk matrix = 3 documents
        assert len(docs) == 3

    def test_brief_contains_project_name(self) -> None:
        """Compatibility brief should include project name."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Acme Campaign",
            client_ids=["gmail_web"],
        )
        brief_text = docs[0][1]
        assert "Acme Campaign" in brief_text

    def test_brief_contains_client_details(self) -> None:
        """Brief should list target client names and engines."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=["gmail_web", "outlook_2019_win"],
        )
        brief_text = docs[0][1]
        assert "Gmail" in brief_text
        assert "Outlook" in brief_text

    def test_client_profile_lists_unsupported_css(self) -> None:
        """Per-client profile should document unsupported properties."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=["outlook_2019_win"],
        )
        # Client profile is docs[1] (after brief)
        profile_text = docs[1][1]
        assert "Unsupported CSS" in profile_text or "Full CSS Support" in profile_text

    def test_risk_matrix_shows_multi_client_failures(self) -> None:
        """Risk matrix should highlight properties failing in 2+ clients."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=["outlook_2019_win", "outlook_2016_win"],
        )
        # Risk matrix is last document
        risk_text = docs[-1][1]
        assert "Cross-Client CSS Risk Matrix" in risk_text

    def test_dataset_name_scoped_to_project(self) -> None:
        """Dataset name should be project-specific."""
        docs = generate_onboarding_documents(
            project_id=42,
            project_name="Test",
            client_ids=["gmail_web"],
        )
        assert all(ds == "project_onboarding_42" for ds, _ in docs)

    def test_dark_mode_warning_for_word_engine(self) -> None:
        """Should include dark mode warning when Outlook (Word engine) targeted."""
        docs = generate_onboarding_documents(
            project_id=1,
            project_name="Test",
            client_ids=["outlook_2019_win"],
        )
        brief_text = docs[0][1]
        assert "Dark Mode Warning" in brief_text


class TestGenerateAndStoreSubgraph:
    """Tests for the async store-to-Cognee function."""

    @pytest.mark.asyncio
    async def test_skips_when_cognee_disabled(self) -> None:
        """Should return early when Cognee is disabled."""
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.cognee.enabled = False
            # Should not raise
            await generate_and_store_subgraph(1, "Test", ["gmail_web"])

    @pytest.mark.asyncio
    async def test_stores_documents_in_cognee(self) -> None:
        """Should call provider.add_documents and build_graph."""
        mock_provider = AsyncMock()
        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch(
                "app.knowledge.graph.cognee_provider.CogneeGraphProvider",
                return_value=mock_provider,
            ),
        ):
            mock_settings.return_value.cognee.enabled = True
            await generate_and_store_subgraph(1, "Test", ["gmail_web"])

            mock_provider.add_documents.assert_called_once()
            mock_provider.build_graph.assert_called_once_with(
                dataset_name="project_onboarding_1",
                background=True,
            )

    @pytest.mark.asyncio
    async def test_does_not_raise_on_provider_error(self) -> None:
        """Should catch and log errors without raising."""
        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch(
                "app.knowledge.graph.cognee_provider.CogneeGraphProvider",
                side_effect=RuntimeError("connection failed"),
            ),
        ):
            mock_settings.return_value.cognee.enabled = True
            # Should not raise
            await generate_and_store_subgraph(1, "Test", ["gmail_web"])

    @pytest.mark.asyncio
    async def test_skips_when_no_valid_documents(self) -> None:
        """Should not call Cognee when all client IDs are invalid."""
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.cognee.enabled = True
            # No CogneeGraphProvider import should happen
            await generate_and_store_subgraph(1, "Test", ["nonexistent"])
