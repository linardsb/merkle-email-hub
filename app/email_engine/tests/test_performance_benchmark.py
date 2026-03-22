# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Performance benchmarks for CSS compilation pipeline.

Run with: make bench
Not included in standard `make test`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Generator
from unittest.mock import patch

import pytest

from app.email_engine.css_compiler.compiler import EmailCSSCompiler
from app.email_engine.tests.conftest import make_mock_registry


def _generate_scaled_email(section_count: int) -> str:
    """Generate an email with N sections for scaling benchmarks.

    Uses table-based layout matching real email component patterns.
    """
    styles = "\n".join(
        f".section-{i} {{ color: #{i:02x}{i:02x}{i:02x}; font-size: {12 + i}px; "
        f"padding: {i}px; margin: {i}px; line-height: 1.{i % 10}; }}"
        for i in range(section_count)
    )
    sections = "\n".join(
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td class="section-{i}" style="padding: {10 + i}px; font-family: Arial, sans-serif;">'
        f"<h2>Section {i}</h2><p>Content block {i} with text.</p>"
        f"</td></tr></table>"
        for i in range(section_count)
    )
    return (
        f"<!DOCTYPE html><html><head><style>{styles}</style></head>"
        f'<body><table role="presentation" width="600" align="center" '
        f'cellpadding="0" cellspacing="0" border="0"><tr><td>'
        f"{sections}"
        f"</td></tr></table></body></html>"
    )


@pytest.fixture(autouse=True)
def _mock_ontology() -> Generator[None]:
    reg = make_mock_registry(support_none=False)
    with (
        patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
        patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
    ):
        yield


def _time_fn(fn: Callable[..., object], *args: object, iterations: int = 5) -> float:
    """Return median execution time in ms over N iterations."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.monotonic()
        fn(*args)
        times.append((time.monotonic() - start) * 1000)
    times.sort()
    return times[len(times) // 2]


@pytest.mark.benchmark
class TestCompilationBenchmarks:
    """Benchmark compile() vs optimize_css() performance."""

    @pytest.mark.parametrize("sections", [5, 15, 30])
    def test_optimize_faster_than_compile_scaled(self, sections: int) -> None:
        """optimize_css() should be faster than compile() on synthetic scaled emails."""
        html = _generate_scaled_email(sections)
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])

        compile_ms = _time_fn(compiler.compile, html)
        optimize_ms = _time_fn(compiler.optimize_css, html)

        print(
            f"\n  [{sections} sections] compile={compile_ms:.1f}ms  optimize={optimize_ms:.1f}ms  "
            f"speedup={compile_ms / max(optimize_ms, 0.01):.1f}x"
        )

        assert optimize_ms < compile_ms, (
            f"optimize_css ({optimize_ms:.1f}ms) should be faster than compile ({compile_ms:.1f}ms)"
        )

    def test_optimize_real_templates(self, representative_templates: dict[str, str]) -> None:
        """Benchmark optimize_css() on real golden templates from the library."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for name, html in representative_templates.items():
            ms = _time_fn(compiler.optimize_css, html)
            print(f"\n  [{name}] optimize={ms:.1f}ms  size={len(html)}b")
            assert ms < 200, f"Template '{name}' optimize took {ms:.1f}ms, expected <200ms"

    def test_compile_real_templates(self, representative_templates: dict[str, str]) -> None:
        """Benchmark full compile() on real golden templates."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for name, html in representative_templates.items():
            ms = _time_fn(compiler.compile, html)
            print(f"\n  [{name}] compile={ms:.1f}ms  size={len(html)}b")
            assert ms < 500, f"Template '{name}' compile took {ms:.1f}ms, expected <500ms"

    def test_optimize_30_sections_under_100ms(self) -> None:
        """30-section email optimize_css should complete in under 100ms."""
        html = _generate_scaled_email(30)
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        ms = _time_fn(compiler.optimize_css, html)
        print(f"\n  [30 sections] optimize={ms:.1f}ms")
        assert ms < 100, f"optimize_css took {ms:.1f}ms, expected <100ms"

    def test_compile_50_sections_completes(self) -> None:
        """50-section email compile() should complete without error."""
        html = _generate_scaled_email(50)
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        result = compiler.compile(html)
        assert result.compiled_size > 0
        print(f"\n  [50 sections] compile={result.compile_time_ms:.1f}ms")

    def test_optimize_email_shell_component(self, component_html: dict[str, str]) -> None:
        """Benchmark optimize_css() on the email-shell component (heaviest CSS)."""
        shell = component_html.get("email-shell", "")
        if not shell:
            pytest.skip("email-shell component not in seeds")
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        ms = _time_fn(compiler.optimize_css, shell)
        print(f"\n  [email-shell] optimize={ms:.1f}ms  size={len(shell)}b")
        assert ms < 200, f"email-shell optimize took {ms:.1f}ms, expected <200ms"

    def test_optimize_all_components(self, component_html: dict[str, str]) -> None:
        """Benchmark optimize_css() across all 21 seeded components."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for slug, html in component_html.items():
            ms = _time_fn(compiler.optimize_css, html)
            print(f"\n  [{slug}] optimize={ms:.1f}ms  size={len(html)}b")
