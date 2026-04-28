"""CRDT WebSocket load test against ``app/streaming/websocket/``.

Spawns N virtual users that each open a Yjs sync session, send a small
update every few seconds, and report sub-task latency back to Locust's
stats engine. Use ``websocket-client`` because Locust runs on gevent and
``websocket-client`` is gevent-friendly.

Run locally::

    uv run locust -f tests/load/locust_ws.py \\
        --headless -u 25 -r 5 -t 120s \\
        --host ws://localhost:8891
"""

from __future__ import annotations

import secrets
import time
import uuid
from typing import Any

from locust import User, between, events, task

try:
    import websocket  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover — optional load-test dep
    msg = "websocket-client is required for WebSocket load tests; install with `uv pip install websocket-client`."
    raise RuntimeError(msg) from exc


def _fire_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int = 0,
    exception: BaseException | None = None,
) -> None:
    """Bridge a custom WebSocket sub-event into Locust's stats pipeline."""
    events.request.fire(
        request_type=request_type,
        name=name,
        response_time=response_time,
        response_length=response_length,
        exception=exception,
        context={},
    )


class CrdtClient(User):
    """Simulate one CRDT collaborator on a shared room."""

    wait_time = between(2, 5)

    def __init__(self, environment: Any) -> None:
        super().__init__(environment)
        self._ws: websocket.WebSocket | None = None
        self._room = f"loadtest-{uuid.uuid4().hex[:8]}"

    def on_start(self) -> None:
        url = f"{self.host}/ws/collab/{self._room}"
        start = time.perf_counter()
        try:
            self._ws = websocket.create_connection(url, timeout=10)
            elapsed = (time.perf_counter() - start) * 1000
            _fire_request("WS", "connect", elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            _fire_request("WS", "connect", elapsed, exception=exc)
            self._ws = None

    def on_stop(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    @task
    def send_update(self) -> None:
        if self._ws is None:
            return
        # Yjs update messages start with a varint type tag; for load purposes a
        # short random binary payload exercises the same code path without
        # needing a full pycrdt encode.
        payload = secrets.token_bytes(64)
        start = time.perf_counter()
        try:
            self._ws.send_binary(payload)
            elapsed = (time.perf_counter() - start) * 1000
            _fire_request("WS", "update", elapsed, response_length=len(payload))
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            _fire_request("WS", "update", elapsed, exception=exc)
            self._ws = None
