"""Unit tests for workflow task wrappers."""

from __future__ import annotations

import pytest

from app.workflows.exceptions import WorkflowValidationError
from app.workflows.tasks.blueprint_run import BlueprintRunTask
from app.workflows.tasks.chaos_test import ChaosTestTask
from app.workflows.tasks.esp_push import ESPPushTask
from app.workflows.tasks.locale_build import LocaleBuildTask
from app.workflows.tasks.qa_check import QACheckTask


class TestBlueprintRunTask:
    def test_validate_inputs_missing_brief(self) -> None:
        task = BlueprintRunTask()
        with pytest.raises(WorkflowValidationError, match="brief"):
            task.validate_inputs({"blueprint_name": "full_pipeline"})

    def test_validate_inputs_missing_blueprint_name(self) -> None:
        task = BlueprintRunTask()
        with pytest.raises(WorkflowValidationError, match="blueprint_name"):
            task.validate_inputs({"brief": "test"})

    def test_validate_inputs_valid(self) -> None:
        task = BlueprintRunTask()
        result = task.validate_inputs({"brief": "test", "blueprint_name": "full_pipeline"})
        assert result["brief"] == "test"


class TestQACheckTask:
    def test_validate_inputs_missing_html(self) -> None:
        task = QACheckTask()
        with pytest.raises(WorkflowValidationError, match="html"):
            task.validate_inputs({})

    def test_validate_inputs_empty_html(self) -> None:
        task = QACheckTask()
        with pytest.raises(WorkflowValidationError, match="html"):
            task.validate_inputs({"html": ""})

    def test_validate_inputs_valid(self) -> None:
        task = QACheckTask()
        result = task.validate_inputs({"html": "<p>test</p>"})
        assert result["html"] == "<p>test</p>"


class TestChaosTestTask:
    def test_validate_inputs_missing_html(self) -> None:
        task = ChaosTestTask()
        with pytest.raises(WorkflowValidationError, match="html"):
            task.validate_inputs({})


class TestESPPushTask:
    def test_validate_inputs_missing_required(self) -> None:
        task = ESPPushTask()
        with pytest.raises(WorkflowValidationError, match="Missing required"):
            task.validate_inputs({"html": "<p>test</p>"})

    def test_validate_inputs_valid(self) -> None:
        task = ESPPushTask()
        result = task.validate_inputs(
            {
                "html": "<p>test</p>",
                "connector_type": "braze",
                "content_block_name": "test-block",
            }
        )
        assert result["connector_type"] == "braze"


class TestLocaleBuildTask:
    def test_validate_inputs_missing_template_id(self) -> None:
        task = LocaleBuildTask()
        with pytest.raises(WorkflowValidationError, match="template_id"):
            task.validate_inputs({"locales": ["en"]})

    def test_validate_inputs_missing_locales(self) -> None:
        task = LocaleBuildTask()
        with pytest.raises(WorkflowValidationError, match="locales"):
            task.validate_inputs({"template_id": "123"})
