# Incident Response

Procedures for triaging, resolving, and documenting production incidents.

---

## 1. Severity Classification

| Severity | Definition | Examples | Response Time |
|----------|-----------|----------|---------------|
| **S1** | Platform down — all users affected | All health checks failing, database unreachable, nginx 502 | Immediate |
| **S2** | Feature broken — specific functionality unavailable | AI generation failing, email export broken, one agent returning errors | <30 minutes |
| **S3** | Degraded performance — service slow but functional | API latency >5s p99, slow database queries, Redis timeouts | <2 hours |
| **S4** | Cosmetic — no functional impact | UI rendering glitch, incorrect log formatting, stale cache data | Next business day |

---

## 2. Triage Flowchart

Start here for any reported issue. Follow the decision tree top to bottom.

### Step 1: Check Readiness

```bash
curl -s http://localhost:8891/health/ready | python3 -m json.tool
```

| Response | Next Step |
|----------|-----------|
| `{"status":"ready","database":"connected","redis":"connected"}` | All core services up. Go to Step 4 (application-level). |
| `{"database":"connected","redis":"unavailable"}` | Redis is down. Go to **Redis Down** incident below. |
| 503 or connection refused | Core service(s) down. Go to Step 2. |

### Step 2: Identify Which Service Is Down

```bash
# Check individual health endpoints
curl -s http://localhost:8891/health        # App process alive?
curl -s http://localhost:8891/health/db     # Database reachable?
curl -s http://localhost:8891/health/redis  # Redis reachable?

# Check Docker service status
docker compose ps
```

| Service Status | Next Step |
|---------------|-----------|
| `app` unhealthy or exited | Go to **App Crash** incident below |
| `db` unhealthy or exited | Go to **Database Down** incident below |
| `redis` unhealthy or exited | Go to **Redis Down** incident below |
| `migrate` exited with code 1 | Go to **Migration Failure** incident below |
| `nginx` unhealthy | Check nginx config: `docker compose logs nginx --tail 20` |
| All healthy but 503 on `/health/ready` | Connection pool exhaustion. Go to **Connection Exhaustion** below |

### Step 3: Check Recent Changes

```bash
# Recent deploys
git log --oneline -5

# Recent container restarts
docker compose ps --format "table {{.Name}}\t{{.Status}}"

# Recent error logs
docker compose logs app --tail 50 2>&1 | grep -i error
```

### Step 4: Application-Level Issues

If all health checks pass but a feature is broken:

```bash
# Check app logs for the specific feature
docker compose logs app --tail 100 2>&1 | grep -i "<feature_name>"

# Check rate limiting
docker compose logs nginx --tail 50 2>&1 | grep "limiting"

# Check AI provider status
docker compose logs app --tail 50 2>&1 | grep -i "ai\|llm\|anthropic\|openai"
```

---

## 3. Common Incidents

### Migration Failure

**Symptoms:** `migrate` container exits with code 1. `app` never starts (waits for migration).

**Diagnosis:**
```bash
docker compose logs migrate --tail 30
```

Look for: `alembic.util.exc.CommandError`, constraint violations, missing columns.

**Resolution:**
```bash
# Check current migration state
uv run alembic current

# If the migration has a bug, fix it and re-run
docker compose restart migrate

# If the migration partially applied and left bad state:
# 1. Backup first
./scripts/backup-db.sh

# 2. Rollback the failed migration
./scripts/safe_alembic.sh downgrade -1 --i-know-what-i-am-doing

# 3. Fix the migration file
# 4. Re-run
uv run alembic upgrade head
```

---

### Database Down

**Symptoms:** `/health/db` returns 503. App logs show `ConnectionRefusedError` or `OperationalError`.

**Diagnosis:**
```bash
docker compose logs db --tail 30

# Check if PostgreSQL process is running inside container
docker compose exec db pg_isready -U postgres -d email_hub
```

**Resolution:**
```bash
# Restart PostgreSQL
docker compose restart db

# Wait for healthy (check every 5 seconds)
docker compose logs -f db

# If data corruption suspected:
# 1. Stop database
docker compose stop db

# 2. Restore from backup (see disaster-recovery.md)
./scripts/restore-db.sh

# 3. Start database
docker compose start db
```

---

### Redis Down

**Symptoms:** `/health/redis` returns 503. Rate limiting falls back to in-memory (single-worker only). Feature flags revert to defaults.

**Diagnosis:**
```bash
docker compose logs redis --tail 20

# Check Redis inside container
docker compose exec redis redis-cli ping
# Expected: PONG
```

**Resolution:**
```bash
# Restart Redis
docker compose restart redis

# Verify
curl -s http://localhost:8891/health/redis
# Expected: {"status":"healthy","service":"redis"}

# Re-set feature flags if they were non-default (see disaster-recovery.md section 5)
```

**Note:** Redis loss is low-impact. Rate limits reset (brief window of no limiting), caches rebuild on demand. Only feature flags need manual restoration if they differed from defaults.

---

### App Crash / OOM

**Symptoms:** `app` container repeatedly restarting. `/health` returns connection refused or 502 via nginx.

**Diagnosis:**
```bash
# Check exit reason
docker compose logs app --tail 50

# Check memory usage
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Common causes:
# - Memory limit (1024M) exceeded
# - Gunicorn worker timeout (120s)
# - Unhandled exception in startup
```

**Resolution:**
```bash
# If OOM: reduce workers temporarily
WEB_CONCURRENCY=1 docker compose up -d app

# If startup exception: check logs, fix code, redeploy
docker compose logs app --tail 100 2>&1 | grep "Error\|Exception\|Traceback"

# If worker timeout: check for long-running requests
docker compose logs app --tail 100 2>&1 | grep "WORKER TIMEOUT"
```

---

### AI Provider Outage

**Symptoms:** 502 or timeout on AI generation endpoints (`/api/v1/email/generate`, agent endpoints). Health checks pass (AI is not a health dependency).

**Diagnosis:**
```bash
# Check AI-related logs
docker compose logs app --tail 50 2>&1 | grep -i "ai\|anthropic\|openai\|timeout\|rate.limit"

# Check if fallback chain is configured
grep "FALLBACK_CHAINS" .env
```

**Resolution:**
1. Check provider status page (Anthropic, OpenAI)
2. If fallback chain is configured (`AI__FALLBACK_CHAINS`), verify the secondary provider works
3. If no fallback, temporarily switch provider:
   ```bash
   # Edit .env
   AI__PROVIDER=openai
   AI__API_KEY=sk-...
   AI__MODEL=gpt-4o-mini

   # Restart app
   docker compose restart app
   ```
4. Monitor: `docker compose logs -f app 2>&1 | grep -i ai`

---

### Database Connection Exhaustion

**Symptoms:** `/health/db` returns 503 intermittently. App logs show `QueuePool limit reached` or `TimeoutError`.

**Diagnosis:**
```bash
# Check active connections
docker compose exec db psql -U emailhub email_hub \
  -c "SELECT count(*) as connections FROM pg_stat_activity WHERE datname='email_hub';"

# Compare against pool size
# Default: POOL_SIZE (3) + POOL_MAX_OVERFLOW (5) = 8 max connections
grep "POOL" .env
```

**Resolution:**
```bash
# Immediate: restart app to release connections
docker compose restart app

# If recurring: increase pool size
# Edit .env:
# DATABASE__POOL_SIZE=10
# DATABASE__POOL_MAX_OVERFLOW=10
docker compose restart app

# Investigate: find slow queries holding connections
docker compose exec db psql -U emailhub email_hub \
  -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query
      FROM pg_stat_activity
      WHERE datname='email_hub' AND state != 'idle'
      ORDER BY duration DESC LIMIT 5;"
```

---

### Eval Pipeline Disagreement

**Symptoms:** Judge verdicts show >20% flip rate when re-judged. Eval regression gate fails.

**Diagnosis:**
```bash
# Compare verdicts
make eval-compare

# Or run directly
uv run python scripts/eval-compare-verdicts.py \
  traces/verdicts.json traces/verdicts-rejudge.json
```

**Resolution:**
1. Review flagged criteria in the comparison output
2. If the flip is expected (prompt improvement): reset baseline with `make eval-baseline`
3. If the flip is unexpected: review judge prompts in `app/ai/agents/evals/judges/`
4. For manual override: edit the verdict file directly and re-run `make eval-analysis`

---

## 4. Post-Incident

After resolving any S1 or S2 incident, write a brief.

### Create Incident Brief

```bash
mkdir -p docs/incidents
```

Create `docs/incidents/YYYY-MM-DD-short-title.md`:

```markdown
# Incident: [Short Title]

**Date:** YYYY-MM-DD HH:MM UTC
**Severity:** S1/S2/S3
**Duration:** X minutes
**Resolved by:** [name]

## Summary
One-paragraph description of what happened.

## Timeline
- HH:MM — Issue detected (how: alert / user report / monitoring)
- HH:MM — Triage started
- HH:MM — Root cause identified
- HH:MM — Fix applied
- HH:MM — Verified resolved

## Root Cause
What caused the incident.

## Resolution
What was done to fix it.

## Action Items
- [ ] Update runbook: [which section]
- [ ] Add monitoring for: [what]
- [ ] Preventive change: [what]
```

### Update Runbooks

If the incident revealed a gap in these procedures, update the relevant runbook immediately.
