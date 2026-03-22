"""Email-specific CSS compiler built on Lightning CSS."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import lightningcss

from app.ai.shared import sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.ontology.registry import OntologyRegistry, load_ontology

from .conversions import (
    CSSConversion,
    get_conversions_for_property,
    resolve_css_variables,
    should_remove_property,
)
from .inliner import extract_styles, inline_styles, parse_css_rules

logger = get_logger(__name__)

_INLINE_STYLE_RE = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)


@dataclass(frozen=True)
class CompilationResult:
    """Result of CSS compilation."""

    html: str
    original_size: int
    compiled_size: int
    removed_properties: list[str]
    conversions: list[CSSConversion]
    warnings: list[str]
    compile_time_ms: float


@dataclass(frozen=True)
class OptimizedCSS:
    """Result of CSS optimization (stages 1-5 only, no inlining).

    HTML contains optimized <style> blocks ready for external inliner (e.g. Maizzle/Juice).
    """

    html: str
    removed_properties: list[str]
    conversions: list[CSSConversion]
    warnings: list[str]
    optimize_time_ms: float


class EmailCSSCompiler:
    """Email-specific CSS compiler with ontology-driven optimization.

    Pipeline stages:
    1. Parse — extract CSS from <style> blocks + inline styles
    2. Analyze — cross-reference against ontology support matrix
    3. Transform — apply conversions for unsupported properties
    4. Eliminate — remove properties with zero support across all targets
    5. Optimize — Lightning CSS minification
    6. Inline — inject optimized styles as inline style attributes
    7. Output — sanitized final HTML
    """

    def __init__(
        self,
        target_clients: list[str] | None = None,
        css_variables: dict[str, str] | None = None,
    ) -> None:
        settings = get_settings()
        self._target_clients = target_clients or settings.email_engine.css_compiler_target_clients
        self._css_variables = css_variables or {}
        self._registry: OntologyRegistry | None = None

    @property
    def registry(self) -> OntologyRegistry:
        if self._registry is None:
            self._registry = load_ontology()
        return self._registry

    def compile(self, html: str) -> CompilationResult:
        """Run the full CSS compilation pipeline."""
        start = time.monotonic()
        original_size = len(html.encode("utf-8"))
        stage_timings: dict[str, float] = {}

        # Stages 1-5: Parse, Analyze, Transform, Eliminate, Optimize
        t0 = time.monotonic()
        html_no_styles, minified_blocks, removed, conversions, warnings = (
            self._run_optimization_stages(html)
        )
        stage_timings["optimize"] = (time.monotonic() - t0) * 1000

        # Stage 6: Inline — parse rules and apply as inline styles
        t0 = time.monotonic()
        all_rules: list[tuple[str, list[tuple[str, str]]]] = []
        at_rules: list[str] = []  # @media etc. — keep in <style>
        for block in minified_blocks:
            rules = parse_css_rules(block)
            all_rules.extend(rules)
            # Preserve @-rules that can't be inlined
            for line in block.split("}"):
                stripped = line.strip()
                if stripped.startswith("@"):
                    at_rules.append(stripped + "}")

        result_html = inline_styles(html_no_styles, all_rules)

        # Re-inject @-rules that can't be inlined (e.g. @media)
        if at_rules:
            at_css = "\n".join(at_rules)
            result_html = result_html.replace("</head>", f"<style>{at_css}</style></head>", 1)
        stage_timings["inline"] = (time.monotonic() - t0) * 1000

        # Stage 7: Output — sanitize
        t0 = time.monotonic()
        result_html = sanitize_html_xss(result_html)
        compiled_size = len(result_html.encode("utf-8"))
        stage_timings["sanitize"] = (time.monotonic() - t0) * 1000

        compile_time = (time.monotonic() - start) * 1000

        logger.info(
            "css_compiler.compile_completed",
            original_size=original_size,
            compiled_size=compiled_size,
            reduction_pct=round((1 - compiled_size / original_size) * 100, 1)
            if original_size > 0
            else 0,
            removed_count=len(removed),
            conversion_count=len(conversions),
            target_clients=self._target_clients,
            compile_time_ms=round(compile_time, 2),
            **{f"stage_{k}_ms": round(v, 2) for k, v in stage_timings.items()},
        )

        return CompilationResult(
            html=result_html,
            original_size=original_size,
            compiled_size=compiled_size,
            removed_properties=removed,
            conversions=conversions,
            warnings=warnings,
            compile_time_ms=round(compile_time, 2),
        )

    def optimize_css(self, html: str) -> OptimizedCSS:
        """Run CSS optimization stages 1-5 only (no inlining).

        Produces HTML with optimized <style> blocks, ready for an external
        inliner like Maizzle/Juice to convert to inline styles. Skips stage 6
        (BeautifulSoup inlining) and stage 7 (XSS sanitization — caller is
        responsible for sanitizing after inlining).

        Use this before sending HTML to the Maizzle sidecar: ontology-driven
        optimization reduces CSS rules before Juice inlines them.
        """
        start = time.monotonic()

        html_no_styles, minified_blocks, removed, conversions, warnings = (
            self._run_optimization_stages(html)
        )

        # Re-inject optimized <style> blocks (NOT inlined)
        if minified_blocks:
            style_tags = "\n".join(
                f"<style>{block}</style>" for block in minified_blocks if block.strip()
            )
            html_no_styles = html_no_styles.replace("</head>", f"{style_tags}</head>", 1)

        optimize_time = (time.monotonic() - start) * 1000

        logger.info(
            "css_compiler.optimize_completed",
            removed_count=len(removed),
            conversion_count=len(conversions),
            target_clients=self._target_clients,
            optimize_time_ms=round(optimize_time, 2),
        )

        return OptimizedCSS(
            html=html_no_styles,
            removed_properties=removed,
            conversions=conversions,
            warnings=warnings,
            optimize_time_ms=round(optimize_time, 2),
        )

    def _run_optimization_stages(
        self, html: str
    ) -> tuple[str, list[str], list[str], list[CSSConversion], list[str]]:
        """Run stages 1-5: Parse, Analyze, Transform, Eliminate, Optimize.

        Returns (html_without_styles, minified_css_blocks, removed, conversions, warnings).
        """
        removed: list[str] = []
        conversions: list[CSSConversion] = []
        warnings: list[str] = []

        # Stage 1: Parse — extract <style> blocks
        html_no_styles, css_blocks = extract_styles(html)

        # Stage 2+3+4: Analyze, Transform, Eliminate on <style> CSS
        optimized_css_blocks: list[str] = []
        for block in css_blocks:
            processed, blk_removed, blk_conversions, blk_warnings = self._process_css_block(block)
            optimized_css_blocks.append(processed)
            removed.extend(blk_removed)
            conversions.extend(blk_conversions)
            warnings.extend(blk_warnings)

        # Stage 2+3+4 on inline styles
        html_no_styles = self._process_inline_styles(html_no_styles, removed, conversions, warnings)

        # Stage 5: Optimize — Lightning CSS minification
        minified_blocks: list[str] = []
        for block in optimized_css_blocks:
            minified = self._minify_css(block, warnings)
            minified_blocks.append(minified)

        return html_no_styles, minified_blocks, removed, conversions, warnings

    def _process_css_block(
        self, css_text: str
    ) -> tuple[str, list[str], list[CSSConversion], list[str]]:
        """Analyze, transform, and eliminate unsupported CSS in a block."""
        removed: list[str] = []
        conversions: list[CSSConversion] = []
        warnings: list[str] = []

        # Resolve CSS variables first
        if self._css_variables:
            css_text = resolve_css_variables(css_text, self._css_variables)

        # Process each declaration
        lines: list[str] = []
        for line in css_text.split(";"):
            line = line.strip()
            if not line or ":" not in line:
                lines.append(line)
                continue

            prop, val = line.split(":", 1)
            prop = prop.strip()
            val = val.strip()

            # Check if property should be removed entirely
            if should_remove_property(prop, val, self._target_clients, self.registry):
                removed.append(f"{prop}: {val}")
                continue

            # Check for conversions
            prop_conversions = get_conversions_for_property(
                prop, val, self._target_clients, self.registry
            )
            if prop_conversions:
                conversions.extend(prop_conversions)
                # Apply first conversion, keep original as fallback comment
                first = prop_conversions[0]
                replacement = (
                    f"{first.replacement_property}: {first.replacement_value}"
                    if first.replacement_value
                    else f"{first.replacement_property}: {val}"
                )
                lines.append(replacement)
            else:
                lines.append(f"{prop}: {val}")

        return "; ".join(part for part in lines if part), removed, conversions, warnings

    def _process_inline_styles(
        self,
        html: str,
        removed: list[str],
        conversions: list[CSSConversion],
        warnings: list[str],
    ) -> str:
        """Process inline style= attributes in the HTML."""

        def _replace_style(m: re.Match[str]) -> str:
            style_content = m.group(1)
            processed, blk_removed, blk_conversions, blk_warnings = self._process_css_block(
                style_content
            )
            removed.extend(blk_removed)
            conversions.extend(blk_conversions)
            warnings.extend(blk_warnings)
            return f'style="{processed}"'

        return _INLINE_STYLE_RE.sub(_replace_style, html)

    def _minify_css(self, css_text: str, warnings: list[str]) -> str:
        """Minify CSS using Lightning CSS."""
        if not css_text.strip():
            return css_text

        # Wrap bare declarations in a dummy rule for Lightning CSS parsing
        needs_wrapping = "{" not in css_text
        if needs_wrapping:
            css_text = f"__dummy__ {{ {css_text} }}"

        try:
            parser_flags = lightningcss.calc_parser_flags(nesting=True)
            result = lightningcss.process_stylesheet(
                css_text,
                filename="email.css",
                parser_flags=parser_flags,
                minify=True,
            )
            if needs_wrapping:
                # Unwrap dummy rule
                result = re.sub(r"__dummy__\s*\{(.*)\}", r"\1", result, flags=re.DOTALL).strip()
            return result
        except Exception as exc:
            warnings.append(f"Lightning CSS minification failed: {exc}")
            # Strip the wrapping if we added it
            if needs_wrapping:
                css_text = css_text.replace("__dummy__ {", "").rstrip("}")
            return css_text
