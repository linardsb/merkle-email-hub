"""Cascading auto-repair pipeline — deterministic HTML fixes before QA gate."""

from app.qa_engine.repair.pipeline import RepairPipeline, RepairResult, RepairStage

__all__ = ["RepairPipeline", "RepairResult", "RepairStage"]
