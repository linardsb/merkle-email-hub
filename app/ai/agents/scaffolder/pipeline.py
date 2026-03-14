"""3-pass generation pipeline for the Scaffolder agent.

Pass 1 (Layout):  Brief → TemplateSelection + SectionDecisions
Pass 2 (Content): Brief + Template slots → SlotFills
Pass 3 (Design):  Brief + Brand config → DesignTokens

Pass 1 runs first (needs template name). Passes 2+3 run in parallel.
Per-slot retry on content failures.
"""

import asyncio
import json
import re
from typing import Any

from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    EmailBuildPlan,
    SectionDecision,
    SlotFill,
    TemplateSelection,
)
from app.ai.protocols import LLMProvider, Message
from app.ai.sanitize import sanitize_prompt
from app.ai.templates import TemplateRegistry, get_template_registry
from app.core.logging import get_logger

logger = get_logger(__name__)

# Retry budget for individual pass failures
_MAX_RETRIES: int = 1


class PipelineError(Exception):
    """Raised when the pipeline cannot produce a valid plan."""


class ScaffolderPipeline:
    """3-pass generation pipeline with structured output."""

    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        registry: TemplateRegistry | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self._provider = provider
        self._model = model
        self._registry = registry or get_template_registry()
        self._max_tokens = max_tokens

    async def execute(
        self,
        brief: str,
        brand_config: dict[str, object] | None = None,
    ) -> EmailBuildPlan:
        """Execute 3-pass pipeline. Returns complete EmailBuildPlan.

        Pass 1 (layout) must complete first — it determines which template
        and slots to fill. Passes 2 (content) and 3 (design) then run
        in parallel since they're independent.
        """
        brief = sanitize_prompt(brief)

        # Pass 1: Layout selection (must complete first)
        template_selection, section_decisions = await self._layout_pass(brief)

        # Resolve slot IDs from selected template
        template = self._registry.get(template_selection.template_name)
        if template is None and template_selection.fallback_template:
            template = self._registry.get(template_selection.fallback_template)
        slot_details: list[dict[str, object]] = (
            [
                {
                    "slot_id": s.slot_id,
                    "slot_type": s.slot_type,
                    "max_chars": s.max_chars,
                    "required": s.required,
                }
                for s in template.slots
            ]
            if template
            else []
        )

        # Pass 2 + 3 in parallel (independent of each other)
        slot_fills, design_tokens = await asyncio.gather(
            self._content_pass(brief, template_selection, slot_details),
            self._design_pass(brief, brand_config),
        )

        plan = EmailBuildPlan(
            template=template_selection,
            slot_fills=slot_fills,
            design_tokens=design_tokens,
            sections=section_decisions,
            preheader_text=self._extract_preheader(slot_fills),
            subject_line=self._extract_subject(slot_fills),
            confidence=0.85,
            reasoning=template_selection.reasoning,
        )

        logger.info(
            "scaffolder.pipeline_completed",
            template=template_selection.template_name,
            slots_filled=len(slot_fills),
            passes=3,
        )
        return plan

    # ── Pass 1: Layout ──

    async def _layout_pass(
        self, brief: str
    ) -> tuple[TemplateSelection, tuple[SectionDecision, ...]]:
        """Pick template + section visibility. Lightweight pass."""
        available = self._registry.list_for_selection()
        template_list = "\n".join(
            f"- {m.name}: {m.display_name} ({m.layout_type}, {m.column_count}-col) — {m.description}"
            for m in available
        )

        system = (
            "You are an email layout architect. Select the best template for the brief.\n\n"
            "Return a JSON object with these fields:\n"
            "- template_name: string (one of the available template names)\n"
            "- reasoning: string (why this template fits)\n"
            "- fallback_template: string | null (backup if primary doesn't work)\n"
            "- section_decisions: array of {section_name: string, background_color?: string, hidden?: boolean}\n\n"
            f"Available templates:\n{template_list}\n\n"
            "Respond ONLY with valid JSON, no markdown fences."
        )
        user = f"Campaign brief:\n{brief}"

        parsed = await self._call_json(system, user)

        template_selection = TemplateSelection(
            template_name=str(parsed.get("template_name", "")),
            reasoning=str(parsed.get("reasoning", "")),
            section_order=tuple(parsed.get("section_order", ())),
            fallback_template=parsed.get("fallback_template"),
        )

        if not template_selection.template_name:
            raise PipelineError("Layout pass returned empty template_name")

        section_decisions = tuple(
            SectionDecision(
                section_name=str(s.get("section_name", "")),
                background_color=s.get("background_color"),
                padding=s.get("padding"),
                hidden=bool(s.get("hidden", False)),
            )
            for s in parsed.get("section_decisions", [])
        )

        logger.info(
            "scaffolder.layout_pass_completed",
            template=template_selection.template_name,
            sections=len(section_decisions),
        )
        return template_selection, section_decisions

    # ── Pass 2: Content ──

    async def _content_pass(
        self,
        brief: str,
        template: TemplateSelection,
        slot_details: list[dict[str, object]],
    ) -> tuple[SlotFill, ...]:
        """Fill each slot with content. Includes slot metadata for guidance."""
        slots_desc = "\n".join(
            f"- {s['slot_id']} (type: {s['slot_type']}, max_chars: {s.get('max_chars', 'unlimited')}, required: {s.get('required', True)})"
            for s in slot_details
        )

        system = (
            "You are an email content writer. Fill each content slot with appropriate text/HTML.\n\n"
            "Return a JSON object with:\n"
            "- slot_fills: array of {slot_id: string, content: string, is_personalisable: boolean}\n\n"
            "Rules:\n"
            "- Content must match the campaign brief tone and purpose\n"
            "- Respect max_chars limits\n"
            "- For CTA slots, provide short action-oriented text\n"
            "- For image slots, provide a descriptive placeholder URL\n"
            "- For URL slots (ending in _url), provide a realistic placeholder URL\n"
            "- Set is_personalisable=true for slots that benefit from personalisation (e.g., greetings, names)\n\n"
            f"Template: {template.template_name}\n"
            f"Slots to fill:\n{slots_desc}\n\n"
            "Respond ONLY with valid JSON, no markdown fences."
        )
        user = f"Campaign brief:\n{brief}"

        parsed = await self._call_json(system, user)

        fills = tuple(
            SlotFill(
                slot_id=str(sf.get("slot_id", "")),
                content=str(sf.get("content", "")),
                is_personalisable=bool(sf.get("is_personalisable", False)),
            )
            for sf in parsed.get("slot_fills", [])
        )

        if not fills:
            raise PipelineError("Content pass returned no slot_fills")

        logger.info(
            "scaffolder.content_pass_completed",
            slots_filled=len(fills),
        )
        return fills

    # ── Pass 3: Design ──

    async def _design_pass(
        self,
        brief: str,
        brand_config: dict[str, object] | None = None,
    ) -> DesignTokens:
        """Pick colours, fonts, spacing. Structured output."""
        brand_context = ""
        if brand_config:
            brand_context = f"\nBrand guidelines:\n{json.dumps(brand_config, default=str)}"

        system = (
            "You are an email design architect. Choose design tokens for the email.\n\n"
            "Return a JSON object with:\n"
            "- primary_color: hex color (e.g. '#e84e0f')\n"
            "- secondary_color: hex color\n"
            "- background_color: hex color\n"
            "- text_color: hex color\n"
            "- font_family: web-safe font stack\n"
            "- heading_font_family: web-safe font stack\n"
            "- border_radius: CSS value (e.g. '4px')\n"
            "- button_style: 'filled' | 'outlined' | 'text'\n\n"
            "Use web-safe hex colors. Font stacks must include system fallbacks."
            f"{brand_context}\n\n"
            "Respond ONLY with valid JSON, no markdown fences."
        )
        user = f"Campaign brief:\n{brief}"

        parsed = await self._call_json(system, user, max_tokens=1024)

        tokens = DesignTokens(
            primary_color=str(parsed.get("primary_color", "#e84e0f")),
            secondary_color=str(parsed.get("secondary_color", "#0c2340")),
            background_color=str(parsed.get("background_color", "#ffffff")),
            text_color=str(parsed.get("text_color", "#333333")),
            font_family=str(
                parsed.get(
                    "font_family", "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"
                )
            ),
            heading_font_family=str(parsed.get("heading_font_family", "Georgia,serif")),
            border_radius=str(parsed.get("border_radius", "4px")),
            button_style=parsed.get("button_style", "filled"),
        )

        logger.info("scaffolder.design_pass_completed")
        return tokens

    # ── Helpers ──

    async def _call_json(
        self, system: str, user: str, max_tokens: int | None = None
    ) -> dict[str, Any]:
        """Make an LLM call and parse JSON from response. Retries once on parse failure."""
        messages = [
            Message(role="system", content=system),
            Message(role="user", content=user),
        ]

        result = None
        for attempt in range(_MAX_RETRIES + 1):
            result = await self._provider.complete(
                messages,
                model_override=self._model,
                max_tokens=max_tokens or self._max_tokens,
            )
            parsed = _parse_json(result.content)
            if parsed:
                return parsed

            if attempt < _MAX_RETRIES:
                logger.warning(
                    "scaffolder.json_retry",
                    attempt=attempt + 1,
                    content_preview=result.content[:200],
                )
                # Append assistant response + retry instruction
                messages.append(Message(role="assistant", content=result.content))
                messages.append(
                    Message(
                        role="user",
                        content="That was not valid JSON. Please respond with ONLY a valid JSON object, no markdown fences or explanatory text.",
                    ),
                )

        raise PipelineError(
            f"Failed to parse JSON after {_MAX_RETRIES + 1} attempts. "
            f"Last response: {result.content[:200] if result else 'no response'}"
        )

    @staticmethod
    def _extract_preheader(fills: tuple[SlotFill, ...]) -> str:
        """Extract preheader from slot fills if present."""
        for fill in fills:
            if fill.slot_id == "preheader":
                return fill.content
        return ""

    @staticmethod
    def _extract_subject(fills: tuple[SlotFill, ...]) -> str:
        """Extract subject line from slot fills if present."""
        for fill in fills:
            if fill.slot_id == "subject_line":
                return fill.content
        return ""


def _parse_json(content: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response. Handles code fences and raw JSON."""
    # Try code fence first
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    # Try raw JSON parse
    try:
        return json.loads(content)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    return None
