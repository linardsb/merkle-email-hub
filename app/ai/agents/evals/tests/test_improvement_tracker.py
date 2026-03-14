"""Tests for improvement tracker."""

from pathlib import Path

from app.ai.agents.evals.improvement_tracker import (
    ImprovementEntry,
    load_improvements,
    record_improvement,
    summarise_progress,
)


class TestRecordImprovement:
    def test_appends_entry_to_file(self, tmp_path: Path, monkeypatch: object) -> None:
        import app.ai.agents.evals.improvement_tracker as mod

        log_path = tmp_path / "improvement_log.jsonl"
        monkeypatch.setattr(mod, "IMPROVEMENT_LOG", log_path)  # type: ignore[attr-defined]

        entry = record_improvement(
            change_description="11.22.8 agent redefinition",
            agent="scaffolder",
            criterion="mso_conditional_correctness",
            before_rate=0.0,
            after_rate=0.99,
            task_id="11.22.8",
        )

        assert entry.delta == 0.99
        assert entry.agent == "scaffolder"
        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_appends_multiple_entries(self, tmp_path: Path, monkeypatch: object) -> None:
        import app.ai.agents.evals.improvement_tracker as mod

        log_path = tmp_path / "improvement_log.jsonl"
        monkeypatch.setattr(mod, "IMPROVEMENT_LOG", log_path)  # type: ignore[attr-defined]

        record_improvement("change 1", "scaffolder", "crit1", 0.5, 0.7, "11.22.1")
        record_improvement("change 2", "dark_mode", "crit2", 0.1, 0.9, "11.22.2")

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2


class TestLoadImprovements:
    def test_loads_entries(self, tmp_path: Path) -> None:
        log_path = tmp_path / "improvement_log.jsonl"
        entry = ImprovementEntry(
            date="2026-03-14T00:00:00+00:00",
            change_description="test",
            agent="scaffolder",
            criterion="crit",
            before_rate=0.5,
            after_rate=0.8,
            delta=0.3,
            task_id="11.22.9",
        )
        log_path.write_text(entry.model_dump_json() + "\n")

        entries = load_improvements(log_path)
        assert len(entries) == 1
        assert entries[0].delta == 0.3

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        entries = load_improvements(tmp_path / "nonexistent.jsonl")
        assert entries == []


class TestSummariseProgress:
    def test_summarises_latest_per_agent(self, tmp_path: Path, monkeypatch: object) -> None:
        import app.ai.agents.evals.improvement_tracker as mod

        log_path = tmp_path / "improvement_log.jsonl"
        monkeypatch.setattr(mod, "IMPROVEMENT_LOG", log_path)  # type: ignore[attr-defined]

        record_improvement("v1", "scaffolder", "mso", 0.0, 0.5, "11.22.1")
        record_improvement("v2", "scaffolder", "mso", 0.5, 0.99, "11.22.4")

        summary = summarise_progress(log_path)
        assert summary["entries"] == 2
        latest = summary["latest"]
        assert latest["scaffolder"]["mso"] == 0.99  # type: ignore[index]
