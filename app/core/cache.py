"""Lightweight LRU + TTL cache for in-process state."""

from __future__ import annotations

import time
from collections import OrderedDict


class LruWithTtl[K, V]:
    """Bounded mapping with per-entry TTL and LRU eviction.

    `get()` returns `None` once an entry's TTL elapses or the entry was never
    inserted. `put()` enforces the size cap by evicting the least-recently used
    entry. Not thread-safe; protect with a lock if shared across threads.
    """

    def __init__(self, *, maxsize: int, default_ttl: float) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._d: OrderedDict[K, tuple[V, float]] = OrderedDict()
        self._maxsize = maxsize
        self._default_ttl = default_ttl

    def get(self, key: K) -> V | None:
        item = self._d.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at <= time.monotonic():
            del self._d[key]
            return None
        self._d.move_to_end(key)
        return value

    def put(self, key: K, value: V, *, ttl: float | None = None) -> None:
        if key in self._d:
            del self._d[key]
        self._d[key] = (value, time.monotonic() + (ttl if ttl is not None else self._default_ttl))
        if len(self._d) > self._maxsize:
            self._d.popitem(last=False)

    def pop(self, key: K) -> None:
        self._d.pop(key, None)

    def __len__(self) -> int:
        return len(self._d)
