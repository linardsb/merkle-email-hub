# Performance Tuning

Configuration knobs and monitoring commands for each infrastructure layer.

---

## 1. PostgreSQL

### Connection Pool

The application uses SQLAlchemy async connection pooling.

| Variable | Default | Rule of Thumb | Description |
|----------|---------|--------------|-------------|
| `DATABASE__POOL_SIZE` | 3 | 2 x CPU cores | Minimum persistent connections |
| `DATABASE__POOL_MAX_OVERFLOW` | 5 | 1-2 x pool_size | Burst connections above pool_size |
| `DATABASE__POOL_RECYCLE` | 3600 | 1800-3600 | Recycle idle connections (seconds) |

**Example for a 4-core machine:**
```env
DATABASE__POOL_SIZE=8
DATABASE__POOL_MAX_OVERFLOW=8
DATABASE__POOL_RECYCLE=1800
```

### Monitoring

```bash
# Active connections
docker compose exec db psql -U emailhub email_hub \
  -c "SELECT count(*) as total,
      count(*) FILTER (WHERE state = 'active') as active,
      count(*) FILTER (WHERE state = 'idle') as idle
      FROM pg_stat_activity WHERE datname = 'email_hub';"

# Long-running queries (>5 seconds)
docker compose exec db psql -U emailhub email_hub \
  -c "SELECT pid, now() - query_start AS duration, left(query, 80) as query
      FROM pg_stat_activity
      WHERE datname = 'email_hub' AND state = 'active'
        AND now() - query_start > interval '5 seconds'
      ORDER BY duration DESC;"

# Table sizes (identify bloat)
docker compose exec db psql -U emailhub email_hub \
  -c "SELECT relname as table, pg_size_pretty(pg_total_relation_size(relid)) as size
      FROM pg_catalog.pg_statio_user_tables
      ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;"
```

### PostgreSQL Server Tuning

If using a custom `postgresql.conf` (not the Docker default):

| Parameter | Guideline | Description |
|-----------|-----------|-------------|
| `shared_buffers` | 25% of RAM | Shared memory for caching (e.g., 64M for 256M container) |
| `work_mem` | 4-16 MB | Per-sort/hash memory (careful: multiplied by concurrent queries) |
| `effective_cache_size` | 50-75% of RAM | Planner hint for OS cache availability |
| `maintenance_work_mem` | 64-256 MB | For VACUUM, CREATE INDEX (set higher for large tables) |

**Check current settings:**
```bash
docker compose exec db psql -U emailhub email_hub \
  -c "SHOW shared_buffers; SHOW work_mem; SHOW effective_cache_size;"
```

---

## 2. Redis

### Memory Management

| Variable | Default | Description |
|----------|---------|-------------|
| `maxmemory` | 128M (Docker limit) | Maximum memory Redis will use |
| `maxmemory-policy` | `noeviction` (Redis default) | What happens when maxmemory is reached |

**Recommended production policy:** `allkeys-lru` — evicts least-recently-used keys when memory is full. Safe because most Redis data in this app is cache/ephemeral.

```bash
# Check current memory usage
docker compose exec redis redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human|maxmemory_policy"

# Set eviction policy at runtime
docker compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Increase memory limit at runtime
docker compose exec redis redis-cli CONFIG SET maxmemory 256mb
```

### Monitoring

```bash
# Memory usage
docker compose exec redis redis-cli INFO memory

# Key metrics to watch:
# - used_memory_human: current usage
# - used_memory_peak_human: peak usage
# - maxmemory_human: configured limit
# - evicted_keys: keys removed by eviction (should be 0 or low)

# Cache hit/miss ratio
docker compose exec redis redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
# Hit rate = hits / (hits + misses). Target: >90%

# Key count by pattern
docker compose exec redis redis-cli --scan --pattern "slowapi:*" | wc -l
docker compose exec redis redis-cli --scan --pattern "flags:*" | wc -l
docker compose exec redis redis-cli --scan --pattern "design_sync:*" | wc -l
```

### Persistence

```bash
# Check current persistence config
docker compose exec redis redis-cli CONFIG GET save
docker compose exec redis redis-cli CONFIG GET appendonly

# Last successful save
docker compose exec redis redis-cli LASTSAVE
```

---

## 3. Gunicorn

The backend runs Gunicorn with Uvicorn workers (async ASGI).

### Worker Configuration

| Parameter | Default | Rule of Thumb | Description |
|-----------|---------|--------------|-------------|
| `WEB_CONCURRENCY` | 2 | 2 x CPU + 1 | Number of worker processes |
| `--timeout` | 120 | 60-120 | Kill worker if request exceeds this (seconds) |
| `--graceful-timeout` | 30 | 15-30 | Wait for in-flight requests during shutdown |
| `--max-requests` | 1000 | 500-5000 | Recycle worker after N requests (prevents memory leaks) |
| `--max-requests-jitter` | 100 | 10-20% of max-requests | Randomize recycling to avoid thundering herd |

**Set worker count:**
```bash
# Via environment variable
WEB_CONCURRENCY=5 docker compose up -d app

# Or in .env
WEB_CONCURRENCY=5
```

### When to Adjust

| Symptom | Diagnosis | Action |
|---------|-----------|--------|
| `WORKER TIMEOUT` in logs | Request took >120s | Increase `--timeout` or optimize the slow endpoint |
| High memory usage (>800M) | Workers accumulating memory | Decrease `--max-requests` (e.g., 500) for faster recycling |
| All workers busy, requests queuing | Not enough concurrency | Increase `WEB_CONCURRENCY` (ensure enough CPU/RAM) |
| Slow restarts during deploy | Graceful timeout too long | Decrease `--graceful-timeout` if acceptable |

### Monitoring

```bash
# Check worker count and PIDs
docker compose exec app ps aux | grep gunicorn

# Memory per worker
docker compose exec app ps aux --sort=-%mem | head -10
```

---

## 4. Uvicorn (Within Gunicorn)

Uvicorn runs inside each Gunicorn worker as the ASGI server.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--limit-concurrency` | unlimited | Max concurrent connections per worker |
| `--backlog` | 2048 | TCP connection queue size |
| `--limit-max-requests` | (set by Gunicorn) | Handled by Gunicorn's `--max-requests` |

These are configured in the Dockerfile CMD. To override:

```dockerfile
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "${WEB_CONCURRENCY:-2}", \
     "--preload", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--bind", "0.0.0.0:8891", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
```

For development (single process with auto-reload):

```bash
uv run uvicorn app.main:app --reload --port 8891
```

---

## 5. Rate Limiting

### Application-Level (slowapi)

| Endpoint Group | Variable | Default | Description |
|---------------|----------|---------|-------------|
| Default | `RATE_LIMIT__DEFAULT` | 120/minute | Most API endpoints |
| Auth | `RATE_LIMIT__AUTH` | 10/minute | Login, register, token refresh |
| Health | `RATE_LIMIT__HEALTH` | 60/minute | Health check endpoints |
| Chat | `RATE_LIMIT__CHAT` | 10/minute | Chat/conversation endpoints |
| AI Generation | `AI__RATE_LIMIT_GENERATION` | 5/minute | Email generation, agent runs |
| AI Chat | `AI__RATE_LIMIT_CHAT` | 20/minute | AI-assisted chat |

**Adjust in `.env`:**
```env
RATE_LIMIT__DEFAULT=200/minute
RATE_LIMIT__AUTH=20/minute
```

### Nginx-Level

```nginx
# Defined in nginx.conf
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
```

| Zone | Rate | Burst | Description |
|------|------|-------|-------------|
| api | 30 req/s | 20 | General API traffic |
| auth | 5 req/s | 5 | Authentication endpoints |

**Check if rate limiting is triggering:**
```bash
docker compose logs nginx --tail 100 2>&1 | grep "limiting"
```

### Tuning Strategy

- If legitimate users are being rate-limited: increase the limit for that endpoint group
- If under attack: decrease limits, especially on auth endpoints
- Nginx limits are the first defense (connection level); slowapi limits are per-user (application level)

---

## 6. AI Token Budget

### Per-User Throttling

| Variable | Default | Description |
|----------|---------|-------------|
| `AI__DAILY_QUOTA` | 50 | Max AI requests per user per day |
| `AI__STREAM_TIMEOUT_SECONDS` | 120 | Max duration for streaming AI response |

### Token Budget (Per-Request)

| Variable | Default | Description |
|----------|---------|-------------|
| `AI__TOKEN_BUDGET_ENABLED` | false | Enable input token limiting |
| `AI__TOKEN_BUDGET_RESERVE` | 4096 | Tokens reserved for response |
| `AI__TOKEN_BUDGET_MAX` | 0 | Max input tokens (0 = auto from model spec) |

### Cost Governor (Monthly)

| Variable | Default | Description |
|----------|---------|-------------|
| `AI__COST_GOVERNOR_ENABLED` | false | Enable monthly spend tracking |
| `AI__MONTHLY_BUDGET_GBP` | 600.0 | Monthly budget cap (0 = unlimited) |
| `AI__BUDGET_WARNING_THRESHOLD` | 0.8 | Warn at 80% of budget |

**Production recommendation:**
```env
AI__TOKEN_BUDGET_ENABLED=true
AI__TOKEN_BUDGET_RESERVE=4096
AI__COST_GOVERNOR_ENABLED=true
AI__MONTHLY_BUDGET_GBP=600.0
AI__BUDGET_WARNING_THRESHOLD=0.8
```

---

## 7. Docker Resource Limits

Current limits in `docker-compose.yml`:

| Service | CPU | Memory | When to Increase |
|---------|-----|--------|-----------------|
| db | 0.5 | 256M | Slow queries, many concurrent connections |
| redis | 0.25 | 128M | High cache usage, frequent evictions |
| app | 1.0 | 1024M | OOM kills, many workers needed |
| cms | 0.5 | 512M | Slow page builds, many concurrent users |
| maizzle-builder | 0.5 | 256M | Slow template compilation |
| nginx | 0.25 | 128M | Rarely needs increase |

**Override in `docker-compose.override.yml`:**
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2048M
  db:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
```

**Monitor current usage:**
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```
