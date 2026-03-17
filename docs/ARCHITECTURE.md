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
