"""Image asset downloading and re-hosting for template uploads."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from lxml import html as lxml_html

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SEMAPHORE = asyncio.Semaphore(8)
_HUB_URL_PATTERN = re.compile(r"/api/v1/")


@dataclass(frozen=True, slots=True)
class ImportedImage:
    """Metadata for a single imported image."""

    original_url: str
    hub_url: str
    display_width: int | None
    display_height: int | None
    intrinsic_width: int
    intrinsic_height: int
    alt: str
    file_size_bytes: int
    mime_type: str


class ImageImporter:
    """Downloads external images from uploaded HTML, stores locally, rewrites URLs."""

    async def import_images(
        self,
        html: str,
        upload_id: int,
    ) -> tuple[str, list[ImportedImage]]:
        """Parse HTML, download external images, return modified HTML + metadata."""
        settings = get_settings().templates
        if not settings.import_images:
            return html, []

        tree = lxml_html.fromstring(html)
        img_elements = tree.xpath("//img[@src]")

        # Collect work items, respecting max_images_per_template
        work: list[tuple[lxml_html.HtmlElement, str]] = []
        for img in img_elements:
            src = img.get("src", "").strip()
            if not src:
                continue
            if self._should_skip(img, src):
                continue
            work.append((img, src))
            if len(work) >= settings.max_images_per_template:
                logger.warning(
                    "template_upload.image_limit_reached",
                    upload_id=upload_id,
                    limit=settings.max_images_per_template,
                )
                break

        if not work:
            return html, []

        # Download concurrently
        storage_dir = self._get_storage_dir(upload_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        imported: list[ImportedImage] = []

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.image_download_timeout, pool=30.0),
            follow_redirects=True,
            max_redirects=3,
        ) as client:
            tasks = [
                self._process_one(client, img, src, upload_id, storage_dir) for img, src in work
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                logger.warning(
                    "template_upload.image_import_error",
                    error=str(result),
                )
                continue
            if result is not None:
                imported.append(result)

        # Serialize modified tree back to string
        if not html.strip().lower().startswith("<!doctype") and "<html" not in html[:200].lower():
            body = tree.find(".//body")
            if body is not None:
                modified_html = (body.text or "") + "".join(
                    lxml_html.tostring(child, encoding="unicode") for child in body
                )
            else:
                modified_html = lxml_html.tostring(tree, encoding="unicode")
        else:
            modified_html = lxml_html.tostring(tree, encoding="unicode")

        logger.info(
            "template_upload.images_imported",
            upload_id=upload_id,
            attempted=len(work),
            imported=len(imported),
        )
        return modified_html, imported

    async def _process_one(
        self,
        client: httpx.AsyncClient,
        img: lxml_html.HtmlElement,
        src: str,
        upload_id: int,
        storage_dir: Path,
    ) -> ImportedImage | None:
        """Download, validate, store one image. Returns None on failure."""
        settings = get_settings().templates
        data = await self._download(client, src, settings.max_image_download_size)
        if data is None:
            return None

        # Validate image content
        mime_type = self._detect_mime(data)
        if mime_type is None:
            logger.warning("template_upload.invalid_image_content", url=src)
            return None

        # Get intrinsic dimensions
        intrinsic_w, intrinsic_h = self._get_dimensions(data, mime_type)

        # Store file
        content_hash = hashlib.sha256(data).hexdigest()[:12]
        ext = self._mime_to_ext(mime_type)
        filename = f"{content_hash}.{ext}"
        file_path = storage_dir / filename
        if not file_path.exists():
            file_path.write_bytes(data)

        # Build hub URL
        hub_url = f"/api/v1/templates/upload/assets/{upload_id}/{filename}"

        # Read display dimensions from HTML attributes
        display_w = self._parse_int_attr(img, "width")
        display_h = self._parse_int_attr(img, "height")

        # Rewrite src in the tree
        img.set("src", hub_url)

        return ImportedImage(
            original_url=src,
            hub_url=hub_url,
            display_width=display_w,
            display_height=display_h,
            intrinsic_width=intrinsic_w,
            intrinsic_height=intrinsic_h,
            alt=img.get("alt", ""),
            file_size_bytes=len(data),
            mime_type=mime_type,
        )

    # -- Helpers --

    def _should_skip(self, img: lxml_html.HtmlElement, src: str) -> bool:
        """Return True if this image should not be downloaded."""
        # Data URIs
        if src.startswith("data:"):
            return True
        # Already hub-hosted
        if _HUB_URL_PATTERN.search(src):
            return True
        # Non-HTTP schemes
        parsed = urlparse(src)
        if parsed.scheme and parsed.scheme not in ("http", "https", ""):
            return True
        # Tracking pixels: both width AND height present and <= 2
        w = self._parse_int_attr(img, "width")
        h = self._parse_int_attr(img, "height")
        return bool(w is not None and h is not None and w <= 2 and h <= 2)

    @staticmethod
    async def _download(client: httpx.AsyncClient, url: str, max_size: int) -> bytes | None:
        """Download with semaphore, size limit, and retry on 429/503."""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with _SEMAPHORE:
                    resp = await client.get(url, headers={"User-Agent": "EmailHub/1.0"})
                if resp.status_code in (429, 503) and attempt < max_retries:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                if resp.status_code != 200:
                    logger.warning(
                        "template_upload.image_download_failed",
                        url=url,
                        status=resp.status_code,
                    )
                    return None
                if len(resp.content) > max_size:
                    logger.warning(
                        "template_upload.image_too_large",
                        url=url,
                        size=len(resp.content),
                        max=max_size,
                    )
                    return None
                return resp.content
            except httpx.HTTPError as exc:
                if attempt < max_retries:
                    continue
                logger.warning(
                    "template_upload.image_download_error",
                    url=url,
                    error=str(exc),
                )
                return None
        return None

    @staticmethod
    def _detect_mime(data: bytes) -> str | None:
        """Validate image via magic bytes. Returns mime type or None."""
        if data[:4] == b"\x89PNG":
            return "image/png"
        if data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if b"<svg" in data[:500] and b"xmlns" in data[:1000]:
            # Require xmlns to distinguish real SVGs from arbitrary XML fragments.
            # Served with CSP default-src 'none' as additional mitigation.
            return "image/svg+xml"
        return None

    @staticmethod
    def _get_dimensions(data: bytes, mime_type: str) -> tuple[int, int]:
        """Extract intrinsic dimensions. Returns (0, 0) on failure."""
        if mime_type == "image/svg+xml":
            try:
                import re as _re

                text = data.decode("utf-8", errors="ignore")
                vb = _re.search(r'viewBox=["\'](\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text)
                if vb:
                    return int(vb.group(3)), int(vb.group(4))
                w_match = _re.search(r'width=["\'](\d+)', text)
                h_match = _re.search(r'height=["\'](\d+)', text)
                if w_match and h_match:
                    return int(w_match.group(1)), int(h_match.group(1))
            except Exception:
                logger.debug("template_upload.svg_dimension_parse_failed", mime=mime_type)
            return 0, 0
        try:
            from app.shared.imaging import safe_image_open

            img = safe_image_open(BytesIO(data))
            return img.size
        except Exception:
            return 0, 0

    @staticmethod
    def _mime_to_ext(mime_type: str) -> str:
        return {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/svg+xml": "svg",
        }.get(mime_type, "bin")

    @staticmethod
    def _parse_int_attr(elem: lxml_html.HtmlElement, attr: str) -> int | None:
        val = elem.get(attr, "")
        try:
            return int(val.replace("px", "").strip()) if val else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _get_storage_dir(upload_id: int) -> Path:
        settings = get_settings().templates
        return Path(settings.image_storage_path) / str(upload_id)
