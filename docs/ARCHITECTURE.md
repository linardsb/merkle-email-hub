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
