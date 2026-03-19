"""Assemble GoldenTemplate from analysis results."""

from __future__ import annotations

import hashlib

from app.ai.templates.models import (
    DefaultTokens,
    GoldenTemplate,
    TemplateMetadata,
    TemplateSlot,
)


class TemplateBuilder:
    """Constructs a GoldenTemplate from upload analysis + user overrides."""

    def build(
        self,
        sanitized_html: str,
        slots: tuple[TemplateSlot, ...],
        tokens: DefaultTokens,
        layout_type: str,
        column_count: int,
        sections: list[str],
        name: str | None = None,
        description: str | None = None,
    ) -> GoldenTemplate:
        """Create GoldenTemplate with uploaded_ namespace prefix."""
        # Generate name from content hash if not provided
        html_hash = hashlib.sha256(sanitized_html.encode()).hexdigest()[:6]
        template_name = name or f"uploaded_{layout_type}_{html_hash}"

        # Ensure uploaded_ prefix
        if not template_name.startswith("uploaded_"):
            template_name = f"uploaded_{template_name}"

        display_name = template_name.replace("_", " ").replace("uploaded ", "Uploaded ").title()
        desc = description or f"Uploaded {layout_type} template with {len(slots)} slots"

        has_hero = any(s.slot_type == "image" and s.required for s in slots)

        metadata = TemplateMetadata(
            name=template_name,
            display_name=display_name,
            layout_type=layout_type,  # type: ignore[arg-type]
            column_count=column_count,
            has_hero_image=has_hero,
            has_navigation=False,
            has_social_links=any(s.slot_type == "social" for s in slots),
            sections=tuple(sections),
            ideal_for=("uploaded",),
            description=desc,
        )

        return GoldenTemplate(
            metadata=metadata,
            html=sanitized_html,
            slots=slots,
            default_tokens=tokens,
            source="uploaded",
            project_id=None,
        )
