"""Tests for output_mode parameter in build_system_prompt across agents."""

from app.ai.agents.accessibility.prompt import build_system_prompt as a11y_prompt
from app.ai.agents.code_reviewer.prompt import build_system_prompt as reviewer_prompt
from app.ai.agents.content.prompt import build_system_prompt as content_prompt
from app.ai.agents.dark_mode.prompt import build_system_prompt as dark_mode_prompt
from app.ai.agents.outlook_fixer.prompt import build_system_prompt as outlook_prompt
from app.ai.agents.personalisation.prompt import build_system_prompt as pers_prompt
from app.ai.agents.scaffolder.prompt import build_system_prompt as scaffolder_prompt


class TestBuildSystemPromptOutputMode:
    """Verify all 7 agents accept output_mode and return mode-appropriate content."""

    def test_scaffolder_html_mode(self) -> None:
        prompt = scaffolder_prompt([], output_mode="html")
        assert "Output Format: HTML" in prompt
        assert "Output Format: Structured" not in prompt

    def test_scaffolder_structured_mode(self) -> None:
        prompt = scaffolder_prompt([], output_mode="structured")
        assert "Output Format: Structured" in prompt
        assert "EmailBuildPlan" in prompt
        assert "Output Format: HTML" not in prompt

    def test_dark_mode_structured(self) -> None:
        prompt = dark_mode_prompt([], output_mode="structured")
        assert "DarkModePlan" in prompt

    def test_outlook_fixer_structured(self) -> None:
        prompt = outlook_prompt([], output_mode="structured")
        assert "OutlookFixPlan" in prompt

    def test_accessibility_structured(self) -> None:
        prompt = a11y_prompt([], output_mode="structured")
        assert "AccessibilityPlan" in prompt

    def test_personalisation_structured(self) -> None:
        prompt = pers_prompt([], output_mode="structured")
        assert "PersonalisationPlan" in prompt

    def test_code_reviewer_structured(self) -> None:
        prompt = reviewer_prompt([], output_mode="structured")
        assert "CodeReviewPlan" in prompt

    def test_content_structured(self) -> None:
        prompt = content_prompt([], output_mode="structured")
        assert "ContentPlan" in prompt

    def test_all_agents_default_to_html(self) -> None:
        for prompt_fn in [
            scaffolder_prompt,
            dark_mode_prompt,
            outlook_prompt,
            a11y_prompt,
            pers_prompt,
            reviewer_prompt,
            content_prompt,
        ]:
            prompt = prompt_fn([])
            assert "Output Format: Structured" not in prompt

    def test_security_rules_always_present(self) -> None:
        for prompt_fn in [
            scaffolder_prompt,
            dark_mode_prompt,
            outlook_prompt,
            a11y_prompt,
            pers_prompt,
            reviewer_prompt,
            content_prompt,
        ]:
            for mode in ("html", "structured"):
                prompt = prompt_fn([], output_mode=mode)
                assert "Security Rules" in prompt
