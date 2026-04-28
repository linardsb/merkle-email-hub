"""Maizzle build endpoint load test.

Run locally::

    uv run locust -f tests/load/locustfile.py \\
        --headless -u 10 -r 2 -t 60s \\
        --host http://localhost:3001

Real golden templates from ``app/ai/templates/library/`` are used as payloads —
never fabricate email HTML in load tests (project rule).

Capture baseline RPS / p95 in ``docs/load-baseline.md`` after each major
infrastructure change (CPU bump, redis-cluster swap, etc.).
"""

from __future__ import annotations

import secrets
from pathlib import Path

from locust import HttpUser, between, events, task
from locust.env import Environment

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "app" / "ai" / "templates" / "library"

# Loaded once at process start so each VU re-uses the in-memory copy.
_TEMPLATES: list[tuple[str, str]] = []


@events.init.add_listener
def _load_templates(environment: Environment, **_kwargs: object) -> None:
    """Read every golden template from disk into memory before VUs spawn."""
    if _TEMPLATES:
        return
    for path in sorted(_TEMPLATE_DIR.glob("*.html")):
        _TEMPLATES.append((path.stem, path.read_text(encoding="utf-8")))
    if not _TEMPLATES:
        msg = f"No templates found under {_TEMPLATE_DIR}"
        raise RuntimeError(msg)


class MaizzleBuilder(HttpUser):
    """Hammer the Maizzle sidecar's /build endpoint with real templates."""

    wait_time = between(1, 3)

    @task(4)
    def build_template(self) -> None:
        name, source = secrets.choice(_TEMPLATES)
        self.client.post(
            "/build",
            json={"source": source, "target_clients": ["gmail", "outlook"]},
            name=f"/build [{name}]",
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health")
