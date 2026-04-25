# Dependency Debt — Deferred SCA Findings

Registry of vulnerability findings surfaced by CI tools (pip-audit, Trivy)
that are intentionally suppressed at the gate. Each entry must record:
package, advisory ID, severity, why deferred, expected fix trigger, owner.

For Dependabot-surfaced advisories, see `docs/dependabot-status.md` — the same
upstream CVE may appear in both registries when both gates flag it.

## pip-audit deferrals (`uv run pip-audit --strict --ignore-vuln <ID>`)

| Package | Advisory | Severity | Pinned at | Why deferred | Fix trigger | Owner |
|---|---|---|---|---|---|---|
| pip | [CVE-2026-3219](https://github.com/advisories/GHSA-58qw-9mgm-455v) (GHSA-58qw-9mgm-455v) | medium | 26.0.1 | No upstream patch released; vulnerability is in pip's parsing of attacker-crafted package files (tar+ZIP). We resolve only against PyPI through `uv` and do not pip-install attacker-controlled URLs. Same item tracked as Dependabot #101 in `docs/dependabot-status.md`. | pip releases a patched version | Linards |

CI invocation lives at `.github/workflows/ci.yml` (backend job, `pip-audit` step) and `Makefile :: ci-be`.

## Trivy deferrals (`.trivyignore`)

Populated as Phase 2 §2.1 lands. First scan triage will append base-image CVEs
that have no upstream fix; each entry needs an expiration date and re-check trigger.

| Image | CVE | Severity | Why deferred | Expires | Owner |
|---|---|---|---|---|---|
| _none yet_ | | | | | |

## mypy stub-gap deferrals (post-Phase 3 §3.5)

Recorded here once Phase 3 §3.5 reduces the `[[tool.mypy.overrides]]` block
in `pyproject.toml` — only the modules we cannot remove (no published stubs)
remain, with a one-line justification.

## How to re-check

```bash
# pip-audit (backend)
uv run pip-audit --strict

# Trivy (after §2.1 lands)
docker build -t merkle-email-hub:local .
trivy image --severity HIGH,CRITICAL --ignore-unfixed merkle-email-hub:local
```
