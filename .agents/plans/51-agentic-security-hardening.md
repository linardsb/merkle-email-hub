# Phase 51 — Agentic Security Hardening

> Close the 7 gaps between the existing G1–G5 envelope (commit `3f96ceb5`, Apr 25 2026 — `app/ai/agents/base.py`, `app/ai/agents/audit.py`) and the architectural mandates in *Technical Security Architecture: Out-of-Band Fail-Safes and Defense-in-Depth for Agentic Systems*.

---

## 1 · Why now

The Apr 25 envelope shipped **G1–G5** (sanitization, USER_INPUT delimiter, in-process kill flag, token+time caps, single audit line). It is **necessary but not sufficient** for the Autonomous AI Trifecta:

`Risk = (Autonomy × Power) / Assurance`

Power has grown across Phase 45–50 (cron jobs `app/scheduling/`, plugin connectors `app/plugins/`, VLM verify loop `app/design_sync/visual_verify.py`, custom-component generation `app/design_sync/custom_component_generator.py`, full-design PNG pipeline 50.1) — assurance must catch up.

**Failure mode the envelope still allows:** `SECURITY__DISABLED_AGENTS` is checked *by the same process* that may be running the offending loop. If that process is hung, OOM, or compacted (OpenClaw scenario), the in-band check never fires. We need control planes that bypass the model's interpretation loop entirely.

---

## 2 · Scope

7 subtasks. Backend (`app/`) and one side-car (`services/tool-runner/`). One frontend touch in 51.6.

| #    | Subtask                                              | Doc § | Size      | Order  |
| ---- | ---------------------------------------------------- | ----- | --------- | ------ |
| 51.1 | Credential revocation on kill                        | §3.4  | S (½d)    | 1      |
| 51.2 | Safe compaction — pinned safety instructions         | §2 L2 | M (1–2d)  | 2      |
| 51.3 | Tool-call cap + planning telemetry                   | §4 §6 | S (1d)    | 3      |
| 51.4 | Tamper-evident append-only audit                     | §6    | M (1–2d)  | 4      |
| 51.5 | Toxic-combination policy DSL                         | §5    | M (2–3d)  | 5      |
| 51.6 | HITL cryptographic signatures                        | §4    | M (1–2d)  | 6      |
| 51.7 | Infra-level kill + sandboxed tool execution          | §3 §5 | L (3–5d)  | 7      |

**Total:** ~10–14 dev-days. Strict order — each builds on the previous chain head.

---

## 3 · Non-negotiables

- **No regressions to G1–G5.** `BaseAgentService.process` envelope (`3f96ceb5`) stays. New layers wrap, never replace.
- **Default-deny on policy ambiguity.** If 51.5 DSL evaluator can't interpret a rule, the action is rejected, not allowed. (§4)
- **Audit chain includes the kill itself.** Killing an agent (51.7) emits an `ai.agent_killed` entry that is part of the tamper-evident chain (51.4).
- **Performance cap.** Per-action security overhead ≤ 50ms p95 (excluding HITL waits in 51.6). Verified by new `make bench` case `bench_security_envelope`.
- **All 7 subtasks ship behind feature flags** under `SECURITY__*` for progressive rollout without redeploy.
- **Backwards compat.** Existing 2037+ `app/ai` tests must pass after each subtask. Calibration gate (`make eval-calibration-gate`) within 5pp.

---

## 4 · Success criteria

| Check         | Verification                                                           |
| ------------- | ---------------------------------------------------------------------- |
| Trifecta      | Each subtask reduces (Autonomy × Power) / Assurance — see "Reduces:"   |
| Tests         | ≥ 80 new tests across the 7 subtasks                                   |
| Calibration   | `make eval-calibration-gate` passes                                    |
| Bench         | Agent envelope p95 still < 250ms                                       |
| Source doc    | `docs/security/agentic-defense-in-depth.md` committed and referenced   |

---

## 51.1 — Credential revocation on kill (S)

**Goal:** When `SECURITY__DISABLED_AGENTS` fires (or 51.7 infra-kill), all credential leases for the agent are immediately invalidated and re-leasing is blocked.

**Reduces:** Power — revokes tools/credentials at kill time.

**Files**

| File                                    | Change                                                                                      |
| --------------------------------------- | ------------------------------------------------------------------------------------------- |
| `app/core/credentials.py`               | Add `revoke_for_agent(agent_id, reason, ttl=None)` + `is_revoked(agent_id)` checks in `lease()` |
| `app/ai/agents/base.py`                 | On kill-switch hit (the 503 path in `process()`), call `revoke_for_agent` for every pool the agent leased from |
| `app/core/credentials_routes.py`        | Add `POST /api/v1/credentials/revoke` admin-only                                            |
| `app/core/config/security.py`           | New `revocation_default_ttl_s: int \| None = None`                                          |

**Tests** (~8 in `app/core/tests/test_credentials_revocation.py`)
- Revoke during lease — active lease completes, next `lease()` raises `CredentialRevokedError`
- Revoke is global across replicas (Redis-persisted via `_KeyState`)
- `ttl=None` = permanent until manual restore
- Audit line `credentials.revoked_for_agent` emitted (chained per 51.4 once shipped)
- Re-enable after revoke restores leasing
- Revoke endpoint rejects non-admin (403)

---

## 51.2 — Safe compaction: pinned safety instructions (M)

**Goal:** During context compaction or sliding-window evictions in `BlueprintEngine` and `BaseAgentService`, system-prompt safety clauses are re-injected before every model call — never elided.

**Reduces:** Likelihood of OpenClaw-style instruction drop during long blueprint runs (multi-revision Evaluator loops, Phase 48.4).

**Files**

| File                                       | Change                                                                  |
| ------------------------------------------ | ----------------------------------------------------------------------- |
| `app/ai/agents/safety_preamble.py`         | New module — loads canonical preamble from `safety_preamble.md`, exposes `SAFETY_PREAMBLE: str` and `PREAMBLE_VERSION: str` |
| `app/ai/agents/safety_preamble.md`         | New — canonical safety clauses (USER_INPUT delimiter rules, instruction hierarchy, tool-use constraints) |
| `app/ai/agents/base.py`                    | `_assemble_messages()` always prepends `SAFETY_PREAMBLE` regardless of compaction state; verify present in returned messages |
| `app/ai/blueprints/engine.py`              | New LAYER 12 in `_build_node_context()` — pin preamble after any context-size reduction |
| `app/core/config/security.py`              | `safety_preamble_version: str = ""` (logs warn if loaded version diverges from config) |

**Tests** (~10 in `app/ai/agents/tests/test_safe_compaction.py`)
- Preamble present even when conversation history forced to compact (mock `tiktoken` to overflow)
- Preamble version mismatch logs `security.safety_preamble_version_drift`
- Removing `safety_preamble.md` fails-closed: `process()` returns 503 on next call
- Preamble present in both `process()` and `stream_process()`
- Blueprint engine's LAYER 12 fires after every node context build, not just first

---

## 51.3 — Tool-call cap + planning telemetry (S)

**Goal:** Complete K_max (§4) by adding a per-session tool-call count cap; complete audit (§6) by capturing intermediate reasoning steps.

**Reduces:** Autonomy (bounded tool-call count) + sensors for indirect injection (planning telemetry).

**Files**

| File                                | Change                                                                                  |
| ----------------------------------- | --------------------------------------------------------------------------------------- |
| `app/ai/agents/base.py`             | New `_ToolCallCounter` per `process()`; raises `ToolCapExceededError` at `SECURITY__AGENT_MAX_TOOL_CALLS+1` |
| `app/ai/agents/audit.py`            | Extend `ai.agent_decision` with `tool_calls_made: int`, `planning_steps: list[str]`     |
| `app/ai/agents/exceptions.py`       | New `ToolCapExceededError(AppError)`                                                    |
| `app/core/config/security.py`       | `agent_max_tool_calls: int = 25`                                                        |
| `app/core/exceptions.py`            | Map `ToolCapExceededError` → 503 with reason `tool_cap_exceeded`                        |

**Tests** (~6 in `app/ai/agents/tests/test_tool_cap.py`)
- Cap raises at N+1 — agent emits `cap_exceeded` audit line
- Planning steps captured for structured-mode agents (Scaffolder)
- Counter resets between `process()` invocations
- Existing `agent_decision` consumers (Loki dashboards in Phase 44.9) unaffected — additive schema only
- `tool_calls_made=0` for agents that don't use tools

---

## 51.4 — Tamper-evident append-only audit (M)

**Goal:** Each `ai.agent_decision` entry hash-chains to the previous; chain anchored to a write-once store the agent process can't delete from.

**Reduces:** Insider/compromised-agent ability to scrub history.

**Files**

| File                                       | Change                                                                                                |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `app/ai/agents/audit.py`                   | Add `previous_hash: str` field; compute `blake2b(prev_entry_canonical_json)`; per-process Redis-stored chain head at `agent_audit:chain_head` |
| `app/ai/agents/audit_chain.py`             | New module — `verify_chain(entries) -> tuple[bool, int]`; periodic snapshot to S3 with Object Lock (no-op if `AWS__S3_LOG_BUCKET` empty) |
| `app/core/config/observability.py`         | `AGENT_AUDIT__CHAIN_ENABLED: bool = false`, `AGENT_AUDIT__SNAPSHOT_INTERVAL_S: int = 21600`, `AGENT_AUDIT__S3_BUCKET: str = ""` |
| `app/scheduling/jobs/audit_anchor.py`      | New cron `@scheduled_job(cron="0 */6 * * *")` snapshots chain to S3                                  |
| `app/admin/audit_routes.py`                | New admin-only `GET /api/v1/admin/audit/verify-chain` returns first tampered index                   |

**Tests** (~12 in `app/ai/agents/tests/test_audit_chain.py`)
- Chain integrity: tamper with middle entry → `verify_chain` returns `(False, idx)`
- Process restart: chain head reloaded from Redis, next entry's `previous_hash` correct
- S3 snapshot mode idempotent + uses Object Lock retention
- Disabled flag bypasses chain entirely (existing audit format preserved)
- Multiple processes coexist — Redis `WATCH/MULTI/EXEC` prevents race
- Verify endpoint rejects non-admin

**Depends on:** 51.3 (additive schema lands first)

---

## 51.5 — Toxic-combination policy DSL (M)

**Goal:** Central `app/ai/policy/` package with declarative rules ("agent X cannot combine `db_read` + `external_http` in one session"), evaluated in `BaseAgentService` before each tool dispatch.

**Reduces:** Power (mediation invariant) + Autonomy (deny-first).

**Files**

| File                                    | Change                                                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `app/ai/policy/__init__.py`             | New package                                                                                            |
| `app/ai/policy/dsl.py`                  | Pydantic `Rule(name, agent: str \| "*", forbid_combination: list[str], when: dict[str, str])` — when uses key-equality, no full DSL |
| `app/ai/policy/engine.py`               | `PolicyEngine` with `check_action(agent_id, tool, session_state) -> Decision`; tracks tools-used-this-session; `Decision = Allow \| Deny(reason) \| Gate(approval_id)` |
| `app/ai/policy/rules/default.yaml`      | Initial rules — forbid `db_write` + `external_http`, forbid `delete_*` after `bulk_read`              |
| `app/ai/agents/base.py`                 | Call `policy_engine.check_action()` between G4 (caps) and G5 (audit) in tool dispatch                 |
| `app/core/config/security.py`           | `policy_enabled: bool = false`, `policy_rules_dir: Path = Path("app/ai/policy/rules")`                |
| `app/ai/agents/exceptions.py`           | New `PolicyDeniedError(AppError)`                                                                      |

**Tests** (~15 in `app/ai/policy/tests/test_engine.py`)
- Forbid combination — first tool allowed, second denied
- `agent="*"` matches all
- Rule with stale schema fails-closed (default-deny on parse error)
- Rule reload on file mtime change (proven pattern from `judge_corrections.py`)
- Policy denies emit `ai.policy_denied` audit entry (chained per 51.4)
- `when` clause matches/skips correctly
- Empty rules dir = allow all (with WARN log)
- Disabled flag short-circuits to allow

**Blocks:** 51.7 (sandbox enforces what policy decides)

---

## 51.6 — HITL cryptographic signatures (M)

**Goal:** `/api/v1/approvals` decisions carry an Ed25519 signature from the approver's session key (or registered hardware key). Gated actions verify signature before unblocking.

**Reduces:** Agent's ability to fabricate or replay an approval.

**Files (backend)**

| File                                  | Change                                                                                          |
| ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `app/auth/keys.py`                    | New — `register_approver_key()`, `sign_decision()`, `verify_signature()` using `cryptography.hazmat.primitives.asymmetric.ed25519` |
| `app/auth/models.py`                  | New `ApproverPublicKey` table — `user_id`, `public_key_pem`, `fingerprint`, `created_at`        |
| `app/approval/service.py`             | On decision: require + verify signature; reject 400 if missing/invalid                           |
| `app/approval/models.py`              | Add `signature: bytes`, `signing_key_fingerprint: str` columns                                  |
| `alembic/versions/`                   | New migration — `approver_public_keys` + `approval_decisions.signature/fingerprint`             |
| `app/approval/routes.py`              | `POST /api/v1/approvals/{id}/decide` accepts `{decision, signature}`                            |
| `app/auth/routes.py`                  | `POST /api/v1/auth/keys/register` accepts public key PEM                                        |
| `app/core/config/security.py`         | `approvals_require_signature: bool = false`                                                     |

**Files (frontend)**

| File                                              | Change                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `cms/lib/approval-signing.ts`                     | New — `signDecision(payload)` via WebCrypto (Ed25519); key gen + IndexedDB persistence |
| `cms/components/approvals/decision-bar.tsx`       | Sign decision client-side before POST                                                  |
| `cms/components/approvals/key-registration.tsx`   | New — first-login flow, key gen + register public key with backend                    |
| `cms/hooks/use-approver-key.ts`                   | New — load/generate key from IndexedDB                                                |

**Tests** (~14 split BE + FE)
- Sign + verify round-trip (BE)
- Tampered payload fails verification (BE)
- Missing signature returns 400 when flag enabled (BE)
- Replayed signature on different decision rejected — nonce tied to approval ID (BE)
- Key registration is admin-protected (BE)
- Frontend: key generation idempotent across reloads (FE)
- Frontend: IndexedDB clear forces re-registration (FE)
- E2E: full flow — register → approve → verify (FE @smoke)

---

## 51.7 — Infra-level kill + sandboxed tool execution (L)

**Goal:** Separate side-car (`tool-runner`) executes side-effecting tools in a hardened container. Agents propose actions via JSON-RPC; side-car validates schema + policy (51.5) + executes. A privileged admin endpoint can SIGKILL the side-car independently of the API process.

**Reduces:** Blast radius (sandboxing) + makes kill actually kill (separate process).

**Files**

| File                                          | Change                                                                                  |
| --------------------------------------------- | --------------------------------------------------------------------------------------- |
| `services/tool-runner/`                       | New service — FastAPI + uvicorn; seccomp profile + read-only root FS + egress allowlist |
| `services/tool-runner/main.py`                | JSON-RPC endpoints per side-effecting tool (file ops, external HTTP, DB writes)         |
| `services/tool-runner/Dockerfile`             | Based on `gcr.io/distroless/python3-debian12`; non-root; no shell                       |
| `services/tool-runner/seccomp.json`           | Minimal syscall allowlist                                                               |
| `services/tool-runner/egress-allowlist.yaml`  | HTTP egress hosts                                                                        |
| `app/ai/agents/tools/runner_client.py`        | Replace direct tool imports with HTTP calls to side-car; preserves call sites           |
| `app/admin/kill_routes.py`                    | New admin-only `POST /api/v1/admin/kill-agent` — calls Docker/k8s API to terminate agent worker; gated by 51.6 signed request |
| `docker-compose.yml`                          | Add `tool-runner` service                                                               |
| `infra/k8s/tool-runner.yaml`                  | k8s deployment — separate node pool ideal                                               |
| `Makefile`                                    | New `tool-runner-dev` target                                                            |
| `app/core/config/security.py`                 | `sandbox_enabled: bool = false`, `sandbox_agents: list[str] = []`, `tool_runner_url: str = "http://tool-runner:8901"` |

**Tests** (~20 split unit + integration)
- Side-car receives only sanitized JSON-RPC, no shell injection vector
- SIGKILL on side-car: in-flight calls return 502 to agent; envelope emits `tool_runner_unreachable`
- Egress allowlist blocks unauthorized hosts
- Kill endpoint requires signed request (rejects unsigned per 51.6)
- Audit line `agent.killed_by_admin` chained per 51.4
- Sandbox-disabled fallback works (in-process tool calls preserved)
- Per-agent sandbox toggle (`SECURITY__SANDBOX_AGENTS=scaffolder`) — only that agent uses side-car

**Depends on:** 51.5 (sandbox uses policy DSL for tool gating), 51.6 (kill endpoint uses signing infra)

---

## 5 · Out of scope (Phase 52+)

- **Real-time anomaly detection** (§2 Layer 4 ML behavioral baselines) — existing `failure_warnings.py` covers some; ML-based deferred.
- **Inter-agent attack mitigation** (§1 trifecta last column) — relevant when multi-agent orchestration ships.
- **Hardware kill dashboards** (§3.3 hardware-level interfaces) — k8s admin console sufficient for v1.
- **Penetration test** of new system — recommend after 51.7 ships, separate engagement.
- **Hardware key (YubiKey) for 51.6** — opt-in v2; v1 uses session-bound Ed25519 in IndexedDB.

---

## 6 · Rollout plan

| Step    | Action                                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------- |
| 51.1    | Ship default-on; backwards-compat — no consumers today                                                  |
| 51.2    | Ship default-on; preamble file is checked into the repo                                                 |
| 51.3    | Ship default-on; `agent_max_tool_calls=25` is permissive enough not to trip current agents             |
| 51.4    | Ship `AGENT_AUDIT__CHAIN_ENABLED=false` for 1 week → verify chain growth in staging → flip on          |
| 51.5    | Ship empty `default.yaml` → populate rules over 2 weeks based on observed tool combinations            |
| 51.6    | `APPROVALS__REQUIRE_SIGNATURE=false` until all approvers have keys registered → flip on                |
| 51.7    | Staging-only 2 weeks → check `make bench` p95 → gradual prod per-agent (`SECURITY__SANDBOX_AGENTS=scaffolder` first) |

---

## 7 · Open questions

1. **Hardware key story for 51.6** — YubiKey or session-bound Ed25519 in IndexedDB? Recommend latter for v1; hardware as opt-in.
2. **Audit S3 bucket ownership** — does an existing AWS account already have Object Lock enabled? If not, 51.4's S3 mode stays disabled until ops provisions it.
3. **Sandbox runtime in 51.7** — gVisor adds ~30ms per syscall. Within p95 budget? Benchmark before committing; fallback is plain Docker with seccomp + read-only FS, which is cheaper but weaker.
4. **Tool taxonomy for 51.5** — current code doesn't have a unified tool name registry. Either build one as part of 51.5, or extract from existing `mcp_batch_execute` allowlist.

---

## 8 · References

- Source doc — *Technical Security Architecture: Out-of-Band Fail-Safes and Defense-in-Depth for Agentic Systems* (commit alongside this plan as `docs/security/agentic-defense-in-depth.md`).
- Existing envelope — commit `3f96ceb5` (Apr 25 2026), `app/ai/agents/base.py`, `app/ai/agents/audit.py`, `app/core/config/security.py`.
- Phase 46.1 — `CredentialPool` (basis for 51.1).
- Phase 44.9 — Loki/Promtail observability (basis for 51.4 chain anchoring).
- Phase 48.4 — Evaluator agent revision loop (longest-running agent flow; 51.2 must protect it).
