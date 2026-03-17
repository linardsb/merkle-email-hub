"""BIMI readiness checker — DNS lookups + SVG validation."""

from __future__ import annotations

import asyncio
import re

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

from .types import BIMIStatus, DMARCInfo, SVGValidationResult

logger = get_logger(__name__)

# Domain validation: RFC 1035 labels
_DOMAIN_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$")

# BIMI record parsing
_BIMI_VERSION_RE = re.compile(r"v\s*=\s*BIMI1", re.IGNORECASE)
_BIMI_L_RE = re.compile(r"l\s*=\s*(https?://[^\s;]+)", re.IGNORECASE)
_BIMI_A_RE = re.compile(r"a\s*=\s*(https?://[^\s;]+)", re.IGNORECASE)

# SVG Tiny PS forbidden elements (simplified check for common violations)
_SVG_FORBIDDEN_ELEMENTS = {
    "script",
    "foreignObject",
    "use",
    "image",
    "a",
    "animate",
    "animateTransform",
    "animateMotion",
    "set",
    "filter",
    "feGaussianBlur",
    "feColorMatrix",
}

# Pre-compiled patterns for forbidden element detection
_SVG_FORBIDDEN_PATTERNS = {
    elem: re.compile(rf"<{re.escape(elem)}[\s/>]", re.IGNORECASE)
    for elem in _SVG_FORBIDDEN_ELEMENTS
}

# SVG must not reference external resources
_SVG_EXTERNAL_REF_RE = re.compile(r'(?:xlink:href|href)\s*=\s*["\'](?!#)', re.IGNORECASE)


class BIMIReadinessChecker:
    """Check a domain's BIMI readiness: DMARC, BIMI DNS, SVG, CMC."""

    async def check_domain(self, domain: str) -> BIMIStatus:
        """Run all BIMI readiness checks for a domain."""
        if not _DOMAIN_RE.match(domain):
            return BIMIStatus(
                domain=domain,
                dmarc_ready=False,
                dmarc_policy="invalid_domain",
                issues=["Invalid domain format"],
            )

        issues: list[str] = []

        # Phase 1: DNS lookups (DMARC + BIMI in parallel)
        dmarc_record, bimi_record = await asyncio.gather(
            self._lookup_dmarc(domain),
            self._lookup_bimi(domain),
        )

        # Phase 2: Parse DMARC
        dmarc_info: DMARCInfo | None = None
        dmarc_policy = "missing"
        dmarc_ready = False

        if dmarc_record:
            dmarc_info = self._parse_dmarc(dmarc_record)
            dmarc_policy = dmarc_info.policy
            dmarc_ready = dmarc_policy in ("quarantine", "reject")
            if not dmarc_ready:
                issues.append(
                    f"DMARC policy is '{dmarc_policy}' — must be 'quarantine' or 'reject' for BIMI. "
                    f"Update your _dmarc.{domain} TXT record to include p=reject (recommended) or p=quarantine."
                )
            if dmarc_info.pct < 100:
                issues.append(
                    f"DMARC pct={dmarc_info.pct}% — some providers require pct=100 for BIMI."
                )
        else:
            issues.append(
                f"No DMARC record found at _dmarc.{domain}. "
                "BIMI requires a DMARC policy of 'quarantine' or 'reject'."
            )

        # Phase 3: Parse BIMI record
        bimi_record_exists = False
        bimi_svg_url: str | None = None
        bimi_authority_url: str | None = None

        if bimi_record:
            if _BIMI_VERSION_RE.search(bimi_record):
                bimi_record_exists = True
                l_match = _BIMI_L_RE.search(bimi_record)
                a_match = _BIMI_A_RE.search(bimi_record)
                bimi_svg_url = l_match.group(1) if l_match else None
                bimi_authority_url = a_match.group(1) if a_match else None

                if not bimi_svg_url:
                    issues.append("BIMI record exists but has no l= (logo URL) tag.")
            else:
                issues.append(
                    f"BIMI TXT record found but does not contain v=BIMI1: {bimi_record[:100]}"
                )
        else:
            issues.append(
                f"No BIMI record found at default._bimi.{domain}. "
                "Add a TXT record with: v=BIMI1; l=<svg_url>; a=<cmc_pem_url>"
            )

        # Phase 4: SVG validation (only if we have a URL)
        svg_valid: bool | None = None
        svg_validation: SVGValidationResult | None = None

        if bimi_svg_url:
            svg_validation = await self._validate_svg(bimi_svg_url)
            svg_valid = svg_validation.valid
            issues.extend(svg_validation.issues)

        # Phase 5: CMC status
        cmc_status = "unknown"
        if bimi_authority_url:
            cmc_status = "present"
        elif bimi_record_exists:
            cmc_status = "missing"
            issues.append(
                "No CMC (Certified Mark Certificate) URL in BIMI record (a= tag). "
                "While not required by all providers, Gmail requires a VMC or CMC."
            )

        # Generate the BIMI TXT record template
        generated_record = self._generate_record(domain, bimi_svg_url, bimi_authority_url)

        logger.info(
            "bimi.check_completed",
            domain=domain,
            dmarc_ready=dmarc_ready,
            bimi_exists=bimi_record_exists,
            svg_valid=svg_valid,
            cmc_status=cmc_status,
            issue_count=len(issues),
        )

        return BIMIStatus(
            domain=domain,
            dmarc_ready=dmarc_ready,
            dmarc_policy=dmarc_policy,
            dmarc_record=dmarc_record,
            dmarc_info=dmarc_info,
            bimi_record_exists=bimi_record_exists,
            bimi_record=bimi_record,
            bimi_svg_url=bimi_svg_url,
            bimi_authority_url=bimi_authority_url,
            svg_valid=svg_valid,
            svg_validation=svg_validation,
            cmc_status=cmc_status,
            generated_record=generated_record,
            issues=issues,
        )

    # --- DNS Lookups ---

    async def _lookup_dmarc(self, domain: str) -> str | None:
        """Look up _dmarc.{domain} TXT record via asyncio.resolver."""
        settings = get_settings()
        try:
            import dns.asyncresolver  # dnspython

            resolver = dns.asyncresolver.Resolver()
            resolver.lifetime = settings.qa_bimi.dns_timeout_seconds
            answers = await resolver.resolve(f"_dmarc.{domain}", "TXT")
            # Concatenate all TXT strings
            for rdata in answers:
                txt = b"".join(rdata.strings).decode("utf-8", errors="replace")
                if "dmarc" in txt.lower():
                    return txt
        except Exception:
            logger.debug("bimi.dmarc_lookup_failed", domain=domain, exc_info=True)
        return None

    async def _lookup_bimi(self, domain: str) -> str | None:
        """Look up default._bimi.{domain} TXT record."""
        settings = get_settings()
        try:
            import dns.asyncresolver

            resolver = dns.asyncresolver.Resolver()
            resolver.lifetime = settings.qa_bimi.dns_timeout_seconds
            answers = await resolver.resolve(f"default._bimi.{domain}", "TXT")
            for rdata in answers:
                txt = b"".join(rdata.strings).decode("utf-8", errors="replace")
                if "bimi" in txt.lower():
                    return txt
        except Exception:
            logger.debug("bimi.bimi_lookup_failed", domain=domain, exc_info=True)
        return None

    # --- DMARC Parsing ---

    def _parse_dmarc(self, record: str) -> DMARCInfo:
        """Parse a DMARC TXT record into structured data."""
        tags: dict[str, str] = {}
        for part in record.split(";"):
            part = part.strip()
            if "=" in part:
                key, _, val = part.partition("=")
                tags[key.strip().lower()] = val.strip()

        policy = tags.get("p", "none").lower()
        sp = tags.get("sp")
        pct_str = tags.get("pct", "100")
        try:
            pct = max(0, min(100, int(pct_str)))
        except ValueError:
            pct = 100

        return DMARCInfo(
            raw_record=record,
            policy=policy,
            subdomain_policy=sp,
            pct=pct,
        )

    # --- SVG Validation (Tiny PS profile) ---

    async def _validate_svg(self, svg_url: str) -> SVGValidationResult:
        """Fetch and validate SVG against BIMI Tiny PS requirements."""
        settings = get_settings()
        issues: list[str] = []

        # Validate URL scheme
        if not svg_url.startswith("https://"):
            return SVGValidationResult(
                valid=False,
                issues=["SVG URL must use HTTPS"],
            )

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(settings.qa_bimi.svg_fetch_timeout_seconds),
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    svg_url,
                    headers={"Accept": "image/svg+xml"},
                )
                response.raise_for_status()

                # Size check
                content_length = len(response.content)
                if content_length > settings.qa_bimi.svg_max_size_bytes:
                    issues.append(
                        f"SVG is {content_length} bytes — max allowed is {settings.qa_bimi.svg_max_size_bytes} bytes (32KB)."
                    )

                svg_text = response.text

        except httpx.HTTPStatusError as exc:
            return SVGValidationResult(
                valid=False,
                issues=[f"Failed to fetch SVG: HTTP {exc.response.status_code}"],
            )
        except httpx.TimeoutException:
            return SVGValidationResult(
                valid=False,
                issues=["SVG fetch timed out"],
            )
        except Exception:
            return SVGValidationResult(
                valid=False,
                issues=["Failed to fetch SVG from URL"],
            )

        # Parse SVG content for Tiny PS compliance
        issues.extend(self._check_svg_tiny_ps(svg_text))

        return SVGValidationResult(
            valid=len(issues) == 0,
            issues=issues,
        )

    def _check_svg_tiny_ps(self, svg_text: str) -> list[str]:
        """Check SVG content against BIMI Tiny PS profile requirements."""
        issues: list[str] = []
        svg_lower = svg_text.lower()

        # Must be SVG
        if "<svg" not in svg_lower:
            issues.append("Content does not appear to be an SVG file.")
            return issues

        # Must declare baseProfile="tiny-ps" (recommended but not always enforced)
        if 'baseprofile="tiny-ps"' not in svg_lower:
            issues.append('SVG should declare baseProfile="tiny-ps" for BIMI compliance.')

        # Check for forbidden elements
        for elem, pattern in _SVG_FORBIDDEN_PATTERNS.items():
            if pattern.search(svg_text):
                issues.append(f"SVG contains forbidden element <{elem}>.")

        # Check for external references
        if _SVG_EXTERNAL_REF_RE.search(svg_text):
            issues.append("SVG contains external references (href/xlink:href to external URL).")

        # Check viewBox for square aspect ratio
        viewbox_match = re.search(r'viewBox\s*=\s*"([^"]+)"', svg_text, re.IGNORECASE)
        if viewbox_match:
            parts = viewbox_match.group(1).split()
            if len(parts) == 4:
                try:
                    width = float(parts[2])
                    height = float(parts[3])
                    if width > 0 and height > 0 and abs(width - height) > 0.01:
                        issues.append(
                            f"SVG viewBox is not square ({width}x{height}). BIMI requires a square logo."
                        )
                except ValueError:
                    issues.append("Could not parse SVG viewBox dimensions.")
        else:
            issues.append("SVG is missing a viewBox attribute.")

        # Check for title element (required by BIMI spec)
        if "<title" not in svg_lower:
            issues.append("SVG is missing a <title> element (required by BIMI spec).")

        return issues

    # --- Record Generator ---

    def _generate_record(
        self,
        domain: str,
        svg_url: str | None = None,
        authority_url: str | None = None,
    ) -> str:
        """Generate a BIMI TXT record string for the domain."""
        l_part = svg_url or "https://example.com/bimi/logo.svg"
        a_part = authority_url or ""

        record = f"v=BIMI1; l={l_part};"
        if a_part:
            record += f" a={a_part};"

        return f'default._bimi.{domain} IN TXT "{record}"'
