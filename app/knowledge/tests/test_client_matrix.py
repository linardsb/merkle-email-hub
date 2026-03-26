"""Tests for the email client rendering matrix loader and registry."""

from __future__ import annotations

from pathlib import Path

from app.knowledge.client_matrix import (
    AudienceConstraints,
    ClientProfile,
    CSSSupport,
    DarkModeProfile,
    KnownBug,
    load_client_matrix,
)
from app.knowledge.ontology.types import ClientEngine, SupportLevel


class TestLoadClientMatrix:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()

    def test_loads_yaml_successfully(self) -> None:
        matrix = load_client_matrix()
        assert matrix.version == "1.0"
        assert len(matrix.clients) >= 16

    def test_singleton_cache(self) -> None:
        m1 = load_client_matrix()
        m2 = load_client_matrix()
        assert m1 is m2

    def test_cache_clear_reloads(self) -> None:
        m1 = load_client_matrix()
        load_client_matrix.cache_clear()
        m2 = load_client_matrix()
        assert m1 is not m2
        assert m1.version == m2.version

    def test_missing_file_returns_empty_matrix(self, tmp_path: Path) -> None:
        matrix = load_client_matrix(path=tmp_path / "nonexistent.yaml")
        assert matrix.version == "0.0"
        assert len(matrix.clients) == 0

    def test_malformed_yaml_returns_empty_matrix(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not_a_dict: [1, 2, 3]\n", encoding="utf-8")
        load_client_matrix.cache_clear()
        matrix = load_client_matrix(path=bad_file)
        # YAML parses to a dict with one key, so it goes through _parse_yaml
        # but has no "clients" key → empty
        assert len(matrix.clients) == 0

    def test_non_dict_yaml_returns_empty_matrix(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "scalar.yaml"
        bad_file.write_text("just a string\n", encoding="utf-8")
        load_client_matrix.cache_clear()
        matrix = load_client_matrix(path=bad_file)
        assert matrix.version == "0.0"
        assert len(matrix.clients) == 0


class TestGetClient:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()
        self.matrix = load_client_matrix()

    def test_known_client(self) -> None:
        client = self.matrix.get_client("outlook_365_win")
        assert client is not None
        assert isinstance(client, ClientProfile)
        assert client.display_name == "Outlook 365 (Windows)"
        assert client.engine == ClientEngine.WORD

    def test_gmail_web(self) -> None:
        client = self.matrix.get_client("gmail_web")
        assert client is not None
        assert client.engine == ClientEngine.BLINK

    def test_apple_mail_macos(self) -> None:
        client = self.matrix.get_client("apple_mail_macos")
        assert client is not None
        assert client.engine == ClientEngine.WEBKIT

    def test_unknown_returns_none(self) -> None:
        assert self.matrix.get_client("nonexistent_client") is None

    def test_all_client_mapping_ids_present(self) -> None:
        """Every ID from audience_context.CLIENT_MAPPING must exist."""
        required_ids = [
            "gmail_web",
            "gmail_ios",
            "gmail_android",
            "outlook_365_win",
            "outlook_2019_win",
            "apple_mail_macos",
            "apple_mail_ios",
            "samsung_mail",
            "yahoo_web",
            "yahoo_ios",
            "yahoo_android",
            "thunderbird",
            "outlook_mac",
            "outlook_web",
            "aol_web",
            "protonmail_web",
        ]
        for cid in required_ids:
            assert self.matrix.get_client(cid) is not None, f"Missing client: {cid}"


class TestGetCSSSupport:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()
        self.matrix = load_client_matrix()

    def test_outlook_flexbox_unsupported(self) -> None:
        css = self.matrix.get_css_support("outlook_365_win", "flexbox")
        assert css is not None
        assert isinstance(css, CSSSupport)
        assert css.support == SupportLevel.NONE
        assert "table" in css.workaround.lower()

    def test_apple_mail_flexbox_supported(self) -> None:
        css = self.matrix.get_css_support("apple_mail_macos", "flexbox")
        assert css is not None
        assert css.support == SupportLevel.FULL

    def test_unknown_property_returns_none(self) -> None:
        assert self.matrix.get_css_support("outlook_365_win", "nonexistent") is None

    def test_unknown_client_returns_none(self) -> None:
        assert self.matrix.get_css_support("nonexistent", "flexbox") is None

    def test_gmail_border_radius_supported(self) -> None:
        css = self.matrix.get_css_support("gmail_web", "border-radius")
        assert css is not None
        assert css.support == SupportLevel.FULL


class TestGetDarkMode:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()
        self.matrix = load_client_matrix()

    def test_gmail_forced_inversion(self) -> None:
        dm = self.matrix.get_dark_mode("gmail_web")
        assert dm is not None
        assert isinstance(dm, DarkModeProfile)
        assert dm.type == "forced_inversion"
        assert dm.developer_control == "none"
        assert dm.selectors == ()

    def test_apple_mail_developer_controlled(self) -> None:
        dm = self.matrix.get_dark_mode("apple_mail_macos")
        assert dm is not None
        assert dm.type == "developer_controlled"
        assert dm.developer_control == "full"
        assert "@media (prefers-color-scheme: dark)" in dm.selectors

    def test_outlook_com_partial(self) -> None:
        dm = self.matrix.get_dark_mode("outlook_web")
        assert dm is not None
        assert dm.type == "partial_developer"
        assert "[data-ogsc]" in dm.selectors
        assert "[data-ogsb]" in dm.selectors

    def test_samsung_double_inversion(self) -> None:
        dm = self.matrix.get_dark_mode("samsung_mail")
        assert dm is not None
        assert dm.type == "double_inversion_risk"

    def test_unknown_returns_none(self) -> None:
        assert self.matrix.get_dark_mode("nonexistent") is None


class TestGetKnownBugs:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()
        self.matrix = load_client_matrix()

    def test_outlook_has_bugs(self) -> None:
        bugs = self.matrix.get_known_bugs("outlook_365_win")
        assert len(bugs) >= 3
        assert all(isinstance(b, KnownBug) for b in bugs)
        bug_ids = {b.id for b in bugs}
        assert "ghost_table" in bug_ids
        assert "dpi_scaling" in bug_ids

    def test_apple_mail_no_bugs(self) -> None:
        bugs = self.matrix.get_known_bugs("apple_mail_macos")
        assert bugs == []

    def test_unknown_returns_empty(self) -> None:
        assert self.matrix.get_known_bugs("nonexistent") == []


class TestGetConstraintsForClients:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()
        self.matrix = load_client_matrix()

    def test_single_client_gmail(self) -> None:
        constraints = self.matrix.get_constraints_for_clients(["gmail_web"])
        assert isinstance(constraints, AudienceConstraints)
        assert constraints.clip_threshold_kb == 102
        assert not constraints.vml_required
        assert "blink" in constraints.rendering_engines

    def test_multi_client_outlook_gmail(self) -> None:
        constraints = self.matrix.get_constraints_for_clients(
            ["gmail_web", "outlook_365_win"],
        )
        assert constraints.vml_required is True
        assert constraints.mso_conditionals is True
        assert constraints.clip_threshold_kb == 102
        assert "word" in constraints.rendering_engines
        assert "blink" in constraints.rendering_engines
        # flexbox should be in unsupported
        props = {(cat, prop) for cat, prop, _ in constraints.unsupported_properties}
        assert ("layout", "flexbox") in props

    def test_vml_required_if_any_client_needs_it(self) -> None:
        constraints = self.matrix.get_constraints_for_clients(
            ["apple_mail_macos", "outlook_365_win"],
        )
        assert constraints.vml_required is True

    def test_no_vml_for_webmail_only(self) -> None:
        constraints = self.matrix.get_constraints_for_clients(
            ["gmail_web", "apple_mail_macos"],
        )
        assert constraints.vml_required is False

    def test_empty_client_list(self) -> None:
        constraints = self.matrix.get_constraints_for_clients([])
        assert constraints.unsupported_properties == ()
        assert not constraints.vml_required
        assert constraints.clip_threshold_kb is None

    def test_bug_deduplication(self) -> None:
        """Same bug ID from multiple Outlook versions shouldn't duplicate."""
        constraints = self.matrix.get_constraints_for_clients(
            ["outlook_365_win", "outlook_2019_win"],
        )
        bug_ids = [b.id for b in constraints.known_bugs]
        assert len(bug_ids) == len(set(bug_ids)), "Bugs should be deduplicated"


class TestFormatAudienceContext:
    def setup_method(self) -> None:
        load_client_matrix.cache_clear()
        self.matrix = load_client_matrix()

    def test_gmail_outlook_includes_key_warnings(self) -> None:
        output = self.matrix.format_audience_context(["gmail_web", "outlook_365_win"])
        assert "RENDERING ENGINES" in output
        assert "VML required" in output
        assert "MSO conditional" in output
        assert "102KB" in output
        assert "DARK MODE TYPES" in output
        assert "KNOWN RENDERING BUGS" in output
        assert "ghost_table" in output

    def test_apple_mail_only_minimal_output(self) -> None:
        output = self.matrix.format_audience_context(["apple_mail_macos"])
        assert "VML" not in output
        assert "MSO" not in output
        assert "clipping" not in output
        assert "RENDERING ENGINES" in output
        assert "webkit" in output

    def test_empty_clients(self) -> None:
        output = self.matrix.format_audience_context([])
        assert output == ""
