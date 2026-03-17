"""Tests for email generators."""

from app.qa_engine.property_testing.generators import EmailConfig, build_email, email_configs


class TestEmailConfig:
    def test_strategy_produces_valid_config(self):
        strategy = email_configs()
        config = strategy.example()
        assert isinstance(config, EmailConfig)
        assert 1 <= config.section_count <= 15
        assert len(config.section_types) >= 1


class TestBuildEmail:
    def test_produces_valid_html(self):
        config = EmailConfig(
            section_count=3,
            section_types=("hero", "content", "cta"),
            content_lengths=(100, 200, 50),
            font_family="Arial, sans-serif",
            primary_color="#2563eb",
            background_color="#ffffff",
            text_color="#000000",
            image_count=1,
            image_widths=(300,),
            table_nesting_depth=2,
            has_mso_conditionals=True,
            has_dark_mode=True,
            dark_mode_complete=True,
            link_count=2,
            include_javascript_links=False,
            include_empty_alt=False,
            target_size_kb=10,
        )
        html = build_email(config)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "<!--[if mso]>" in html
        assert "prefers-color-scheme" in html

    def test_deterministic_output(self):
        """Same config always produces same HTML."""
        config = EmailConfig(
            section_count=2,
            section_types=("hero", "content"),
            content_lengths=(50, 50),
            font_family="Arial, sans-serif",
            primary_color="#ff0000",
            background_color="#ffffff",
            text_color="#000000",
            image_count=0,
            image_widths=(),
            table_nesting_depth=1,
            has_mso_conditionals=False,
            has_dark_mode=False,
            dark_mode_complete=False,
            link_count=0,
            include_javascript_links=False,
            include_empty_alt=False,
            target_size_kb=0,
        )
        html1 = build_email(config)
        html2 = build_email(config)
        assert html1 == html2

    def test_size_padding(self):
        """Target size produces approximately correct output."""
        config = EmailConfig(
            section_count=1,
            section_types=("content",),
            content_lengths=(50,),
            font_family="Arial, sans-serif",
            primary_color="#000000",
            background_color="#ffffff",
            text_color="#000000",
            image_count=0,
            image_widths=(),
            table_nesting_depth=0,
            has_mso_conditionals=False,
            has_dark_mode=False,
            dark_mode_complete=False,
            link_count=0,
            include_javascript_links=False,
            include_empty_alt=False,
            target_size_kb=120,
        )
        html = build_email(config)
        size_kb = len(html.encode("utf-8")) / 1024
        assert size_kb >= 100

    def test_javascript_links_generated(self):
        config = EmailConfig(
            section_count=1,
            section_types=("content",),
            content_lengths=(50,),
            font_family="Arial, sans-serif",
            primary_color="#000000",
            background_color="#ffffff",
            text_color="#000000",
            image_count=0,
            image_widths=(),
            table_nesting_depth=0,
            has_mso_conditionals=False,
            has_dark_mode=False,
            dark_mode_complete=False,
            link_count=3,
            include_javascript_links=True,
            include_empty_alt=False,
            target_size_kb=0,
        )
        html = build_email(config)
        assert "javascript:void(0)" in html

    def test_empty_alt_generated(self):
        config = EmailConfig(
            section_count=1,
            section_types=("content",),
            content_lengths=(50,),
            font_family="Arial, sans-serif",
            primary_color="#000000",
            background_color="#ffffff",
            text_color="#000000",
            image_count=2,
            image_widths=(300, 300),
            table_nesting_depth=0,
            has_mso_conditionals=False,
            has_dark_mode=False,
            dark_mode_complete=False,
            link_count=0,
            include_javascript_links=False,
            include_empty_alt=True,
            target_size_kb=0,
        )
        html = build_email(config)
        assert 'alt=""' in html


class TestRandomEmailConfig:
    def test_seed_reproducibility(self):
        import random

        rng1 = random.Random(42)
        rng2 = random.Random(42)
        from app.qa_engine.property_testing.generators import random_email_config

        c1 = random_email_config(rng1)
        c2 = random_email_config(rng2)
        assert c1 == c2

    def test_different_seeds_differ(self):
        import random

        from app.qa_engine.property_testing.generators import random_email_config

        c1 = random_email_config(random.Random(1))
        c2 = random_email_config(random.Random(99999))
        # Different seeds should produce different configs (extremely unlikely to be equal)
        assert c1 != c2

    def test_no_dark_mode(self):
        config = EmailConfig(
            section_count=1,
            section_types=("content",),
            content_lengths=(50,),
            font_family="Arial, sans-serif",
            primary_color="#000000",
            background_color="#ffffff",
            text_color="#000000",
            image_count=0,
            image_widths=(),
            table_nesting_depth=0,
            has_mso_conditionals=False,
            has_dark_mode=False,
            dark_mode_complete=False,
            link_count=0,
            include_javascript_links=False,
            include_empty_alt=False,
            target_size_kb=0,
        )
        html = build_email(config)
        assert "prefers-color-scheme" not in html

    def test_deep_table_nesting(self):
        config = EmailConfig(
            section_count=10,
            section_types=("content",) * 10,
            content_lengths=(50,) * 10,
            font_family="Arial, sans-serif",
            primary_color="#000000",
            background_color="#ffffff",
            text_color="#000000",
            image_count=0,
            image_widths=(),
            table_nesting_depth=8,
            has_mso_conditionals=False,
            has_dark_mode=False,
            dark_mode_complete=False,
            link_count=0,
            include_javascript_links=False,
            include_empty_alt=False,
            target_size_kb=0,
        )
        html = build_email(config)
        # Count nested table opens — should have at least 8 nested
        assert html.count("<table") >= 8
