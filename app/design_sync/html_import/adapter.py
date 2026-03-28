"""Main HTML import adapter — orchestrates HTML → EmailDesignDocument."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.design_sync.email_design_document import (
    DocumentLayout,
    DocumentSection,
    DocumentSource,
    DocumentTokens,
    EmailDesignDocument,
)
from app.design_sync.exceptions import HtmlImportError
from app.design_sync.html_import.dom_parser import ParsedEmail, parse_email_dom
from app.design_sync.html_import.section_classifier import (
    classify_sections,
    classify_with_ai_fallback,
)
from app.design_sync.html_import.token_extractor import extract_tokens

logger = get_logger(__name__)

_MAX_HTML_SIZE = 2 * 1024 * 1024  # 2 MB


class HtmlImportAdapter:
    """Reverse-engineer arbitrary email HTML into an ``EmailDesignDocument``."""

    async def parse(
        self,
        raw_html: str,
        *,
        use_ai: bool | None = None,
        source_name: str | None = None,
    ) -> EmailDesignDocument:
        """Parse email HTML into an ``EmailDesignDocument``.

        Raises ``HtmlImportError`` on validation/parsing failures.
        """
        # 1. Validate size
        if len(raw_html.encode("utf-8", errors="replace")) > self._max_size():
            raise HtmlImportError(f"HTML exceeds maximum size of {self._max_size()} bytes")

        if not raw_html.strip():
            raise HtmlImportError("HTML input is empty")

        # 2. DOM parse
        try:
            parsed = parse_email_dom(raw_html)
        except Exception as exc:
            raise HtmlImportError(f"Failed to parse HTML: {exc}") from exc

        if not parsed.sections:
            raise HtmlImportError("No sections detected in HTML")

        # 3. Classify sections
        ai_enabled = self._resolve_ai_enabled(use_ai)
        if ai_enabled:
            classified_sections = await classify_with_ai_fallback(parsed.sections, ai_enabled=True)
        else:
            classified_sections = classify_sections(parsed.sections)

        # 4. Extract tokens
        tokens = extract_tokens(parsed.style_blocks, classified_sections)

        # 5. Build document
        doc = self._build_document(parsed, classified_sections, tokens, source_name)

        # 6. Log completion
        ai_count = sum(1 for s in doc.sections if s.classification_confidence is not None)
        logger.info(
            "design_sync.html_import.parse_completed",
            section_count=len(doc.sections),
            color_count=len(doc.tokens.colors),
            typography_count=len(doc.tokens.typography),
            ai_sections=ai_count,
            ai_enabled=ai_enabled,
            container_width=parsed.container_width,
            has_dark_mode=parsed.has_dark_mode,
        )

        return doc

    def _resolve_ai_enabled(self, use_ai: bool | None) -> bool:
        """Resolve AI enablement from param or config."""
        if use_ai is not None:
            return use_ai
        try:
            return get_settings().design_sync.html_import_ai_enabled
        except Exception:
            logger.warning(
                "design_sync.html_import.config_fallback", field="html_import_ai_enabled"
            )
            return True

    def _max_size(self) -> int:
        """Get max HTML size from config."""
        try:
            return get_settings().design_sync.html_import_max_size_bytes
        except Exception:
            logger.warning(
                "design_sync.html_import.config_fallback", field="html_import_max_size_bytes"
            )
            return _MAX_HTML_SIZE

    def _build_document(
        self,
        parsed: ParsedEmail,
        classified_sections: list[DocumentSection],
        tokens: DocumentTokens,
        source_name: str | None,
    ) -> EmailDesignDocument:
        """Assemble the final ``EmailDesignDocument``."""
        source = DocumentSource(
            provider="html",
            file_ref=source_name,
        )

        layout = DocumentLayout(
            container_width=parsed.container_width,
            overall_width=float(parsed.container_width),
        )

        return EmailDesignDocument(
            version="1.0",
            tokens=tokens,
            sections=classified_sections,
            layout=layout,
            source=source,
        )
