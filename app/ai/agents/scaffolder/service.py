# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false
"""Scaffolder agent service — orchestrates LLM → extract → sanitize → QA."""

import json
import re
import time
import uuid
from collections.abc import AsyncIterator

from app.ai.agents.scaffolder.prompt import SCAFFOLDER_SYSTEM_PROMPT
from app.ai.agents.scaffolder.schemas import ScaffolderRequest, ScaffolderResponse
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

# ── Regex patterns for HTML extraction and XSS sanitization ──

_CODE_BLOCK_RE = re.compile(
    r"```(?:html|HTML)?\s*\n(.*?)```",
    re.DOTALL,
)

_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_EVENT_HANDLER_RE = re.compile(r"""\s+on\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)""", re.IGNORECASE)
_JS_PROTOCOL_RE = re.compile(r"""(href|src)\s*=\s*["']?\s*javascript:""", re.IGNORECASE)
_DANGEROUS_TAG_RE = re.compile(
    r"<(iframe|embed|object|form)\b[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_DANGEROUS_SELF_CLOSING_RE = re.compile(
    r"<(iframe|embed|object)\b[^>]*/?>",
    re.IGNORECASE,
)
_DATA_URI_RE = re.compile(r"""(href|src)\s*=\s*["']?\s*data:""", re.IGNORECASE)


def extract_html(content: str) -> str:
    """Extract HTML from markdown code blocks.

    Looks for ```html ... ``` blocks. Falls back to raw content
    if no code block is found.

    Args:
        content: Raw LLM response text.

    Returns:
        Extracted HTML string.
    """
    match = _CODE_BLOCK_RE.search(content)
    if match:
        return match.group(1).strip()
    return content.strip()


def sanitize_html_xss(html: str) -> str:
    """Strip XSS vectors from generated HTML.

    Removes script tags, event handlers, javascript: protocol,
    dangerous tags (iframe, embed, object, form), and data: URIs.
    Preserves MSO conditional comments needed for Outlook rendering.

    Args:
        html: HTML string to sanitize.

    Returns:
        Sanitized HTML string.
    """
    result = html

    # Remove <script> tags and their content
    result = _SCRIPT_TAG_RE.sub("", result)

    # Remove event handlers (onclick, onload, etc.)
    result = _EVENT_HANDLER_RE.sub("", result)

    # Remove javascript: protocol
    result = _JS_PROTOCOL_RE.sub(r'\1=""', result)

    # Remove dangerous tags with content
    result = _DANGEROUS_TAG_RE.sub("", result)

    # Remove self-closing dangerous tags
    result = _DANGEROUS_SELF_CLOSING_RE.sub("", result)

    # Remove data: URIs
    result = _DATA_URI_RE.sub(r'\1=""', result)

    return result


class ScaffolderService:
    """Orchestrates the scaffolder agent pipeline.

    Pipeline: build messages → LLM call → validate output →
    extract HTML → XSS sanitize → optional QA checks.
    """

    async def generate(self, request: ScaffolderRequest) -> ScaffolderResponse:
        """Generate email HTML from a campaign brief (non-streaming).

        Args:
            request: The scaffolder request with brief and options.

        Returns:
            ScaffolderResponse with generated HTML and optional QA results.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("complex")
        model_id = f"{provider_name}:{model}"

        # Build messages with system prompt and sanitized brief
        messages = [
            Message(role="system", content=SCAFFOLDER_SYSTEM_PROMPT),
            Message(role="user", content=sanitize_prompt(request.brief)),
        ]

        logger.info(
            "agents.scaffolder.generate_started",
            provider=provider_name,
            model=model,
            brief_length=len(request.brief),
            run_qa=request.run_qa,
        )

        # Resolve provider and call LLM
        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            result = await provider.complete(messages, model_override=model, max_tokens=8192)
        except Exception as e:
            logger.error(
                "agents.scaffolder.generate_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"Scaffolder generation failed: {e}") from e

        # Process output: validate → extract → XSS sanitize
        raw_content = validate_output(result.content)
        html = extract_html(raw_content)
        html = sanitize_html_xss(html)

        logger.info(
            "agents.scaffolder.generate_completed",
            model=model_id,
            html_length=len(html),
            usage=result.usage,
        )

        # Optional QA checks (in-memory, not persisted)
        qa_results: list[QACheckResult] | None = None
        qa_passed: bool | None = None

        if request.run_qa:
            qa_results = []
            for check in ALL_CHECKS:
                check_result = await check.run(html)
                qa_results.append(check_result)
            qa_passed = all(r.passed for r in qa_results)

            logger.info(
                "agents.scaffolder.qa_completed",
                qa_passed=qa_passed,
                checks_passed=sum(1 for r in qa_results if r.passed),
                checks_total=len(qa_results),
            )

        return ScaffolderResponse(
            html=html,
            qa_results=qa_results,
            qa_passed=qa_passed,
            model=model_id,
        )

    async def stream_generate(self, request: ScaffolderRequest) -> AsyncIterator[str]:
        """Stream email HTML generation as SSE-formatted chunks.

        QA is skipped in streaming mode (requires complete HTML).

        Args:
            request: The scaffolder request with brief.

        Yields:
            SSE-formatted data strings.

        Raises:
            AIExecutionError: If the LLM provider fails.
        """
        settings = get_settings()
        provider_name = settings.ai.provider
        model = resolve_model("complex")
        model_id = f"{provider_name}:{model}"
        response_id = f"scaffold-{uuid.uuid4().hex[:12]}"

        messages = [
            Message(role="system", content=SCAFFOLDER_SYSTEM_PROMPT),
            Message(role="user", content=sanitize_prompt(request.brief)),
        ]

        logger.info(
            "agents.scaffolder.stream_started",
            provider=provider_name,
            model=model,
            brief_length=len(request.brief),
        )

        registry = get_registry()
        provider = registry.get_llm(provider_name)

        try:
            async for chunk in provider.stream(messages, model_override=model, max_tokens=8192):  # type: ignore[attr-defined]
                sse_data = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(sse_data)}\n\n"

        except Exception as e:
            logger.error(
                "agents.scaffolder.stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                provider=provider_name,
            )
            if isinstance(e, AIExecutionError):
                raise
            raise AIExecutionError(f"Scaffolder streaming failed: {e}") from e

        yield "data: [DONE]\n\n"

        logger.info(
            "agents.scaffolder.stream_completed",
            response_id=response_id,
            provider=provider_name,
        )


# ── Module-level singleton ──

_scaffolder_service: ScaffolderService | None = None


def get_scaffolder_service() -> ScaffolderService:
    """Get or create the scaffolder service singleton.

    Returns:
        Singleton ScaffolderService instance.
    """
    global _scaffolder_service
    if _scaffolder_service is None:
        _scaffolder_service = ScaffolderService()
    return _scaffolder_service
