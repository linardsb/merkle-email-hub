"""Per-build CSS compatibility audit check.

Surfaces ontology-driven CSS compatibility data as a per-client matrix
showing which properties survive, were converted, or were removed in
each target email client.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from app.core.logging import get_logger
from app.email_engine.css_compiler.compiler import EmailCSSCompiler, OptimizedCSS
from app.email_engine.css_compiler.conversions import CSSConversion
from app.knowledge.ontology.query import unsupported_css_in_html
from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import CSSProperty, SupportLevel
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

_DEFAULT_TARGET_CLIENTS = [
    "gmail-web",
    "outlook-web",
    "apple-mail",
    "yahoo-mail-web",
    "samsung-mail",
]


class PropertyStatus(StrEnum):
    """Support status for a CSS property in a specific client."""

    SUPPORTED = "supported"
    CONVERTED = "converted"
    REMOVED = "removed"
    PARTIAL = "partial"


class CSSAuditCheck:
    """Per-build CSS compatibility audit.

    Runs the CSS compiler in optimize-only mode and builds a per-client
    matrix showing the support status of every CSS property used in the
    email. Severity classification:
    - error: property removed with no fallback in a tier-1 client
    - warning: property converted to fallback
    - info: property has partial support
    """

    name = "css_audit"

    async def run(
        self,
        html: str,
        config: QACheckConfig | None = None,
        *,
        compilation_result: OptimizedCSS | None = None,
    ) -> QACheckResult:
        target_clients: list[str] = (
            config.params.get("target_clients", _DEFAULT_TARGET_CLIENTS)
            if config
            else _DEFAULT_TARGET_CLIENTS
        )
        tier1_clients: list[str] = (
            config.params.get("tier1_clients", ["gmail-web", "outlook-web"])
            if config
            else ["gmail-web", "outlook-web"]
        )

        # Use pre-computed result or run optimizer
        if compilation_result is None:
            compiler = EmailCSSCompiler(target_clients=target_clients)
            compilation_result = compiler.optimize_css(html)

        registry = load_ontology()

        # Collect all CSS properties used in the HTML via ontology scan
        ontology_issues = unsupported_css_in_html(html)

        # Build sets for quick lookup from compilation result
        removed_set: set[str] = set(compilation_result.removed_properties)
        conversion_map: dict[str, CSSConversion] = {}
        for conv in compilation_result.conversions:
            conversion_map[conv.original_property] = conv

        # Build per-client compatibility matrix
        matrix: dict[str, dict[str, str]] = {}
        all_properties: set[str] = set()

        for issue in ontology_issues:
            prop_name = str(issue["property_name"])
            all_properties.add(prop_name)

        # Also include converted/removed properties not in ontology issues
        for prop in removed_set:
            all_properties.add(prop)
        for prop in conversion_map:
            all_properties.add(prop)

        # Pre-cache ontology lookups to avoid repeated find_property_by_name calls
        prop_cache: dict[str, CSSProperty | None] = {}
        for prop_name in all_properties:
            prop_cache[prop_name] = registry.find_property_by_name(prop_name)

        per_client_supported: dict[str, int] = {}
        total_props = len(all_properties)

        for client_id in target_clients:
            client_statuses: dict[str, str] = {}
            supported_count = 0

            for prop_name in sorted(all_properties):
                status = self._resolve_property_status(
                    prop_name, client_id, removed_set, conversion_map, registry, prop_cache
                )
                client_statuses[prop_name] = status
                if status in (PropertyStatus.SUPPORTED.value, PropertyStatus.PARTIAL.value):
                    supported_count += 1

            matrix[client_id] = client_statuses
            per_client_supported[client_id] = supported_count

        # Calculate per-client coverage scores
        client_coverage: dict[str, float] = {}
        for client_id in target_clients:
            if total_props == 0:
                client_coverage[client_id] = 100.0
            else:
                client_coverage[client_id] = round(
                    (per_client_supported.get(client_id, 0) / total_props) * 100, 1
                )

        # Overall coverage score (average across target clients)
        overall_coverage = (
            round(sum(client_coverage.values()) / len(client_coverage), 1)
            if client_coverage
            else 100.0
        )

        # Severity classification
        errors: list[str] = []
        warnings: list[str] = []
        infos: list[str] = []

        for prop_name in sorted(all_properties):
            for client_id in tier1_clients:
                cell_status = matrix.get(client_id, {}).get(prop_name)
                if cell_status == PropertyStatus.REMOVED.value:
                    css_prop = prop_cache.get(prop_name)
                    has_fallback = bool(css_prop and registry.fallbacks_for(css_prop.id))
                    if not has_fallback:
                        errors.append(f"{prop_name} removed in {client_id} (no fallback)")
                    else:
                        warnings.append(f"{prop_name} removed in {client_id} (fallback available)")
                elif cell_status == PropertyStatus.CONVERTED.value:
                    warnings.append(f"{prop_name} converted in {client_id}")
                elif cell_status == PropertyStatus.PARTIAL.value:
                    infos.append(f"{prop_name} partial support in {client_id}")

        # Build structured details as JSON
        structured_details: dict[str, Any] = {
            "compatibility_matrix": matrix,
            "conversions": [
                {
                    "original_property": c.original_property,
                    "original_value": c.original_value,
                    "replacement_property": c.replacement_property,
                    "replacement_value": c.replacement_value,
                    "reason": c.reason,
                    "affected_clients": list(c.affected_clients),
                }
                for c in compilation_result.conversions
            ],
            "removed_properties": compilation_result.removed_properties,
            "client_coverage_score": client_coverage,
            "overall_coverage_score": overall_coverage,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(infos),
            "issues": errors[:5] + warnings[:5],
        }

        has_errors = len(errors) > 0
        has_warnings = len(warnings) > 0
        severity = "error" if has_errors else ("warning" if has_warnings else "info")
        passed = not has_errors

        # Score: normalized coverage (0-1)
        score = round(overall_coverage / 100.0, 2)

        logger.info(
            "css_audit.run_completed",
            properties=total_props,
            clients=len(target_clients),
            coverage=overall_coverage,
            errors=len(errors),
            warnings=len(warnings),
        )

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=max(0.0, min(1.0, score)),
            details=json.dumps(structured_details),
            severity=severity,
        )

    def _resolve_property_status(
        self,
        prop_name: str,
        client_id: str,
        removed_set: set[str],
        conversion_map: dict[str, CSSConversion],
        registry: OntologyRegistry,
        prop_cache: dict[str, CSSProperty | None],
    ) -> str:
        """Determine the support status of a CSS property for a specific client."""
        if prop_name in removed_set:
            css_prop = prop_cache.get(prop_name)
            if css_prop:
                support = registry.get_support(css_prop.id, client_id)
                if support == SupportLevel.NONE:
                    return PropertyStatus.REMOVED.value
                if support == SupportLevel.PARTIAL:
                    return PropertyStatus.PARTIAL.value
                # Removed for other clients, but this client supports it
                return PropertyStatus.SUPPORTED.value
            return PropertyStatus.REMOVED.value

        if prop_name in conversion_map:
            conv = conversion_map[prop_name]
            if client_id in conv.affected_clients:
                return PropertyStatus.CONVERTED.value
            return PropertyStatus.SUPPORTED.value

        # Check ontology support
        css_prop = prop_cache.get(prop_name)
        if css_prop:
            support = registry.get_support(css_prop.id, client_id)
            if support == SupportLevel.NONE:
                return PropertyStatus.REMOVED.value
            if support == SupportLevel.PARTIAL:
                return PropertyStatus.PARTIAL.value
            return PropertyStatus.SUPPORTED.value

        # Property not in ontology — assume supported
        return PropertyStatus.SUPPORTED.value
