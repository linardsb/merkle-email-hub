"""Schema.org auto-markup injection for email HTML."""

from app.email_engine.schema_markup.classifier import (
    EmailIntent,
    EmailIntentClassifier,
    ExtractedEntity,
    IntentType,
)
from app.email_engine.schema_markup.injector import InjectionResult, SchemaMarkupInjector
from app.email_engine.schema_markup.validator import SchemaValidator, ValidationResult

__all__ = [
    "EmailIntent",
    "EmailIntentClassifier",
    "ExtractedEntity",
    "InjectionResult",
    "IntentType",
    "SchemaMarkupInjector",
    "SchemaValidator",
    "ValidationResult",
]
