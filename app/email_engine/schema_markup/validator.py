"""Schema.org JSON-LD validator for email markup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ValidationResult:
    """Result of JSON-LD validation."""

    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# Required properties per schema.org type
_REQUIRED_PROPERTIES: dict[str, set[str]] = {
    "Product": {"name"},
    "Offer": {"price", "priceCurrency"},
    "Order": {"orderNumber", "merchant"},
    "Event": {"name", "startDate"},
    "EmailMessage": set(),
    "ViewAction": {"url", "name"},
    "ConfirmAction": {"handler"},
    "RsvpAction": {"handler"},
    "TrackAction": {"url"},
    "Organization": {"name"},
}

# Gmail-specific validation rules
_GMAIL_ACTION_TYPES = {"ViewAction", "ConfirmAction", "TrackAction", "SaveAction", "RsvpAction"}


class SchemaValidator:
    """Validates JSON-LD against schema.org vocabulary and Gmail requirements."""

    def validate(self, json_ld: dict[str, Any]) -> ValidationResult:
        """Validate a JSON-LD object for email injection.

        Args:
            json_ld: Parsed JSON-LD dictionary.

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Must have @context
        context = json_ld.get("@context")
        if context != "https://schema.org" and context != "http://schema.org":
            errors.append("Missing or invalid @context — must be https://schema.org")

        # Must have @type
        schema_type = json_ld.get("@type")
        if not schema_type:
            errors.append("Missing @type")
            return ValidationResult(valid=False, errors=tuple(errors), warnings=tuple(warnings))

        # Validate required properties
        type_str = str(schema_type)
        if type_str in _REQUIRED_PROPERTIES:
            for prop in _REQUIRED_PROPERTIES[type_str]:
                if prop not in json_ld:
                    errors.append(f"Missing required property '{prop}' for {type_str}")

        # Validate nested objects recursively
        self._validate_nested(json_ld, errors, warnings)

        # Gmail-specific: action URLs must be HTTPS
        self._validate_action_urls(json_ld, errors, warnings)

        valid = len(errors) == 0

        if not valid:
            logger.warning(
                "schema_markup.validation_failed",
                schema_type=type_str,
                error_count=len(errors),
            )

        return ValidationResult(valid=valid, errors=tuple(errors), warnings=tuple(warnings))

    def _validate_nested(
        self,
        obj: dict[str, Any],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate nested schema.org objects."""
        for _key, value in obj.items():
            if isinstance(value, dict) and "@type" in value:
                nested = cast(dict[str, Any], value)
                nested_type = str(nested["@type"])
                if nested_type in _REQUIRED_PROPERTIES:
                    for prop in _REQUIRED_PROPERTIES[nested_type]:
                        if prop not in nested:
                            errors.append(
                                f"Missing required property '{prop}' for nested {nested_type}"
                            )
                self._validate_nested(nested, errors, warnings)

    def _validate_action_urls(
        self,
        obj: dict[str, Any],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Gmail requires HTTPS for all action handler URLs."""
        schema_type = obj.get("@type", "")

        if str(schema_type) in _GMAIL_ACTION_TYPES:
            # Check url property
            url = obj.get("url")
            if isinstance(url, str) and not url.startswith("https://"):
                errors.append(f"Action URL must be HTTPS: {url[:80]}")

            # Check handler.url for confirm/RSVP actions
            handler = obj.get("handler")
            if isinstance(handler, dict):
                handler_dict = cast(dict[str, Any], handler)
                handler_url = handler_dict.get("url")
                if isinstance(handler_url, str) and not handler_url.startswith("https://"):
                    errors.append(f"Action handler URL must be HTTPS: {handler_url[:80]}")

        # Recurse into nested objects
        for value in obj.values():
            if isinstance(value, dict):
                self._validate_action_urls(cast(dict[str, Any], value), errors, warnings)
