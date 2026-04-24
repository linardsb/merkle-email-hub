# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401
"""Import annotator agent service."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import lxml.html
from lxml.cssselect import CSSSelector

from app.ai.agents.base import BaseAgentService
from app.ai.agents.import_annotator.exceptions import ImportAnnotationError
from app.ai.agents.import_annotator.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.import_annotator.schemas import (
    AnnotationDecision,
    ImportAnnotationResult,
)
from app.ai.fallback import call_with_fallback
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import get_fallback_chain, resolve_model
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ImportAnnotatorService(BaseAgentService):
    agent_name = "import_annotator"
    sanitization_profile = "import_annotator"
    model_tier = "standard"
    stream_prefix = "import"
    run_qa_default = False  # Annotating, not generating email HTML
    _output_mode_supported = True

    def build_system_prompt(
        self,
        relevant_skills: list[str],
        output_mode: str = "html",
        *,
        client_id: str | None = None,
    ) -> str:
        return build_system_prompt(relevant_skills, output_mode, client_id=client_id)

    def detect_relevant_skills(self, request: Any) -> list[str]:
        html = request.get("html", "")
        esp_platform = request.get("esp_platform")
        return detect_relevant_skills(html, esp_platform)

    def _build_user_message(self, request: Any) -> str:
        html = request.get("html", "")
        esp_platform = request.get("esp_platform")
        msg = f"Annotate the following email HTML with data-section-id attributes.\n\n```html\n{html}\n```"
        if esp_platform:
            msg += f"\n\nESP platform: {esp_platform} — pay special attention to its token syntax."
        return msg

    def _build_response(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        """Not used — we override annotate() as the main entry point."""
        return {}

    async def annotate(self, html: str, esp_platform: str | None = None) -> dict[str, Any]:
        """Annotate HTML with section boundaries.

        Returns dict with annotated_html, sections, and warnings.
        """
        # Check for already-annotated HTML
        if "data-section-id=" in html:
            logger.info("import_annotator.already_annotated")
            return {
                "annotated_html": html,
                "sections": [],
                "warnings": ["HTML already contains data-section-id annotations. No changes made."],
            }

        # Validate size
        html_size = len(html.encode("utf-8"))
        if html_size > 2 * 1024 * 1024:  # 2MB
            logger.warning("import_annotator.oversized", size=html_size)
            raise ImportAnnotationError("HTML exceeds maximum size of 2MB")

        request: dict[str, Any] = {"html": html, "esp_platform": esp_platform}
        relevant_skills = self.detect_relevant_skills(request)
        system_prompt = build_system_prompt(relevant_skills, output_mode="structured")
        user_message = self._build_user_message(request)

        structured_instruction = (
            "\n\nRespond with ONLY a JSON object matching this schema:\n"
            "```json\n"
            "{\n"
            '  "annotations": [\n'
            "    {\n"
            '      "section_id": "uuid-string",\n'
            '      "component_name": "Header|Hero|Content|CTA|Footer|Columns|Divider|Spacer",\n'
            '      "element_selector": "CSS path to the element",\n'
            '      "layout_type": "single|columns",\n'
            '      "confidence": 0.95,\n'
            '      "reasoning": "why this boundary"\n'
            "    }\n"
            "  ],\n"
            '  "warnings": ["optional warning strings"],\n'
            '  "overall_confidence": 0.9,\n'
            '  "reasoning": "overall analysis"\n'
            "}\n"
            "```\n"
            "Do NOT include the annotated HTML — only the JSON decisions."
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt + structured_instruction),
            Message(role="user", content=user_message),
        ]

        try:
            settings = get_settings()
            provider_name = settings.ai.provider
            model = resolve_model(self.model_tier)
            registry = get_registry()
            chain = get_fallback_chain(self.model_tier)

            if chain and chain.has_fallbacks:
                response = await call_with_fallback(
                    chain, registry, messages, max_tokens=self.max_tokens
                )
            else:
                provider = registry.get_llm(provider_name)
                response = await provider.complete(
                    messages, model_override=model, max_tokens=self.max_tokens
                )
            raw = response.content

            result = self._parse_annotation_result(raw)
            annotated_html = self._apply_annotations(html, result)

            sections = [
                {
                    "section_id": a.section_id,
                    "component_name": a.component_name,
                    "element_selector": a.element_selector,
                    "layout_type": a.layout_type,
                }
                for a in result.annotations
            ]

            logger.info(
                "import_annotator.completed",
                section_count=len(result.annotations),
                warning_count=len(result.warnings),
                confidence=result.overall_confidence,
            )

            return {
                "annotated_html": annotated_html,
                "sections": sections,
                "warnings": list(result.warnings),
            }

        except ImportAnnotationError:
            raise
        except Exception as exc:
            logger.error("import_annotator.failed", error=str(exc), exc_info=True)
            return {
                "annotated_html": html,
                "sections": [],
                "warnings": ["Annotation failed, returning original HTML unchanged."],
            }

    def _parse_annotation_result(self, raw: str) -> ImportAnnotationResult:
        """Parse LLM JSON response into ImportAnnotationResult."""
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [line for line in lines[1:] if not line.strip().startswith("```")]
            content = "\n".join(lines)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ImportAnnotationError(f"Failed to parse AI response as JSON: {exc!s}") from exc

        raw_annotations = data.get("annotations", [])
        if not isinstance(raw_annotations, list):
            raise ImportAnnotationError("AI response 'annotations' field is not a list")

        annotations = tuple(
            AnnotationDecision(
                section_id=str(a.get("section_id", str(uuid.uuid4()))),
                component_name=str(a.get("component_name", "Content")),
                element_selector=str(a.get("element_selector", "")),
                layout_type=str(a.get("layout_type", "single")),
                confidence=float(a.get("confidence", 0.5)),
                reasoning=str(a.get("reasoning", "")),
            )
            for a in raw_annotations
            if isinstance(a, dict)
        )

        return ImportAnnotationResult(
            annotations=annotations,
            warnings=tuple(data.get("warnings", [])),
            overall_confidence=float(data.get("overall_confidence", 0.5)),
            reasoning=data.get("reasoning", ""),
        )

    _MAX_SELECTOR_LEN = 500
    _SELECTOR_SAFE_RE = re.compile(r"^[a-zA-Z0-9\s>+~.:,\[\]=\-_^$*#()\"'\|@/]+$")

    def _validate_selector(self, selector_str: str) -> bool:
        """Reject overly long or suspiciously complex CSS selectors."""
        if len(selector_str) > self._MAX_SELECTOR_LEN:
            return False
        return bool(self._SELECTOR_SAFE_RE.match(selector_str))

    def _apply_annotations(self, html: str, result: ImportAnnotationResult) -> str:
        """Apply annotation decisions to HTML using lxml CSS selectors."""
        doc = lxml.html.document_fromstring(html)

        applied = 0
        for annotation in result.annotations:
            selector_str = annotation.element_selector
            if not selector_str or not self._validate_selector(selector_str):
                if selector_str:
                    logger.warning(
                        "import_annotator.selector_rejected",
                        selector=selector_str[:100],
                        section_id=annotation.section_id,
                    )
                continue
            try:
                selector = CSSSelector(selector_str)
                elements = selector(doc)
                if elements:
                    el = elements[0]
                    el.set("data-section-id", annotation.section_id)
                    el.set("data-component-name", annotation.component_name)
                    if annotation.layout_type == "columns":
                        el.set("data-section-layout", "columns")
                    applied += 1
            except Exception:
                logger.warning(
                    "import_annotator.selector_failed",
                    selector=selector_str,
                    section_id=annotation.section_id,
                )
                continue

        if applied == 0:
            logger.warning("import_annotator.no_annotations_applied")
            return html

        result_html = lxml.html.tostring(doc, encoding="unicode")

        # Re-prepend DOCTYPE if original had one and lxml stripped it
        doctype_match = re.match(r"(<!DOCTYPE[^>]{0,2000}>)", html, re.IGNORECASE)
        if doctype_match and not result_html.strip().startswith("<!DOCTYPE"):
            result_html = doctype_match.group(1) + "\n" + result_html

        return result_html


_service: ImportAnnotatorService | None = None


def get_import_annotator_service() -> ImportAnnotatorService:
    global _service
    if _service is None:
        _service = ImportAnnotatorService()
    return _service
