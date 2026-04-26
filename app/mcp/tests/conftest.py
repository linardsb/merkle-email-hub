"""Shared fixtures for MCP tests.

By default, every MCP test runs with the full admin scope set in
``current_scopes_var`` so the per-tool ``@require_scope`` decorator
does not interfere with tests that exercise the tool body directly.

Tests that *want* to verify deny behavior should override the scope
set explicitly (e.g. via ``current_scopes_var.set(frozenset({"read"}))``
within the test body) — see ``test_scope_enforcement.py``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.mcp.auth import current_scopes_var


@pytest.fixture(autouse=True)
def _grant_admin_scope() -> Iterator[None]:
    token = current_scopes_var.set(frozenset({"read", "write", "admin"}))
    try:
        yield
    finally:
        current_scopes_var.reset(token)
