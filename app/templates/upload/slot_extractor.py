"""Convert detected content regions into TemplateSlot objects."""

from __future__ import annotations

from app.ai.templates.models import TemplateSlot
from app.templates.upload.analyzer import SectionInfo, SlotInfo

# Map analyzer slot types to TemplateSlot slot_type literals
_SLOT_TYPE_MAP: dict[str, str] = {
    "headline": "headline",
    "body": "body",
    "image": "image",
    "cta": "cta",
    "footer": "footer",
    "social": "social",
    "preheader": "preheader",
    "nav": "nav",
    "divider": "divider",
}


class SlotExtractor:
    """Converts raw slot analysis into formal TemplateSlot definitions."""

    def extract(
        self,
        slots: list[SlotInfo],
        sections: list[SectionInfo],  # noqa: ARG002
    ) -> tuple[TemplateSlot, ...]:
        """Map SlotInfo -> TemplateSlot with CSS selectors and type inference."""
        result: list[TemplateSlot] = []

        for slot in slots:
            slot_type = _SLOT_TYPE_MAP.get(slot.slot_type, "body")

            result.append(
                TemplateSlot(
                    slot_id=slot.slot_id,
                    slot_type=slot_type,  # type: ignore[arg-type]
                    selector=slot.selector,
                    required=slot.required,
                    max_chars=slot.max_chars,
                    placeholder=slot.content_preview[:60] if slot.content_preview else "",
                )
            )

        return tuple(result)
