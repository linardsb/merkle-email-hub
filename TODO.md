# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–24):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA — Playwright rendering, ODiff baselines, VLM analysis agent #10, auto-fix pipeline, visual QA dashboard). Phase 18 (rendering resilience & property-based testing — chaos engine with 8 profiles, Hypothesis-based property testing with 10 invariants, resilience score integration, knowledge feedback loop). Phase 19 (Outlook transition advisor & email CSS compiler — Word-engine dependency analyzer, audience-aware migration planner, Lightning CSS 7-stage compiler with ontology-driven conversions). Phase 20 (Gmail AI intelligence & deliverability — Gemini summary predictor, schema.org auto-injection, deliverability scoring, BIMI readiness check). Phase 21 (real-time ontology sync & competitive intelligence — caniemail auto-sync, rendering change detector with 25 feature templates, competitive intelligence dashboard). Phase 22 (AI evolution infrastructure — capability registry, prompt template store, token budget manager, fallback chains, cost governor, cross-module integration tests + ADR-009). Phase 23 (multimodal protocol & MCP agent interface — 7 subtasks: content block protocol, adapter serialization, agent integration, MCP tool server with 17 tools, voice brief pipeline, frontend multimodal UI, tests & ADR-010; 197 tests). Phase 24 (real-time collaboration & visual builder — 9 subtasks: WebSocket infra, Yjs CRDT engine, collaborative cursor & presence, visual builder canvas & palette, property panels, bidirectional code↔builder sync, frontend integration, tests & docs, AI-powered HTML import with 10th agent).

---

## ~~Phase 24 — Real-Time Collaboration & Visual Builder~~ DONE

> All 9 subtasks complete. See [docs/TODO-completed.md](docs/TODO-completed.md) for detailed completion records.
> 24.1 WebSocket infra, 24.2 Yjs CRDT, 24.3 Presence, 24.4 Visual builder canvas, 24.5 Property panels, 24.6 Bidirectional sync, 24.7 Frontend integration, 24.8 Tests & docs, 24.9 AI-powered HTML import.

---

## Phase 25 — Platform Ecosystem & Advanced Integrations

**What:** Plugin architecture for community-contributed components, Tolgee integration for multilingual campaigns, Kestra workflow orchestration replacing ad-hoc blueprint scheduling, Penpot as a self-hosted Figma alternative, Typst for programmatic QA report generation, self-serve template learning pipeline with automatic skill extraction, template-to-eval generation, deliverability intelligence, and multi-variant campaign assembly. Each integration compounds with existing capabilities — Tolgee + Maizzle enables per-locale builds, uploaded templates train agents automatically, variant generation turns one brief into A/B-testable campaigns.
**Why:** These extend the Hub from a tool into a platform. A plugin architecture means the community can add QA checks, agent skills, export connectors, and component packages without core changes. The template learning pipeline (25.10-25.12) creates a flywheel: developers upload production templates → system extracts patterns → agents learn → output quality improves → developers upload more. Deliverability intelligence (25.13) catches inbox placement risks that no other build-time tool addresses. Multi-variant assembly (25.14) automates the most tedious part of email marketing — A/B test creation.
**Dependencies:** All previous phases — plugins extend every subsystem, Tolgee hooks into Maizzle, Kestra wraps the blueprint engine, Penpot reuses the design sync protocol (Phase 12), Typst consumes QA engine data.
**Design principle:** Plugins are sandboxed — they can read Hub data and contribute capabilities but cannot modify core behavior. External integrations are protocol-based — swap Tolgee for another TMS, swap Kestra for Temporal, swap Penpot for any design tool that speaks the protocol. Every integration ships behind a feature flag.

### 25.1 Plugin Architecture — Manifest, Discovery & Registry `[Backend]`
**What:** Define the plugin manifest format, discovery mechanism, and central registry. Plugins declare their type (QA check, agent skill, export connector, component package, theme), required Hub API version, permissions, and entry points. The registry discovers plugins from a configurable directory, validates manifests, and registers capabilities with the appropriate subsystem.
**Why:** Without a formal plugin architecture, every new capability requires core code changes. A plugin system lets the community contribute: custom QA checks for specific industries (finance compliance, healthcare HIPAA), agent skills for niche use cases (AMP email generation, interactive email), ESP connectors for less common providers (Mailtrap, Postmark), and component packages (holiday themes, industry-specific templates).
**Implementation:**
- Create `app/plugins/` package:
  - `manifest.py` — `PluginManifest` Pydantic model:
    - `name: str` — unique plugin identifier (reverse domain: `com.example.my-plugin`)
    - `version: str` — semver (validated)
    - `hub_api_version: str` — minimum Hub API version required (e.g., `">=1.0"`)
    - `plugin_type: PluginType` — enum: `qa_check`, `agent_skill`, `export_connector`, `component_package`, `theme`, `workflow_step`
    - `entry_point: str` — Python module path for plugin entry (e.g., `my_plugin.main`)
    - `permissions: list[PluginPermission]` — enum: `read_templates`, `read_components`, `read_qa_results`, `write_qa_results`, `call_llm`, `network_access`, `file_read`
    - `config_schema: dict | None` — JSON Schema for plugin-specific configuration
    - `metadata: PluginMetadata` — `author`, `description`, `homepage`, `license`, `tags`
    - Loaded from `plugin.yaml` or `plugin.json` in plugin directory
  - `discovery.py` — `PluginDiscovery`:
    - `discover(plugin_dir: Path) -> list[PluginManifest]` — scans directory for plugin manifests
    - Plugin directory structure: `plugins/{plugin-name}/plugin.yaml` + Python package
    - Validation: manifest schema check, version compatibility check, dependency resolution
    - Hot reload support: `watch(plugin_dir)` using `watchdog` — detects new/modified plugins without restart
    - Conflict detection: two plugins registering same QA check name → error logged, second rejected
  - `registry.py` — `PluginRegistry` singleton:
    - `register(manifest: PluginManifest, module: ModuleType) -> None` — registers plugin with appropriate subsystem:
      - `qa_check` → registers with `QAEngineService` as additional check
      - `agent_skill` → registers with `SkillOverrideManager` as SKILL.md override
      - `export_connector` → registers with `ConnectorSyncService` as new provider
      - `component_package` → bulk imports components via `ComponentService`
      - `theme` → registers design system theme with `DesignSystemService`
      - `workflow_step` → registers with Kestra workflow (25.5) as custom step
    - `unregister(plugin_name: str) -> None` — cleanly removes plugin
    - `list_plugins() -> list[PluginInfo]` — returns all registered plugins with status
    - `get_plugin(name: str) -> PluginInstance` — returns loaded plugin instance
    - `PluginInfo(manifest: PluginManifest, status: str, loaded_at: datetime, error: str | None)`
  - `loader.py` — `PluginLoader`:
    - `load(manifest: PluginManifest) -> ModuleType` — `importlib` dynamic import of entry point module
    - Plugin entry point must export `setup(hub: HubPluginAPI) -> None` function
    - Module loaded in isolated namespace (no access to `app.core` internals)
    - Import timeout: 10s (prevents hanging plugins from blocking startup)
- Create `app/plugins/api.py` — `HubPluginAPI`:
  - Sandboxed API surface exposed to plugins:
    - `api.qa.register_check(name, check_fn)` — register QA check
    - `api.knowledge.search(query)` — read-only knowledge search
    - `api.components.list(category)` — list components
    - `api.templates.get(template_id)` — get template HTML
    - `api.llm.complete(messages, model_tier)` — call LLM (only if `call_llm` permission)
    - `api.config.get(key)` — read plugin-specific config
  - Permission enforcement: each API method checks `manifest.permissions` before executing
- Modify `app/main.py` — on startup: discover plugins → validate → load → register
- Modify `app/plugins/routes.py` — admin endpoints:
  - `GET /api/v1/plugins` — list all plugins with status
  - `POST /api/v1/plugins/{name}/enable` — enable a discovered plugin
  - `POST /api/v1/plugins/{name}/disable` — disable without removing
  - `DELETE /api/v1/plugins/{name}` — unregister and remove
  - `GET /api/v1/plugins/{name}/config` — get plugin config
  - `PUT /api/v1/plugins/{name}/config` — update plugin config
- Config: `PLUGINS__ENABLED: bool = False`, `PLUGINS__DIRECTORY: str = "plugins/"`, `PLUGINS__HOT_RELOAD: bool = False`, `PLUGINS__MAX_LOAD_TIME_S: int = 10`
**Security:** Plugins run in-process but with a restricted API surface — no direct database access, no file system writes, no network access (unless `network_access` permission granted). Plugin code is not sandboxed at the OS level (Python limitation) — this is a trust-based system suitable for enterprise self-hosted deployments where plugins are vetted. Admin-only plugin management endpoints. Plugin errors are caught and logged — a crashing plugin never takes down the Hub. Plugin config stored in database — not in plugin directory (prevents tampering).
**Verify:** Create sample QA check plugin (`plugin.yaml` + Python module) → place in plugins directory → Hub discovers on startup → plugin appears in `GET /plugins` → run QA → custom check included in results. Disable plugin → QA runs without it. Plugin requesting `call_llm` without permission → API call rejected. Hot reload: add new plugin to directory → registered without restart (when enabled). `make test` passes.
- [x] ~~25.1 Plugin architecture — manifest, discovery & registry~~ DONE

### 25.2 Plugin Sandboxed Execution & Lifecycle `[Backend]`
**What:** Execution sandbox for plugins with resource limits, error isolation, and lifecycle hooks. Plugins get CPU/memory budgets, structured logging, health checks, and graceful shutdown. The sandbox ensures a misbehaving plugin cannot degrade Hub performance or crash the service.
**Why:** Plugins run third-party code in the Hub process. Without resource controls, a single plugin with an infinite loop or memory leak brings down the entire platform. Enterprise deployments need guarantees that plugin failures are isolated. Lifecycle hooks (startup, shutdown, health check) enable monitoring and graceful degradation.
**Implementation:**
- Create `app/plugins/sandbox.py` — `PluginSandbox`:
  - `execute(plugin: PluginInstance, fn: str, *args, timeout_s: float = 30) -> Any` — run plugin function with:
    - Timeout: `asyncio.wait_for()` with configurable per-plugin timeout
    - Error isolation: all exceptions caught, logged with plugin context, returned as `PluginError`
    - Resource tracking: wall-clock time measured, logged in structured format
  - `PluginExecutionContext` — passed to every plugin function:
    - `context.logger` — structured logger prefixed with plugin name
    - `context.config` — plugin-specific configuration (read-only)
    - `context.metrics` — counter/gauge registration for plugin metrics
  - `async health_check(plugin: PluginInstance) -> PluginHealth` — calls plugin's `health()` function if defined, times out after 5s
  - `PluginHealth(status: str, message: str | None, latency_ms: float)` — status: `healthy`, `degraded`, `unhealthy`
- Create `app/plugins/lifecycle.py` — `PluginLifecycleManager`:
  - `async startup(plugin: PluginInstance) -> None` — calls plugin `setup()`, validates return, marks as active
  - `async shutdown(plugin: PluginInstance) -> None` — calls plugin `teardown()` if defined, waits up to 10s, marks as inactive
  - `async restart(plugin: PluginInstance) -> None` — shutdown → load → startup (for hot reload)
  - Periodic health checks: every 60s, check all active plugins, disable unhealthy plugins after 3 consecutive failures
  - Startup ordering: plugins loaded in dependency order (if plugin A depends on plugin B, B loads first)
- Modify `app/plugins/registry.py` — integrate sandbox execution:
  - QA check plugins: `sandbox.execute(plugin, "run_check", html, config)` with 30s timeout
  - Agent skill plugins: `sandbox.execute(plugin, "process", request)` with 60s timeout
  - Export connector plugins: `sandbox.execute(plugin, "push", template, connection)` with 120s timeout
- Modify `app/plugins/routes.py` — add:
  - `GET /api/v1/plugins/{name}/health` — plugin health status
  - `POST /api/v1/plugins/{name}/restart` — restart plugin (admin only)
  - `GET /api/v1/plugins/health` — all plugins health summary
- Config: `PLUGINS__DEFAULT_TIMEOUT_S: int = 30`, `PLUGINS__HEALTH_CHECK_INTERVAL_S: int = 60`, `PLUGINS__MAX_CONSECUTIVE_FAILURES: int = 3`
**Security:** Timeout enforcement prevents infinite loops. Error isolation prevents plugin exceptions from propagating to request handlers. Plugin functions cannot catch `asyncio.CancelledError` (timeout is non-negotiable). Structured logging with plugin name prefix enables security audit of plugin actions. Health checks run with minimal permissions.
**Verify:** Plugin with `time.sleep(60)` → timeout after 30s → error logged → Hub continues serving. Plugin raising exception → caught, logged, result indicates error → Hub unaffected. Health check on healthy plugin → `healthy` status. Plugin failing health check 3 times → auto-disabled. Restart disabled plugin → re-enabled if health check passes. `make test` passes.
- [x] ~~25.2 Plugin sandboxed execution & lifecycle~~ DONE

### 25.3 Tolgee Multilingual Campaign Support `[Backend]`
**What:** Integrate Tolgee (self-hosted translation management system) for multilingual email campaigns. Sync email content keys to Tolgee for translation, pull translations back, and trigger per-locale Maizzle builds. Supports ICU message format for pluralization and gender-aware content. Translation memory and machine translation suggestions speed up the translation workflow.
**Why:** Enterprise email campaigns routinely deploy in 5-20 languages. Currently, translations are managed in spreadsheets or external TMS with manual copy-paste into templates. Tolgee integration automates the full loop: extract translatable strings → translate → build per-locale email → QA each locale. The Hub's Maizzle sidecar already supports per-locale builds — Tolgee provides the translation data.
**Implementation:**
- Create `app/connectors/tolgee/` package:
  - `client.py` — `TolgeeClient(httpx.AsyncClient)`:
    - `async list_projects() -> list[TolgeeProject]` — list Tolgee projects
    - `async get_translations(project_id: int, language: str, namespace: str | None) -> dict[str, str]` — fetch translations for a language
    - `async push_keys(project_id: int, keys: list[TranslationKey]) -> PushResult` — create/update translation keys with source text
    - `async get_languages(project_id: int) -> list[TolgeeLanguage]` — list project languages
    - `async import_translations(project_id: int, format: str, data: bytes) -> ImportResult` — bulk import translations
    - `async export_translations(project_id: int, format: str, languages: list[str]) -> bytes` — bulk export
    - Authentication: Tolgee PAT (Personal Access Token) stored encrypted in `ESPConnection` model (reusing connector infrastructure)
    - Base URL: configurable for self-hosted instances
  - `extractor.py` — `TranslationKeyExtractor`:
    - `extract_keys(html: str, template_id: int) -> list[TranslationKey]` — scan email HTML for translatable content:
      - Text content in `<td>`, `<p>`, `<h1>`-`<h6>`, `<a>`, `<span>` elements
      - `alt` attributes on `<img>` elements
      - `title` attributes
      - Subject line and preview text (from template metadata)
    - `TranslationKey(key: str, source_text: str, context: str | None, namespace: str)` — key format: `template_{id}.section_{name}.{element}` (e.g., `template_42.hero.heading`)
    - ICU format detection: content with `{count, plural, ...}` or `{gender, select, ...}` preserved as-is
    - Skips non-translatable content: URLs, email addresses, code snippets, tracking parameters
  - `builder.py` — `LocaleEmailBuilder`:
    - `async build_locale(template_html: str, translations: dict[str, str], locale: str) -> str` — inject translations into template:
      - Replace source text with translations at each key location
      - Adjust RTL/LTR direction for Arabic, Hebrew, Farsi, Urdu locales
      - Handle text expansion: German/Finnish text is ~30% longer than English — validate no Gmail clipping after translation
    - `async build_all_locales(template_id: int, locales: list[str]) -> dict[str, str]` — parallel build for all target locales
    - Integration with Maizzle sidecar: `POST /build` with `locale` parameter for locale-specific Tailwind config
  - `schemas.py` — `TolgeeConnectionRequest`, `TranslationSyncRequest`, `LocaleBuildRequest`, `LocaleBuildResponse`, `TranslationKeySchema`
- Modify `app/connectors/routes.py` — add endpoints:
  - `POST /api/v1/connectors/tolgee/connect` — create Tolgee connection (encrypted credentials)
  - `POST /api/v1/connectors/tolgee/sync-keys` — push translatable keys to Tolgee with auth + `5/minute`
  - `POST /api/v1/connectors/tolgee/pull` — pull translations from Tolgee with auth + `10/minute`
  - `POST /api/v1/connectors/tolgee/build-locales` — build email in multiple locales with auth + `3/minute`
  - `GET /api/v1/connectors/tolgee/languages` — list available languages
- Config: `TOLGEE__ENABLED: bool = False`, `TOLGEE__BASE_URL: str = "http://localhost:25432"`, `TOLGEE__DEFAULT_LOCALE: str = "en"`, `TOLGEE__MAX_LOCALES_PER_BUILD: int = 20`
**Security:** Tolgee PAT stored encrypted (Fernet) in `ESPConnection` — same security model as ESP credentials (Phase 13). Translation content is text-only — no HTML injection possible (translations injected as text nodes, not raw HTML). RTL direction changes applied via `dir` attribute only — no CSS injection. Tolgee API calls use HTTPS. Rate limited to prevent API abuse.
**Verify:** Connect to Tolgee → extract 15 keys from template → push to Tolgee → verify keys appear in Tolgee UI. Add German translations in Tolgee → pull → build German locale → German text present in output. RTL locale (Arabic) → `dir="rtl"` applied. Long German text → Gmail clipping warning. ICU pluralization → preserved in translation. `make test` passes.
- [x] ~~25.3 Tolgee multilingual campaign support~~ DONE

### 25.4 Tolgee Frontend & Per-Locale Maizzle Builds `[Frontend]`
**What:** Frontend UI for Tolgee integration: translation key viewer/editor, locale build dashboard with per-locale QA results, side-by-side locale preview, and in-context translation overlay. Non-translators can see which text is translatable and what the email looks like in each language.
**Why:** Translation workflows fail when the translator can't see the email context. Tolgee's in-context translation pattern lets translators click on text in the email preview and translate it directly — no switching between spreadsheet and email. Per-locale QA results catch locale-specific issues (text overflow in German, RTL layout breaks in Arabic) that english-only QA misses.
**Implementation:**
- Create `cms/apps/web/src/components/tolgee/` package:
  - `TranslationPanel.tsx` — main translation management panel:
    - Key list with source text, translation status per locale (translated, untranslated, machine-translated)
    - Inline translation editing for quick fixes
    - "Sync to Tolgee" button to push local edits
    - Translation progress bar per locale
    - Filter: by status (untranslated first), by section, by key
  - `LocalePreview.tsx` — side-by-side locale comparison:
    - Locale selector dropdown (flags + language names)
    - Split view: source locale left, target locale right
    - Rendered email preview per locale (using iframe)
    - "Build All" button → triggers per-locale Maizzle builds
  - `LocaleQAResults.tsx` — per-locale QA summary:
    - Matrix view: locales × QA checks with pass/fail indicators
    - Locale-specific issues highlighted (e.g., "German: Gmail clipping threshold exceeded by 3KB")
    - "Run QA for All Locales" batch action
  - `InContextOverlay.tsx` — translation overlay on email preview:
    - Hover over text in preview → tooltip showing translation key + current translation
    - Click → inline edit field → save → preview updates
    - Highlight untranslated strings with yellow background
    - Toggle overlay on/off via toolbar button
  - `TolgeeConnectionDialog.tsx` — connection setup dialog:
    - Tolgee URL input + PAT input
    - Test connection button
    - Project selector after successful connection
    - Language configuration (which locales to enable)
- Create `cms/apps/web/src/hooks/use-tolgee.ts` — SWR hooks:
  - `useTolgeeConnection()` — connection status
  - `useTranslationKeys(templateId)` — translatable keys for template
  - `useTranslations(templateId, locale)` — translations for a locale
  - `useLocaleBuild(templateId, locales)` — trigger locale builds
  - `useLocaleQA(templateId, locale)` — QA results for locale
- Add i18n keys across 6 locales — ~50 keys for translation UI labels
- SDK regeneration for Tolgee endpoints
**Security:** Tolgee PAT displayed as masked value in connection dialog. Translation edits go through text sanitization. In-context overlay is read-only unless user has developer/admin role. Locale preview iframe sandboxed.
**Verify:** Connect to Tolgee → translation keys extracted → view in panel → translate German → preview shows German text → QA checks pass. In-context overlay: hover → key shown → edit → translation saved. Side-by-side: English left, German right, layout intact. `make check-fe` passes.
- [x] ~~25.4 Tolgee frontend & per-locale Maizzle builds~~ DONE

### 25.5 Kestra Workflow Orchestration `[Backend]`
**What:** Integrate Kestra (open-source workflow orchestration engine) to replace the blueprint engine's ad-hoc pipeline scheduling with declarative YAML workflows. Each email build becomes a Kestra flow with typed inputs, conditional branching (skip Visual QA if no screenshots enabled), parallel task execution (run QA checks concurrently), automatic retry with backoff, and a full audit trail. Blueprint engine remains the node execution logic; Kestra handles scheduling, retries, and cross-workflow coordination.
**Why:** The blueprint engine (Phase 14) handles single-run orchestration well, but lacks: (1) scheduled recurring builds (weekly newsletter pipeline), (2) cross-workflow dependencies (design import → build → QA → approve → push to ESP), (3) production-grade retry with dead-letter queues, (4) workflow versioning and rollback. Kestra provides all of these as a self-hosted service with a web UI. The Hub becomes a set of Kestra tasks that Kestra orchestrates — separation of concerns.
**Implementation:**
- Create `app/workflows/` package:
  - `kestra_client.py` — `KestraClient(httpx.AsyncClient)`:
    - `async create_flow(namespace: str, flow_id: str, definition: dict) -> Flow` — register a workflow
    - `async trigger_execution(namespace: str, flow_id: str, inputs: dict) -> Execution` — start workflow execution
    - `async get_execution(execution_id: str) -> Execution` — poll execution status
    - `async list_executions(namespace: str, flow_id: str) -> list[Execution]` — execution history
    - `async get_logs(execution_id: str) -> list[LogEntry]` — execution logs
    - `Execution(id: str, status: str, started: datetime, ended: datetime | None, inputs: dict, outputs: dict, task_runs: list[TaskRun])`
    - Authentication: Kestra API token stored in settings (not per-user)
  - `tasks/` — Hub-specific Kestra task definitions:
    - `blueprint_run.py` — `BlueprintRunTask` — wraps `BlueprintService.create_run()` as Kestra task:
      - Input: brief text, project_id, template preferences
      - Output: blueprint run ID, generated HTML, QA score
      - Retry policy: 3 attempts with 30s backoff on LLM timeout/rate-limit
    - `qa_check.py` — `QACheckTask` — wraps `QAEngineService.run_checks()`:
      - Input: HTML, config overrides
      - Output: QA results, pass/fail, score
      - Conditional: skip if HTML is None (previous task failed)
    - `chaos_test.py` — `ChaosTestTask` — wraps chaos engine:
      - Input: HTML, profiles
      - Output: resilience score, failures
    - `esp_push.py` — `ESPPushTask` — wraps ESP sync:
      - Input: HTML, connection_id, template_name
      - Output: push result, remote template ID
    - `locale_build.py` — `LocaleBuildTask` — wraps Tolgee locale builder (25.3):
      - Input: template_id, locales
      - Output: per-locale HTML map
    - `approval_gate.py` — `ApprovalGateTask` — creates approval request and waits:
      - Input: template_id, approver_role
      - Output: approval status (blocks workflow until approved/rejected)
      - Implements Kestra's `pause` task type for human-in-the-loop
  - `flow_templates/` — pre-built YAML workflow templates:
    - `email_build_and_qa.yaml` — standard flow: blueprint run → QA → chaos test (parallel) → visual QA → result
    - `multilingual_campaign.yaml` — extract keys → await translations → parallel locale builds → per-locale QA → approval gate → ESP push per locale
    - `weekly_newsletter.yaml` — scheduled trigger (cron) → content pull → blueprint run → QA → approval → ESP push
    - `design_import_pipeline.yaml` — design sync → layout analysis → brief generation → blueprint run → visual comparison → approval
  - `schemas.py` — `WorkflowTriggerRequest`, `WorkflowStatusResponse`, `WorkflowListResponse`
- Modify `app/workflows/routes.py` — workflow endpoints:
  - `GET /api/v1/workflows` — list available workflow templates + custom workflows
  - `POST /api/v1/workflows/trigger` — trigger workflow execution with inputs, auth + `5/minute`
  - `GET /api/v1/workflows/{execution_id}` — execution status + task run details
  - `GET /api/v1/workflows/{execution_id}/logs` — execution logs
  - `POST /api/v1/workflows/flows` — create custom workflow from YAML (admin only)
  - `GET /api/v1/workflows/flows/{flow_id}` — get workflow definition
- Modify `app/main.py` — register Kestra task definitions on startup, sync flow templates to Kestra
- Config: `KESTRA__ENABLED: bool = False`, `KESTRA__API_URL: str = "http://localhost:8080"`, `KESTRA__API_TOKEN: str = ""`, `KESTRA__NAMESPACE: str = "merkle-email-hub"`, `KESTRA__DEFAULT_RETRY_ATTEMPTS: int = 3`, `KESTRA__DEFAULT_RETRY_BACKOFF_S: int = 30`
**Security:** Kestra API token stored in settings (not in database — single instance token). Workflow inputs validated via Pydantic schemas before passing to Kestra. Custom workflow YAML validated against allowlist of Hub task types — no arbitrary script execution. Approval gate tasks enforce RBAC. Kestra runs as a separate Docker service — network-isolated from public internet (accessible only from Hub backend). Workflow logs may contain template content — same data classification as blueprint run logs.
**Verify:** Trigger `email_build_and_qa` flow → blueprint runs → QA checks run → results returned via status endpoint. Flow with LLM timeout → retries 3 times → succeeds on retry 2. `multilingual_campaign` flow → locale builds run in parallel → per-locale QA → approval gate pauses workflow → approve → ESP push completes. Scheduled `weekly_newsletter` → executes on cron schedule. Custom workflow YAML with invalid task type → rejected. `make test` passes.
- [x] ~~25.5 Kestra workflow orchestration~~ DONE

### 25.6 Penpot Design-to-Email Pipeline `[Backend]`
**What:** Self-hosted, API-driven design-to-email pipeline using Penpot's CSS-native design primitives. Replaces or supplements Figma import (Phase 12) with a zero-cost, self-hosted alternative. Uses Penpot's API to extract components, layouts, typography, and colors — converting them to Hub components and design system tokens. Leverages Penpot's native CSS output (unlike Figma which requires translation from proprietary format).
**Why:** Figma charges per-editor ($15-75/month/seat) and restricts API access on lower tiers. Penpot is open-source, self-hosted, and outputs native CSS — making the design-to-email conversion more accurate (no Figma-to-CSS translation layer). For enterprises already using Penpot (growing in EU due to GDPR/data sovereignty), this is the natural design import path. The Hub's existing design sync protocol (Phase 12) provides the abstraction layer — Penpot becomes a second implementation alongside Figma.
**Implementation:**
- Create `app/design_sync/penpot/` package:
  - `client.py` — `PenpotClient(httpx.AsyncClient)`:
    - `async list_projects() -> list[PenpotProject]` — list Penpot projects via API
    - `async get_file(file_id: str) -> PenpotFile` — get file with pages, components, colors
    - `async get_components(file_id: str) -> list[PenpotComponent]` — extract component library
    - `async export_svg(file_id: str, object_id: str) -> bytes` — export node as SVG
    - `async export_css(file_id: str, object_id: str) -> str` — get CSS for a design element (Penpot native feature)
    - `async get_colors(file_id: str) -> list[PenpotColor]` — shared color library
    - `async get_typography(file_id: str) -> list[PenpotTypography]` — typography styles
    - Authentication: Penpot access token stored encrypted in `DesignConnection` (reusing Phase 12 model)
    - Base URL: configurable for self-hosted instances
  - `converter.py` — `PenpotToEmailConverter`:
    - `convert_component(component: PenpotComponent) -> ComponentVersion` — convert Penpot component to Hub component:
      - Extract CSS from Penpot's native CSS output (no Figma translation needed)
      - Convert CSS layout to email-safe HTML: flexbox → table (using CSS compiler from 19.3), grid → table
      - Map Penpot layers to HTML elements: frame → `<table>`, text → `<td>`, image → `<img>`, rectangle → `<div>` with background
      - Preserve Penpot component variants as Hub `ComponentVersion` compatibility configurations
    - `convert_colors(colors: list[PenpotColor]) -> BrandPalette` — map to design system colors (11.25.1)
    - `convert_typography(typography: list[PenpotTypography]) -> Typography` — map to design system fonts
    - `convert_layout(page: PenpotPage) -> LayoutAnalysis` — reuse layout analyzer (12.4) with Penpot-specific section detection
  - `sync_provider.py` — `PenpotSyncProvider` implementing `DesignSyncProtocol` (Phase 12 protocol):
    - `async list_files(connection_id: int) -> list[DesignFile]` — Penpot files as `DesignFile`
    - `async import_design(file_id: str, connection_id: int) -> DesignImport` — full import pipeline
    - `async extract_components(file_id: str, connection_id: int) -> list[Component]` — component extraction
    - Reuses existing `DesignImportService` workflow (create import → analyze layout → generate brief → convert)
  - `schemas.py` — Penpot-specific request/response schemas
- Modify `app/design_sync/routes.py` — add Penpot connection type:
  - `POST /api/v1/design-sync/connections` — already supports `provider` field, add `"penpot"` option
  - Penpot connections use same endpoints as Figma: file browser, import, component extraction
- Modify `app/design_sync/service.py` — register `PenpotSyncProvider` alongside `FigmaSyncProvider`
- Config: `DESIGN_SYNC__PENPOT_ENABLED: bool = False`, `DESIGN_SYNC__PENPOT_BASE_URL: str = "http://localhost:9001"`
**Security:** Penpot access token stored encrypted (Fernet). Penpot API calls use HTTPS (or internal network for self-hosted). CSS output from Penpot validated and sanitized before use in email HTML. SVG exports validated (no scripts, no external references — same validation as BIMI SVG in 20.4). BOLA protection on design connections.
**Verify:** Connect to self-hosted Penpot → list projects → browse files → import design → layout analyzed → brief generated → Scaffolder produces email matching design. Component extraction: Penpot components → Hub components with valid HTML. Color extraction: Penpot shared colors → design system palette. Typography: Penpot text styles → design system fonts. CSS conversion: Penpot flexbox → email table layout. `make test` passes.
- [x] ~~25.6 Penpot design-to-email pipeline~~ DONE

### 25.7 Typst QA Report Generator `[Backend]`
**What:** Programmatic PDF generation for QA reports and client approval packages using Typst (Rust-based typesetting system, <100ms per document). Auto-generates branded PDF reports from Hub QA results, including visual regression screenshots, chaos test summaries, deliverability scores, and agent decision traces. Output suitable for client presentations and compliance archives.
**Why:** Clients and compliance teams need PDF reports — not dashboard links. Currently, QA results exist only in the Hub UI. Typst replaces LaTeX/wkhtmltopdf with a modern, fast, programmable alternative. A single QA report PDF containing all check results, screenshots, and recommendations is the deliverable that justifies the Hub's value to stakeholders who never log into the platform.
**Implementation:**
- Create `app/reporting/` package:
  - `typst_renderer.py` — `TypstRenderer`:
    - `async render(template_name: str, data: dict) -> bytes` — compile Typst template with data to PDF
    - Uses `typst` CLI via subprocess: `typst compile input.typ output.pdf --font-path fonts/`
    - Template + data merged: Typst templates use `#import "data.json"` for dynamic content
    - Temporary files: write `.typ` + `data.json` to temp directory, compile, read PDF, cleanup
    - Font embedding: Hub brand fonts bundled in `app/reporting/fonts/` for consistent rendering
    - Compilation timeout: 10s (Typst compiles ~100 pages in <1s — 10s is generous safety margin)
  - `templates/` — Typst report templates:
    - `qa_report.typ` — full QA report:
      - Cover page: project name, template name, date, Hub logo
      - Executive summary: overall pass/fail, score, top 3 issues
      - Check-by-check results: table with check name, status, score, details
      - Visual regression section: screenshot comparison grid (if available)
      - Chaos test results: resilience score bar chart, per-profile breakdown
      - Deliverability section: score gauge, dimension breakdown
      - Agent decisions: which agents contributed, key decisions made
      - Recommendations: prioritized fix list with estimated effort
    - `approval_package.typ` — client approval document:
      - Email preview renders (desktop, mobile, Outlook)
      - QA summary (pass/fail only — no technical details)
      - Brand compliance confirmation
      - Signature/approval section
    - `regression_report.typ` — visual regression comparison:
      - Baseline vs current screenshots side-by-side
      - Diff highlights
      - Changed regions annotated
  - `report_builder.py` — `ReportBuilder`:
    - `async build_qa_report(qa_run_id: int) -> bytes` — fetch QA results, screenshots, chaos data → compile PDF
    - `async build_approval_package(template_id: int, qa_run_id: int) -> bytes` — fetch template + QA → compile PDF
    - `async build_regression_report(entity_type: str, entity_id: int) -> bytes` — fetch baselines + current → compile PDF
    - Data assembly: queries QA engine, rendering service, blueprint service for all report data
    - Image embedding: screenshots base64-decoded and embedded in Typst as inline images
  - `schemas.py` — `ReportRequest(report_type: str, qa_run_id: int | None, template_id: int | None)`, `ReportResponse(pdf_base64: str, filename: str, size_bytes: int, generated_at: datetime)`
- Create `app/reporting/routes.py` — report endpoints:
  - `POST /api/v1/reports/qa` — generate QA report PDF with auth + `5/minute`
  - `POST /api/v1/reports/approval` — generate approval package PDF with auth + `5/minute`
  - `POST /api/v1/reports/regression` — generate regression report PDF with auth + `5/minute`
  - `GET /api/v1/reports/{report_id}` — retrieve previously generated report (cached in Redis for 24h)
- Modify `app/main.py` — register reporting routes
- Config: `REPORTING__ENABLED: bool = False`, `REPORTING__TYPST_BINARY: str = "typst"`, `REPORTING__CACHE_TTL_H: int = 24`, `REPORTING__MAX_REPORT_SIZE_MB: int = 50`
**Security:** Typst CLI runs as subprocess with fixed arguments — no user input in command. Report data sourced from authenticated API calls — BOLA enforced on all data fetches. PDF output is a binary document — no executable content. Temporary files written to OS temp directory with restricted permissions, deleted after compilation. Report cache uses Redis with TTL — auto-expiry prevents stale data. Rate limited to prevent CPU abuse.
**Verify:** Generate QA report for a template with 11 checks → PDF output with all sections populated. Generate approval package → client-friendly PDF without technical jargon. Report with screenshots → images embedded correctly. Report with no visual regression data → section gracefully omitted. Typst compilation completes in <1s for standard report. Cached report retrieved without recompilation. `make test` passes.
- [x] ~~25.7 Typst QA report generator~~ DONE

### 25.8 Frontend Ecosystem Dashboard `[Frontend]`
**What:** Unified frontend dashboard for plugin management, Tolgee translations, Kestra workflows, Penpot design sync, and report generation. Extends the workspace with ecosystem-level views that surface cross-cutting information: active workflow executions, translation progress, plugin health, and generated reports.
**Why:** Each integration (plugins, Tolgee, Kestra, Penpot, Typst) adds backend capabilities — the frontend must surface them in a unified experience. A fragmented UI with separate pages per integration creates cognitive overhead. The ecosystem dashboard provides a single view of "what's happening across all integrations" with drill-down into specifics.
**Implementation:**
- Create `cms/apps/web/src/components/ecosystem/` package:
  - `EcosystemDashboard.tsx` — main dashboard page:
    - Four-quadrant layout: Plugins (top-left), Workflows (top-right), Translations (bottom-left), Reports (bottom-right)
    - Each quadrant shows summary stats + 3 most recent items + "View All" link
    - Real-time updates via SWR polling (30s interval for workflows, 60s for others)
  - `PluginManagerPanel.tsx` — plugin administration:
    - Plugin list: name, type, status (active/disabled/error), version, health indicator
    - Enable/disable toggle per plugin
    - Plugin config editor (JSON form generated from `config_schema`)
    - "Install Plugin" dialog: upload plugin zip or enter Git URL
    - Health dashboard: per-plugin health history graph
    - Admin-only access
  - `WorkflowPanel.tsx` — Kestra workflow management:
    - Active executions: list with status, progress, elapsed time
    - Workflow templates: available flows with "Trigger" button
    - Execution detail: task run timeline (Gantt-style), logs viewer, input/output inspector
    - Scheduled workflows: cron expression display, next run time, enable/disable
  - `ReportPanel.tsx` — report generation and history:
    - "Generate Report" dialog: select report type, template, QA run
    - Report history: list with type, date, size, download button
    - PDF preview: embedded `<iframe>` with PDF viewer
    - Batch generation: "Generate reports for all templates in project"
  - `PenpotPanel.tsx` — Penpot connection management:
    - Connection status + project browser (reuses `DesignFileBrowser` from 12.7)
    - Quick import actions: "Import Design" → triggers design import pipeline
    - Component sync status: last sync time, component count
- Create SWR hooks: `use-plugins.ts`, `use-workflows.ts`, `use-reports.ts`, `use-penpot.ts`
- Add navigation: "Ecosystem" entry in main sidebar navigation (below existing entries)
- Add i18n keys across 6 locales — ~70 keys
- SDK regeneration for all new endpoints
**Security:** Plugin management requires admin role. Workflow triggers require developer/admin role. Report downloads validated for ownership (BOLA). PDF preview uses sandboxed iframe.
**Verify:** Ecosystem dashboard loads with all four quadrants populated. Plugin manager: install → enable → health check passes → disable. Workflow panel: trigger flow → execution appears → progress updates → completion. Report panel: generate QA report → PDF appears in history → download works → preview renders. Penpot panel: connect → browse files → import design. `make check-fe` passes.
- [x] ~~25.8 Frontend ecosystem dashboard~~ **DONE**

### 25.9 Tests & Documentation `[Full-Stack]`
**What:** Comprehensive test suite for plugin architecture (manifest validation, discovery, sandbox execution, lifecycle, registry integration), Tolgee (client, key extraction, locale builds, RTL handling), Kestra (client, task execution, flow templates, retry logic), Penpot (client, CSS conversion, component extraction, design sync protocol compliance), Typst (template compilation, data assembly, report correctness), and ecosystem dashboard. ADR-012 documenting platform ecosystem architecture.
**Implementation:**
- Create `app/plugins/tests/` — 30+ tests:
  - `test_manifest.py` — manifest parsing, validation, version compatibility
  - `test_discovery.py` — directory scanning, conflict detection, hot reload
  - `test_registry.py` — plugin registration per type, unregister, list
  - `test_sandbox.py` — timeout enforcement, error isolation, resource tracking
  - `test_lifecycle.py` — startup ordering, health checks, auto-disable
  - `test_api.py` — permission enforcement, API surface correctness
  - Sample plugin: `tests/fixtures/sample_qa_plugin/` with `plugin.yaml` + Python module
- Create `app/connectors/tolgee/tests/` — 20+ tests:
  - `test_client.py` — API calls (mocked httpx), auth, error handling
  - `test_extractor.py` — key extraction from HTML, ICU format preservation, skip rules
  - `test_builder.py` — locale builds, RTL handling, text expansion detection
  - Route tests for all Tolgee endpoints
- Create `app/workflows/tests/` — 20+ tests:
  - `test_kestra_client.py` — API calls (mocked httpx), flow CRUD, execution polling
  - `test_tasks.py` — each task type with mocked service calls, retry logic
  - `test_flow_templates.py` — YAML validation, task type allowlist enforcement
  - Route tests for workflow endpoints
- Create `app/design_sync/penpot/tests/` — 15+ tests:
  - `test_client.py` — API calls, auth, file listing
  - `test_converter.py` — CSS conversion, component mapping, layout analysis
  - `test_sync_provider.py` — protocol compliance with `DesignSyncProtocol`
- Create `app/reporting/tests/` — 15+ tests:
  - `test_typst_renderer.py` — compilation, timeout, temp file cleanup
  - `test_report_builder.py` — data assembly, image embedding, section omission
  - Route tests for report endpoints
- Frontend tests (Vitest + Testing Library):
  - `ecosystem-dashboard.test.tsx`, `plugin-manager.test.tsx`, `workflow-panel.test.tsx`, `report-panel.test.tsx`
- ADR-012 in `docs/ARCHITECTURE.md` — Platform Ecosystem Architecture
- SDK regeneration with all new types
- Target: 110+ tests
**Verify:** `make test` passes with all new tests. `make check-fe` passes. `make check` all green. No regression in existing test suite. SDK types match API responses.
- [x] ~~25.9 Tests & documentation~~ **DONE**

### 25.10 Template Learning Pipeline — Self-Serve HTML Upload `[Full-Stack]`
**What:** Allow email developers to upload production HTML templates via UI or API. The system automatically extracts patterns, registers them as golden templates with slot definitions, generates eval test cases, and propagates knowledge to agent skills and CRAG retrieval.
**Why:** Currently, adding a new template requires code changes: hand-write slot definitions, add to `TemplateRegistry`, create eval cases. This bottleneck means the system only learns from templates that engineers explicitly add. In practice, email teams have hundreds of battle-tested templates from years of production sends — each encoding hard-won knowledge about client quirks, layout patterns, and ESP-specific tricks. Self-serve upload turns every production template into agent training data. The competitive moat is that the system gets smarter with use — every uploaded template improves scaffolder selection, CRAG knowledge retrieval, and QA accuracy.
**Dependencies:** Phase 24B (HTML import annotation from 24.9), Phase 11.25 (design system extraction), Knowledge base (RAG embeddings).
**Design principle:** Upload is one click. Everything else is automatic. Developer can review and adjust extracted metadata, but the defaults should be 90% correct. Templates are never executed — only analyzed statically.
**Implementation:**
- Create `app/templates/upload/` — template upload pipeline:
  - `analyzer.py` — static HTML analysis: detect sections (reuse 24.9 section annotator), extract slot positions from content blocks, infer slot types (text, image, CTA, URL) from tag context + aria roles + content patterns, detect design tokens (colors, fonts, spacing from inline styles), detect ESP platform from personalisation syntax, measure structural complexity (column count, nesting depth, MSO conditional presence)
  - `slot_extractor.py` — convert detected content regions into `SlotDefinition` objects: identify repeating patterns (e.g., product cards → slot with `max_items`), detect required vs optional slots (hero image = required, social links = optional), extract `max_chars` from container width heuristics
  - `token_extractor.py` — extract `DefaultTokens` from inline styles: build color palette from all hex values with role inference (most-used bg color → `background`, button bg → `cta`, link color → `link`), extract font stacks, spacing values. Reuse `resolve_color_map()` pattern from design system
  - `template_builder.py` — assemble `GoldenTemplate` from analysis: generate unique template name from subject line or content heuristic, set `layout_type` (newsletter, promotional, transactional, retention) from structural signals, set `column_count` from detected layout, generate `display_name` and `description`
  - `eval_generator.py` — auto-generate eval test cases from uploaded template: create 3-5 synthetic briefs that would plausibly select this template, extract expected slot fills from existing content, generate golden assembly output for regression testing, append to `app/ai/agents/evals/synthetic_data_scaffolder.py`
  - `knowledge_injector.py` — create knowledge base entry: extract email-development-relevant patterns (e.g., "uses VML background images for Outlook", "CSS grid with table fallback", "Braze connected_content for dynamic pricing"), chunk into knowledge documents with embeddings, tag with relevant categories (`css_support`, `client_quirks`, `best_practices`), make available to CRAG retrieval for all agents
- Create `app/templates/upload/routes.py` — REST API:
  - `POST /api/v1/templates/upload` — accept HTML file (max 2MB), return analysis preview
  - `POST /api/v1/templates/upload/{id}/confirm` — confirm and register template after developer review
  - `GET /api/v1/templates/upload/{id}/preview` — preview extracted metadata before confirmation
  - `DELETE /api/v1/templates/upload/{id}` — reject and discard
- Create `cms/apps/web/src/components/templates/upload/` — frontend:
  - `TemplateUploadDialog.tsx` — drag-and-drop HTML file upload with live preview
  - `TemplateAnalysisPreview.tsx` — shows detected sections, slots, tokens, ESP platform; developer can adjust before confirming
  - `TemplateSlotEditor.tsx` — inline editor for slot definitions (rename, change type, set required/optional, set max_chars)
  - `TemplatePalettePreview.tsx` — visual color swatch display of extracted palette with role assignments
- Modify `app/ai/templates/__init__.py` — `TemplateRegistry`:
  - Add `register_uploaded(template: GoldenTemplate, source: str) -> None` — registers template from upload pipeline
  - Add `source` metadata field to `GoldenTemplate` — `"builtin"` vs `"uploaded"` for provenance tracking
  - Uploaded templates are project-scoped by default (not global) unless admin promotes
- Modify `app/ai/agents/scaffolder/pipeline.py`:
  - `_layout_pass` includes uploaded templates in selection (with `[uploaded]` tag in the prompt so LLM knows provenance)
  - Weight uploaded templates lower initially, increase weight as eval pass rate improves (earned trust)
**Security:** Uploaded HTML is sanitized with nh3 before analysis (XSS prevention). Template content is analyzed but never executed. Eval test cases use synthetic data only. Knowledge base entries are text summaries, not raw HTML. File size capped at 2MB. Rate limited (5 uploads/hour per user). Admin approval required for global promotion.
**Verify:** Upload a Braze newsletter template → system detects 5 sections, 12 slots, Liquid platform, 6-color palette → developer confirms → template appears in scaffolder selection → scaffolder can select it for matching briefs → CRAG retrieval surfaces template patterns when agents process similar emails. Upload a Mailchimp promotional template → different slot structure detected → eval cases generated → `make eval-golden` includes new template.
- [x] ~~25.10 Template learning pipeline (backend)~~ **DONE**

### 25.11 Automatic Skill Extraction from Templates `[Backend]`
**What:** When a template is uploaded (25.10), automatically analyze its HTML patterns and generate agent skill file amendments. Detected patterns like "VML bulletproof buttons", "CSS grid with table fallback", or "Gmail-safe responsive images" become learnable knowledge that updates agent SKILL.md files.
**Why:** Agent skills are currently hand-written by engineers who read email client documentation and encode patterns into SKILL.md files. This is slow, incomplete, and doesn't capture production-tested techniques. Every uploaded template embodies real-world email development knowledge — the system should learn from it automatically. This closes the feedback loop: developers build templates → upload to Hub → Hub agents learn the patterns → agents produce better output → developers upload more. The competitive advantage is compounding: each template makes the system smarter.
**Dependencies:** Phase 25.10 (template upload), Agent skills infrastructure (SKILL.md files + L3 skill files), Eval system (amendment suggester).
**Design principle:** Extract patterns with high confidence only — it's better to miss a pattern than to add an incorrect skill entry. All extracted skills are staged for developer review before applying. Skills are attributed to source template for traceability.
**Implementation:**
- Create `app/ai/skills/extractor.py` — pattern extraction engine:
  - `extract_patterns(html: str, analysis: TemplateAnalysis) -> list[SkillPattern]`
  - `SkillPattern` dataclass: `pattern_name`, `category` (outlook_fix, dark_mode, responsive, accessibility, performance), `description`, `html_example`, `confidence`, `source_template_id`, `applicable_agents` (list of agent names)
  - Pattern detectors (each is a function that scans HTML):
    - `detect_vml_patterns()` — VML shapes (`v:roundrect`, `v:rect`, `v:oval`), VML fills, VML textboxes → skill entries for `outlook_fixer`
    - `detect_mso_conditionals()` — MSO version targeting (`<!--[if gte mso 9]>`), ghost tables, DPI scaling → skill entries for `outlook_fixer`, `scaffolder`
    - `detect_dark_mode_patterns()` — `prefers-color-scheme` media queries, `[data-ogsc]`/`[data-ogsb]` Outlook selectors, `color-scheme` meta, image swap patterns, inverted logo handling → skill entries for `dark_mode`
    - `detect_responsive_patterns()` — fluid width tables, `max-width` on containers, media queries for breakpoints, stacking column patterns, font-size clamp patterns → skill entries for `scaffolder`
    - `detect_accessibility_patterns()` — `role="presentation"` on layout tables, `aria-label` on links, `lang` attributes, heading hierarchy, scope attributes → skill entries for `accessibility`
    - `detect_esp_patterns()` — Liquid control flow patterns (if/for/case), AMPscript patterns, merge tag patterns, conditional content blocks, dynamic image URLs → skill entries for `personalisation`
    - `detect_performance_patterns()` — image lazy loading, CSS minification, unused CSS removal, Gmail-safe class naming conventions, `display:none` for preheader → skill entries for `code_reviewer`
    - `detect_progressive_enhancement()` — flexbox with table fallback, grid with block fallback, border-radius with VML, background-image with VML rect → skill entries for `scaffolder`, `outlook_fixer`
- Create `app/ai/skills/amendment.py` — skill file amendment pipeline:
  - `generate_amendments(patterns: list[SkillPattern]) -> list[SkillAmendment]`
  - `SkillAmendment` dataclass: `agent_name`, `skill_file` (SKILL.md or L3 file path), `section`, `content` (markdown to append), `confidence`, `source_pattern_id`
  - Deduplication: check existing skill content for similar patterns (semantic similarity via embeddings) — don't add duplicate entries
  - Conflict detection: flag if new pattern contradicts existing skill guidance
  - `apply_amendments(amendments: list[SkillAmendment], dry_run: bool = True) -> AmendmentReport`
  - Dry-run mode (default): generates diff preview without modifying files
  - Apply mode: appends pattern sections to skill files with `<!-- auto-extracted from template: {name} -->` attribution comments
- Create `app/ai/skills/routes.py` — API for skill amendment review:
  - `GET /api/v1/skills/amendments/pending` — list pending amendments from recent uploads
  - `POST /api/v1/skills/amendments/{id}/approve` — apply amendment to skill file
  - `POST /api/v1/skills/amendments/{id}/reject` — discard with reason
  - `POST /api/v1/skills/amendments/batch` — approve/reject multiple
- Integrate with eval system:
  - After skill amendments are applied, trigger targeted eval runs for affected agents
  - Compare pass rates before/after amendment — auto-revert if pass rate drops (eval-gated skill updates)
  - Record amendment impact in `traces/improvement_log.jsonl`
**Security:** Pattern extraction is static analysis only — no code execution. Amendments are staged, never auto-applied to production without review. Skill files are version-controlled — git revert available for any bad amendment. Rate limited to prevent skill file spam.
**Verify:** Upload template with VML bulletproof button → system extracts `vml_bulletproof_button` pattern → generates skill amendment for `outlook_fixer/skills/vml_reference.md` → developer approves → next eval run shows outlook_fixer handles similar patterns better. Upload template with CSS grid + table fallback → `progressive_enhancement` pattern extracted → scaffolder skill updated → eval confirms improved progressive tier generation.
- [x] ~~25.11 Automatic skill extraction from templates~~ **DONE**

### 25.12 Template-to-Eval Pipeline `[Backend]`
**What:** Automatically generate eval test cases from uploaded templates. Each uploaded template becomes a regression test ensuring the scaffolder can select it, fill its slots correctly, and assemble valid HTML that passes QA.
**Why:** The eval system currently has 10-14 synthetic test cases per agent, hand-written with artificial scenarios. Real production templates test dimensions that synthetic cases miss: actual slot configurations, real-world color palettes, production ESP syntax, battle-tested responsive patterns. Every uploaded template is a free, high-quality eval case. Over time, the eval suite grows proportionally with template diversity — 100 uploaded templates = 300-500 eval test cases covering real-world edge cases.
**Dependencies:** Phase 25.10 (template upload analysis), Eval system (`runner.py`, `judge_runner.py`, `golden_cases.py`).
**Design principle:** Generated test cases must be deterministic (no LLM calls during eval generation). Each test case validates a specific capability: template selection accuracy, slot fill quality, design token extraction, or assembly correctness. Cases are tagged with source template for traceability.
**Implementation:**
- Create `app/ai/agents/evals/template_eval_generator.py`:
  - `generate_eval_cases(template: GoldenTemplate, analysis: TemplateAnalysis) -> list[EvalCase]`
  - **Template selection cases** (1-2 per template):
    - Generate synthetic brief that should select this template (based on template's layout_type, column_count, sections)
    - Expected: scaffolder's layout pass returns this template name
    - Negative case: generate brief that should NOT select this template — verify it doesn't
  - **Slot fill cases** (1-2 per template):
    - Provide brief + template → verify all required slots are filled, slot content matches type constraints, personalisable slots are marked correctly
    - Validate slot content length vs `max_chars`
  - **Assembly cases** (1 per template — becomes a golden case):
    - Pre-built `EmailBuildPlan` with known fills + design tokens → assemble → verify output HTML structure matches expected (DOCTYPE, section count, slot content present, colors replaced)
    - This extends `golden_cases.py` — each uploaded template adds 1 golden case
  - **QA pass-through cases** (1 per template):
    - Assembled HTML from template → run all 13 QA checks → verify no unexpected failures
    - Captures the template's baseline QA profile (some templates may intentionally score lower on certain checks)
- Modify `app/ai/agents/evals/golden_cases.py`:
  - `load_golden_cases()` now also loads auto-generated cases from uploaded templates
  - Auto-generated cases stored in `app/ai/agents/evals/data/uploaded_golden/` as JSON files (one per template)
  - `make eval-golden` runs both built-in and uploaded golden cases
- Modify `app/ai/agents/evals/runner.py`:
  - `--include-uploaded` flag to include uploaded template cases in full eval runs
  - Template-sourced cases tagged with `source: "uploaded:{template_name}"` in traces
- Create `app/ai/agents/evals/template_eval_routes.py` — API:
  - `GET /api/v1/evals/templates` — list all template-sourced eval cases
  - `GET /api/v1/evals/templates/{template_id}/cases` — cases for a specific template
  - `DELETE /api/v1/evals/templates/{template_id}/cases` — remove cases (e.g., when template is deleted)
**Security:** Eval cases use synthetic data only — template HTML is analyzed but subscriber data is never included. Generated briefs are deterministic strings, not LLM output. Cases stored as JSON in the repo — version controlled.
**Verify:** Upload newsletter template → 5 eval cases auto-generated (2 selection, 1 fill, 1 golden, 1 QA) → `make eval-golden` includes the new golden case → passes. Upload 10 templates → 50 cases generated → eval suite coverage increases measurably. Delete a template → associated eval cases removed.
- [x] ~~25.12 Template-to-eval pipeline~~ **DONE**

### 25.13 Email Deliverability Intelligence `[Backend]`
**What:** Real-time deliverability risk scoring integrated into the QA pipeline. Analyzes email HTML for patterns that trigger spam filters, damage sender reputation, or cause inbox placement issues across major ISPs (Gmail, Microsoft, Yahoo/AOL). Goes beyond the existing `spam_score` check by incorporating structural analysis, authentication readiness, and ISP-specific heuristics.
**Why:** The current `spam_score` check uses 59 keyword triggers — it catches "FREE!!!" but misses structural deliverability risks: image-to-text ratio >60%, hidden text (white-on-white), excessive link density, missing List-Unsubscribe header prep, URL shortener usage, and Gmail Promotions tab triggers. These structural factors account for more inbox placement failures than keyword triggers. No existing tool combines HTML structural analysis with ISP-specific heuristics in the email build pipeline — most deliverability tools operate at the send/infrastructure level, not the content level.
**Dependencies:** Phase 24B (QA engine with 13 checks), Knowledge base (ISP behavior data).
**Design principle:** Actionable scoring with specific remediation. Don't just say "deliverability risk: medium" — say "image-to-text ratio is 72% (Gmail threshold: 60%). Add 3+ lines of text to body section." Every flag includes the specific ISP affected, the threshold violated, and a concrete fix.
**Implementation:**
- Create `app/qa_engine/checks/deliverability_intel.py` — enhanced deliverability check:
  - **Image-to-text ratio analysis**: calculate ratio from HTML structure (img tags area vs text content length), flag per ISP threshold (Gmail <60%, Microsoft <40% for new senders)
  - **Link density scoring**: count links per 100 words, flag if >3 (spam trigger for Yahoo/AOL), detect URL shorteners (bit.ly, tinyurl — major red flag), detect excessive tracking parameters
  - **Hidden content detection**: white-on-white text (color matches bg within 10% brightness), `font-size: 0`, `display: none` on content divs (vs legitimate preheader technique), `visibility: hidden`
  - **Authentication readiness**: detect if template includes DKIM-alignment-friendly structures, check for SPF-breaking patterns (embedded images from different domains), verify List-Unsubscribe-Post header placeholder present
  - **ISP-specific heuristics**:
    - Gmail: Promotions tab triggers (coupon codes, "shop now" CTAs, price displays >3 instances), engagement signals (personalization, interactive elements), structured data markup opportunities
    - Microsoft: SmartScreen patterns (new domain sensitivity, link count thresholds, attachment indicators)
    - Yahoo/AOL: sender reputation signals in HTML (consistent footer, physical address presence, unsubscribe link prominence)
  - **Structural red flags**: single large image email ("image-only email"), no plain-text fallback indicator, excessive HTML weight (>102KB Gmail clipping risk — already in file_size check, but now with Gmail-specific context), broken responsive design (no media queries + wide tables = mobile spam trigger)
- Create `app/qa_engine/deliverability_analyzer.py` — cached analysis:
  - `DeliverabilityAnalysis` dataclass: `image_text_ratio`, `link_density`, `hidden_content_count`, `auth_readiness_score`, `isp_risks` (dict per ISP), `structural_flags`, `overall_risk` (low/medium/high/critical)
  - ISP risk profiles loaded from `app/qa_engine/data/isp_profiles.yaml`
- Create `app/qa_engine/data/isp_profiles.yaml` — ISP-specific thresholds:
  - Gmail: image_ratio_max, link_density_max, promo_tab_triggers, clipping_threshold
  - Microsoft: smartscreen_link_max, new_sender_strictness, attachment_indicator_words
  - Yahoo: footer_requirements, unsubscribe_prominence_min, sender_reputation_signals
- Register as enhancement to existing `deliverability` check (currently disabled by default — this makes it useful)
**Security:** Analysis is static HTML parsing only. No network calls to ISPs. ISP profiles are developer-maintained YAML. No sender reputation data stored (that's infrastructure-level, not content-level).
**Verify:** Email with 80% images → flags "image-to-text ratio 80% exceeds Gmail threshold 60%". Email with 5 bit.ly links → flags "URL shorteners detected — major deliverability risk". Email with white-on-white hidden text → flags specific element. Clean email with balanced content → "deliverability risk: low" with no flags. `make test` passes.
- [x] ~~25.13 Email deliverability intelligence~~ **DONE**

### 25.14 Multi-Variant Campaign Assembly `[Backend]`
**What:** Generate A/B/n email variants from a single brief, with systematic variation of subject lines, CTAs, hero images, content length, and layout. Each variant includes predicted engagement differentiators and QA results. Integrates with the scaffolder pipeline to produce 2-5 variants in a single pipeline run.
**Why:** A/B testing is the most requested feature in email marketing, but creating variants is tedious: manually duplicate the email, change one element, re-QA, re-preview. The Hub can automate this because it already has structured plans (EmailBuildPlan), slot-level content generation, and deterministic assembly. Generating variants is just running the content pass multiple times with different strategies and assembling each. No other tool generates pre-QA'd, pre-rendered email variants from a single brief.
**Dependencies:** Phase 11.22 (structured output + EmailBuildPlan), Scaffolder pipeline, QA engine, Rendering profiles.
**Design principle:** Each variant must differ in a measurable, testable way. Not "slightly different wording" but "Variant A: urgency-driven CTA + short copy vs Variant B: benefit-driven CTA + long copy." The system explains WHY each variant exists and WHAT hypothesis it tests. Variants share the same design tokens and template — only content strategy varies.
**Implementation:**
- Create `app/ai/agents/scaffolder/variant_generator.py`:
  - `generate_variants(brief: str, plan: EmailBuildPlan, count: int = 3) -> list[VariantPlan]`
  - `VariantPlan` dataclass: `variant_id` (A/B/C/...), `strategy_name` (e.g., "urgency_driven", "benefit_focused", "social_proof"), `hypothesis` (testable statement), `slot_overrides` (dict of slot_id → alternate content), `subject_line`, `preheader`, `predicted_differentiator` (what makes this variant distinct)
  - Variant strategies (each is a prompt modifier for the content pass):
    - `urgency_driven` — time-limited language, scarcity cues, action-oriented CTAs
    - `benefit_focused` — outcome-oriented, feature→benefit transformation, longer explanatory copy
    - `social_proof` — testimonials, user counts, trust badges, case study references
    - `curiosity_gap` — question-based subject lines, partial reveals, "find out" CTAs
    - `personalization_heavy` — maximum use of personalisation slots, dynamic content blocks, conditional sections
    - `minimal` — short copy, single CTA, clean layout, mobile-optimized for quick scanning
  - Strategy selection: LLM picks top N strategies most relevant to the brief (e.g., a sale brief → urgency + social_proof + benefit)
- Create `app/ai/agents/scaffolder/schemas/variant.py`:
  - `VariantPlan` — as above
  - `VariantResult` — `variant_id`, `html`, `build_plan`, `qa_results`, `qa_passed`, `strategy_name`, `hypothesis`
  - `CampaignVariantSet` — `brief`, `base_plan`, `variants: list[VariantResult]`, `comparison_matrix` (side-by-side differences)
- Modify `app/ai/agents/scaffolder/pipeline.py`:
  - Add `execute_variants(brief, count=3) -> CampaignVariantSet`:
    - Run layout pass once (all variants share template + sections)
    - Run design pass once (all variants share design tokens)
    - Run content pass N times with different strategy prompts (parallelized)
    - Assemble N variants
    - QA all N variants in parallel
    - Generate comparison matrix (which slots differ, subject line differences, predicted A/B test outcomes)
  - Reuse pipeline checkpointing — if variant 3 fails, variants 1-2 are preserved
- Create `app/ai/agents/scaffolder/routes.py` additions:
  - `POST /api/v1/email/generate-variants` — brief + variant_count → CampaignVariantSet
  - `GET /api/v1/email/variants/{set_id}` — retrieve variant set
  - `GET /api/v1/email/variants/{set_id}/{variant_id}/preview` — render specific variant
- Create `cms/apps/web/src/components/variants/` — frontend:
  - `VariantComparisonView.tsx` — side-by-side preview of all variants with diff highlighting
  - `VariantStrategyCard.tsx` — shows strategy name, hypothesis, predicted differentiator
  - `VariantSelector.tsx` — pick which variants to export/send
**Security:** Variant generation uses the same sanitization pipeline as single-email generation. No additional attack surface. Variant count capped at 5 to prevent resource abuse. Rate limited (3 variant sets/hour per user).
**Verify:** Brief "Summer sale for premium subscribers" → 3 variants generated: urgency (countdown CTA), benefit (savings calculator), social proof (customer testimonials) → all 3 pass QA → side-by-side preview shows measurable differences in subject line, hero copy, CTA text. Single-template brief → all variants use same layout, only content differs. `make test` passes. `make eval-golden` passes.
- [x] ~~25.14 Multi-variant campaign assembly~~ **DONE**

### 25.15 Tests & Documentation for 25.10–25.14 `[Full-Stack]`
**What:** Test suite for template learning pipeline, skill extraction, template-to-eval, deliverability intelligence, and multi-variant assembly.
**Implementation:**
- `app/templates/upload/tests/` — 25+ tests:
  - `test_analyzer.py` — section detection, slot extraction, token extraction, ESP detection
  - `test_template_builder.py` — GoldenTemplate assembly, layout type inference, naming
  - `test_knowledge_injector.py` — knowledge document creation, embedding, CRAG retrieval
  - Route tests for upload API
- `app/ai/skills/tests/` — 15+ tests:
  - `test_extractor.py` — each pattern detector (VML, MSO, dark mode, responsive, accessibility, ESP, performance, progressive enhancement)
  - `test_amendment.py` — skill file amendment generation, deduplication, conflict detection
- `app/ai/agents/evals/tests/test_template_eval_generator.py` — 10+ tests:
  - Selection case generation, slot fill case generation, golden case generation, QA pass-through case generation
  - Case deletion on template removal
- `app/qa_engine/tests/test_deliverability_intel.py` — 15+ tests:
  - Image-to-text ratio calculation, link density scoring, hidden content detection, ISP-specific heuristics, auth readiness
- `app/ai/agents/scaffolder/tests/test_variant_generator.py` — 15+ tests:
  - Strategy selection, variant plan generation, parallel content pass, comparison matrix, QA per variant
- Target: 80+ tests
**Verify:** `make test` passes. `make check` all green. `make eval-golden` passes (no regression).
- [ ] 25.15 Tests & documentation for 25.10–25.14

---

## Security Checklist (Run Before Each Sprint Demo)

- [ ] All new endpoints have auth dependency injection
- [ ] All new endpoints have rate limiting configured
- [ ] All request schemas validate input (no raw strings to DB)
- [ ] All response schemas exclude sensitive fields
- [ ] No credentials in logs (grep for password, secret, key, token in log output)
- [ ] New database tables have appropriate RLS policies
- [ ] Frontend forms sanitise input before API calls
- [ ] Preview iframes use sandbox attribute
- [ ] Error responses don't leak internal details
- [ ] Audit entries created for all state-changing operations
- [ ] CORS configuration checked (no wildcards)
- [ ] Docker containers run as non-root
- [ ] New environment variables documented in `.env.example`

---

## Success Criteria (Updated)

| Metric | Phase 22 (Current) | Target (Phase 25) |
|--------|--------------------|--------------------|
| Campaign build time | Under 4 hours | Under 1 hour (Kestra parallel pipelines) |
| Cross-client rendering defects | Auto-fixed by VLM agent | Near-zero (property-tested + plugin checks) |
| Component reuse rate | 60%+ | 80%+ (plugin component packages) |
| AI agent count | 10 (Visual QA) | 12+ (plugin agents) |
| QA checks | 14 (resilience, deliverability, BIMI) | 16+ (plugin checks) |
| Ontology freshness | Auto-synced daily | Real-time change detection + plugin extensions |
| Outlook migration readiness | Automated advisor | Audience-aware phased plans |
| Gmail AI optimization | Summary prediction + schema.org | Full AI inbox optimization |
| Cloud AI API spend | Under £600/month (cost governor) | Under £600/month (budget caps + plugin cost tracking) |
| Email CSS output size | 15-25% smaller (CSS compiler) | Optimal per-client bundles |
| Knowledge base entries | 1000+ (auto-synced) | Self-growing (chaos findings + plugin contributions) |
| Multilingual campaigns | Manual per-locale builds | Automated via Tolgee (20+ locales) |
| Workflow orchestration | Single blueprint runs | Declarative YAML workflows (Kestra) |
| Design import sources | Figma only | Figma + Penpot (zero-cost self-hosted) |
| QA report delivery | Dashboard only | PDF reports (Typst, <100ms generation) |
| External tool integration | REST API only | MCP server (IDE-native, any MCP client) |
| Collaboration | Single-user editing | Real-time multi-user CRDT (visual + code) |
| Non-developer access | Code editor only | Visual drag-and-drop builder |
