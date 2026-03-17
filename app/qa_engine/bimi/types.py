from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DMARCInfo:
    """Parsed DMARC record details."""

    raw_record: str
    policy: str  # none | quarantine | reject
    subdomain_policy: str | None = None  # sp= tag
    pct: int = 100  # pct= tag (percentage of messages subject to filtering)


@dataclass(frozen=True)
class SVGValidationResult:
    """SVG Tiny PS profile validation result."""

    valid: bool
    issues: list[str] = field(default_factory=lambda: [])


@dataclass(frozen=True)
class BIMIStatus:
    """Complete BIMI readiness assessment for a domain."""

    domain: str

    # DMARC
    dmarc_ready: bool  # p=quarantine or p=reject
    dmarc_policy: str  # none | quarantine | reject | missing
    dmarc_record: str | None = None
    dmarc_info: DMARCInfo | None = None

    # BIMI record
    bimi_record_exists: bool = False
    bimi_record: str | None = None
    bimi_svg_url: str | None = None
    bimi_authority_url: str | None = None  # CMC PEM URL

    # SVG validation
    svg_valid: bool | None = None  # None = not checked (no BIMI record)
    svg_validation: SVGValidationResult | None = None

    # CMC (Certified Mark Certificate)
    cmc_status: str = "unknown"  # present | missing | unknown

    # Generated record
    generated_record: str = ""  # Template TXT record for deployment

    # All issues found
    issues: list[str] = field(default_factory=lambda: [])

    @property
    def ready(self) -> bool:
        """True when domain is fully BIMI-ready."""
        return (
            self.dmarc_ready
            and self.bimi_record_exists
            and self.svg_valid is True
            and self.cmc_status == "present"
        )
