"""Assemble GoldenTemplate from analysis results."""

from __future__ import annotations

import hashlib

from app.ai.templates.models import (
    DefaultTokens,
    GoldenTemplate,
    TemplateMetadata,
    TemplateSlot,
)
from app.templates.upload.analyzer import WrapperInfo
from app.templates.upload.wrapper_utils import inject_centering_wrapper


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
        wrapper: WrapperInfo | None = None,
    ) -> GoldenTemplate:
        """Create GoldenTemplate with uploaded_ namespace prefix."""
        # Ensure centering wrapper is present if metadata says one existed
        if wrapper is not None:
            sanitized_html = self._ensure_wrapper(sanitized_html, wrapper)

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

        # Serialize wrapper info for storage
        wrapper_metadata: dict[str, str | None] | None = None
        if wrapper is not None:
            wrapper_metadata = {
                "tag": wrapper.tag,
                "width": wrapper.width,
                "align": wrapper.align,
                "style": wrapper.style,
                "bgcolor": wrapper.bgcolor,
                "cellpadding": wrapper.cellpadding,
                "cellspacing": wrapper.cellspacing,
                "border": wrapper.border,
                "role": wrapper.role,
                "inner_td_style": wrapper.inner_td_style,
                "mso_wrapper": wrapper.mso_wrapper,
            }

        return GoldenTemplate(
            metadata=metadata,
            html=sanitized_html,
            slots=slots,
            default_tokens=tokens,
            source="uploaded",
            project_id=None,
            wrapper_metadata=wrapper_metadata,
        )

    @staticmethod
    def _ensure_wrapper(html: str, wrapper: WrapperInfo) -> str:
        """Ensure centering wrapper is present in HTML.

        If the HTML already has centering (detected by inject_centering_wrapper),
        returns it unchanged. Otherwise, injects a centering wrapper
        using the metadata from the original import.
        """
        width = int(wrapper.width) if wrapper.width and wrapper.width.isdigit() else 600
        return inject_centering_wrapper(
            html,
            width=width,
            mso_wrapper=wrapper.mso_wrapper,
        )
