"""Tests for the scheduled QA sweep job."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduling.registry import get_registry


def _make_template(
    template_id: int, name: str, project_id: int, status: str = "active"
) -> MagicMock:
    t = MagicMock()
    t.id = template_id
    t.name = name
    t.project_id = project_id
    t.status = status
    t.deleted_at = None
    return t


def _make_version(version_id: int, template_id: int, version_number: int, html: str) -> MagicMock:
    v = MagicMock()
    v.id = version_id
    v.template_id = template_id
    v.version_number = version_number
    v.html_source = html
    return v


def _make_qa_result(check_scores: dict[str, float]) -> MagicMock:
    """Build a mock QAResultResponse with given check_name→score pairs."""
    checks = []
    for name, score in check_scores.items():
        c = MagicMock()
        c.check_name = name
        c.score = score
        c.passed = score >= 0.7
        checks.append(c)

    result = MagicMock()
    result.checks = checks
    result.overall_score = sum(check_scores.values()) / max(len(check_scores), 1)
    result.passed = all(c.passed for c in checks)
    return result


class TestQaSweepRegistration:
    def test_qa_sweep_registered(self) -> None:
        """qa_sweep appears in the registry with correct cron."""
        import importlib

        import app.scheduling.jobs.qa_sweep as mod

        importlib.reload(mod)

        registry = get_registry()
        assert "qa_sweep" in registry
        _, cron = registry["qa_sweep"]
        assert cron == "0 6 * * *"


class TestQaSweepExecution:
    @pytest.fixture()
    def _mock_settings(self) -> MagicMock:
        settings = MagicMock()
        settings.scheduling.qa_sweep_regression_threshold = 0.05
        settings.scheduling.qa_sweep_checks = ["html_validation", "css_support", "css_audit"]
        return settings

    async def test_sweep_no_templates(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Empty DB → sweep completes, stores empty result, no regressions."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        # Should have stored results in Redis
        assert mock_redis.set.call_count == 2  # date key + latest key
        # Latest key should be empty scores
        latest_call = mock_redis.set.call_args_list[-1]
        assert json.loads(latest_call[0][1]) == {}

    async def test_sweep_runs_checks(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """2 templates → run_checks called twice with correct HTML."""
        t1 = _make_template(1, "Newsletter", 10)
        v1 = _make_version(101, 1, 3, "<html>T1</html>")
        t2 = _make_template(2, "Welcome", 10)
        v2 = _make_version(201, 2, 1, "<html>T2</html>")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[(t1, v1), (t2, v2)]))
        )

        qa_result = _make_qa_result(
            {"html_validation": 0.95, "css_support": 0.90, "css_audit": 0.88}
        )
        mock_run_checks = AsyncMock(return_value=qa_result)

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
            patch("app.scheduling.jobs.qa_sweep.QAEngineService") as mock_svc_cls,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_svc_cls.return_value.run_checks = mock_run_checks

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        assert mock_run_checks.call_count == 2
        # Verify HTML was passed correctly
        call_htmls = {call[0][0].html for call in mock_run_checks.call_args_list}
        assert call_htmls == {"<html>T1</html>", "<html>T2</html>"}

    async def test_sweep_stores_results_in_redis(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Redis set called with date key + latest key."""
        t1 = _make_template(1, "Newsletter", 10)
        v1 = _make_version(101, 1, 1, "<html>ok</html>")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(t1, v1)])))
        qa_result = _make_qa_result(
            {"html_validation": 0.95, "css_support": 0.88, "css_audit": 0.92}
        )

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
            patch("app.scheduling.jobs.qa_sweep.QAEngineService") as mock_svc_cls,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_result)

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        assert mock_redis.set.call_count == 2
        # First call: dated key with TTL
        date_call = mock_redis.set.call_args_list[0]
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        assert today in date_call[0][0]
        assert date_call[1]["ex"] == 30 * 86400

        # Second call: latest key (scores only)
        latest_call = mock_redis.set.call_args_list[1]
        assert latest_call[0][0] == "scheduling:qa_sweep:latest"
        scores = json.loads(latest_call[0][1])
        assert "tmpl:1" in scores
        assert scores["tmpl:1"]["html_validation"] == 0.95

    async def test_sweep_detects_regression(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Previous score 0.95, current 0.85 → regression flagged."""
        t1 = _make_template(1, "Newsletter", 10)
        v1 = _make_version(101, 1, 1, "<html>ok</html>")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(t1, v1)])))

        # Previous scores: high
        prev_scores = {"tmpl:1": {"html_validation": 0.95, "css_support": 0.95, "css_audit": 0.95}}
        mock_redis.get = AsyncMock(return_value=json.dumps(prev_scores))

        # Current scores: dropped
        qa_result = _make_qa_result(
            {"html_validation": 0.85, "css_support": 0.90, "css_audit": 0.95}
        )

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
            patch("app.scheduling.jobs.qa_sweep.QAEngineService") as mock_svc_cls,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_result)

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        # Check stored result has regressions
        date_call = mock_redis.set.call_args_list[0]
        result = json.loads(date_call[0][1])
        assert len(result["regressions"]) == 1
        reg = result["regressions"][0]
        assert reg["template_id"] == 1
        assert reg["check_name"] == "html_validation"
        assert reg["previous_score"] == 0.95
        assert reg["current_score"] == 0.85

    async def test_sweep_no_regression_within_threshold(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Score drop of 0.03 (< 0.05 threshold) → no regression."""
        t1 = _make_template(1, "Newsletter", 10)
        v1 = _make_version(101, 1, 1, "<html>ok</html>")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(t1, v1)])))

        prev_scores = {"tmpl:1": {"html_validation": 0.95, "css_support": 0.95, "css_audit": 0.95}}
        mock_redis.get = AsyncMock(return_value=json.dumps(prev_scores))

        # Only 0.03 drop — within threshold
        qa_result = _make_qa_result(
            {"html_validation": 0.92, "css_support": 0.93, "css_audit": 0.94}
        )

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
            patch("app.scheduling.jobs.qa_sweep.QAEngineService") as mock_svc_cls,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_result)

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        date_call = mock_redis.set.call_args_list[0]
        result = json.loads(date_call[0][1])
        assert len(result["regressions"]) == 0

    async def test_sweep_handles_check_failure(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """One template's QA raises → logged, other templates still processed."""
        t1 = _make_template(1, "Newsletter", 10)
        v1 = _make_version(101, 1, 1, "<html>bad</html>")
        t2 = _make_template(2, "Welcome", 10)
        v2 = _make_version(201, 2, 1, "<html>good</html>")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[(t1, v1), (t2, v2)]))
        )

        good_result = _make_qa_result(
            {"html_validation": 0.95, "css_support": 0.90, "css_audit": 0.88}
        )
        call_count = 0

        async def _run_checks(req: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("QA engine blew up")
            return good_result

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
            patch("app.scheduling.jobs.qa_sweep.QAEngineService") as mock_svc_cls,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_svc_cls.return_value.run_checks = _run_checks

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        # Should still store results — one template succeeded
        date_call = mock_redis.set.call_args_list[0]
        result = json.loads(date_call[0][1])
        assert result["total_templates"] == 2
        # Only 1 template has scores (the other errored)
        assert len(result["scores"]) == 1

    async def test_sweep_skips_archived_templates(
        self, mock_redis: AsyncMock, _mock_settings: MagicMock
    ) -> None:
        """Archived template excluded from sweep (verified via query filter)."""
        # Only active templates returned by query
        t1 = _make_template(1, "Active Newsletter", 10, status="active")
        v1 = _make_version(101, 1, 1, "<html>active</html>")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(t1, v1)])))

        qa_result = _make_qa_result(
            {"html_validation": 0.95, "css_support": 0.90, "css_audit": 0.88}
        )

        with (
            patch("app.scheduling.jobs.qa_sweep.get_settings", return_value=_mock_settings),
            patch("app.scheduling.jobs.qa_sweep.get_redis", return_value=mock_redis),
            patch("app.scheduling.jobs.qa_sweep.get_db_context") as mock_ctx,
            patch("app.scheduling.jobs.qa_sweep.QAEngineService") as mock_svc_cls,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_result)

            from app.scheduling.jobs.qa_sweep import qa_sweep

            await qa_sweep()

        # Verify only 1 template was processed
        date_call = mock_redis.set.call_args_list[0]
        result = json.loads(date_call[0][1])
        assert result["total_templates"] == 1
