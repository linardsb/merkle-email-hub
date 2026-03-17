"""Outlook Word-Engine Dependency Analyzer.

Static analyzer and modernizer for Word rendering engine dependencies in email HTML.
"""

from app.qa_engine.outlook_analyzer.detector import OutlookDependencyDetector
from app.qa_engine.outlook_analyzer.modernizer import OutlookModernizer
from app.qa_engine.outlook_analyzer.planner import MigrationPlanner
from app.qa_engine.outlook_analyzer.types import (
    AudienceProfile,
    MigrationPhase,
    MigrationPlan,
    ModernizationStep,
    ModernizeResult,
    OutlookAnalysis,
    OutlookDependency,
)

__all__ = [
    "AudienceProfile",
    "MigrationPhase",
    "MigrationPlan",
    "MigrationPlanner",
    "ModernizationStep",
    "ModernizeResult",
    "OutlookAnalysis",
    "OutlookDependency",
    "OutlookDependencyDetector",
    "OutlookModernizer",
]
