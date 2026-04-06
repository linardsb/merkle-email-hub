"""Shared test fixtures for Evaluator agent tests."""

import json
from unittest.mock import AsyncMock

import pytest

from app.ai.protocols import CompletionResponse


@pytest.fixture
def accept_verdict_json() -> str:
    """LLM response JSON for an accept verdict."""
    return json.dumps(
        {
            "verdict": "accept",
            "score": 0.92,
            "issues": [],
            "feedback": "Output meets all quality criteria",
            "suggested_corrections": [],
        }
    )


@pytest.fixture
def revise_verdict_json() -> str:
    """LLM response JSON for a revise verdict with issues."""
    return json.dumps(
        {
            "verdict": "revise",
            "score": 0.55,
            "issues": [
                {
                    "severity": "major",
                    "category": "layout",
                    "description": "Hero section uses div instead of table layout",
                    "location": "section.hero",
                },
                {
                    "severity": "minor",
                    "category": "accessibility",
                    "description": "Missing alt text on decorative image",
                    "location": "img.logo",
                },
            ],
            "feedback": "Layout structure needs table-based correction",
            "suggested_corrections": [
                "Replace div-based hero with table/tr/td",
                "Add alt='' to decorative images",
            ],
        }
    )


@pytest.fixture
def reject_verdict_json() -> str:
    """LLM response JSON for a reject verdict."""
    return json.dumps(
        {
            "verdict": "reject",
            "score": 0.15,
            "issues": [
                {
                    "severity": "critical",
                    "category": "structure",
                    "description": "Output is not valid HTML — missing doctype and head",
                },
            ],
            "feedback": "Fundamental structural failures prevent revision",
            "suggested_corrections": [],
        }
    )


@pytest.fixture
def mock_eval_provider(accept_verdict_json: str) -> AsyncMock:
    """Mock LLM provider returning an accept verdict."""
    provider = AsyncMock()
    provider.complete.return_value = CompletionResponse(
        content=f"```json\n{accept_verdict_json}\n```",
        model="test-eval-model",
        usage={"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
    )
    return provider


@pytest.fixture
def sample_brief() -> str:
    """Sample campaign brief for testing."""
    return "Create a promotional email for a summer sale with hero image, 3 product cards, and CTA button."


@pytest.fixture
def sample_agent_output() -> str:
    """Sample agent HTML output for testing."""
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Summer Sale</title></head>
<body>
<table role="presentation" width="600">
<tr><td style="font-family:Arial,sans-serif;font-size:24px;font-weight:bold;color:#333;">Summer Sale</td></tr>
<tr><td><img src="https://example.com/hero.png" alt="Summer sale hero" width="600"></td></tr>
<tr><td><a href="https://example.com/shop">Shop Now</a></td></tr>
</table>
</body>
</html>"""
