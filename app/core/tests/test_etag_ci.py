"""CI gate: ETag middleware is registered and functional on the production app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestETagMiddlewareCI:
    """Verify ETag middleware is wired into the production app."""

    def setup_method(self) -> None:
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_etag_header_on_health(self) -> None:
        """Health endpoint returns ETag header (middleware active)."""
        resp = self.client.get("/health")
        assert resp.status_code == 200
        assert "ETag" in resp.headers, "ETag middleware not registered in app"

    def test_304_on_health_etag_match(self) -> None:
        """Health endpoint returns 304 when ETag matches."""
        resp1 = self.client.get("/health")
        etag = resp1.headers["ETag"]
        resp2 = self.client.get("/health", headers={"If-None-Match": etag})
        assert resp2.status_code == 304

    def test_cache_control_header(self) -> None:
        """ETag responses include Cache-Control: no-cache, must-revalidate."""
        resp = self.client.get("/health")
        assert resp.headers.get("Cache-Control") == "no-cache, must-revalidate"
