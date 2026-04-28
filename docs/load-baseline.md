# Load test baselines

Captured RPS and latency for the Maizzle sidecar and CRDT WebSocket workloads.
Re-run the relevant scenario after any infrastructure change (CPU/RAM bump,
Redis cluster swap, MJML compiler upgrade, sidecar replica change) and update
the table below. Treat a >25 % p95 regression as a release blocker.

## How to run

```sh
# Maizzle sidecar HTTP load
uv run locust -f tests/load/locustfile.py \
    --headless -u 10 -r 2 -t 60s \
    --host http://localhost:3001 \
    --csv reports/load/maizzle

# CRDT WebSocket load (requires websocket-client)
uv pip install websocket-client
uv run locust -f tests/load/locust_ws.py \
    --headless -u 25 -r 5 -t 120s \
    --host ws://localhost:8891 \
    --csv reports/load/crdt
```

CSV outputs land under `reports/load/<scenario>_stats.csv` — copy the relevant
row into the table when committing a new baseline.

## Maizzle `/build`

| Date | VUs | Duration | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Notes |
|------|-----|----------|-----|----------|----------|----------|-------|
| TBD  | 10  | 60 s     | TBD | TBD      | TBD      | TBD      | First run after Phase 3 §3.2 lands |

## CRDT WebSocket

| Date | VUs | Duration | Connect p95 (ms) | Update p95 (ms) | Disconnect rate | Notes |
|------|-----|----------|------------------|-----------------|-----------------|-------|
| TBD  | 25  | 120 s    | TBD              | TBD             | TBD             | First run after Phase 3 §3.2 lands |

## Release gating

- Locust runs are **not** wired into CI — `make load-test` is a release-time
  manual check.
- If p95 latency on either scenario regresses by >25 % vs the latest baseline,
  block the release until investigated.
- Lock the baseline by committing this file with the populated row alongside
  any infrastructure change PR.
