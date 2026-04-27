"""Tests for hook profile filtering."""

from __future__ import annotations

from app.ai.hooks.profiles import profile_includes


class TestProfileIncludes:
    def test_profile_includes_same_level(self) -> None:
        assert profile_includes("minimal", "minimal") is True
        assert profile_includes("standard", "standard") is True
        assert profile_includes("strict", "strict") is True

    def test_profile_includes_higher(self) -> None:
        assert profile_includes("strict", "minimal") is True
        assert profile_includes("strict", "standard") is True
        assert profile_includes("standard", "minimal") is True

    def test_profile_excludes_lower(self) -> None:
        assert profile_includes("minimal", "standard") is False
        assert profile_includes("minimal", "strict") is False
        assert profile_includes("standard", "strict") is False
