"""Email Chaos Engine — controlled degradation testing."""

from app.qa_engine.chaos.composable import compose_profiles
from app.qa_engine.chaos.engine import ChaosEngine
from app.qa_engine.chaos.profiles import PROFILES, ChaosProfile

__all__ = ["PROFILES", "ChaosEngine", "ChaosProfile", "compose_profiles"]
