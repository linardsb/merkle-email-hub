"""Mock design sync provider for demo without Figma/Penpot/etc.

Returns hardcoded design file structures representing realistic email layouts,
enabling the full design-to-email pipeline to work in development.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.design_sync.protocol import (
    DesignComponent,
    DesignFile,
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExportedImage,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)


class MockDesignSyncService:
    """Mock provider returning pre-built email layout structures."""

    async def list_files(self, access_token: str) -> list[DesignFile]:
        """Return a set of mock design files for browsing."""
        return [
            DesignFile(
                file_id="summer-campaign",
                name="Summer Campaign Email",
                url="demo://summer-campaign",
                thumbnail_url="https://via.placeholder.com/320x200/2563EB/FFFFFF?text=Summer+Campaign",
                last_modified=datetime(2026, 3, 15, 10, 30, tzinfo=UTC),
                folder="Email Campaigns",
            ),
            DesignFile(
                file_id="welcome-series",
                name="Welcome Series Templates",
                url="demo://welcome-series",
                thumbnail_url="https://via.placeholder.com/320x200/7C3AED/FFFFFF?text=Welcome+Series",
                last_modified=datetime(2026, 3, 12, 14, 0, tzinfo=UTC),
                folder="Email Campaigns",
            ),
            DesignFile(
                file_id="product-launch",
                name="Product Launch Announcement",
                url="demo://product-launch",
                thumbnail_url="https://via.placeholder.com/320x200/F59E0B/FFFFFF?text=Product+Launch",
                last_modified=datetime(2026, 3, 10, 9, 15, tzinfo=UTC),
                folder="Email Campaigns",
            ),
            DesignFile(
                file_id="design-system",
                name="Email Design System",
                url="demo://design-system",
                thumbnail_url="https://via.placeholder.com/320x200/10B981/FFFFFF?text=Design+System",
                last_modified=datetime(2026, 3, 18, 16, 45, tzinfo=UTC),
                folder="Brand Assets",
            ),
            DesignFile(
                file_id="newsletter-q2",
                name="Q2 Newsletter Template",
                url="demo://newsletter-q2",
                thumbnail_url="https://via.placeholder.com/320x200/EF4444/FFFFFF?text=Newsletter+Q2",
                last_modified=datetime(2026, 3, 8, 11, 0, tzinfo=UTC),
                folder="Newsletters",
            ),
        ]

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:
        """Always returns True — mock connections are always valid."""
        return True

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:
        """Return a realistic set of design tokens for an email template."""
        return ExtractedTokens(
            colors=[
                ExtractedColor(name="Primary", hex="#2563EB"),
                ExtractedColor(name="Secondary", hex="#7C3AED"),
                ExtractedColor(name="Accent", hex="#F59E0B"),
                ExtractedColor(name="Background", hex="#FFFFFF"),
                ExtractedColor(name="Text", hex="#1F2937"),
                ExtractedColor(name="Link", hex="#2563EB"),
                ExtractedColor(name="Dark Background", hex="#111827"),
                ExtractedColor(name="Divider", hex="#E5E7EB"),
            ],
            typography=[
                ExtractedTypography(
                    name="Heading", family="Inter", weight="700", size=28, line_height=1.2
                ),
                ExtractedTypography(
                    name="Subheading", family="Inter", weight="600", size=22, line_height=1.3
                ),
                ExtractedTypography(
                    name="Body", family="Inter", weight="400", size=16, line_height=1.5
                ),
                ExtractedTypography(
                    name="Small", family="Inter", weight="400", size=12, line_height=1.4
                ),
            ],
            spacing=[
                ExtractedSpacing(name="Section", value=32),
                ExtractedSpacing(name="Element", value=16),
                ExtractedSpacing(name="Container Padding", value=24),
            ],
        )

    async def get_file_structure(
        self, file_ref: str, access_token: str, *, depth: int | None = 2
    ) -> DesignFileStructure:
        """Return a realistic email layout with standard sections."""
        return DesignFileStructure(
            file_name="Summer Campaign Email",
            pages=[
                DesignNode(
                    id="page-1",
                    name="Email Template",
                    type=DesignNodeType.PAGE,
                    children=[
                        DesignNode(
                            id="header-frame",
                            name="Header",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=80,
                            x=0,
                            y=0,
                            children=[
                                DesignNode(
                                    id="logo-img",
                                    name="Logo",
                                    type=DesignNodeType.IMAGE,
                                    width=150,
                                    height=40,
                                ),
                                DesignNode(
                                    id="nav-text",
                                    name="Navigation",
                                    type=DesignNodeType.TEXT,
                                    text_content="Home | Products | Contact",
                                ),
                            ],
                        ),
                        DesignNode(
                            id="hero-frame",
                            name="Hero",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=400,
                            x=0,
                            y=80,
                            children=[
                                DesignNode(
                                    id="hero-img",
                                    name="Hero Image",
                                    type=DesignNodeType.IMAGE,
                                    width=600,
                                    height=300,
                                ),
                                DesignNode(
                                    id="hero-heading",
                                    name="Heading",
                                    type=DesignNodeType.TEXT,
                                    text_content="Summer Sale is Here",
                                ),
                                DesignNode(
                                    id="hero-cta",
                                    name="CTA Button",
                                    type=DesignNodeType.FRAME,
                                    width=200,
                                    height=48,
                                ),
                            ],
                        ),
                        DesignNode(
                            id="content-frame",
                            name="Two Column Content",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=300,
                            x=0,
                            y=480,
                            children=[
                                DesignNode(
                                    id="col-left",
                                    name="Left Column",
                                    type=DesignNodeType.FRAME,
                                    width=280,
                                    height=280,
                                ),
                                DesignNode(
                                    id="col-right",
                                    name="Right Column",
                                    type=DesignNodeType.FRAME,
                                    width=280,
                                    height=280,
                                ),
                            ],
                        ),
                        DesignNode(
                            id="cta-frame",
                            name="CTA Section",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=120,
                            x=0,
                            y=780,
                        ),
                        DesignNode(
                            id="footer-frame",
                            name="Footer",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=160,
                            x=0,
                            y=900,
                            children=[
                                DesignNode(
                                    id="social-icons",
                                    name="Social Icons",
                                    type=DesignNodeType.GROUP,
                                ),
                                DesignNode(
                                    id="footer-text",
                                    name="Legal Text",
                                    type=DesignNodeType.TEXT,
                                    text_content="Unsubscribe | Privacy Policy",
                                ),
                                DesignNode(
                                    id="address-text",
                                    name="Address",
                                    type=DesignNodeType.TEXT,
                                    text_content="123 Innovation Drive, London",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    async def list_components(self, file_ref: str, access_token: str) -> list[DesignComponent]:
        """Return a set of reusable design components."""
        return [
            DesignComponent(
                component_id="comp-header",
                name="Email Header",
                description="Logo + navigation bar",
                containing_page="Email Template",
            ),
            DesignComponent(
                component_id="comp-hero",
                name="Hero Block",
                description="Full-width image with overlay text and CTA",
                containing_page="Email Template",
            ),
            DesignComponent(
                component_id="comp-two-col",
                name="Two Column Layout",
                description="Side-by-side content blocks",
                containing_page="Email Template",
            ),
            DesignComponent(
                component_id="comp-cta",
                name="CTA Button",
                description="Primary action button with rounded corners",
                containing_page="Email Template",
            ),
            DesignComponent(
                component_id="comp-footer",
                name="Email Footer",
                description="Social links, legal text, unsubscribe",
                containing_page="Email Template",
            ),
        ]

    async def export_images(
        self,
        file_ref: str,
        access_token: str,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> list[ExportedImage]:
        """Return placeholder image URLs for requested nodes."""
        return [
            ExportedImage(
                node_id=nid,
                url=f"https://via.placeholder.com/600x300/2563EB/FFFFFF?text={nid}",
                format=format,
            )
            for nid in node_ids
        ]
