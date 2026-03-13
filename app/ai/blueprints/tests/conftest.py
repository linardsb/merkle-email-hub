"""Shared test fixtures for blueprint tests."""

from unittest.mock import AsyncMock

import pytest

from app.ai.protocols import CompletionResponse


@pytest.fixture
def sample_html_valid() -> str:
    """Minimal valid email HTML that passes all 10 QA checks."""
    return """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test Email</title>
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<style>
:root { color-scheme: light dark; }
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a1a !important; }
  .dark-text { color: #e0e0e0 !important; }
}
[data-ogsc] .dark-text { color: #e0e0e0; }
[data-ogsb] .dark-bg { background-color: #1a1a1a; }
</style>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body>
<table role="presentation" width="600">
<tr><td><h1>Welcome</h1></td></tr>
<tr><td><img src="https://example.com/hero.png" alt="Hero image" width="600" height="300"></td></tr>
<tr><td><a href="https://example.com">Visit us</a></td></tr>
</table>
</body>
</html>"""


@pytest.fixture
def sample_html_minimal() -> str:
    """Bare-bones HTML that fails most QA checks."""
    return "<html><body><p>Hello</p></body></html>"


@pytest.fixture
def mock_provider() -> AsyncMock:
    """Mock LLM provider returning valid HTML in a code block."""
    provider = AsyncMock()
    provider.complete.return_value = CompletionResponse(
        content=(
            "```html\n"
            '<!DOCTYPE html><html lang="en"><head>'
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Test Email</title>"
            '<meta name="color-scheme" content="light dark">'
            "</head><body>"
            '<table role="presentation"><tr><td>Generated</td></tr></table>'
            "</body></html>\n"
            "```"
        ),
        model="test-model",
        usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    )
    return provider
