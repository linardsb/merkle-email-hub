# Plan: Phase 6.2 Response & Error Hardening

## Context

The OWASP API Security audit (2026-03-06) found three response-level vulnerabilities:

- **6.2.1 (HIGH)**: `POST /email/build` leaks raw exception messages (e.g., internal service URLs, HTTP status codes from sidecar)
- **6.2.2 (HIGH)**: LLM provider calls have no circuit breaker — cascading failures when provider is down; raw provider errors (API keys, rate limits, model details) leak in error messages
- **6.2.3 (MEDIUM)**: Global exception handler returns `"type": "BuildFailedError"` — leaks internal class hierarchy to clients

### Root Cause

Exception messages created with `str(exc)` or f-strings embedding raw errors are passed through exception handlers that return `{"error": str(exc), "type": type(exc).__name__}` verbatim to HTTP responses.

### Affected Files (Audit)

| File | Line | Issue |
|------|------|-------|
| `app/core/exceptions.py:83` | `"error": str(exc)` | Leaks raw message to client |
| `app/core/exceptions.py:84` | `"type": type(exc).__name__` | Leaks class name |
| `app/ai/exceptions.py:65-66` | Same pattern | Leaks AI provider details |
| `app/email_engine/service.py:64` | `build.error_message = str(exc)` | Stores raw error in DB |
| `app/email_engine/service.py:65` | `raise BuildFailedError(str(exc))` | Propagates raw error |
| `app/connectors/service.py:88-89` | Same pattern | Stores + propagates raw error |
| `app/ai/adapters/openai_compat.py:134` | `f"LLM API returned {status_code}: {detail}"` | HTTP response body in error |
| `app/ai/adapters/anthropic.py:125` | `f"Anthropic API error: {e.message}"` | Provider error in message |
| `app/ai/agents/scaffolder/service.py:78` | `f"Scaffolder generation failed: {e}"` | Raw exception in message |
| `app/ai/agents/dark_mode/service.py:109` | `f"Dark mode processing failed: {e}"` | Same pattern |
| `app/ai/agents/content/service.py:157` | `f"Content generation failed: {e}"` | Same pattern |
| `app/ai/service.py:91` | `f"Chat completion failed: {e}"` | Same pattern |
| `app/ai/blueprints/engine.py:96` | `BlueprintNodeError(name, str(exc))` | Raw error in node error |

## Files to Create/Modify

### New Files
- `app/core/error_sanitizer.py` — Centralized error message sanitization + safe message registry

### Modified Files
1. `app/core/exceptions.py` — Sanitize responses in global handler (6.2.3)
2. `app/ai/exceptions.py` — Sanitize responses in AI handler (6.2.2, 6.2.3)
3. `app/ai/adapters/openai_compat.py` — Generic error messages (6.2.2)
4. `app/ai/adapters/anthropic.py` — Generic error messages (6.2.2)
5. `app/ai/service.py` — Generic error messages (6.2.2)
6. `app/ai/agents/scaffolder/service.py` — Generic error messages (6.2.2)
7. `app/ai/agents/dark_mode/service.py` — Generic error messages (6.2.2)
8. `app/ai/agents/content/service.py` — Generic error messages (6.2.2)
9. `app/ai/blueprints/engine.py` — Generic error messages (6.2.2)
10. `app/email_engine/service.py` — Sanitize stored + raised errors (6.2.1)
11. `app/connectors/service.py` — Sanitize stored + raised errors (6.2.1)
12. `app/ai/registry.py` — Add circuit breaker to LLM provider calls (6.2.2)
13. `app/core/exceptions.py` — Tests
14. `app/tests/test_error_sanitizer.py` — Unit tests for sanitizer

### No Changes Needed
- `app/core/resilience.py` — CircuitBreaker already exists, reuse as-is
- `app/streaming/routes.py` — Already sends generic WsError messages (safe)
- `app/core/middleware.py` — Logs only, no response leaks (safe)

## Implementation Steps

### Step 1: Create `app/core/error_sanitizer.py`

Central module mapping exception types to safe client-facing messages. This is the **single source of truth** for what clients see.

```python
"""Error message sanitization for HTTP responses.

Maps internal exception types to safe, client-facing messages.
Internal details are logged server-side but never returned to clients.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)

# Maps exception class names to safe client-facing messages.
# Any exception not in this map gets the generic 500 message.
_SAFE_MESSAGES: dict[str, str] = {
    # Core errors — mapped by AppError subclass
    "NotFoundError": "Resource not found",
    "DomainValidationError": "Validation error",
    "ForbiddenError": "Access denied",
    "ConflictError": "Resource conflict",
    "ServiceUnavailableError": "Service temporarily unavailable",
    # Auth errors
    "InvalidCredentialsError": "Invalid email or password",
    "AccountLockedError": "Account is temporarily locked",
    # Email engine
    "BuildFailedError": "Email build failed",
    "BuildServiceUnavailableError": "Build service temporarily unavailable",
    # Connectors
    "ExportFailedError": "Export operation failed",
    "UnsupportedConnectorError": "Unsupported connector type",
    # AI errors
    "AIError": "AI service error",
    "AIConfigurationError": "AI service configuration error",
    "AIExecutionError": "AI request failed",
    # Blueprint errors
    "BlueprintError": "Blueprint execution failed",
    "BlueprintNodeError": "Blueprint step failed",
    "BlueprintEscalatedError": "Blueprint requires manual intervention",
    # Project access
    "ProjectAccessDeniedError": "Access denied",
    # Rendering
    "RenderingSubmitError": "Rendering test submission failed",
    "RenderingTestNotFoundError": "Rendering test not found",
    "RenderingProviderError": "Rendering provider error",
    # QA
    "QAOverrideNotFoundError": "QA result not found",
    # Knowledge
    "DuplicateTagError": "Tag already exists",
}

# Error types where the original message is safe to return
# (validation errors where the message IS the user-facing feedback)
_PASSTHROUGH_TYPES: set[str] = {
    "DomainValidationError",
    "UnsupportedConnectorError",
    "RenderingProviderError",
    "DuplicateTagError",
}


def get_safe_error_message(exc: Exception) -> str:
    """Get a sanitized, client-safe error message for an exception.

    Internal details are logged but never returned to the client.
    For validation-type errors where the message is user feedback,
    the original message is preserved.

    Args:
        exc: The exception to sanitize.

    Returns:
        A safe error message string.
    """
    exc_type = type(exc).__name__

    # Check MRO for passthrough types (allows subclass matching)
    for cls in type(exc).__mro__:
        if cls.__name__ in _PASSTHROUGH_TYPES:
            return str(exc)

    # Look up safe message by class name, walking MRO for inheritance
    for cls in type(exc).__mro__:
        if cls.__name__ in _SAFE_MESSAGES:
            return _SAFE_MESSAGES[cls.__name__]

    # Fallback — generic message, log the unmapped type
    logger.warning(
        "error_sanitizer.unmapped_exception",
        exception_type=exc_type,
    )
    return "An unexpected error occurred"


def get_safe_error_type(exc: Exception) -> str:
    """Get a sanitized error type for the response.

    Returns a generic category instead of the internal class name.

    Args:
        exc: The exception to categorize.

    Returns:
        A safe error type string.
    """
    from app.core.exceptions import (
        ConflictError,
        DomainValidationError,
        ForbiddenError,
        NotFoundError,
        ServiceUnavailableError,
    )

    if isinstance(exc, NotFoundError):
        return "not_found"
    if isinstance(exc, DomainValidationError):
        return "validation_error"
    if isinstance(exc, ForbiddenError):
        return "forbidden"
    if isinstance(exc, ConflictError):
        return "conflict"
    if isinstance(exc, ServiceUnavailableError):
        return "service_unavailable"

    # AI errors — check by module to avoid circular imports
    exc_module = type(exc).__module__ or ""
    if "ai" in exc_module or "blueprint" in exc_module:
        return "ai_error"

    return "server_error"
```

### Step 2: Update `app/core/exceptions.py` — Sanitize Global Handler (6.2.3)

Replace raw `str(exc)` and `type(exc).__name__` with sanitized versions.

**In `app_exception_handler` (line ~80-86):**

```python
async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application exceptions globally."""
    from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type

    logger.error(
        "app.error",
        extra={
            "error_type": type(exc).__name__,       # Internal — log only
            "error_message": str(exc),               # Internal — log only
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, DomainValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(exc, ForbiddenError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ServiceUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "error": get_safe_error_message(exc),
            "type": get_safe_error_type(exc),
        },
    )
```

**Auth handlers stay as-is** — they already use generic messages.

### Step 3: Update `app/ai/exceptions.py` — Sanitize AI Handler (6.2.2, 6.2.3)

Same pattern — replace raw `str(exc)` with sanitized message.

**In `ai_exception_handler` (line ~62-68):**

```python
async def ai_exception_handler(request: Request, exc: AIError) -> JSONResponse:
    from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type

    logger.error(
        "ai.error",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, AIExecutionError):
        status_code = status.HTTP_502_BAD_GATEWAY

    return JSONResponse(
        status_code=status_code,
        content={
            "error": get_safe_error_message(exc),
            "type": get_safe_error_type(exc),
        },
    )
```

### Step 4: Sanitize LLM Adapter Error Messages (6.2.2)

The adapter errors are the **source** of leaked details. Even though the exception handlers now sanitize responses, we should also clean up the source to prevent accidental re-use of these messages elsewhere.

**`app/ai/adapters/openai_compat.py` — 4 changes:**

| Line | Before | After |
|------|--------|-------|
| 128-130 | `msg = f"LLM API request timed out after {_REQUEST_TIMEOUT}s"` | Keep (safe — no external data) |
| 131-141 | `msg = f"LLM API returned {status_code}: {detail}"` | `msg = "LLM API request failed"` |
| 142-145 | `msg = f"LLM API request failed: {e}"` | `msg = "LLM API request failed"` |
| 233-243 | `msg = f"LLM streaming request failed: {e}"` | `msg = "LLM streaming request failed"` |

Keep the `detail` in the logger call (line 139) — that's server-side only. Remove it from `msg`.

**`app/ai/adapters/anthropic.py` — 3 changes:**

| Line | Before | After |
|------|--------|-------|
| 121 | `msg = "Anthropic API authentication failed — check AI__API_KEY"` | `msg = "AI provider authentication failed"` |
| 125 | `msg = f"Anthropic API error: {e.message}"` | `msg = "AI provider request failed"` |
| 210 | `msg = f"Anthropic streaming error: {e.message}"` | `msg = "AI provider streaming failed"` |

### Step 5: Sanitize Agent Service Error Messages (6.2.2)

All agent services use `f"Agent failed: {e}"` which embeds raw exceptions.

**Pattern to apply in all 3 agent services + AI chat service:**

```python
# BEFORE (scaffolder/service.py:78)
raise AIExecutionError(f"Scaffolder generation failed: {e}") from e

# AFTER
raise AIExecutionError("Scaffolder generation failed") from e
```

**Files and lines to change:**

| File | Line | Before | After |
|------|------|--------|-------|
| `app/ai/agents/scaffolder/service.py` | 78 | `f"Scaffolder generation failed: {e}"` | `"Scaffolder generation failed"` |
| `app/ai/agents/scaffolder/service.py` | 178 | `f"Scaffolder streaming failed: {e}"` | `"Scaffolder streaming failed"` |
| `app/ai/agents/dark_mode/service.py` | 109 | `f"Dark mode processing failed: {e}"` | `"Dark mode processing failed"` |
| `app/ai/agents/dark_mode/service.py` | 220 | `f"Dark mode streaming failed: {e}"` | `"Dark mode streaming failed"` |
| `app/ai/agents/content/service.py` | 157 | `f"Content generation failed: {e}"` | `"Content generation failed"` |
| `app/ai/agents/content/service.py` | 231 | `f"Content streaming failed: {e}"` | `"Content streaming failed"` |
| `app/ai/service.py` | 91 | `f"Chat completion failed: {e}"` | `"Chat completion failed"` |
| `app/ai/service.py` | 192 | `f"Chat streaming failed: {e}"` | `"Chat streaming failed"` |

### Step 6: Sanitize Blueprint Engine Error (6.2.2)

**`app/ai/blueprints/engine.py:96`:**

```python
# BEFORE
raise BlueprintNodeError(current_node_name, str(exc)) from exc

# AFTER — use generic reason, log the real error
logger.error(
    "blueprints.node_failed",
    node=current_node_name,
    error=str(exc),
    error_type=type(exc).__name__,
)
raise BlueprintNodeError(current_node_name, "execution failed") from exc
```

### Step 7: Sanitize Email Engine Error Storage + Raise (6.2.1)

**`app/email_engine/service.py:62-65`:**

```python
# BEFORE
except Exception as exc:
    build.status = "failed"
    build.error_message = str(exc)
    raise BuildFailedError(str(exc)) from exc

# AFTER
except Exception as exc:
    build.status = "failed"
    build.error_message = "Build failed"  # Safe for DB/API exposure
    logger.error(
        "email_engine.build_error",
        build_id=build.id,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )
    raise BuildFailedError("Email build failed") from exc
```

### Step 8: Sanitize Connector Error Storage + Raise (6.2.1)

**`app/connectors/service.py:86-89`:**

```python
# BEFORE
except Exception as exc:
    record.status = "failed"
    record.error_message = str(exc)
    raise ExportFailedError(str(exc)) from exc

# AFTER
except Exception as exc:
    record.status = "failed"
    record.error_message = "Export failed"  # Safe for DB/API exposure
    logger.error(
        "connectors.export_error",
        record_id=record.id,
        connector=data.connector_type,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )
    raise ExportFailedError("Export operation failed") from exc
```

### Step 9: Add LLM Circuit Breaker (6.2.2)

Add a circuit breaker around LLM provider calls in the registry layer so all callers benefit.

**`app/ai/registry.py` — wrap `get_llm` return with circuit breaker:**

Read the file first to determine exact insertion point. The approach:

1. Import `CircuitBreaker` from `app.core.resilience`
2. Create a module-level breaker: `_llm_breaker = CircuitBreaker(name="llm-provider", failure_threshold=5, reset_timeout=60.0)`
3. The circuit breaker is already used via `async with breaker:` context manager in the rendering module. The same pattern applies here, but since the registry returns a provider object (not a single call), the breaker should wrap the actual `complete()` and `stream()` calls.

**Better approach**: Create a `ResilientLLMProvider` wrapper class in `app/ai/registry.py`:

```python
class ResilientLLMProvider:
    """Wraps an LLM provider with circuit breaker protection."""

    def __init__(self, provider: LLMProvider, breaker: CircuitBreaker) -> None:
        self._provider = provider
        self._breaker = breaker

    async def complete(self, messages: list[Message], **kwargs: object) -> CompletionResponse:
        async with self._breaker:
            return await self._provider.complete(messages, **kwargs)

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[str]:
        # Circuit breaker checks on entry only (can't wrap async generator)
        async with self._breaker:
            # Must consume inside breaker context for failure tracking
            pass  # Breaker validates circuit state
        async for chunk in self._provider.stream(messages, **kwargs):
            yield chunk
```

**Note**: The streaming case is tricky — the circuit breaker uses `async with` but generators can't be fully wrapped. Two options:
- **Option A**: Only check circuit state on entry (breaker `__aenter__` + immediate `__aexit__` with no error). Failures during streaming won't trip the breaker but initial connection failures will.
- **Option B**: Wrap `stream()` to collect the first chunk inside the breaker context, then yield remaining chunks outside.

**Decision**: Use Option A — it's simpler and catches the common failure (provider down). Streaming mid-stream failures are rare and logged separately.

Actually, the simplest correct approach: don't wrap `stream()` in circuit breaker at all — only wrap `complete()`. Streaming already has its own error handling and is used for real-time UI where circuit breaker semantics (fail fast) are less useful.

```python
from app.core.resilience import CircuitBreaker

_llm_breaker = CircuitBreaker(name="llm-provider", failure_threshold=5, reset_timeout=60.0)


def get_llm(self, provider_name: str) -> LLMProvider:
    """Get LLM provider, wrapped with circuit breaker."""
    provider = self._resolve_provider(provider_name)
    return _ResilientLLMProvider(provider, _llm_breaker)
```

**Important**: Read `app/ai/registry.py` during implementation to understand the exact structure before applying. The wrapper must conform to `LLMProvider` protocol.

### Step 10: Write Tests

**`app/tests/test_error_sanitizer.py`:**

```python
"""Tests for error message sanitization."""

import pytest

from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type
from app.core.exceptions import (
    AppError,
    ConflictError,
    DomainValidationError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)


class TestGetSafeErrorMessage:
    """Verify internal details are never returned to clients."""

    def test_not_found_returns_generic(self) -> None:
        exc = NotFoundError("User id=42 in org_id=7 not found")
        assert get_safe_error_message(exc) == "Resource not found"

    def test_forbidden_returns_generic(self) -> None:
        exc = ForbiddenError("User 5 not member of project 12")
        assert get_safe_error_message(exc) == "Access denied"

    def test_service_unavailable_returns_generic(self) -> None:
        exc = ServiceUnavailableError("Cannot connect to postgres://prod-db:5432")
        assert get_safe_error_message(exc) == "Service temporarily unavailable"

    def test_validation_error_passes_through(self) -> None:
        exc = DomainValidationError("Name must be at least 3 characters")
        assert get_safe_error_message(exc) == "Name must be at least 3 characters"

    def test_unknown_exception_returns_generic(self) -> None:
        exc = RuntimeError("segfault at 0xDEADBEEF")
        assert get_safe_error_message(exc) == "An unexpected error occurred"

    def test_app_error_base_returns_generic(self) -> None:
        exc = AppError("Internal: pool_size=10 exceeded")
        assert "pool_size" not in get_safe_error_message(exc)

    def test_ai_execution_error_hides_provider_details(self) -> None:
        from app.ai.exceptions import AIExecutionError
        exc = AIExecutionError("Anthropic rate limit: 429 Too Many Requests")
        assert "Anthropic" not in get_safe_error_message(exc)
        assert "429" not in get_safe_error_message(exc)

    def test_build_failed_hides_sidecar_url(self) -> None:
        from app.email_engine.exceptions import BuildFailedError
        exc = BuildFailedError("Cannot connect to http://maizzle-builder:3001")
        assert "maizzle-builder" not in get_safe_error_message(exc)
        assert "3001" not in get_safe_error_message(exc)


class TestGetSafeErrorType:
    """Verify internal class names are never returned."""

    def test_not_found(self) -> None:
        assert get_safe_error_type(NotFoundError("x")) == "not_found"

    def test_validation(self) -> None:
        assert get_safe_error_type(DomainValidationError("x")) == "validation_error"

    def test_forbidden(self) -> None:
        assert get_safe_error_type(ForbiddenError("x")) == "forbidden"

    def test_conflict(self) -> None:
        assert get_safe_error_type(ConflictError("x")) == "conflict"

    def test_service_unavailable(self) -> None:
        assert get_safe_error_type(ServiceUnavailableError("x")) == "service_unavailable"

    def test_unknown_returns_server_error(self) -> None:
        assert get_safe_error_type(RuntimeError("x")) == "server_error"

    def test_ai_error_returns_ai_error(self) -> None:
        from app.ai.exceptions import AIExecutionError
        assert get_safe_error_type(AIExecutionError("x")) == "ai_error"
```

## Verification

- [ ] `make lint` passes (ruff format + lint)
- [ ] `make types` passes (mypy + pyright)
- [ ] `make test` passes (all 346+ existing tests + new sanitizer tests)
- [ ] Manual verification: raise a `BuildFailedError("secret internal url")` and confirm HTTP response shows `"Email build failed"` not the internal URL
- [ ] Grep for `str(exc)` in exception handlers — should only appear in `logger.error()` calls, never in `JSONResponse` content
- [ ] Grep for `"type": type(exc).__name__` — should be zero occurrences in response bodies

## Implementation Order

1. `app/core/error_sanitizer.py` (new) — foundation
2. `app/core/exceptions.py` — global handler sanitization
3. `app/ai/exceptions.py` — AI handler sanitization
4. `app/ai/adapters/anthropic.py` — provider error cleanup
5. `app/ai/adapters/openai_compat.py` — provider error cleanup
6. `app/ai/service.py` — chat error cleanup
7. `app/ai/agents/scaffolder/service.py` — agent error cleanup
8. `app/ai/agents/dark_mode/service.py` — agent error cleanup
9. `app/ai/agents/content/service.py` — agent error cleanup
10. `app/ai/blueprints/engine.py` — blueprint error cleanup
11. `app/email_engine/service.py` — build error cleanup
12. `app/connectors/service.py` — export error cleanup
13. `app/ai/registry.py` — LLM circuit breaker wrapper
14. `app/tests/test_error_sanitizer.py` — tests
15. Run `make check` — full validation

## Risk Assessment

- **Low risk**: Exception handler changes are additive (log same details, return less). No business logic changes.
- **Medium risk**: LLM circuit breaker wrapper must conform to `LLMProvider` protocol exactly. Read `app/ai/registry.py` and `app/ai/protocols.py` during implementation.
- **Test impact**: Existing tests that assert on exact error messages in responses will need updating (e.g., `app/ai/blueprints/tests/test_engine.py:395` matches `"crasher.*Something went wrong"` — this will now be `"execution failed"`).
