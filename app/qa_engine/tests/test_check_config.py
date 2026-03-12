"""Tests for QA check configuration system."""

import pytest

from app.qa_engine.check_config import (
    QACheckConfig,
    QAProfileConfig,
    load_defaults,
    merge_profile,
)


class TestQACheckConfig:
    def test_default_config(self) -> None:
        config = QACheckConfig()
        assert config.enabled is True
        assert config.severity == "warning"
        assert config.threshold == 0.5
        assert config.params == {}

    def test_custom_params(self) -> None:
        config = QACheckConfig(params={"max_size_kb": 75})
        assert config.params["max_size_kb"] == 75


class TestQAProfileConfig:
    def test_default_profile(self) -> None:
        profile = QAProfileConfig()
        assert profile.file_size.enabled is True
        assert profile.brand_compliance.enabled is True  # default before YAML

    def test_get_check_config_known(self) -> None:
        profile = QAProfileConfig()
        config = profile.get_check_config("file_size")
        assert config is not None
        assert config.enabled is True

    def test_get_check_config_unknown(self) -> None:
        profile = QAProfileConfig()
        assert profile.get_check_config("nonexistent") is None


class TestLoadDefaults:
    def test_loads_yaml(self) -> None:
        profile = load_defaults()
        assert profile.file_size.params.get("max_size_kb") == 102
        assert profile.brand_compliance.enabled is False
        assert len(profile.spam_score.params.get("triggers", [])) == 10

    def test_cached(self) -> None:
        p1 = load_defaults()
        p2 = load_defaults()
        assert p1 is p2


class TestMergeProfile:
    def test_no_overrides(self) -> None:
        defaults = load_defaults()
        merged = merge_profile(defaults, None)
        assert merged is defaults

    def test_override_single_check(self) -> None:
        defaults = load_defaults()
        merged = merge_profile(defaults, {"file_size": {"params": {"max_size_kb": 75}}})
        assert merged.file_size.params["max_size_kb"] == 75
        # Other checks unaffected
        assert merged.spam_score.params.get("triggers") == defaults.spam_score.params.get(
            "triggers"
        )

    def test_disable_check(self) -> None:
        defaults = load_defaults()
        merged = merge_profile(defaults, {"dark_mode": {"enabled": False}})
        assert merged.dark_mode.enabled is False

    def test_unknown_check_ignored(self) -> None:
        defaults = load_defaults()
        merged = merge_profile(defaults, {"nonexistent_check": {"enabled": False}})
        # Should not raise, unknown keys ignored
        assert merged.file_size.enabled is True


class TestCheckWithConfig:
    """Verify checks respect config parameters."""

    @pytest.mark.anyio
    async def test_file_size_custom_threshold(self) -> None:
        from app.qa_engine.checks.file_size import FileSizeCheck

        check = FileSizeCheck()
        html = "x" * (50 * 1024)  # 50KB

        # Default: passes (under 102KB)
        result_default = await check.run(html)
        assert result_default.passed is True

        # Custom: fails (over 40KB)
        config = QACheckConfig(params={"max_size_kb": 40})
        result_custom = await check.run(html, config)
        assert result_custom.passed is False

    @pytest.mark.anyio
    async def test_spam_custom_triggers(self) -> None:
        from app.qa_engine.checks.spam_score import SpamScoreCheck

        check = SpamScoreCheck()
        html = "<p>Get your free samples today</p>"

        # Default triggers include "free"
        result_default = await check.run(html)
        assert result_default.score < 1.0

        # Custom: empty triggers = always clean
        config = QACheckConfig(params={"triggers": []})
        result_custom = await check.run(html, config)
        assert result_custom.score == 1.0

    @pytest.mark.anyio
    async def test_dark_mode_custom_deduction(self) -> None:
        from app.qa_engine.checks.dark_mode import DarkModeCheck

        check = DarkModeCheck()
        html = "<html><body>Hello</body></html>"  # Missing all dark mode features

        # Default deduction: 0.33 per issue (3 issues = 0.01)
        result_default = await check.run(html)
        assert result_default.score < 0.1

        # Custom: smaller deduction (0.1 per issue, 3 issues = 0.7)
        config = QACheckConfig(params={"deduction_per_issue": 0.1})
        result_custom = await check.run(html, config)
        assert result_custom.score == 0.7

    @pytest.mark.anyio
    async def test_disabled_check_skipped_in_service(self) -> None:
        """Verify the merge + enabled flag works for service-level skip logic."""
        defaults = load_defaults()
        merged = merge_profile(defaults, {"dark_mode": {"enabled": False}})
        config = merged.get_check_config("dark_mode")
        assert config is not None
        assert config.enabled is False
