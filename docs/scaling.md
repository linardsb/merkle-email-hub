# Scaling

## Database connection pool

`DatabaseConfig` (`app/core/config.py`) ships these defaults:

| Setting | Default | Override |
|---|---|---|
| `pool_size` | `20` | `DATABASE__POOL_SIZE` |
| `pool_max_overflow` | `20` | `DATABASE__POOL_MAX_OVERFLOW` |
| `pool_recycle` | `1800` (30 min) | `DATABASE__POOL_RECYCLE` |

### Sizing

Total simultaneous connections per Python process = `pool_size + pool_max_overflow` = **40**. Postgres' default `max_connections` is `100`, so a single backend instance occupies up to 40% of the budget. Headroom is reserved for the Maizzle sidecar's parallel client, alembic migrations, and ad-hoc psql sessions.

### When to increase

Bump only after observing pool exhaustion. Symptoms:
- `QueuePool limit of size N overflow M reached, connection timed out` in logs.
- p95 request latency climbs while `pg_stat_activity` shows mostly idle backends.
- Concurrent request count consistently > `pool_size + pool_max_overflow`.

When you do bump, raise Postgres `max_connections` first, then the pool, then redeploy. Otherwise you trade a Python-side timeout for a Postgres-side `FATAL: too many connections`.

### Monitoring

```sql
-- Live connections by application/state
SELECT application_name, state, count(*)
FROM pg_stat_activity
GROUP BY application_name, state
ORDER BY count DESC;

-- Long-held idle-in-transaction (pool starvation source)
SELECT pid, now() - xact_start AS xact_age, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY xact_age DESC;
```

`pool_recycle=1800` defends against silent connection drops behind NAT/load-balancers (PgBouncer/RDS proxy idle timeout is typically 30–60 min).
