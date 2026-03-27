"""Tests for import annotator skill detection and L3 skill loading (Phase 32.3)."""

from pathlib import Path

from app.ai.agents.import_annotator.prompt import (
    SKILL_FILES,
    build_system_prompt,
    detect_relevant_skills,
)

_SKILL_DIR = Path(__file__).resolve().parents[4] / "app" / "ai" / "agents" / "import_annotator"


class TestSkillDetection:
    """Tests for detect_relevant_skills() heuristics."""

    def test_detect_stripo_markers(self) -> None:
        html = '<div class="esd-structure"><table></table></div>'
        skills = detect_relevant_skills(html)
        assert "common_email_builders" in skills

    def test_detect_bee_markers(self) -> None:
        html = '<div class="bee-row"><div class="bee-col">Content</div></div>'
        skills = detect_relevant_skills(html)
        assert "common_email_builders" in skills

    def test_detect_mailchimp_markers(self) -> None:
        html = '<td mc:edit="hero_text">Hello *|FNAME|*</td>'
        skills = detect_relevant_skills(html)
        assert "common_email_builders" in skills
        assert "esp_token_edge_cases" in skills

    def test_detect_begin_module_comment_markers(self) -> None:
        html = "<!-- BEGIN MODULE: Header --><table></table>"
        skills = detect_relevant_skills(html)
        assert "common_email_builders" in skills

    def test_detect_module_colon_comment_markers(self) -> None:
        html = "<!-- MODULE: Hero --><table></table>"
        skills = detect_relevant_skills(html)
        assert "common_email_builders" in skills

    def test_detect_css_normalization_important(self) -> None:
        important_decls = "color:red !important; " * 6
        html = f'<td style="{important_decls}">text</td>'
        skills = detect_relevant_skills(html)
        assert "css_normalization" in skills

    def test_detect_css_normalization_vendor_webkit(self) -> None:
        html = '<td style="-webkit-text-size-adjust:100%">text</td>'
        skills = detect_relevant_skills(html)
        assert "css_normalization" in skills

    def test_detect_css_normalization_vendor_moz(self) -> None:
        html = '<td style="-moz-text-size-adjust:100%">text</td>'
        skills = detect_relevant_skills(html)
        assert "css_normalization" in skills

    def test_no_css_normalization_when_few_important(self) -> None:
        html = '<td style="color:red !important;">text</td>'
        skills = detect_relevant_skills(html)
        assert "css_normalization" not in skills

    def test_wrapper_always_loaded(self) -> None:
        html = "<p>minimal content</p>"
        skills = detect_relevant_skills(html)
        assert "wrapper_detection" in skills

    def test_wrapper_loaded_even_for_empty_html(self) -> None:
        skills = detect_relevant_skills("")
        assert "wrapper_detection" in skills

    def test_detect_esp_edge_mailchimp_merge(self) -> None:
        html = "<p>Hello *|FNAME|*</p>"
        skills = detect_relevant_skills(html)
        assert "esp_token_edge_cases" in skills

    def test_detect_esp_edge_ampscript_nested(self) -> None:
        html = '<p>%%=Concat(Uppercase(FirstName), " ", LastName)=%%</p>'
        skills = detect_relevant_skills(html)
        assert "esp_token_edge_cases" in skills

    def test_detect_esp_edge_handlebars_partial(self) -> None:
        html = "<p>{{> header_partial }}</p>"
        skills = detect_relevant_skills(html)
        assert "esp_token_edge_cases" in skills

    def test_detect_esp_edge_triple_stache(self) -> None:
        html = "<p>{{{unescaped_content}}}</p>"
        skills = detect_relevant_skills(html)
        assert "esp_token_edge_cases" in skills

    def test_detect_esp_edge_connected_content(self) -> None:
        html = "<p>{% connected_content https://api.example.com :save r %}</p>"
        skills = detect_relevant_skills(html)
        assert "esp_token_edge_cases" in skills

    def test_large_html_loads_all_skills(self) -> None:
        html = "x" * 51_000
        skills = detect_relevant_skills(html)
        assert len(skills) == len(SKILL_FILES)
        assert set(skills) == set(SKILL_FILES.keys())

    def test_no_duplicate_skills(self) -> None:
        # HTML that triggers multiple overlapping detections
        html = '<div class="bee-row" style="-webkit-transform:none !important; color:red !important; font:bold !important; size:12 !important; bg:white !important; border:0 !important;">*|FNAME|* {{ name }} {{{ raw }}}</div>'
        skills = detect_relevant_skills(html)
        assert len(skills) == len(set(skills)), f"Duplicates found: {skills}"

    def test_esp_platform_still_forces_esp_tokens(self) -> None:
        skills = detect_relevant_skills("<p>No tokens</p>", esp_platform="braze")
        assert "esp_tokens" in skills


class TestSkillFilesExist:
    """Verify all registered skill files resolve to real files on disk."""

    def test_all_skill_files_exist(self) -> None:
        for key, rel_path in SKILL_FILES.items():
            full_path = _SKILL_DIR / rel_path
            assert full_path.exists(), f"Skill file missing for '{key}': {full_path}"

    def test_skill_files_have_front_matter(self) -> None:
        for key, rel_path in SKILL_FILES.items():
            content = (_SKILL_DIR / rel_path).read_text(encoding="utf-8")
            assert content.startswith("---"), f"Skill '{key}' missing front matter: {rel_path}"
            assert content.count("---") >= 2, f"Skill '{key}' incomplete front matter: {rel_path}"


class TestBuildSystemPrompt:
    """Verify build_system_prompt includes skill content."""

    def test_includes_wrapper_detection_content(self) -> None:
        prompt = build_system_prompt(["wrapper_detection"])
        assert "--- REFERENCE: wrapper_detection ---" in prompt
        assert "Centering Wrappers" in prompt

    def test_includes_common_email_builders_content(self) -> None:
        prompt = build_system_prompt(["common_email_builders"])
        assert "--- REFERENCE: common_email_builders ---" in prompt
        assert "Stripo" in prompt

    def test_includes_esp_token_edge_cases_content(self) -> None:
        prompt = build_system_prompt(["esp_token_edge_cases"])
        assert "--- REFERENCE: esp_token_edge_cases ---" in prompt
        assert "AMPscript Advanced" in prompt

    def test_includes_css_normalization_content(self) -> None:
        prompt = build_system_prompt(["css_normalization"])
        assert "--- REFERENCE: css_normalization ---" in prompt
        assert "Vendor Prefixes" in prompt

    def test_unknown_skill_key_ignored(self) -> None:
        prompt = build_system_prompt(["nonexistent_skill"])
        assert "--- REFERENCE:" not in prompt


class TestLayoutAndColumnDetection:
    """Tests for table/div layout and column pattern skill detection (Phase 32.8)."""

    def test_table_layout_detection(self) -> None:
        html = "<table><tr><td>Content</td></tr></table>"
        skills = detect_relevant_skills(html)
        assert "table_layouts" in skills

    def test_div_layout_mj_column(self) -> None:
        html = '<div class="mj-column">Content</div>'
        skills = detect_relevant_skills(html)
        assert "div_layouts" in skills

    def test_div_layout_email_body(self) -> None:
        html = '<div class="email-body">Content</div>'
        skills = detect_relevant_skills(html)
        assert "div_layouts" in skills

    def test_column_inline_block(self) -> None:
        html = '<td style="display:inline-block;width:50%">Col</td>'
        skills = detect_relevant_skills(html)
        assert "column_patterns" in skills

    def test_column_float(self) -> None:
        html = '<td style="float:left;width:300px">Col</td>'
        skills = detect_relevant_skills(html)
        assert "column_patterns" in skills


class TestBoundaryConditions:
    """Boundary tests for CSS normalization and HTML size thresholds (Phase 32.8)."""

    def test_css_important_at_5_not_loaded(self) -> None:
        decls = "color:red !important; " * 5
        html = f'<td style="{decls}">text</td>'
        skills = detect_relevant_skills(html)
        assert "css_normalization" not in skills

    def test_css_important_at_6_loaded(self) -> None:
        decls = "color:red !important; " * 6
        html = f'<td style="{decls}">text</td>'
        skills = detect_relevant_skills(html)
        assert "css_normalization" in skills

    def test_esp_platform_plus_builder_combo(self) -> None:
        html = '<div class="esd-structure"><table><tr><td>Stripo</td></tr></table></div>'
        skills = detect_relevant_skills(html, esp_platform="braze")
        assert "esp_tokens" in skills
        assert "common_email_builders" in skills

    def test_html_50k_boundary(self) -> None:
        # At exactly 50,000 bytes — should NOT load all skills
        html_at_boundary = "a" * 50_000
        skills_at = detect_relevant_skills(html_at_boundary)
        assert len(skills_at) < len(SKILL_FILES)

        # At 50,001 bytes — should load ALL skills
        html_over = "a" * 50_001
        skills_over = detect_relevant_skills(html_over)
        assert set(skills_over) == set(SKILL_FILES.keys())
