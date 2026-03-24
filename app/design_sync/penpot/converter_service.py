"""Backward-compatible re-export — converter service moved to app.design_sync.converter_service."""

from app.design_sync.converter_service import (
    EMAIL_SKELETON,
    ConversionResult,
    DesignConverterService,
    PenpotConversionResult,
    PenpotConverterService,
)

__all__ = [
    "EMAIL_SKELETON",
    "ConversionResult",
    "DesignConverterService",
    "PenpotConversionResult",
    "PenpotConverterService",
]
