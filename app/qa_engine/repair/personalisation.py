"""Stage 5: ESP delimiter balancing — warn on imbalanced personalisation tags."""

from __future__ import annotations

import re

from app.qa_engine.repair.pipeline import RepairResult

_LIQUID_OPEN_RE = re.compile(r"\{\{")
_LIQUID_CLOSE_RE = re.compile(r"\}\}")
_AMPSCRIPT_OPEN_RE = re.compile(r"%%\[")
_AMPSCRIPT_CLOSE_RE = re.compile(r"\]%%")


class PersonalisationRepair:
    """Warn on imbalanced ESP personalisation delimiters. Does not auto-fix."""

    @property
    def name(self) -> str:
        return "personalisation"

    def repair(self, html: str) -> RepairResult:
        warnings: list[str] = []

        # Check Liquid/Handlebars {{ ... }}
        liquid_opens = len(_LIQUID_OPEN_RE.findall(html))
        liquid_closes = len(_LIQUID_CLOSE_RE.findall(html))
        if liquid_opens != liquid_closes and (liquid_opens > 0 or liquid_closes > 0):
            warnings.append(
                f"personalisation.imbalanced_delimiters: "
                f"Liquid/Handlebars {{{{ count: {liquid_opens}, "
                f"}}}} count: {liquid_closes}"
            )

        # Check AMPscript %%[ ... ]%%
        amp_opens = len(_AMPSCRIPT_OPEN_RE.findall(html))
        amp_closes = len(_AMPSCRIPT_CLOSE_RE.findall(html))
        if amp_opens != amp_closes and (amp_opens > 0 or amp_closes > 0):
            warnings.append(
                f"personalisation.imbalanced_delimiters: "
                f"AMPscript %%[ count: {amp_opens}, ]%% count: {amp_closes}"
            )

        return RepairResult(html=html, warnings=warnings)
