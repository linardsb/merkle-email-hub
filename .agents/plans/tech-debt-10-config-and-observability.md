# Tech Debt 10 — Config Split + Observability Cleanup

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** `app/core/config.py` is 928 LOC and the #1 most-churned file. `.env.example` covers ~65 of 371 settings. Logging consistency drifts. Several misc High/Medium findings folded in.
**Goal:** Per-domain config files; auto-generated `.env.example`; drift-detection in CI; consistent structured logging.
**Estimated effort:** ½ day.
**Prerequisite:** Plans 01 + 05 landed (they delete dead config flags first, simplifying the split).

## Findings addressed

F032 (`app/core/config.py` 928 LOC, 50 nested classes) — High
F033 (`.env.example` 82% drift) — High
F034 (`extra="ignore"` silently drops typo'd env vars) — Medium
F035 (flag sprawl across BlueprintConfig/AIConfig/PipelineConfig/DESIGN_SYNC) — High
F036 (DB pool size 8 connections) — High
F058 (dynamic event names break `domain.action_state`) — Medium (already fixed in Plan 01)
F059 (PII redaction not applied to SQL echo + stdlib `extra=`) — Medium
F037 (Maizzle no retry/circuit breaker) — High
F036 connector finding (untested, deferred)

## Pre-flight

```bash
git checkout -b refactor/tech-debt-10-config-obs
make check
```

Snapshot all current settings:
```bash
python -c "from app.core.config import get_settings; \
  import json; print(json.dumps(get_settings().model_dump(mode='json'), indent=2))" \
  > /tmp/settings.before.json
```

## Part A — Split `app/core/config.py` (F032)

### A1. New layout

```
app/core/
  config/
    __init__.py        ← Settings root, get_settings(), env loading
    auth.py            ← AuthConfig
    database.py        ← DatabaseConfig
    ai.py              ← AIConfig + EmbeddingConfig + RerankerConfig + EvaluatorConfig
    blueprint.py       ← BlueprintConfig + (PipelineConfig if shipping; else delete per Plan 05)
    qa.py              ← QA*Config (8 sub-configs, see audit F036)
    design_sync.py     ← DesignSyncConfig (47 fields)
    knowledge.py       ← KnowledgeConfig
    connectors.py      ← ESPSyncConfig + CredentialsConfig + per-vendor configs
    notifications.py   ← NotificationsConfig
    scheduling.py      ← SchedulingConfig + DebounceConfig
    security.py        ← SecurityConfig
    rendering.py       ← RenderingConfig + visual diff
    misc.py            ← anything left over (LoggingConfig, EvalConfig, etc.)
```

`app/core/config.py` becomes a 5-line shim re-exporting `Settings` and `get_settings()` for backward compat OR is deleted.

### A2. Migration

For each sub-config:
1. Move the class definition.
2. Move its docstring.
3. Update `Settings` to nest it via field annotation.
4. Run `make types` to verify imports resolve.

### A3. Verify settings parity

```bash
python -c "from app.core.config import get_settings; \
  import json; print(json.dumps(get_settings().model_dump(mode='json'), indent=2))" \
  > /tmp/settings.after.json
diff /tmp/settings.before.json /tmp/settings.after.json  # MUST be empty
```

## Part B — Auto-generate `.env.example` (F033)

### B1. Generator script

**New file:** `scripts/generate-env-example.py`:
```python
"""Generate .env.example from Pydantic Settings model."""
from app.core.config import Settings, get_settings_default

def emit_field(name: str, field: FieldInfo, prefix: str = ""):
    env_name = f"{prefix}{name.upper()}"
    if field.is_complex():  # nested BaseSettings
        for sub_name, sub_field in field.annotation.model_fields.items():
            yield from emit_field(sub_name, sub_field, prefix=f"{env_name}__")
    else:
        default = field.default if field.default is not PydanticUndefined else "<required>"
        yield f"# {field.description or ''}"
        yield f"{env_name}={default}"

def main():
    for field_name, field in Settings.model_fields.items():
        for line in emit_field(field_name, field):
            print(line)
        print()

if __name__ == "__main__":
    main()
```

Wire into Make:
```make
.env.example: app/core/config/*.py
	uv run python scripts/generate-env-example.py > .env.example.tmp
	mv .env.example.tmp .env.example
```

### B2. CI drift gate

`.github/workflows/ci.yml`:
```yaml
- name: Check .env.example drift
  run: |
    uv run python scripts/generate-env-example.py > /tmp/env.generated
    diff .env.example /tmp/env.generated || \
      (echo "::error::.env.example out of sync — run 'make .env.example'" && exit 1)
```

## Part C — Strict env-var parsing (F034)

### C1. Switch to `extra="forbid"` outside test

`app/core/config/__init__.py`:
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="forbid" if os.getenv("ENVIRONMENT") != "test" else "ignore",
        env_file=".env",
    )
```

OR — preferred — keep `extra="ignore"` but add a startup hook that warns on unknown `*__*` env vars by listing the actual env keys and diffing against the model's expected keys.

### C2. Test

Set a typo'd env var (`AUT__JWT_SECRET_KEY=foo`); confirm startup either fails (forbid) or logs a warning (ignore + warn).

## Part D — Flag sprawl audit (F035)

### D1. Run `make flag-audit`

This target exists per CLAUDE.md. Output is at `traces/flag_audit.json` — per-flag age, last-modified date, hits.

### D2. Apply the 90-day / 180-day rule

Per `make flag-audit` output:
- Flags untouched > 180 days → delete the flag + the disabled branch.
- Flags 90-180 days → either flip the default or schedule removal in `feature-flags.yaml`.

Specific candidates for deletion (from audit):
- `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED` (Plan 01 already deletes)
- Other unused `BlueprintConfig` flags (see audit F035 list)

### D3. Group experimental flags

Move `_enabled: bool = False` flags that are genuine experiments into a `BlueprintExperimentsConfig` sub-model so the production `BlueprintConfig` is shorter.

## Part E — DB pool sizing (F036)

### E1. Adjust defaults

`app/core/config/database.py`:
```python
pool_size: int = Field(default=20, ge=1)
max_overflow: int = Field(default=20, ge=0)
pool_recycle: int = 1800  # 30 min
pool_pre_ping: bool = True
```

Total = 40 connections. Postgres default `max_connections` is 100; this leaves headroom for the maizzle sidecar's parallel dev, etc.

### E2. Document

`docs/scaling.md` (new section): explain pool sizing, when to increase, monitoring queries.

## Part F — Maizzle resilience (F037)

### F1. Wrap `_call_builder` with retries + circuit breaker

`app/email_engine/service.py:264`:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.resilience import CircuitBreaker

_maizzle_cb = CircuitBreaker(name="maizzle", failure_threshold=5, recovery_timeout=30)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
)
async def _call_builder(self, ...):
    async with _maizzle_cb:
        async with httpx.AsyncClient(timeout=30.0) as client:
            ...
```

Mirrors `app/rendering/service.py:16` pattern.

### F2. Stop snapshotting URL at import time

`app/email_engine/service.py:35-37` — move `MAIZZLE_BUILDER_URL = settings.maizzle_builder_url` into `_call_builder` body.

## Part G — Logging consistency (F058 + F059)

### G1. F058 was fixed in Plan 01

Verify no new dynamic event names introduced:
```bash
rg 'logger\.(info|warning|error)\(f"[a-z_.]+\.\{' app/ --type py
# Should return 0 hits.
```

### G2. F059: SQL echo bypasses redaction

`app/core/config/database.py`:
```python
echo: bool = False  # never enable in shared logs; structlog redaction does not cover SQLAlchemy logger
```

If dev-time SQL inspection is needed, wire SQLAlchemy logger through structlog's `processors.UnicodeDecoder` + `redact_event_dict`.

### G3. F059: stdlib `logger.error(extra=…)` in `app/core/exceptions.py:111`

Replace stdlib calls with `structlog.get_logger().error(...)` so `redact_event_dict` runs.

## Verification

```bash
make check
diff /tmp/settings.before.json /tmp/settings.after.json    # empty
make .env.example                                          # regen clean
git diff .env.example                                      # only intentional changes
make flag-audit                                            # passes thresholds
```

## Rollback

Each part is an independent revert. Part A (config split) is the most invasive; if anything fails, revert and the shim re-export keeps existing imports working.

## Risk notes

- **Part A breaks every `from app.core.config import …` of a sub-config.** Run `rg "from app.core.config import" app/` before; update each importer in the same PR.
- **Part B `.env.example` regen will produce a large diff** the first time. Review carefully — operators rely on this file. Don't lose comments.
- **Part C `extra="forbid"` is risky** in environments that set platform-specific env vars (PaaS-injected). Keep `ignore` + warning instead if your hosting platform injects extras.
- **Part E pool size bump** can saturate Postgres. Coordinate with infra; check `pg_stat_activity` after deploy.
- **Part F retry on Maizzle** can mask real failures. Add metric `maizzle.retry_count` and alert if >X/min.

## Done when

- [ ] `app/core/config/` package exists; root `config.py` is a shim or removed.
- [ ] `make .env.example` regenerates clean; CI gate added.
- [ ] Typo'd env var either fails startup or logs a warning.
- [ ] `make flag-audit` passes (no flags >180d untouched).
- [ ] DB pool 20+ connections.
- [ ] Maizzle calls wrapped in tenacity + circuit breaker.
- [ ] Zero dynamic-name `domain.{value}.event` log calls.
- [ ] `make check` green.
- [ ] PR titled `refactor(core): split config + .env drift gate + Maizzle resilience (F032 F033 F036 F037)`.
- [ ] Mark F032, F033, F034, F035, F036, F037, F058, F059 as **RESOLVED**.
