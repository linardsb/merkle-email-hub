# Architecture Decision Records

## ADR-001: Agent-Agnostic AI Layer

**Decision:** Use Python Protocol interfaces instead of coupling to any AI framework.

**Context:** The original VTV platform was built on Pydantic AI. While excellent, framework lock-in limits adoption and makes migration costly.

**Solution:** Define Protocol interfaces (`LLMProvider`, `EmbeddingProvider`, `RerankerProvider`, `ToolProvider`) that any implementation can satisfy. The template includes a reference implementation using raw `httpx.AsyncClient` for OpenAI-compatible APIs.

**Consequence:** Users can use any AI framework (Pydantic AI, LangChain, CrewAI, raw SDK) by implementing the Protocol. The service layer never knows or cares what framework is behind the protocol.

## ADR-002: Nested Configuration

**Decision:** Use Pydantic `env_nested_delimiter="__"` for grouped settings.

**Context:** VTV had 50+ flat settings in one class, making it hard to find related settings.

**Solution:** Group settings into nested models: `DatabaseConfig`, `RedisConfig`, `AuthConfig`, `AIConfig`, etc. Environment variables use double-underscore nesting: `DATABASE__URL`, `AUTH__JWT_SECRET_KEY`.

**Consequence:** Settings are logically organized. IDE autocomplete works naturally (`settings.database.url`). `.env` files are more readable.

## ADR-003: Standalone Live Data Pipeline

**Decision:** Decouple the background poller and WebSocket streaming from any AI/agent layer.

**Context:** In VTV, the transit poller was tightly coupled to GTFS-RT feeds and the agent tool system.

**Solution:** Create a generic `DataPoller` base class in `app/core/poller.py` and a standalone `app/streaming/` module. These work independently: you can use the poller without WebSocket, WebSocket without the poller, or both together.

**Consequence:** Any background data fetching use case (weather, stock prices, IoT sensors) can subclass `DataPoller`. The streaming module handles WebSocket lifecycle regardless of data source.

## ADR-004: Vertical Slice Architecture

**Decision:** Each feature owns its complete stack (models, schemas, repository, service, exceptions, routes, tests).

**Context:** Traditional layered architecture (all models in one place, all routes in another) leads to coupling and makes it hard to understand a feature in isolation.

**Solution:** Feature directories under `app/{feature}/` contain everything needed. Shared code lives in `app/shared/` (only for 3+ feature usage) and `app/core/` (infrastructure).

**Consequence:** Features are self-contained and easy to understand. Adding a new feature means creating a new directory, not modifying 6 different layers.

## ADR-005: Redis as Infrastructure Backbone

**Decision:** Use Redis for rate limiting, session caching, feature flags, leader election, Pub/Sub, and health tracking.

**Context:** Multiple features need fast shared state across workers.

**Solution:** Single Redis instance serves multiple purposes with key prefixing (`auth:`, `poller:`, `flags:`, `rate_limit:`). All Redis usage gracefully degrades when Redis is unavailable (fail-open with logging).

**Consequence:** Simple infrastructure (one Redis instance), consistent patterns, and resilient behavior when Redis is down.

## ADR-006: Checkpoint & Recovery

**Decision:** Two-level checkpoint model — blueprint node-level and pipeline pass-level — enables resuming failed runs without re-executing completed work.

**Context:** Blueprint runs orchestrate multiple AI agents sequentially. A failure mid-pipeline (e.g., at node 4 of 7) wastes all prior LLM calls. The Scaffolder agent's 3-pass pipeline (layout → content → design) is particularly expensive, and losing completed passes on retry burns tokens.

**Solution:** Two checkpoint layers:

1. **Blueprint node-level** (`app/ai/blueprints/checkpoint.py`): After each node executes, the engine serializes the full `BlueprintRun` state (progress, HTML, QA results, handoff history, routing decisions) into a `CheckpointData` frozen dataclass. `PostgresCheckpointStore` persists this as JSONB in the `blueprint_checkpoints` table. The save is fire-and-forget — failures are logged but never crash the pipeline. `serialize_run()` / `restore_run()` handle round-trip fidelity. `BlueprintEngine.resume()` loads the latest checkpoint, validates the blueprint name matches and the target node still exists, then continues execution from `next_node_name`.

2. **Pipeline pass-level** (`app/ai/agents/scaffolder/pipeline_checkpoint.py`): The `PipelineCheckpointCallback` protocol lets the Scaffolder save per-pass results (layout, content_design). On retry (`context.iteration > 0`), completed passes are loaded and skipped. An internal `_Adapter` bridges the general `CheckpointStore` to pipeline callbacks, using compound node names (`scaffolder:layout`, `scaffolder:content_design`) with a +100 node index offset.

**Supporting infrastructure:**
- **Cleanup** (`checkpoint_cleanup.py`): `CheckpointCleanupPoller` runs every 24h — `cleanup_old_checkpoints()` removes entries past `max_age_days`, `cleanup_completed_runs()` removes checkpoints for finished runs.
- **Observability**: `GET /runs/{run_id}/checkpoints` lists checkpoints (admin/developer only). `BlueprintRunResponse` includes `checkpoint_count` and `resumed_from` fields. Structured logging with `size_bytes`, `duration_ms`, `age_seconds`.
- **Resume API**: `POST /api/v1/blueprints/resume` with `BlueprintResumeRequest` (run_id, blueprint_name, brief). Auth + rate-limited (3/min).

**Consequence:** Failed runs resume from the last successful node, saving LLM tokens and wall-clock time. The Scaffolder specifically avoids re-running expensive passes. The opt-in design (`checkpoints_enabled` config flag) means zero overhead for deployments that don't need it.

## ADR-007: Rendering Resilience Testing

**Decision:** Three-layer resilience testing — chaos profiles, property-based invariants, and an optional QA check — validates email HTML against real-world client degradation without requiring live rendering infrastructure.

**Context:** Email clients apply destructive transformations to HTML (Gmail strips `<style>` blocks, Outlook removes flexbox, images get blocked). Traditional QA checks validate HTML structure but cannot predict how degraded HTML performs across clients. Property-based testing can find edge cases that hand-written tests miss, but needs domain-specific generators and invariants.

**Solution:** Three complementary testing layers in `app/qa_engine/`:

1. **Chaos Engine** (`chaos/`): 8 pre-built `ChaosProfile` degradation profiles simulate real client behavior (Gmail style strip, Outlook Word engine, image blocking, dark mode inversion, Gmail clipping, mobile narrow viewport, class stripping, media query removal). Each profile is a pure function pipeline — `apply(html) → degraded_html`. Profiles are composable via `compose_profiles()` for compound scenarios. The engine runs all 11 QA checks on both original and degraded HTML, computing a resilience score as `avg(degraded_scores) / original_score`. Critical failures (severity=error) are collected per profile.

2. **Property-Based Testing** (`property_testing/`): 10 `EmailInvariant` checkers (size limit, image width, link integrity, alt text, table nesting, encoding, MSO balance, dark mode readiness, contrast ratio, viewport fit) validate universal email properties. `EmailConfig` frozen dataclass + `build_email()` generator produce synthetic HTML with configurable features. Deterministic seeded RNG enables CI reproducibility; Hypothesis strategies enable interactive exploration. `PropertyTestRunner` orchestrates N test cases with failure collection.

3. **Resilience Check** (`checks/rendering_resilience.py`): Optional QA check #12 that wraps the chaos engine. NOT in `ALL_CHECKS` to prevent recursion — runs separately after the 11 core checks. Pass/fail based on configurable threshold (default 0.7). Severity escalation: <0.4 → error, 0.4–threshold → warning, ≥threshold → info.

**Knowledge feedback loop** (`chaos/knowledge_writer.py`): Critical chaos failures auto-generate knowledge base documents (when enabled + project context provided). Title-based deduplication prevents duplicates. Per-profile fix hints guide remediation. Non-blocking — write failures never break test responses. BOLA-protected via `verify_project_access()`.

**Consequence:** Teams get actionable resilience scores without deploying to real email clients. The property testing layer catches edge cases (oversized images, unbalanced MSO conditionals, low-contrast text) that targeted checks miss. All three layers are pure-CPU with no LLM or database dependency (except knowledge writer), enabling fast CI integration. Each layer is independently feature-flagged (`qa_chaos.enabled`, `qa_property_testing.enabled`, `qa_chaos.resilience_check_enabled`).

## ADR-008: Outlook Transition & CSS Compilation

**Decision:** Two complementary tools — an Outlook dependency analyzer with audience-aware migration planning and an ontology-driven CSS compiler — enable systematic modernization of legacy email HTML without breaking backward compatibility.

**Context:** Email HTML has accumulated decades of Outlook Word-engine workarounds (VML shapes, ghost tables, MSO conditionals, DPI hacks). With New Outlook migrating to Chromium, these dependencies are becoming dead weight. However, removing them blindly risks breaking rendering for organizations where Word-engine Outlook is still prevalent. Separately, email CSS must be compiled to inline styles with client-incompatible properties either converted or removed — decisions that should be driven by the ontology's compatibility matrix, not hardcoded rules.

**Solution:** Two pipelines in `app/qa_engine/outlook_analyzer/` and `app/email_engine/css_compiler/`:

1. **Outlook Dependency Analyzer** (`detector.py`): 7 regex/DOM detection rules identify VML shapes, ghost tables, MSO conditionals, MSO CSS properties, DPI-compensated images, ExternalClass rules, and word-wrap hacks. Each dependency tagged with severity (high/medium/low), removability flag, and modern CSS replacement suggestion. Pure CPU — no LLM, no database.

2. **Outlook Modernizer** (`modernizer.py`): 3 target modes — `new_outlook` (aggressive removal of all Word-engine code), `dual_support` (preserve MSO conditionals while cleaning external hacks), `audit_only` (analysis without modification). Output sanitized via `sanitize_html_xss()`.

3. **Migration Planner** (`planner.py`): Combines dependency analysis with audience client distribution to produce phased migration plans. Risk-tiered phasing (low→medium→high) with safe-when thresholds based on Word-engine audience share. Three recommendation levels: aggressive (<2% Word-engine), moderate (2-10%), conservative (>10%). Industry-default audience fallback when no ESP data available.

4. **Lightning CSS Compiler** (`css_compiler/`): 7-stage pipeline — parse → analyze → transform → eliminate → optimize → inline → sanitize. Ontology-driven decisions: `get_conversions_for_property()` finds fallbacks, `should_remove_property()` eliminates unsupported properties only when no fallback exists. Lightning CSS minification with graceful failure. CSS variable resolution. MSO conditional preservation throughout pipeline.

**Consequence:** Teams can assess Outlook dependency debt quantitatively, get audience-appropriate migration timelines, and compile CSS with ontology-backed safety guarantees. All four components are pure CPU with no LLM dependency, enabling fast CI integration. Feature-flagged independently (`qa_outlook_analyzer.enabled`, `email_engine.css_compiler_enabled`).

## ADR-009: AI Evolution Infrastructure

**Decision:** Five modular infrastructure capabilities — capability registry, prompt template store, token budget manager, fallback chains, and cost governor — provide the operational foundation for safely scaling AI model usage across providers and tiers.

**Context:** The platform's AI layer started with direct provider calls and tier-based routing. As the number of agents, models, and providers grew, several operational gaps emerged: no structured way to track which models support which capabilities (vision, tool use, structured output); no versioned prompt management beyond static SKILL.md files; no protection against context window overflow; no resilience when a provider experiences downtime; and no visibility into token costs or ability to enforce budget limits. These five capabilities address these gaps as internal infrastructure — no new user-facing features, but critical operational scaffolding.

**Solution:** Five independent modules in `app/ai/`, each feature-flagged and backward-compatible:

1. **Capability Registry** (`capability_registry.py`): `ModelSpec` frozen dataclasses with capability sets, context window sizes, cost-per-token, and deprecation dates. `CapabilityRegistry` singleton with `find_models()` returning cheapest-first matches. Integrated into `routing.py` via `resolve_model_by_capabilities()` as an optional layer above tier-based routing. Config: `AI__MODEL_SPECS` JSON array.

2. **Prompt Template Store** (`prompt_store.py`): `PromptTemplate` SQLAlchemy model with agent/version/variant/content fields. Auto-versioning on create, `activate()`/`rollback()` for safe prompt iteration. `PromptStoreService.seed_from_skill_files()` bootstraps from existing SKILL.md files. Integrated into `skill_override.py` as highest-priority prompt source (store > A/B override > disk). 7 REST endpoints at `/api/v1/prompts`. Config: `AI__PROMPT_STORE_ENABLED`.

3. **Token Budget Manager** (`token_budget.py`): `TokenBudgetManager` with tiktoken estimation (char approximation fallback), auto-detected context windows for 13 models, and adaptive trimming — system message preserved, last user message preserved, middle messages dropped oldest-first. Integrated into both `OpenAICompatProvider` and `AnthropicProvider` adapters, called before every `complete()` and `stream()`. Config: `AI__TOKEN_BUDGET_ENABLED`, `AI__TOKEN_BUDGET_RESERVE`, `AI__TOKEN_BUDGET_MAX`.

4. **Fallback Chains** (`fallback.py`): `FallbackChain` of `FallbackEntry` (provider:model pairs) with `_is_retryable()` error classification (timeout, circuit open, rate limit, server errors across httpx/Anthropic/OpenAI SDKs). `call_with_fallback()` async cascade. Integrated at both call sites: `ChatService.chat()` and `BaseAgentService.process()`. Config: `AI__FALLBACK_CHAINS` JSON dict per tier.

5. **Cost Governor** (`cost_governor.py`): `CostGovernor` singleton with per-model pricing (input/output token rates), monthly budget tracking via Redis, dimension breakdowns (by model, agent, project), and three budget states (OK/WARNING/EXCEEDED). `BudgetExceededError` mapped to HTTP 429. Integrated into both adapters: budget check before completion, cost recording after. 2 REST endpoints at `/api/v1/ai/cost`. Config: `AI__COST_GOVERNOR_ENABLED`, `AI__MONTHLY_BUDGET_GBP`, `AI__BUDGET_WARNING_THRESHOLD`.

**Adapter integration order:** For every `complete()` call, the adapter pipeline runs: (1) token budget trimming → (2) cost budget check → (3) API call → (4) cost recording. Fallback chains wrap this entire sequence, retrying with the next provider:model on retryable failures.

**Consequence:** All five capabilities ship disabled by default, ensuring zero impact on existing deployments. Each can be enabled independently. The adapter-level integration means every AI call — chat, agent, blueprint node — automatically benefits from trimming, budgeting, and fallback without caller changes. 190+ tests across 8 test files validate each capability in isolation and the full cross-module pipeline.

## ADR-010: Multimodal Protocol & MCP Agent Interface

**Decision:** A unified content block protocol enables multimodal AI interactions (text, images, audio, structured output), while an MCP server exposes platform capabilities as composable agent tools.

**Context:** The platform's AI agents originally processed text-only inputs and outputs. Adding visual QA (screenshot analysis), design reference images, and voice briefs required multimodal support without breaking existing text-only workflows. Separately, external AI agents (Claude Desktop, Cursor, custom MCP clients) needed programmatic access to the platform's QA, knowledge, rendering, and email engineering capabilities — a use case poorly served by REST APIs designed for human-facing UIs.

**Solution:** Two complementary systems:

1. **Multimodal Content Block Protocol** (`app/ai/multimodal.py`, `multimodal_schemas.py`): Five frozen dataclass content block types — `TextBlock`, `ImageBlock`, `AudioBlock`, `StructuredOutputBlock`, `ToolResultBlock` — unified under `ContentBlock` union type. `Message.content` accepts `str | list[ContentBlock]` for full backward compatibility. Validation enforces MIME types via magic byte verification, size limits (20MB images, 100MB audio, 5min duration), and schema security (no external `$ref`/`$dynamicRef`, max 50 nesting depth). Token estimation uses provider-specific formulas: Anthropic image tokens = width×height/750, text = chars/4, audio = 25 tokens/sec. Pydantic schemas handle API transport with base64 encoding/decoding. Adapters serialize to provider-specific formats: Anthropic uses `source.type=base64` objects, OpenAI uses data URIs. Vision capability checked via the capability registry — non-vision models receive text descriptions instead of images (fail-safe: unknown models assumed capable).

2. **MCP Tool Server** (`app/mcp/`): FastMCP-based server exposing 17 tools across 6 categories (QA, knowledge, email, rendering, templates, AI) and 2 resources (CSS ontology, hub capabilities). Dual transport: streamable HTTP mounted at `/mcp` for production, stdio via `python -m app.mcp` for IDE integration. Tools return LLM-optimized markdown strings (not raw JSON) with token budget truncation (`MCP__MAX_RESPONSE_TOKENS × 4 chars`). Tool allowlist via fnmatch patterns (`MCP__TOOL_ALLOWLIST`). Auth reuses existing JWT infrastructure with role→scope mapping (admin: read+write+admin, developer: read+write, viewer: read). All tool exceptions caught and logged server-side; clients receive generic error messages only.

3. **Voice Brief Input Pipeline** (`app/ai/voice/`): Pluggable transcription via `VoiceTranscriber` Protocol (WhisperAPI and WhisperLocal implementations). `VoiceBriefExtractor` uses LLM to parse transcripts into structured `EmailBrief` (topic, sections with type/description/hints, tone, CTA, audience, constraints). Confidence threshold (default 0.7) — below threshold, raw transcript passed through without structured extraction. Full pipeline: audio → transcribe → validate duration → extract brief → format as natural language → trigger blueprint run. Three rate-limited endpoints at `/api/v1/ai/voice/`.

**Consequence:** Existing text-only agents work unchanged (string content auto-normalized to `[TextBlock]`). New capabilities (visual QA screenshots, design references, voice briefs) flow through the same `Message` and adapter pipeline. MCP clients get full platform access without custom integration code — any MCP-compatible agent can run QA checks, search knowledge, compile CSS, or trigger renders. All three systems are feature-flagged (`AI__MULTIMODAL_ENABLED`, `MCP__ENABLED`, `VOICE__ENABLED`) and ship disabled by default.

## ADR-011: Real-Time Collaboration & Visual Builder

**Status:** Accepted
**Date:** 2026-03-18

**Context:** Email templates need concurrent editing by multiple team members with live presence and conflict-free merging.

**Decision:**
- **Transport:** WebSocket at `/ws/collab/{room_id}` with JWT auth via query param, room-based connection management (`CollabConnectionManager`), and Redis pub/sub for multi-instance broadcasting.
- **CRDT Engine:** Yjs (via pycrdt) for conflict-free concurrent edits. Server-side `YjsDocumentStore` persists compacted state + pending updates in PostgreSQL. Inline compaction at configurable thresholds (count or time).
- **Sync Protocol:** Standard Yjs wire protocol (SyncStep1/SyncStep2/Update). Server acts as central authority — applies updates, persists, and rebroadcasts. Viewers restricted to read-only SyncStep1.
- **Visual Builder:** Component-based email construction with drag-and-drop (dnd-kit). Sections have slot fills, token overrides, and responsive config. Property panels drive all section configuration.
- **Bidirectional Sync:** `BuilderSyncEngine` syncs visual builder ↔ code editor. HTML→sections via `ast-mapper.ts` (supports ESP token preservation). Builder-wins conflict resolution with debounced sync (500ms parse, 200ms serialize).
- **Presence:** Awareness protocol over WebSocket for cursor positions, selections, and activity state. 12-color palette, follow mode, idle detection (15s).

**Consequence:**
- PostgreSQL stores CRDT state — no additional infrastructure needed beyond Redis (already used).
- Compaction prevents unbounded growth of update history.
- ESP token preservation enables round-trip editing of production templates.
- Room-based architecture scales horizontally via Redis pub/sub bridge.
- Viewer role enforced at protocol level — cannot send updates, only sync state vectors.
