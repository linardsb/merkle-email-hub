"""Tests for ETag middleware."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from app.core.etag import ETagMiddleware


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with ETag middleware for testing."""
    test_app = FastAPI()
    test_app.add_middleware(ETagMiddleware)

    @test_app.get("/json")
    def json_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/json-dynamic")
    def json_dynamic(value: str = "default") -> dict[str, str]:
        return {"value": value}

    @test_app.post("/json-post")
    def json_post() -> dict[str, str]:
        return {"created": "true"}

    @test_app.get("/html")
    def html_endpoint() -> HTMLResponse:
        return HTMLResponse("<html></html>")

    return test_app


class TestETagMiddleware:
    """ETag middleware test suite."""

    def setup_method(self) -> None:
        self.app = _make_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_etag_generated_for_get_json(self) -> None:
        """GET JSON response includes ETag header."""
        resp = self.client.get("/json")
        assert resp.status_code == 200
        assert "ETag" in resp.headers
        assert resp.headers["ETag"].startswith('"')
        assert resp.headers["ETag"].endswith('"')
        assert resp.headers["Cache-Control"] == "no-cache, must-revalidate"

    def test_304_when_etag_matches(self) -> None:
        """Returns 304 Not Modified when If-None-Match matches ETag."""
        resp1 = self.client.get("/json")
        etag = resp1.headers["ETag"]

        resp2 = self.client.get("/json", headers={"If-None-Match": etag})
        assert resp2.status_code == 304
        assert resp2.headers["ETag"] == etag
        assert len(resp2.content) == 0

    def test_etag_changes_on_data_change(self) -> None:
        """Different response data produces different ETag."""
        resp1 = self.client.get("/json-dynamic?value=one")
        resp2 = self.client.get("/json-dynamic?value=two")
        assert resp1.headers["ETag"] != resp2.headers["ETag"]

    def test_non_get_bypassed(self) -> None:
        """POST requests do not get ETag headers."""
        resp = self.client.post("/json-post")
        assert resp.status_code == 200
        assert "ETag" not in resp.headers

    def test_non_json_bypassed(self) -> None:
        """Non-JSON GET responses do not get ETag headers."""
        resp = self.client.get("/html")
        assert resp.status_code == 200
        assert "ETag" not in resp.headers

    def test_stale_etag_returns_200(self) -> None:
        """Stale If-None-Match returns full 200 with new ETag."""
        resp = self.client.get("/json", headers={"If-None-Match": '"stale-etag"'})
        assert resp.status_code == 200
        assert "ETag" in resp.headers

    def test_etag_deterministic(self) -> None:
        """Same data produces same ETag across requests."""
        resp1 = self.client.get("/json")
        resp2 = self.client.get("/json")
        assert resp1.headers["ETag"] == resp2.headers["ETag"]

    def test_etag_format_rfc7232(self) -> None:
        """ETag value is a quoted string per RFC 7232."""
        resp = self.client.get("/json")
        etag = resp.headers["ETag"]
        assert etag.startswith('"')
        assert etag.endswith('"')
        # Inner value is hex MD5 (32 chars)
        inner = etag.strip('"')
        assert len(inner) == 32
        assert all(c in "0123456789abcdef" for c in inner)
