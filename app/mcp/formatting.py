"""Format service responses for LLM consumption.

Principles:
1. Lead with the verdict (pass/fail/score), not the data
2. Actionable fixes before raw details
3. Truncate HTML intelligently — keep head + first issue region
4. Always include "what to do next" guidance
5. Stay within token budget
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings


def truncate_html(html: str, max_chars: int = 2000) -> str:
    """Truncate HTML for LLM context, keeping structure hints."""
    if len(html) <= max_chars:
        return html
    # Keep first portion + ellipsis with size info
    return (
        html[:max_chars]
        + f"\n\n[...truncated, {len(html) - max_chars:,} chars remaining, {len(html):,} total]"
    )


def format_qa_result(result: dict[str, Any]) -> str:
    """Format QA check results as actionable markdown."""
    lines: list[str] = []
    score = result.get("overall_score", 0)
    passed = result.get("passed", 0)
    total = result.get("total", 0)
    failed = result.get("failed", 0)

    # Verdict first
    if score >= 90:
        lines.append(
            f"**QA Score: {score}/100** — Production ready ({passed}/{total} checks passed)"
        )
    elif score >= 70:
        lines.append(f"**QA Score: {score}/100** — Needs fixes ({failed} issues found)")
    else:
        lines.append(f"**QA Score: {score}/100** — Significant issues ({failed} checks failed)")

    # Failed checks with fixes
    for check in result.get("checks", []):
        if not check.get("passed"):
            lines.append(f"\n### {check['name']}")
            lines.append(check.get("message", ""))
            if details := check.get("details"):
                for d in details[:5]:  # Cap detail items
                    lines.append(f"  - {d}")

    # Guidance
    if failed > 0:
        lines.append("\n**Next steps:** Fix the issues above, then re-run `qa_check` to verify.")
    else:
        lines.append(
            "\n**Next steps:** Email is ready. Consider running `email_visual_check` for rendering verification."
        )

    return _apply_token_budget("\n".join(lines))


def format_knowledge_result(results: list[dict[str, Any]]) -> str:
    """Format knowledge search results with relevance context."""
    if not results:
        return (
            "No results found. Try broadening your search terms or check the "
            "available knowledge domains: compatibility, how_to, template, debug."
        )

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(f"### Result {i}: {r.get('title', 'Untitled')}")
        lines.append(
            f"**Relevance:** {r.get('score', 0):.0%} | **Domain:** {r.get('domain', 'general')}"
        )
        content = r.get("content", "")
        lines.append(truncate_html(content, max_chars=800))
        lines.append("")

    return _apply_token_budget("\n".join(lines))


def format_css_compilation(result: dict[str, Any]) -> str:
    """Format CSS compilation results showing what changed and why."""
    lines: list[str] = []
    original_size = result.get("original_size", 0)
    compiled_size = result.get("compiled_size", 0)
    reduction = ((original_size - compiled_size) / original_size * 100) if original_size else 0

    lines.append(
        f"**CSS Compiled:** {original_size:,}B → {compiled_size:,}B ({reduction:.0f}% reduction)"
    )

    if conversions := result.get("conversions", []):
        lines.append(f"\n**{len(conversions)} CSS conversions applied** (unsupported → fallback):")
        for c in conversions[:10]:
            lines.append(
                f"  - `{c.get('from', '?')}` → `{c.get('to', '?')}` ({c.get('reason', '')})"
            )

    if removals := result.get("removed_properties", []):
        lines.append(f"\n**{len(removals)} properties removed** (no email client support):")
        for r in removals[:10]:
            lines.append(f"  - `{r}`")

    if compiled_html := result.get("compiled_html"):
        lines.append(f"\n**Compiled HTML** ({compiled_size:,} chars):")
        lines.append(truncate_html(compiled_html))

    return _apply_token_budget("\n".join(lines))


def format_simple_result(data: dict[str, Any] | list[Any] | str, label: str = "Result") -> str:
    """Generic formatter for simple results."""
    if isinstance(data, dict):
        lines = [f"**{label}:**"]
        for k, v in data.items():
            lines.append(f"  - **{k}:** {v}")
        return _apply_token_budget("\n".join(lines))
    if isinstance(data, list):
        lines = [f"**{label}:**"]
        for item in data:
            if isinstance(item, dict):
                parts = [f"{k}={v}" for k, v in item.items()]  # pyright: ignore[reportUnknownVariableType]
                lines.append(f"  - {', '.join(parts)}")
            else:
                lines.append(f"  - {item}")
        return _apply_token_budget("\n".join(lines))
    return _apply_token_budget(data)


def to_dict(obj: Any) -> dict[str, Any]:  # pyright: ignore[reportUnknownVariableType]
    """Convert dataclass/pydantic model to dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[no-any-return]
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(obj)  # pyright: ignore[reportUnknownVariableType]
    if isinstance(obj, dict):
        return obj  # pyright: ignore[reportUnknownVariableType]
    return {"result": str(obj)}


def _apply_token_budget(text: str) -> str:
    """Trim response to configured token budget (char approximation)."""
    max_chars = get_settings().mcp.max_response_tokens * 4  # ~4 chars per token
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...response truncated to fit token budget]"
