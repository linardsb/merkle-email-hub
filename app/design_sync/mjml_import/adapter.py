"""MJML Import Adapter — parse MJML markup into ``EmailDesignDocument``."""

from __future__ import annotations

from lxml import etree

from app.design_sync.email_design_document import (
    DocumentLayout,
    DocumentSource,
    EmailDesignDocument,
)
from app.design_sync.exceptions import MjmlImportError
from app.design_sync.mjml_import.section_parser import parse_sections
from app.design_sync.mjml_import.token_extractor import extract_tokens
from app.design_sync.mjml_import.type_inferrer import infer_section_types

_MAX_MJML_BYTES = 2 * 1024 * 1024  # 2 MB


class MjmlImportAdapter:
    """Parse MJML markup into :class:`EmailDesignDocument`."""

    def parse(self, mjml_source: str) -> EmailDesignDocument:
        raw = mjml_source.encode("utf-8")
        if len(raw) > _MAX_MJML_BYTES:
            msg = "MJML source exceeds 2 MB limit"
            raise MjmlImportError(msg)

        root = self._parse_xml(raw)
        self._validate_root(root)

        head = root.find("mj-head")
        body = root.find("mj-body")
        if body is None:
            msg = "Missing <mj-body> element"
            raise MjmlImportError(msg)

        tokens = extract_tokens(head)
        sections = parse_sections(body)
        sections = infer_section_types(sections)

        container_width = self._parse_container_width(body)

        return EmailDesignDocument(
            version="1.0",
            source=DocumentSource(provider="mjml"),
            tokens=tokens,
            sections=sections,
            layout=DocumentLayout(
                container_width=container_width,
                naming_convention="mjml",
            ),
        )

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _parse_xml(raw: bytes) -> etree._Element:
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            huge_tree=False,
            recover=False,
        )
        try:
            return etree.fromstring(raw, parser=parser)
        except etree.XMLSyntaxError as exc:
            msg = "Invalid MJML XML: document is not well-formed"
            raise MjmlImportError(msg) from exc

    @staticmethod
    def _validate_root(root: etree._Element) -> None:
        raw_tag = root.tag
        tag = raw_tag if isinstance(raw_tag, str) else str(raw_tag)
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag != "mjml":
            msg = f"Root element must be <mjml>, got <{tag}>"
            raise MjmlImportError(msg)

    @staticmethod
    def _parse_container_width(body: etree._Element) -> int:
        width_attr = body.get("width", "600px")
        try:
            return int(width_attr.replace("px", "").strip())
        except (ValueError, AttributeError):
            return 600
