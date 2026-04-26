"""Unit tests for app.core.cache.LruWithTtl."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.cache import LruWithTtl


class TestLruWithTtl:
    def test_get_missing_returns_none(self) -> None:
        cache: LruWithTtl[str, str] = LruWithTtl(maxsize=4, default_ttl=10)
        assert cache.get("absent") is None

    def test_put_then_get(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=4, default_ttl=10)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_ttl_expiry(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=4, default_ttl=5)
        with patch("app.core.cache.time.monotonic", return_value=100.0):
            cache.put("a", 42)
        with patch("app.core.cache.time.monotonic", return_value=110.0):
            # 110 > 100 + 5 → expired
            assert cache.get("a") is None

    def test_per_call_ttl_overrides_default(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=4, default_ttl=1000)
        with patch("app.core.cache.time.monotonic", return_value=0.0):
            cache.put("a", 1, ttl=1)
        with patch("app.core.cache.time.monotonic", return_value=2.0):
            assert cache.get("a") is None

    def test_lru_eviction_when_over_size(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=2, default_ttl=10)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # evicts "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_get_marks_entry_recent(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=2, default_ttl=10)
        cache.put("a", 1)
        cache.put("b", 2)
        # Touch "a" so "b" becomes the LRU
        assert cache.get("a") == 1
        cache.put("c", 3)  # evicts "b"
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_put_existing_key_refreshes(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=2, default_ttl=10)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 99)  # re-insert; LRU becomes "b"
        cache.put("c", 3)  # evicts "b"
        assert cache.get("a") == 99
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_pop_removes_entry(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=4, default_ttl=10)
        cache.put("a", 1)
        cache.pop("a")
        assert cache.get("a") is None

    def test_pop_missing_is_noop(self) -> None:
        cache: LruWithTtl[str, int] = LruWithTtl(maxsize=4, default_ttl=10)
        cache.pop("never-there")
        assert len(cache) == 0

    def test_maxsize_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="maxsize"):
            LruWithTtl[str, int](maxsize=0, default_ttl=1)
