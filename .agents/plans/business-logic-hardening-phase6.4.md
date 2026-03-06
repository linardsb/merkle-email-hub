# Plan: Phase 6.4 — Business Logic Hardening

## Context
Three MEDIUM-severity OWASP findings from security audit. Phase 6.1-6.3 complete.
Tasks: approval state machine (6.4.1), JWT algorithm pinning (6.4.2), LLM output sanitizer (6.4.3).

## Files to Create/Modify

### 6.4.1 — Approval State Machine
- `app/approval/schemas.py` — Add `ApprovalStatus` Literal type, replace regex pattern
- `app/approval/exceptions.py` — Add `InvalidStateTransitionError`
- `app/approval/service.py` — Add transition validation in `decide()`
- `app/tests/test_approval_state_machine.py` — **CREATE** — State machine tests

### 6.4.2 — JWT Algorithm Pinning
- `app/auth/token.py` — Pin algorithm to `HS256` constant, ignore config override
- `app/core/config.py` — Remove `jwt_algorithm` from `AuthConfig` (dead config)
- `app/tests/test_jwt_algorithm.py` — **CREATE** — Algorithm pinning tests

### 6.4.3 — LLM Output Sanitizer
- `pyproject.toml` — Add `nh3>=0.2.18` dependency
- `app/ai/shared.py` — Replace regex sanitizer with `nh3`-based implementation
- `app/ai/agents/tests/test_dark_mode.py` — Update existing XSS tests for new sanitizer behaviour
- `app/tests/test_llm_sanitizer.py` — **CREATE** — Extended XSS vector tests

---

## Implementation Steps

### 6.4.1 — Approval State Machine

**Step 1: Define status type and transitions in `app/approval/schemas.py`**

Add at top of file after imports:

```python
from typing import Literal

ApprovalStatus = Literal["pending", "approved", "rejected", "revision_requested"]

# Valid transitions: current_status -> set of allowed target statuses
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected", "revision_requested"},
    "revision_requested": {"approved", "rejected", "pending"},
    # Terminal states — no outgoing transitions
    "approved": set(),
    "rejected": set(),
}
```

Update `ApprovalDecision`:
```python
class ApprovalDecision(BaseModel):
    status: ApprovalStatus  # replaces str + regex pattern
    review_note: str | None = None
```

**Step 2: Add exception in `app/approval/exceptions.py`**

```python
from app.core.exceptions import DomainValidationError, NotFoundError

class ApprovalNotFoundError(NotFoundError):
    """Raised when an approval request is not found."""

class InvalidStateTransitionError(DomainValidationError):
    """Raised when an approval state transition is invalid."""
```

Using `DomainValidationError` maps to 422 (business rule violation), not 400.

**Step 3: Add validation in `app/approval/service.py` `decide()` method**

```python
from app.approval.exceptions import ApprovalNotFoundError, InvalidStateTransitionError
from app.approval.schemas import VALID_TRANSITIONS

async def decide(
    self, approval_id: int, decision: ApprovalDecision, user: User
) -> ApprovalResponse:
    approval = await self._verify_approval_access(approval_id, user)
    allowed = VALID_TRANSITIONS.get(approval.status, set())
    if decision.status not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot transition from '{approval.status}' to '{decision.status}'"
        )
    approval = await self.repository.update_status(
        approval, decision.status, user.id, decision.review_note
    )
    await self.repository.add_audit(approval_id, decision.status, user.id, decision.review_note)
    logger.info("approval.decided", approval_id=approval_id, status=decision.status)
    return ApprovalResponse.model_validate(approval)
```

**Step 4: Create tests `app/tests/test_approval_state_machine.py`**

Test cases:
1. `pending → approved` — allowed
2. `pending → rejected` — allowed
3. `pending → revision_requested` — allowed
4. `revision_requested → approved` — allowed
5. `revision_requested → rejected` — allowed
6. `revision_requested → pending` — allowed (resubmit)
7. `approved → rejected` — raises `InvalidStateTransitionError` (422)
8. `approved → approved` — raises `InvalidStateTransitionError` (422)
9. `rejected → approved` — raises `InvalidStateTransitionError` (422)
10. `rejected → revision_requested` — raises `InvalidStateTransitionError` (422)

Use `AsyncMock` for DB session, mock repository to return an `ApprovalRequest` with preset `status`. Verify `decide()` raises on invalid transitions before touching the repository.

---

### 6.4.2 — JWT Algorithm Pinning

**Context:** The codebase uses `python-jose[cryptography]` with HS256. Docs reference RS256 but no RSA key infrastructure exists. The pragmatic fix is to **pin HS256 as a hardcoded constant** and remove the configurable `jwt_algorithm` setting that could be manipulated.

The `algorithms=` parameter in `jwt.decode()` is already set (good), but the algorithm value comes from config which an attacker with env access could change to `"none"`.

**Step 1: Pin algorithm in `app/auth/token.py`**

Replace all `settings.auth.jwt_algorithm` references with a module-level constant:

```python
# Pinned algorithm — never read from config to prevent algorithm confusion attacks.
# HS256 (HMAC-SHA256) with a strong secret is sufficient for single-service JWT.
_JWT_ALGORITHM: str = "HS256"
```

Update three locations:
- Line 49: `algorithm=_JWT_ALGORITHM`
- Line 75: `algorithm=_JWT_ALGORITHM`
- Line 141: `algorithms=[_JWT_ALGORITHM]`

Remove `settings.auth.jwt_algorithm` usage entirely from this file.

**Step 2: Remove `jwt_algorithm` from `app/core/config.py` `AuthConfig`**

Delete line 32: `jwt_algorithm: str = "HS256"` from `AuthConfig`.

**Step 3: Update documentation references**

In project CLAUDE.md, the security section says "JWT RS256". Update to "JWT HS256" to match reality. The docs-say-RS256 inconsistency IS task 6.4.2.

Lines to update in `/Users/Berzins/Desktop/merkle-email-hub/CLAUDE.md`:
- "JWT RS256" → "JWT HS256" (search for all occurrences)

**Step 4: Create tests `app/tests/test_jwt_algorithm.py`**

Test cases:
1. `create_access_token` produces a token decodable with HS256
2. `decode_token` rejects a token encoded with HS384 (wrong algorithm)
3. `decode_token` rejects a token with `alg: "none"` header
4. `_JWT_ALGORITHM` constant equals `"HS256"` (regression guard)

---

### 6.4.3 — LLM Output Sanitizer

**Context:** Current `sanitize_html_xss()` in `app/ai/shared.py` uses 6 regex patterns. Regex-based HTML sanitization is fragile against obfuscation (encoded entities, nested tags, SVG-based XSS). The fix is to use `nh3` — a Rust-based HTML sanitizer (successor to `bleach`, which is deprecated).

**Why `nh3` over `bleach`:**
- `bleach` is deprecated (EOL since Jan 2023)
- `nh3` is a Python binding to `ammonia` (Rust), fastest HTML sanitizer
- Zero Python dependencies, battle-tested
- Allowlist-based (safe by default) vs denylist (regex approach)

**Email HTML consideration:** Email templates use `<table>`, `<td>`, `<style>`, MSO conditional comments, VML. The sanitizer must preserve these while stripping XSS.

**Step 1: Add dependency to `pyproject.toml`**

Add `"nh3>=0.2.18"` to `dependencies` list.

**Step 2: Replace `sanitize_html_xss()` in `app/ai/shared.py`**

```python
import nh3

# Tags allowed in email HTML output — covers standard email + Outlook/MSO
_ALLOWED_TAGS: set[str] = {
    # Structure
    "html", "head", "body", "meta", "title", "link",
    # Layout
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup", "col",
    "div", "span", "p", "br", "hr", "center",
    # Text
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "strike", "sub", "sup", "small", "big",
    "blockquote", "pre", "code",
    # Lists
    "ul", "ol", "li", "dl", "dt", "dd",
    # Media
    "img", "picture", "source", "video",
    # Links
    "a",
    # Style
    "style",
    # Accessibility
    "abbr", "address", "cite",
}

_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"class", "id", "style", "dir", "lang", "role", "aria-label", "aria-hidden",
          "aria-describedby", "aria-labelledby", "title", "align", "valign", "width",
          "height", "bgcolor", "background", "border", "cellpadding", "cellspacing"},
    "a": {"href", "target", "rel", "name"},
    "img": {"src", "alt", "loading", "srcset"},
    "td": {"colspan", "rowspan", "scope"},
    "th": {"colspan", "rowspan", "scope"},
    "meta": {"charset", "name", "content", "http-equiv"},
    "link": {"rel", "href", "type", "media"},
    "source": {"srcset", "media", "type"},
    "col": {"span"},
    "colgroup": {"span"},
}

# URL schemes allowed in href/src attributes
_ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "tel"}


def sanitize_html_xss(html: str) -> str:
    """Strip XSS vectors from generated HTML using allowlist-based sanitization.

    Uses nh3 (Rust-based HTML sanitizer) for robust protection against:
    - Script injection (tags, event handlers, javascript: protocol)
    - Dangerous tags (iframe, embed, object, form, svg with scripts)
    - Data URI attacks
    - Encoded/obfuscated XSS vectors

    Preserves email-safe HTML: tables, inline styles, MSO comments, dark mode CSS.

    Args:
        html: HTML string to sanitize.

    Returns:
        Sanitized HTML string.
    """
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel=None,  # Don't force rel attributes on links
        strip_comments=False,  # Preserve MSO conditional comments
    )
```

Remove the 6 compiled regex patterns (`_SCRIPT_TAG_RE`, `_EVENT_HANDLER_RE`, `_JS_PROTOCOL_RE`, `_DANGEROUS_TAG_RE`, `_DANGEROUS_SELF_CLOSING_RE`, `_DATA_URI_RE`) — they're no longer needed.

Keep `extract_html()` and `_CODE_BLOCK_RE` unchanged.

**Step 3: Update existing tests in `app/ai/agents/tests/test_dark_mode.py`**

The existing XSS tests check that dangerous content is removed. With `nh3`, the output format may differ slightly (e.g., tags stripped entirely vs replaced with empty string). Update assertions to match `nh3` output:
- `nh3` strips disallowed tags AND their content (for `<script>`, `<iframe>` etc.)
- `nh3` strips disallowed attributes (event handlers removed from tags)
- `nh3` strips disallowed URL schemes (javascript:, data: in href/src)
- MSO comments should still be preserved (`strip_comments=False`)

**Step 4: Create extended tests `app/tests/test_llm_sanitizer.py`**

Test cases covering vectors that regex missed:
1. Basic script tag removal: `<script>alert(1)</script>` → empty
2. Mixed-case tags: `<ScRiPt>alert(1)</ScRiPt>` → empty
3. Event handlers: `<div onclick="alert(1)">text</div>` → `<div>text</div>`
4. JavaScript protocol: `<a href="javascript:alert(1)">click</a>` → `<a>click</a>` (href stripped)
5. Data URI: `<img src="data:text/html,<script>alert(1)</script>">` → `<img>` (src stripped)
6. SVG XSS: `<svg onload="alert(1)">` → stripped (svg not in allowed tags)
7. Nested script: `<div><script>nested</script></div>` → `<div></div>`
8. Encoded entities in tags: Test that `nh3` handles HTML entity encoding
9. Iframe removal: `<iframe src="evil.com"></iframe>` → empty
10. **Preserves email HTML**: `<table><tr><td style="color:red">Hi</td></tr></table>` → unchanged
11. **Preserves inline styles**: `<div style="background-color:#000">` → preserved
12. **Preserves MSO comments**: `<!--[if mso]><v:rect><![endif]-->` → preserved
13. **Preserves dark mode CSS**: `<style>@media (prefers-color-scheme:dark){}</style>` → preserved
14. **Preserves links**: `<a href="https://example.com">link</a>` → preserved
15. **Strips form tags**: `<form action="/steal"><input></form>` → stripped

**Step 5: Install dependency and verify**

```bash
uv add nh3
```

---

## Verification

- [ ] `make lint` passes (ruff format + lint on all modified files)
- [ ] `make types` passes (mypy + pyright — nh3 has type stubs)
- [ ] `make test` passes (all existing + new tests)
- [ ] Manual verification: invalid approval transition returns 422
- [ ] Manual verification: JWT tokens still work after algorithm pinning
- [ ] Manual verification: `sanitize_html_xss("<script>alert(1)</script>")` returns empty string

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| 6.4.1 State machine | Low — additive validation, no schema change | Tests cover all 10 transition combos |
| 6.4.2 JWT pinning | Low — algorithm already HS256, just removing config path | Test that existing tokens still decode |
| 6.4.3 nh3 sanitizer | Medium — new dependency, output format may differ | Extensive test suite, preserve email HTML patterns |

## Order of Implementation

1. **6.4.2 JWT algorithm** — smallest change, no new deps
2. **6.4.1 Approval state machine** — pure logic, no deps
3. **6.4.3 LLM output sanitizer** — new dependency, most test updates
