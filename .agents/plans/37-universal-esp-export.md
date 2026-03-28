# Phase 37: Universal ESP Export

## Goal

Any email HTML produced by the pipeline can be exported to **any ESP** with correct personalization tokens and uploaded via that ESP's API. HTML structure is ESP-agnostic — only token syntax and API upload differ.

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| ESPSyncProvider Protocol | Done | `app/connectors/sync_protocol.py` |
| Klaviyo provider | Done | `app/connectors/klaviyo/sync_provider.py` |
| HubSpot provider | Done | `app/connectors/hubspot/sync_provider.py` |
| Braze/SFMC/Adobe/Taxi providers | Done | `app/connectors/` (existing) |
| Token detection (7 ESPs) | Done | `app/qa_engine/personalisation_validator.py` |
| Token validation + QA | Done | `app/qa_engine/checks/personalisation_syntax.py` |
| Personalisation agent (7 ESPs) | Done | `app/ai/agents/personalisation/` |
| Resilient HTTP + retry | Done | `app/connectors/http_resilience.py` |
| Credential encryption | Done | `sync_models.py` (Fernet) |
| Token rewriting | **Missing** | — |
| Mailchimp/SendGrid/AC/Iterable/Brevo adapters | **Missing** | — |
| ESP-agnostic token IR | **Missing** | — |

## Architecture

```
Pipeline HTML (ESP-agnostic, no tokens)
    │
    ▼
Personalisation Agent (injects tokens for target ESP)
    │
    ▼
HTML with ESP-specific tokens
    │
    ├─► Direct download (HTML file)
    │
    └─► ESP API upload via provider adapter
        ├── Klaviyo   (done)
        ├── HubSpot   (done)
        ├── Braze     (done)
        ├── SFMC      (done)
        ├── Adobe     (done)
        ├── Mailchimp (new)
        ├── SendGrid  (new)
        ├── ActiveCampaign (new)
        ├── Iterable  (new)
        └── Brevo     (new)
```

### Key insight: two export paths

**Path A — Fresh email (no existing tokens):**
Pipeline HTML → Personalisation agent injects tokens for target ESP → upload.
This already works for the 6 existing providers.

**Path B — Imported email with existing tokens → export to different ESP:**
HTML with Klaviyo tokens → **token rewriter** → HTML with SFMC tokens → upload.
This is the missing piece.

---

## Subtask 37.1: Token Intermediate Representation (IR)

**Goal:** Define an ESP-agnostic token format that any ESP syntax can round-trip through.

**File:** `app/connectors/token_ir.py` (~200 lines)

### IR Schema (frozen dataclasses)

```
TokenIR:
  variables: list[VariableToken]     # {{ first_name }}
  conditionals: list[ConditionalToken] # {% if x %}...{% endif %}
  loops: list[LoopToken]             # {% for item in items %}...{% endfor %}
  filters: list[FilterToken]         # | uppercase, | default: "Friend"

VariableToken:
  name: str              # "first_name" (normalized, ESP-agnostic)
  fallback: str | None   # "Friend"
  source_span: tuple[int, int]  # character offsets in HTML

ConditionalToken:
  variable: str
  operator: Literal["exists", "eq", "neq", "gt", "lt", "contains"]
  value: str | None
  body_html: str
  else_html: str | None
  source_span: tuple[int, int]

LoopToken:
  item_name: str         # "item"
  collection: str        # "event.items"
  body_html: str
  source_span: tuple[int, int]

FilterToken:
  name: str              # "uppercase", "default", "date", "currency"
  args: tuple[str, ...]
```

### Parser per ESP (`parse_{esp}(html) -> TokenIR`)

Reuse existing regex patterns from `personalisation_validator.py:_PLATFORM_PATTERNS` — they already extract tokens for 7 ESPs. Extend to produce IR nodes instead of raw matches.

### Emitter per ESP (`emit_{esp}(ir, html) -> str`)

Replace IR spans in HTML with target ESP syntax. One function per ESP, ~30-50 lines each.

**Filter mapping table** (subset — each ESP supports different filters):

| IR filter | Klaviyo | HubSpot | Braze | SFMC | Mailchimp |
|-----------|---------|---------|-------|------|-----------|
| `default` | `\|default:"X"` | `\|default("X")` | `\|default:"X"` | `IIF(Empty(@v),"X",@v)` | N/A |
| `uppercase` | `\|upper` | `\|upper` | `\|upcase` | `Uppercase(@v)` | `\|upper` |
| `date` | `\|date:"fmt"` | `\|datetimeformat("fmt")` | `\|date:"%b %d"` | `Format(@d,"fmt")` | N/A |
| `currency` | `\|floatformat:2` | `\|format_currency("USD")` | `\|money` | `FormatCurrency(@v,"en-US")` | N/A |

**Not all filters translate 1:1.** When a filter has no equivalent, emit a `<!-- MANUAL: {filter} not supported on {esp} -->` comment and preserve the raw value. Log a warning.

### Tests: 25-30

- Round-trip: parse Klaviyo → IR → emit HubSpot → parse HubSpot → IR (structural equality)
- Each ESP parser extracts correct IR from sample HTML
- Each ESP emitter produces valid syntax
- Unsupported filter → comment fallback
- Nested conditionals preserve structure
- Spans don't overlap or corrupt HTML

---

## Subtask 37.2: Token Rewriter Service

**Goal:** Orchestrate cross-ESP token migration in a single async call.

**File:** `app/connectors/token_rewriter.py` (~120 lines)

```python
class TokenRewriterService:
    async def rewrite(
        html: str,
        source_esp: str | None,  # auto-detect if None
        target_esp: str,
    ) -> TokenRewriteResult

TokenRewriteResult:
    html: str
    source_esp: str
    target_esp: str
    tokens_rewritten: int
    warnings: list[str]  # unsupported filters, ambiguous patterns
```

**Flow:**
1. Detect source ESP (reuse `personalisation_validator.py:detect_platform()`)
2. Parse source tokens → IR
3. Emit target tokens from IR
4. Run `personalisation_syntax` QA check on output (validate result)
5. Return result with warnings

**Wire into:**
- `ConnectorSyncService.push_template()` — if template has tokens from a different ESP, auto-rewrite before push
- New endpoint: `POST /api/v1/connectors/sync/rewrite-tokens` (developer role, 30/min)

### Tests: 12-15

- Auto-detect + rewrite Klaviyo → SFMC
- Auto-detect + rewrite Braze → HubSpot
- No tokens → passthrough (0 rewritten)
- Mixed platform tokens → warning + best-effort
- QA validation catches broken output

---

## Subtask 37.3: Mailchimp Provider

**File:** `app/connectors/mailchimp/sync_provider.py` (~170 lines)

| Aspect | Detail |
|--------|--------|
| Auth | `Bearer {api_key}`, datacenter from key suffix (`us21`) |
| Base URL | `https://{dc}.api.mailchimp.com/3.0` |
| Templates API | `GET/POST/PATCH/DELETE /templates` + `/templates/{id}` |
| Pagination | `offset` + `count` (max 1000) |
| HTML field | `html` in request/response body |
| Credentials | `{"api_key": "..."}` |
| Rate limit | 10 concurrent connections per API key |

**Token syntax:** `*|FNAME|*`, `*|IF:FNAME|*...*|END:IF|*`

Add `"mailchimp"` to `PROVIDER_REGISTRY`, `ESPConnectionCreate` regex, config URLs.

### Tests: 14 (mirror Klaviyo/HubSpot test structure)

---

## Subtask 37.4: SendGrid Provider

**File:** `app/connectors/sendgrid/sync_provider.py` (~160 lines)

| Aspect | Detail |
|--------|--------|
| Auth | `Bearer {api_key}` |
| Base URL | `https://api.sendgrid.com/v3` |
| Templates API | `/templates` (CRUD) + `/templates/{id}/versions` |
| Note | Templates have **versions** — create version, not template, for HTML updates |
| HTML field | `html_content` on version object |
| Pagination | None (max 200 templates returned) |
| Credentials | `{"api_key": "SG...."}` |

**Token syntax:** Handlebars `{{first_name}}`, `{{#if}}...{{/if}}`, `{{#each}}...{{/each}}`

### Tests: 14

---

## Subtask 37.5: ActiveCampaign Provider

**File:** `app/connectors/activecampaign/sync_provider.py` (~150 lines)

| Aspect | Detail |
|--------|--------|
| Auth | `Api-Token: {api_key}` header |
| Base URL | `https://{account}.api-us1.com/api/3` |
| Templates API | `GET/POST/PUT/DELETE /messages` (personal email templates) |
| HTML field | `message` (full HTML) |
| Pagination | `offset` + `limit` |
| Credentials | `{"api_key": "...", "account": "mycompany"}` |

**Token syntax:** `%FIRSTNAME%`, limited conditionals.

### Tests: 14

---

## Subtask 37.6: Iterable Provider

**File:** `app/connectors/iterable/sync_provider.py` (~160 lines)

| Aspect | Detail |
|--------|--------|
| Auth | `Api-Key: {api_key}` header |
| Base URL | `https://api.iterable.com/api` |
| Templates API | `/templates/email/get`, `/templates/email/upsert` |
| HTML field | `html` in request body |
| Pagination | Offset-based |
| Credentials | `{"api_key": "..."}` |

**Token syntax:** Handlebars `{{first_name}}`, `{{#if}}...{{/if}}`, `{{defaultIfEmpty}}`, `{{#each}}`

### Tests: 14

---

## Subtask 37.7: Brevo (ex-Sendinblue) Provider

**File:** `app/connectors/brevo/sync_provider.py` (~150 lines)

| Aspect | Detail |
|--------|--------|
| Auth | `api-key: {api_key}` header |
| Base URL | `https://api.brevo.com/v3` |
| Templates API | `GET/POST/PUT/DELETE /smtp/templates` |
| HTML field | `htmlContent` |
| Pagination | `offset` + `limit` |
| Credentials | `{"api_key": "xkeysib-..."}` |

**Token syntax:** Django/Jinja2 `{{ contact.FIRSTNAME }}`, `{% if %}...{% endif %}`

### Tests: 14

---

## Subtask 37.8: Export Orchestration & UI Endpoints

**Goal:** Unified export flow that combines token rewriting + ESP upload.

**File updates:** `app/connectors/sync_service.py`, `app/connectors/sync_routes.py`

### New endpoint

```
POST /api/v1/connectors/sync/export
{
  "html": "...",                    # or template_id to fetch from DB
  "target_esp": "klaviyo",
  "connection_id": "uuid",          # which ESP connection to push to
  "source_esp": null,               # auto-detect, or explicit
  "template_name": "Welcome Email",
  "rewrite_tokens": true            # default true
}

Response:
{
  "esp_template_id": "...",
  "tokens_rewritten": 5,
  "warnings": [],
  "preview_url": "https://..."     # if ESP returns one
}
```

### Flow

1. Fetch HTML (from body or DB)
2. If `rewrite_tokens` and source ≠ target → `TokenRewriterService.rewrite()`
3. `ConnectorSyncService.push_template()` via target provider
4. Return ESP template ID + metadata

### Bulk export endpoint

```
POST /api/v1/connectors/sync/export-bulk
{
  "template_ids": ["uuid1", "uuid2"],
  "target_esp": "hubspot",
  "connection_id": "uuid"
}
```

Processes sequentially with per-template error isolation. Returns list of results.

### Tests: 15-20

- Full flow: HTML with Braze tokens → export to Klaviyo connection → tokens rewritten + pushed
- Bulk export with partial failure
- No connection → 404
- Invalid ESP → 422
- Rate limiting

---

## Subtask 37.9: Mock ESP Sidecar Updates

**File:** `services/mock-esp/` (existing mock server)

Add mock routes for new ESPs so tests don't need real API keys:

| ESP | Mock routes |
|-----|-------------|
| Mailchimp | `GET/POST/PATCH/DELETE /mailchimp/templates/*` |
| SendGrid | `GET/POST/PATCH/DELETE /sendgrid/templates/*` |
| ActiveCampaign | `GET/POST/PUT/DELETE /activecampaign/messages/*` |
| Iterable | `GET/POST /iterable/templates/email/*` |
| Brevo | `GET/POST/PUT/DELETE /brevo/smtp/templates/*` |

Config URLs in `ESPSyncConfig` already follow this pattern (`http://mock-esp:3002/{esp}`).

### Tests: integration tests use mock-esp, no new test files needed

---

## Subtask 37.10: Tests & Integration Verification

- Token IR round-trip tests across all 11 ESPs (7 parsers × 11 emitters = 77 combinations, test representative subset ~25)
- Rewriter service end-to-end
- Each new provider: 14 unit tests (mirror existing pattern)
- Export orchestration: 15 integration tests
- QA validation on rewritten output
- Bulk export with mixed source ESPs

**Total new tests: ~170-190**

---

## Dependency Graph

```
37.1 Token IR ──────► 37.2 Rewriter Service ──► 37.8 Export Orchestration
                                                       │
37.3 Mailchimp ─────┐                                  │
37.4 SendGrid ──────┤                                  │
37.5 ActiveCampaign ┼──► 37.9 Mock ESP updates ────────┘
37.6 Iterable ──────┤
37.7 Brevo ─────────┘
                                                  37.10 Tests (last)
```

**Parallelizable:** 37.3–37.7 (all provider adapters) can be built in parallel. 37.1 and 37.3–37.7 can also be parallel (no dependency).

---

## Scope Boundaries

**In scope:**
- Token syntax rewriting between any supported ESP pair
- API upload adapters for 11 ESPs total (6 existing + 5 new)
- Unified export endpoint with auto-rewrite
- Bulk export
- Mock ESP for testing

**Out of scope:**
- Figma plugin (Phase 38 candidate)
- ESP analytics/reporting sync (read campaign stats back)
- ESP list/audience management
- ESP automation/workflow triggers
- Token rewriting for non-personalization ESP features (e.g., AMP for email, interactive content)
- Cross-ESP campaign migration (templates + audiences + automations)

## Line estimate

| Subtask | New lines | Test lines |
|---------|-----------|------------|
| 37.1 Token IR | ~350 | ~400 |
| 37.2 Rewriter service | ~120 | ~200 |
| 37.3-37.7 Providers (×5) | ~800 | ~700 |
| 37.8 Export orchestration | ~200 | ~250 |
| 37.9 Mock ESP updates | ~300 | — |
| **Total** | **~1,770** | **~1,550** |
