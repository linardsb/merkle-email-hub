"""Conversion diagnostic pipeline — observability for design-to-email conversion."""

from app.design_sync.diagnose.models import DiagnosticReport
from app.design_sync.diagnose.runner import DiagnosticRunner

__all__ = ["DiagnosticReport", "DiagnosticRunner"]
