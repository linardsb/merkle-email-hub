# pyright: reportUnknownVariableType=false
"""Orchestrator for the Design → Scaffolder → Template conversion pipeline."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.design_sync.exceptions import SyncFailedError
from app.design_sync.models import DesignConnection
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedTokens,
)
from app.design_sync.repository import DesignSyncRepository
from app.design_sync.schemas import (
    DesignTokensResponse,
    DownloadAssetsResponse,
    LayoutAnalysisResponse,
    StoredAssetResponse,
)

if TYPE_CHECKING:
    from app.ai.agents.scaffolder.schemas import ScaffolderResponse
    from app.design_sync.service import DesignSyncService

logger = get_logger(__name__)


class DesignImportService:
    """Orchestrates the Figma → Scaffolder → Template conversion pipeline.

    Runs as a background task with its own DB session (via get_db_context).
    Updates DesignImport status as it progresses:
    pending → converting → completed/failed
    """

    def __init__(
        self,
        design_service_factory: type[DesignSyncService],
        user: User,
    ) -> None:
        self._service_factory = design_service_factory
        self._user = user

    async def run_conversion(
        self,
        import_id: int,
        *,
        run_qa: bool = True,
        output_mode: Literal["html", "structured"] = "structured",
    ) -> None:
        """Background pipeline: layout analysis → asset download → Scaffolder → Template creation.

        Creates its own DB session to avoid sharing the request-scoped session.
        """
        async with get_db_context() as db:
            repo = DesignSyncRepository(db)
            design_service = self._service_factory(db)

            design_import = await repo.get_import_with_assets(import_id)
            if design_import is None:
                logger.error("design_sync.import_not_found", import_id=import_id)
                return

            try:
                await repo.update_import_status(design_import, "converting")

                # 1. Get connection details
                conn = await repo.get_connection(design_import.connection_id)
                if conn is None:
                    logger.error(
                        "design_sync.connection_not_found",
                        import_id=import_id,
                        connection_id=design_import.connection_id,
                    )
                    await repo.update_import_status(
                        design_import,
                        "failed",
                        error_message="Connection not found",
                    )
                    return

                # 1b. Fetch project target clients for compatibility checks
                from app.design_sync.service import fetch_target_clients

                target_clients = await fetch_target_clients(db, conn.project_id)

                # 2. Analyze layout
                layout_response = await design_service.analyze_layout(
                    design_import.connection_id,
                    self._user,
                    selected_node_ids=design_import.selected_node_ids or None,
                )

                # 3. Resolve image assets — prefer already-stored local files,
                #    fall back to downloading from provider API.
                image_node_ids = self._collect_image_node_ids(
                    layout_response,
                    selected_node_ids=design_import.selected_node_ids or None,
                )
                asset_response = None
                if image_node_ids:
                    # 3a. Check for existing local assets first
                    asset_response = self._resolve_local_assets(conn.id, image_node_ids)
                    if asset_response is None:
                        # 3b. Download from provider (best-effort)
                        try:
                            asset_response = await design_service.download_assets(
                                design_import.connection_id,
                                self._user,
                                image_node_ids,
                            )
                        except (SyncFailedError, ConnectionError):
                            logger.warning(
                                "design_sync.assets_skipped",
                                import_id=import_id,
                                exc_info=True,
                            )

                # 4. Get design tokens (best-effort — skip on provider errors)
                tokens = None
                try:
                    tokens = await design_service.get_tokens(
                        design_import.connection_id, self._user
                    )
                except (SyncFailedError, ConnectionError):
                    logger.warning(
                        "design_sync.tokens_skipped",
                        import_id=import_id,
                        exc_info=True,
                    )

                # 5. Build design context
                design_context = self._build_design_context(
                    layout_response, asset_response, tokens, conn
                )

                # 5.5 Design converter pre-processing (provider-agnostic)
                initial_html = ""
                if get_settings().design_sync.converter_enabled:
                    try:
                        from app.design_sync.converter_service import (
                            DesignConverterService,
                        )

                        converter = DesignConverterService()
                        structure = DesignFileStructure(
                            file_name=layout_response.file_name,
                            pages=self._layout_to_design_nodes(layout_response),
                        )
                        extracted_tokens = (
                            self._tokens_to_protocol(tokens) if tokens else ExtractedTokens()
                        )

                        # Validate tokens before converter consumption
                        from app.design_sync.token_transforms import validate_and_transform

                        extracted_tokens, token_warnings = validate_and_transform(
                            extracted_tokens, target_clients=target_clients
                        )
                        if token_warnings:
                            logger.info(
                                "design_sync.import_token_warnings",
                                import_id=import_id,
                                count=len(token_warnings),
                            )

                        # Pass raw_file_data only for Penpot (has richer props)
                        raw_data = (
                            design_import.structure_json if conn.provider == "penpot" else None
                        )
                        conversion = converter.convert(
                            structure,
                            extracted_tokens,
                            raw_file_data=raw_data,
                            selected_nodes=design_import.selected_node_ids or None,
                            target_clients=target_clients,
                        )
                        initial_html = conversion.html
                        if conversion.compatibility_hints:
                            logger.info(
                                "design_sync.conversion_compatibility",
                                hint_count=len(conversion.compatibility_hints),
                                warnings=[
                                    h.message
                                    for h in conversion.compatibility_hints
                                    if h.level == "warning"
                                ],
                            )
                        logger.info(
                            "design_sync.converter_completed",
                            import_id=import_id,
                            provider=conn.provider,
                            sections=conversion.sections_count,
                            warnings_count=len(conversion.warnings),
                        )
                    except Exception:
                        logger.warning(
                            "design_sync.converter_failed",
                            import_id=import_id,
                            exc_info=True,
                        )
                        # Fall back to brief-only path

                # 5.6 Fill image URLs into converter HTML skeleton
                if initial_html and isinstance(design_context.get("image_urls"), dict):
                    initial_html = self._fill_image_urls(
                        initial_html,
                        design_context["image_urls"],  # type: ignore[arg-type]
                    )

                # 6. Call Scaffolder
                scaffolder_response = await self._call_scaffolder(
                    brief=design_import.generated_brief or "",
                    design_context=design_context,
                    run_qa=run_qa,
                    output_mode=output_mode,
                    initial_html=initial_html,
                )

                # 6.5 Post-process: inject design asset URLs into Scaffolder output
                # The Scaffolder (especially in structured mode) may generate
                # placeholder or empty image URLs. Replace them with real asset
                # URLs from the design context.
                image_urls = design_context.get("image_urls")
                if isinstance(image_urls, dict) and image_urls:
                    scaffolder_response = self._inject_asset_urls(
                        scaffolder_response,
                        image_urls,  # pyright: ignore[reportUnknownArgumentType]
                    )

                # 6.6 Fix orphaned footer content outside main wrapper table
                scaffolder_response = self._fix_orphaned_footer(scaffolder_response)

                # 6.7 Sanitize web-only tags and fix text contrast (LAST — catches all prior steps)
                scaffolder_response = self._sanitize_email_html(scaffolder_response)

                # 7. Create Template + TemplateVersion (single transaction)
                raw_name = (
                    design_import.structure_json.get("template_name")
                    if design_import.structure_json
                    else None
                )
                template_name = str(raw_name) if isinstance(raw_name, str) else None
                template_id = await self._create_template(
                    db=db,
                    project_id=design_import.project_id,
                    brief=design_import.generated_brief or "",
                    html=scaffolder_response.html,
                    user_id=design_import.created_by_id,
                    template_name=template_name,
                    provider_name=conn.provider.title(),
                )

                # 8. Mark complete
                await repo.update_import_status(
                    design_import,
                    "completed",
                    result_template_id=template_id,
                    structure_json={
                        **(design_import.structure_json or {}),
                        "scaffolder_model": scaffolder_response.model,
                        "qa_passed": scaffolder_response.qa_passed,
                        "confidence": scaffolder_response.confidence,
                    },
                )

                logger.info(
                    "design_sync.conversion_completed",
                    import_id=import_id,
                    template_id=template_id,
                )

            except Exception:
                logger.exception("design_sync.conversion_failed", import_id=import_id)
                try:
                    design_import = await repo.get_import(import_id)
                    if design_import is not None:
                        await repo.update_import_status(
                            design_import,
                            "failed",
                            error_message="Conversion pipeline failed",
                        )
                except Exception:
                    logger.exception(
                        "design_sync.failure_status_update_failed",
                        import_id=import_id,
                    )

    @staticmethod
    def _resolve_local_assets(
        connection_id: int,
        node_ids: list[str],
    ) -> DownloadAssetsResponse | None:
        """Check if images are already stored locally and return them.

        Avoids calling the provider API when assets were downloaded previously.
        Returns None if no local assets are found for the requested node IDs.
        """
        from app.design_sync.assets import DesignAssetService

        asset_service = DesignAssetService()
        stored_files = asset_service.list_stored_assets(connection_id)
        if not stored_files:
            return None

        # Build a set of stored filenames for fast lookup
        stored_set = set(stored_files)
        matched: list[StoredAssetResponse] = []

        for node_id in node_ids:
            safe_id = node_id.replace(":", "_")
            # Check common formats
            for fmt in ("png", "jpg", "svg"):
                filename = f"{safe_id}.{fmt}"
                if filename in stored_set:
                    matched.append(StoredAssetResponse(node_id=node_id, filename=filename))
                    break

        if not matched:
            return None

        logger.info(
            "design_sync.local_assets_resolved",
            connection_id=connection_id,
            requested=len(node_ids),
            found=len(matched),
        )

        return DownloadAssetsResponse(
            connection_id=connection_id,
            assets=matched,
            total=len(matched),
            skipped=len(node_ids) - len(matched),
        )

    def _collect_image_node_ids(
        self,
        layout: LayoutAnalysisResponse,
        selected_node_ids: list[str] | None = None,
    ) -> list[str]:
        """Extract image node IDs from layout analysis sections.

        When no IMAGE nodes are detected (common at low tree depth), falls back
        to exporting each section frame as an image — Figma's export API can
        render any node as PNG.  Also includes the top-level selected nodes so
        the Scaffolder gets a full visual reference.
        """
        node_ids: list[str] = []
        for section in layout.sections:
            for img in section.images:
                node_ids.append(img.node_id)

        # Fallback: if no IMAGE nodes detected, export section frames themselves
        if not node_ids:
            for section in layout.sections:
                node_ids.append(section.node_id)

        # Also include the top-level selected frames for full-email renders
        if selected_node_ids:
            for nid in selected_node_ids:
                if nid not in node_ids:
                    node_ids.append(nid)

        return node_ids

    def _build_design_context(
        self,
        layout: LayoutAnalysisResponse,
        asset_response: DownloadAssetsResponse | None,
        tokens: DesignTokensResponse | None,
        conn: DesignConnection,
    ) -> dict[str, object]:
        """Build the design context dict for the Scaffolder."""
        image_urls: dict[str, str] = {}
        if asset_response is not None:
            for asset in asset_response.assets:
                image_urls[asset.node_id] = f"/api/v1/design-sync/assets/{conn.id}/{asset.filename}"

        layout_summary = ", ".join(s.section_type for s in layout.sections)

        design_tokens: dict[str, object] | None = None
        if tokens is not None:
            from app.design_sync.converter import convert_spacing
            from app.design_sync.protocol import ExtractedSpacing

            spacing_tokens = [ExtractedSpacing(name=s.name, value=s.value) for s in tokens.spacing]
            design_tokens = {
                "colors": [
                    {"name": c.name, "hex": c.hex, "opacity": c.opacity} for c in tokens.colors
                ],
                "typography": [
                    {
                        "name": t.name,
                        "family": t.family,
                        "weight": t.weight,
                        "size": t.size,
                    }
                    for t in tokens.typography
                ],
                "spacing": convert_spacing(spacing_tokens),
            }

        return {
            "image_urls": image_urls,
            "layout_summary": layout_summary or None,
            "design_tokens": design_tokens,
            "source_file": layout.file_name,
        }

    @staticmethod
    def _fill_image_urls(html_str: str, image_urls: dict[str, str]) -> str:
        """Fill image src attributes in converter HTML using data-node-id → URL mapping.

        The Penpot converter emits ``<img src="" ... data-node-id="X">`` tags.
        This method matches each tag's node ID against the downloaded asset URLs
        and fills in the ``src`` attribute so the Scaffolder receives HTML with
        real image references instead of empty placeholders.
        """
        for node_id, url in image_urls.items():
            escaped_id = re.escape(node_id)
            # Match entire <img> tag containing this data-node-id, then replace src=""
            # Handle both self-closing (/>) and non-self-closing (>) img tags
            pattern = rf'(<img\s[^>]*data-node-id="{escaped_id}"[^>]*/?>)'

            def _replace_src(m: re.Match[str], _url: str = url) -> str:
                return m.group(0).replace('src=""', f'src="{_url}"', 1)

            html_str = re.sub(pattern, _replace_src, html_str)
        return html_str

    @staticmethod
    def _inject_asset_urls(
        response: ScaffolderResponse,
        image_urls: dict[str, str],
    ) -> ScaffolderResponse:
        """Replace placeholder/empty image URLs in Scaffolder output with design assets.

        Strategies (applied in order):
        1. Match ``data-node-id`` attributes to the image_urls mapping.
        2. Replace remaining empty ``src=""`` tags with available asset URLs
           by position (first empty → first unused URL, etc).
        3. Replace common placeholder domains (placehold.co, via.placeholder,
           placeholder.com, dummyimage.com) with asset URLs by position.
        """
        from app.ai.agents.scaffolder.schemas import ScaffolderResponse as _SR

        html = response.html

        # Strategy 1: data-node-id matching (from converter)
        # Handle both self-closing (/>) and non-self-closing (>) img tags
        used_urls: set[str] = set()
        for node_id, url in image_urls.items():
            escaped_id = re.escape(node_id)
            pattern = rf'(<img\s[^>]*data-node-id="{escaped_id}"[^>]*/?>)'

            def _replace_src(m: re.Match[str], _url: str = url) -> str:
                return m.group(0).replace('src=""', f'src="{_url}"', 1)

            new_html = re.sub(pattern, _replace_src, html)
            if new_html != html:
                used_urls.add(url)
            html = new_html

        # Build pool of unused asset URLs for positional assignment
        url_pool = [u for u in image_urls.values() if u not in used_urls]

        # Strategy 2: fill remaining empty src="" attributes
        if url_pool:
            pool_iter = iter(list(url_pool))  # copy so Strategy 3 still has full access

            def _fill_empty(m: re.Match[str]) -> str:
                nonlocal pool_iter
                try:
                    url = next(pool_iter)
                    return m.group(0).replace('src=""', f'src="{url}"', 1)
                except StopIteration:
                    return m.group(0)

            html = re.sub(r'<img\s[^>]*src=""[^>]*/?>', _fill_empty, html)

        # Strategy 3: replace common placeholder URLs — use FULL url list
        # (not just remaining pool) because LLM may have generated new
        # <img> tags with placeholder URLs that weren't in the skeleton
        all_urls = list(image_urls.values())
        if all_urls:
            _PLACEHOLDER_RE = re.compile(
                r'src="https?://(?:'
                r"[\w.-]*placeholder[\w.-]*"
                r"|placehold\.co"
                r"|dummyimage\.com"
                r"|picsum\.photos"
                r"|loremflickr\.com"
                r"|fakeimg\.pl"
                r"|lorempixel\.com"
                r')[^"]*"'
            )
            url_idx = [0]  # mutable counter for closure

            def _fill_placeholder(m: re.Match[str]) -> str:
                if url_idx[0] < len(all_urls):
                    url = all_urls[url_idx[0] % len(all_urls)]
                    url_idx[0] += 1
                    return f'src="{url}"'
                return m.group(0)

            html = _PLACEHOLDER_RE.sub(_fill_placeholder, html)

        return _SR(
            html=html,
            qa_results=response.qa_results,
            qa_passed=response.qa_passed,
            model=response.model,
            confidence=response.confidence,
            skills_loaded=response.skills_loaded,
            mso_warnings=response.mso_warnings,
            plan=response.plan,
        )

    @staticmethod
    def _fix_orphaned_footer(
        response: ScaffolderResponse,
    ) -> ScaffolderResponse:
        """Move content that leaked outside the main wrapper table back inside.

        The Scaffolder sometimes places footer sections (social links,
        unsubscribe) after the closing ``</table>`` of the main email wrapper.
        This causes them to render outside the email container.
        """
        from app.ai.agents.scaffolder.schemas import ScaffolderResponse as _SR

        html = response.html

        # Locate the MSO closing conditional that marks the wrapper boundary.
        # Use regex to tolerate whitespace variations from different generators.
        mso_pattern = re.compile(r"<!--\[if mso\]>\s*</td>\s*</tr>\s*</table>\s*<!\[endif\]-->")
        mso_match = mso_pattern.search(html)
        if mso_match is None:
            return response
        mso_idx = mso_match.start()

        # Find the </table> that directly precedes the MSO close (the wrapper table)
        before_mso = html[:mso_idx].rstrip()
        if before_mso.endswith("</table>"):
            # Structure is correct — no orphaned content
            return response

        wrapper_close_idx = before_mso.rfind("</table>")
        if wrapper_close_idx < 0:
            return response

        orphaned = html[wrapper_close_idx + len("</table>") : mso_idx].strip()
        if not orphaned:
            return response

        # Wrap orphaned content in a table row and insert before the wrapper </table>
        footer_row = f'<tr><td style="padding:0;">\n{orphaned}\n</td></tr>'
        fixed_html = html[:wrapper_close_idx] + "\n" + footer_row + "\n</table>\n" + html[mso_idx:]

        logger.info(
            "design_sync.orphaned_footer_fixed",
            orphaned_length=len(orphaned),
        )

        return _SR(
            html=fixed_html,
            qa_results=response.qa_results,
            qa_passed=response.qa_passed,
            model=response.model,
            confidence=response.confidence,
            skills_loaded=response.skills_loaded,
            mso_warnings=response.mso_warnings,
            plan=response.plan,
        )

    @staticmethod
    def _sanitize_email_html(response: ScaffolderResponse) -> ScaffolderResponse:
        """Post-process: convert web tags to email-safe and fix contrast."""
        from app.ai.agents.scaffolder.schemas import ScaffolderResponse as _SR
        from app.design_sync.converter import sanitize_web_tags_for_email

        html = sanitize_web_tags_for_email(response.html)
        html = DesignImportService._fix_text_contrast(html)

        return _SR(
            html=html,
            qa_results=response.qa_results,
            qa_passed=response.qa_passed,
            model=response.model,
            confidence=response.confidence,
            skills_loaded=response.skills_loaded,
            mso_warnings=response.mso_warnings,
            plan=response.plan,
        )

    @staticmethod
    def _fix_text_contrast(html_str: str) -> str:
        """Fix text with insufficient contrast against dark section backgrounds.

        Scoped per-section: finds each element with a dark bgcolor or
        background-color, then replaces dark text colors only within that
        element's content. Light-background sections are left untouched.
        """
        from app.design_sync.converter import _relative_luminance

        _DARK_TEXT = re.compile(
            r"color:\s*(#000000|#111111|#222222|#333333|#444444|#1a1a1a)",
            re.IGNORECASE,
        )
        # Match opening tags that carry a dark background
        _BG_TAG = re.compile(
            r"<(table|td|tr)(\s[^>]*?)(?:"
            r'bgcolor="(#[0-9a-fA-F]{3,6})"'
            r"|"
            r"background-color:\s*(#[0-9a-fA-F]{3,6})"
            r")([^>]*?)>",
            re.IGNORECASE,
        )

        # Collect byte-ranges of dark-bg sections
        dark_ranges: list[tuple[int, int]] = []
        for m in _BG_TAG.finditer(html_str):
            bg_hex = m.group(3) or m.group(4)
            if not bg_hex or _relative_luminance(bg_hex) >= 0.2:
                continue
            tag_name = m.group(1).lower()
            # Find the matching closing tag from this position
            close_tag = f"</{tag_name}>"
            close_idx = html_str.find(close_tag, m.end())
            if close_idx < 0:
                close_idx = len(html_str)
            dark_ranges.append((m.end(), close_idx))

        if not dark_ranges:
            return html_str

        def _in_dark_range(pos: int) -> bool:
            return any(start <= pos < end for start, end in dark_ranges)

        def _replace_if_dark(m: re.Match[str]) -> str:
            if _in_dark_range(m.start()):
                return "color:#ffffff"
            return m.group(0)

        return _DARK_TEXT.sub(_replace_if_dark, html_str)

    async def _call_scaffolder(
        self,
        brief: str,
        design_context: dict[str, object],
        run_qa: bool,
        output_mode: Literal["html", "structured"],
        initial_html: str = "",
    ) -> ScaffolderResponse:
        """Invoke the Scaffolder agent with the brief and design context."""
        from app.ai.agents.scaffolder.schemas import ScaffolderRequest
        from app.ai.agents.scaffolder.service import get_scaffolder_service

        request = ScaffolderRequest(
            brief=brief,
            run_qa=run_qa,
            output_mode=output_mode,
            design_context=design_context,
            initial_html=initial_html,
        )
        service = get_scaffolder_service()
        return await service.generate(request)

    @staticmethod
    async def _create_template(
        db: object,
        project_id: int,
        brief: str,
        html: str,
        user_id: int,
        template_name: str | None = None,
        provider_name: str = "Figma",
    ) -> int:
        """Create Template + TemplateVersion atomically in a single commit."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.templates.models import Template, TemplateVersion

        session: AsyncSession = db  # type: ignore[assignment]
        name = template_name or DesignImportService._derive_template_name(brief)

        template = Template(
            project_id=project_id,
            name=name,
            description=f"Imported from {provider_name} design",
            status="draft",
            created_by_id=user_id,
        )
        session.add(template)
        await session.flush()  # assign template.id without committing

        version = TemplateVersion(
            template_id=template.id,
            version_number=1,
            html_source=html,
            created_by_id=user_id,
        )
        session.add(version)
        await session.commit()  # single atomic commit

        return template.id

    @staticmethod
    def _derive_template_name(brief: str) -> str:
        """Derive a template name from the first meaningful line of the brief."""
        for line in brief.strip().splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:200]
        return "Imported from Figma"

    @staticmethod
    def _layout_to_design_nodes(layout: LayoutAnalysisResponse) -> list[DesignNode]:
        """Reconstruct DesignNode tree from layout analysis response sections.

        Each AnalyzedSectionResponse becomes a PAGE node containing FRAME children.
        """
        children: list[DesignNode] = []
        for i, section in enumerate(layout.sections):
            child_nodes: list[DesignNode] = []
            for img in section.images:
                img_name = getattr(img, "name", None)
                img_width = getattr(img, "width", None)
                img_height = getattr(img, "height", None)
                child_nodes.append(
                    DesignNode(
                        id=img.node_id,
                        name=img_name if isinstance(img_name, str) else f"image_{img.node_id}",
                        type=DesignNodeType.IMAGE,
                        width=float(img_width) if isinstance(img_width, (int, float)) else None,
                        height=float(img_height) if isinstance(img_height, (int, float)) else None,
                    )
                )
            children.append(
                DesignNode(
                    id=f"section_{i}",
                    name=section.section_type,
                    type=DesignNodeType.FRAME,
                    children=child_nodes,
                    width=600,
                    fill_color=getattr(section, "bg_color", None),
                )
            )
        return [
            DesignNode(
                id="page_0",
                name=layout.file_name,
                type=DesignNodeType.PAGE,
                children=children,
            )
        ]

    @staticmethod
    def _tokens_to_protocol(tokens: DesignTokensResponse) -> ExtractedTokens:
        """Convert response schema back to protocol dataclass."""
        from app.design_sync.protocol import ExtractedColor, ExtractedTypography

        return ExtractedTokens(
            colors=[
                ExtractedColor(name=c.name, hex=c.hex, opacity=c.opacity) for c in tokens.colors
            ],
            typography=[
                ExtractedTypography(
                    name=t.name,
                    family=t.family,
                    weight=t.weight,
                    size=t.size,
                    line_height=t.lineHeight,
                )
                for t in tokens.typography
            ],
        )
