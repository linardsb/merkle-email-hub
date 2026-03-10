"""Tests for ontology graph export to Cognee documents."""

from app.knowledge.ontology.graph_export import export_ontology_documents
from app.knowledge.ontology.registry import load_ontology


class TestExportOntologyDocuments:
    """Verify Cognee document generation from ontology."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()

    def test_returns_non_empty(self) -> None:
        docs = export_ontology_documents()
        assert len(docs) > 0

    def test_document_format(self) -> None:
        docs = export_ontology_documents()
        valid_datasets = {"email_ontology", "competitive_intelligence"}
        for dataset_name, text in docs:
            assert dataset_name in valid_datasets
            assert isinstance(text, str)
            assert len(text) > 0

    def test_client_profiles_present(self) -> None:
        docs = export_ontology_documents()
        all_text = "\n".join(text for _, text in docs)
        assert "Outlook" in all_text
        assert "Gmail" in all_text
        assert "Apple" in all_text

    def test_category_matrices_present(self) -> None:
        docs = export_ontology_documents()
        all_text = "\n".join(text for _, text in docs)
        assert "Support Matrix" in all_text
        assert "| Client | Support | Notes |" in all_text

    def test_fallback_document_present(self) -> None:
        docs = export_ontology_documents()
        all_text = "\n".join(text for _, text in docs)
        assert "Fallback Relationships" in all_text
        assert "Technique" in all_text
