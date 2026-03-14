"""Cascading auto-repair pipeline — 7 deterministic stages, zero LLM calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RepairResult:
    """Aggregated output from one or more repair stages."""

    html: str
    repairs_applied: list[str] = field(default_factory=lambda: list[str]())
    warnings: list[str] = field(default_factory=lambda: list[str]())


class RepairStage(Protocol):
    """A single deterministic repair stage — pure function, no LLM."""

    @property
    def name(self) -> str: ...

    def repair(self, html: str) -> RepairResult: ...


class RepairPipeline:
    """Runs 7 repair stages in sequence. Each receives previous stage's output.

    Stage errors are caught, logged, and added to warnings — never crash the pipeline.
    """

    def __init__(self, stages: list[RepairStage] | None = None) -> None:
        self._stages = stages if stages is not None else self._default_stages()

    def run(self, html: str) -> RepairResult:
        """Run all stages sequentially. Return final HTML + all repairs + warnings."""
        all_repairs: list[str] = []
        all_warnings: list[str] = []
        current = html

        for stage in self._stages:
            try:
                result = stage.repair(current)
                current = result.html
                all_repairs.extend(result.repairs_applied)
                all_warnings.extend(result.warnings)
                if result.repairs_applied:
                    logger.info(
                        "repair.stage_applied",
                        stage=stage.name,
                        count=len(result.repairs_applied),
                        repairs=result.repairs_applied,
                    )
            except Exception as e:
                logger.warning(
                    "repair.stage_failed",
                    stage=stage.name,
                    error=str(e),
                )
                all_warnings.append(f"{stage.name}: repair failed ({e})")

        return RepairResult(
            html=current,
            repairs_applied=all_repairs,
            warnings=all_warnings,
        )

    @staticmethod
    def _default_stages() -> list[RepairStage]:
        from app.qa_engine.repair.accessibility import AccessibilityRepair
        from app.qa_engine.repair.dark_mode import DarkModeRepair
        from app.qa_engine.repair.links import LinkRepair
        from app.qa_engine.repair.mso import MSORepair
        from app.qa_engine.repair.personalisation import PersonalisationRepair
        from app.qa_engine.repair.size import SizeRepair
        from app.qa_engine.repair.structure import StructureRepair

        return [
            StructureRepair(),
            MSORepair(),
            DarkModeRepair(),
            AccessibilityRepair(),
            PersonalisationRepair(),
            SizeRepair(),
            LinkRepair(),
        ]
