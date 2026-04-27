"""Tests for pipeline quality contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ai.pipeline.contracts import (
    Assertion,
    Contract,
    ContractValidator,
    load_contract,
)
from app.qa_engine.schemas import QACheckResult

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contract_defs"


# ── Fixtures & factories ─────────────────────────────────────────────────────


def _make_contract(**overrides: object) -> Contract:
    defaults: dict[str, object] = {
        "name": "test_contract",
        "assertions": (Assertion(check="html_valid", operator="==", threshold=True),),
    }
    defaults.update(overrides)
    return Contract(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def sample_html_valid() -> str:
    """Full email HTML with DOCTYPE, table layout, dark mode, MSO conditionals."""
    return """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Email</title>
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<style>
:root { color-scheme: light dark; }
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a1a !important; }
  .dark-text { color: #e0e0e0 !important; }
}
[data-ogsc] .dark-text { color: #e0e0e0; }
[data-ogsb] .dark-bg { background-color: #1a1a1a; }
</style>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body>
<table role="presentation" width="600">
<tr><td style="font-family:Arial,sans-serif; font-size:24px; font-weight:bold; color:#333333; line-height:28px; mso-line-height-rule:exactly;">Welcome</td></tr>
<tr><td><img src="https://example.com/hero.png" alt="Hero image" width="600" height="300"></td></tr>
<tr><td style="font-family:Arial,sans-serif; font-size:16px; color:#333333; line-height:24px; mso-line-height-rule:exactly;"><a href="https://example.com">Visit us</a></td></tr>
</table>
</body>
</html>"""


@pytest.fixture
def sample_html_oversized(sample_html_valid: str) -> str:
    padding = "<!-- padding -->" * 7000
    return sample_html_valid.replace("</body>", f"{padding}</body>")


@pytest.fixture
def sample_html_no_dark_mode() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Email</title></head>
<body>
<table role="presentation" width="600">
<tr><td style="font-family:Arial,sans-serif; font-size:16px; color:#333333; line-height:24px;">Content</td></tr>
</table>
</body>
</html>"""


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestHtmlValidCheck:
    validator = ContractValidator()

    async def test_valid_html_passes(self, sample_html_valid: str) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="html_valid", operator="==", threshold=True),)
        )
        result = await self.validator.validate(contract, sample_html_valid)
        assert result.passed
        assert result.failures == ()

    async def test_broken_fragment_fails(self) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="html_valid", operator="==", threshold=True),)
        )
        result = await self.validator.validate(contract, "")
        assert not result.passed
        assert len(result.failures) == 1
        assert result.failures[0].assertion.check == "html_valid"


class TestSizeChecks:
    validator = ContractValidator()

    async def test_min_size_passes(self, sample_html_valid: str) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="min_size", operator=">=", threshold=100),)
        )
        result = await self.validator.validate(contract, sample_html_valid)
        assert result.passed

    async def test_max_size_fails(self, sample_html_oversized: str) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="max_size", operator="<=", threshold=102400),)
        )
        result = await self.validator.validate(contract, sample_html_oversized)
        assert not result.passed
        assert result.failures[0].assertion.check == "max_size"


class TestTableLayoutCheck:
    validator = ContractValidator()

    async def test_table_layout_passes(self, sample_html_valid: str) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="has_table_layout", operator="==", threshold=True),)
        )
        result = await self.validator.validate(contract, sample_html_valid)
        assert result.passed

    async def test_div_layout_fails(self) -> None:
        html = """<!DOCTYPE html><html><body>
        <div style="width:600px"><p>Content</p></div>
        </body></html>"""
        contract = _make_contract(
            assertions=(Assertion(check="has_table_layout", operator="==", threshold=True),)
        )
        result = await self.validator.validate(contract, html)
        assert not result.passed


class TestDarkModeCheck:
    validator = ContractValidator()

    async def test_dark_mode_present(self, sample_html_valid: str) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="dark_mode_present", operator="==", threshold=True),)
        )
        result = await self.validator.validate(contract, sample_html_valid)
        assert result.passed

    async def test_dark_mode_missing(self, sample_html_no_dark_mode: str) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="dark_mode_present", operator="==", threshold=True),)
        )
        result = await self.validator.validate(contract, sample_html_no_dark_mode)
        assert not result.passed


class TestNoCriticalQA:
    validator = ContractValidator()

    async def test_no_critical_passes(self) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="no_critical_qa", operator="==", threshold=True),)
        )
        metadata = {
            "qa_results": [
                QACheckResult(
                    check_name="html_validation", passed=True, score=1.0, severity="info"
                ),
                QACheckResult(check_name="dark_mode", passed=True, score=0.9, severity="warning"),
            ]
        }
        result = await self.validator.validate(contract, "<html></html>", metadata)
        assert result.passed

    async def test_critical_finding_fails(self) -> None:
        contract = _make_contract(
            assertions=(Assertion(check="no_critical_qa", operator="==", threshold=True),)
        )
        metadata = {
            "qa_results": [
                QACheckResult(
                    check_name="html_validation", passed=True, score=1.0, severity="info"
                ),
                QACheckResult(check_name="file_size", passed=False, score=0.0, severity="error"),
            ]
        }
        result = await self.validator.validate(contract, "<html></html>", metadata)
        assert not result.passed
        assert result.failures[0].assertion.check == "no_critical_qa"


class TestAssertionOperators:
    validator = ContractValidator()

    async def test_operators(self, sample_html_valid: str) -> None:
        c_ge = _make_contract(assertions=(Assertion(check="min_size", operator=">=", threshold=1),))
        assert (await self.validator.validate(c_ge, sample_html_valid)).passed

        c_le = _make_contract(
            assertions=(Assertion(check="max_size", operator="<=", threshold=999999),)
        )
        assert (await self.validator.validate(c_le, sample_html_valid)).passed

        c_eq = _make_contract(
            assertions=(Assertion(check="html_valid", operator="==", threshold=True),)
        )
        assert (await self.validator.validate(c_eq, sample_html_valid)).passed

        c_fid = _make_contract(
            assertions=(Assertion(check="fidelity_above", operator=">=", threshold=0.5),)
        )
        assert (await self.validator.validate(c_fid, sample_html_valid, {"fidelity": 0.9})).passed

        assert not (
            await self.validator.validate(c_fid, sample_html_valid, {"fidelity": 0.3})
        ).passed


class TestContractValidatorIntegration:
    validator = ContractValidator()

    async def test_full_contract_load_and_validate(self, sample_html_valid: str) -> None:
        load_contract.cache_clear()

        contract = load_contract(CONTRACTS_DIR / "html_valid.yaml")
        assert contract.name == "html_valid"
        assert len(contract.assertions) == 4

        result = await self.validator.validate(contract, sample_html_valid)
        assert result.passed
        assert result.failures == ()
        assert result.duration_ms >= 0

        broken_result = await self.validator.validate(contract, "")
        assert not broken_result.passed
        assert len(broken_result.failures) >= 1
        checks_failed = {f.assertion.check for f in broken_result.failures}
        assert "html_valid" in checks_failed
        assert broken_result.duration_ms >= 0

        load_contract.cache_clear()
