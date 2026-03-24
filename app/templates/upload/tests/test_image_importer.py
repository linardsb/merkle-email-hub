"""Unit tests for ImageImporter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from app.templates.upload.image_importer import ImageImporter

# Valid 1x1 red PNG
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _mock_transport(responses: dict[str, httpx.Response]) -> httpx.MockTransport:
    """Create a mock transport returning configured responses per URL."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for pattern, resp in responses.items():
            if pattern in url:
                return resp
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def importer() -> ImageImporter:
    return ImageImporter()


class TestImportImages:
    @pytest.mark.asyncio
    async def test_import_replaces_external_urls(
        self, importer: ImageImporter, tmp_path: Path
    ) -> None:
        html = """<html><body>
        <table><tr><td>
            <img src="https://cdn.example.com/hero.png" width="600" height="400" alt="Hero">
            <img src="https://cdn.example.com/logo.png" width="200" alt="Logo">
        </td></tr></table>
        </body></html>"""

        transport = _mock_transport(
            {
                "hero.png": httpx.Response(200, content=TINY_PNG),
                "logo.png": httpx.Response(200, content=TINY_PNG),
            }
        )

        with (
            patch("app.templates.upload.image_importer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.__aenter__") as mock_client_enter,
        ):
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_image_download_size = 5 * 1024 * 1024
            settings.max_images_per_template = 50
            settings.image_download_timeout = 5.0
            settings.image_storage_path = str(tmp_path)

            client = httpx.AsyncClient(transport=transport)
            mock_client_enter.return_value = client

            result_html, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 2
        assert "/api/v1/templates/upload/assets/1/" in result_html
        for img in images:
            assert img.hub_url.startswith("/api/v1/templates/upload/assets/1/")
            assert img.original_url.startswith("https://cdn.example.com/")
            assert img.intrinsic_width == 1
            assert img.intrinsic_height == 1
            assert img.mime_type == "image/png"

    @pytest.mark.asyncio
    async def test_skip_data_uri(self, importer: ImageImporter, tmp_path: Path) -> None:
        html = '<html><body><img src="data:image/png;base64,iVBOR"></body></html>'

        with patch("app.templates.upload.image_importer.get_settings") as mock_settings:
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_images_per_template = 50
            settings.image_storage_path = str(tmp_path)

            result_html, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 0
        assert "data:image/png;base64" in result_html

    @pytest.mark.asyncio
    async def test_skip_tracking_pixel(self, importer: ImageImporter, tmp_path: Path) -> None:
        html = '<html><body><img src="https://track.example.com/px.gif" width="1" height="1"></body></html>'

        with patch("app.templates.upload.image_importer.get_settings") as mock_settings:
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_images_per_template = 50
            settings.image_storage_path = str(tmp_path)

            _, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 0

    @pytest.mark.asyncio
    async def test_skip_hub_url(self, importer: ImageImporter, tmp_path: Path) -> None:
        html = '<html><body><img src="/api/v1/design-sync/assets/1/abc.png"></body></html>'

        with patch("app.templates.upload.image_importer.get_settings") as mock_settings:
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_images_per_template = 50
            settings.image_storage_path = str(tmp_path)

            _, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 0

    @pytest.mark.asyncio
    async def test_download_failure_keeps_original(
        self, importer: ImageImporter, tmp_path: Path
    ) -> None:
        html = '<html><body><img src="https://broken.example.com/img.png"></body></html>'

        transport = _mock_transport(
            {
                "img.png": httpx.Response(500),
            }
        )

        with (
            patch("app.templates.upload.image_importer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.__aenter__") as mock_client_enter,
        ):
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_image_download_size = 5 * 1024 * 1024
            settings.max_images_per_template = 50
            settings.image_download_timeout = 5.0
            settings.image_storage_path = str(tmp_path)

            client = httpx.AsyncClient(transport=transport)
            mock_client_enter.return_value = client

            result_html, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 0
        assert "broken.example.com/img.png" in result_html

    @pytest.mark.asyncio
    async def test_max_images_limit(self, importer: ImageImporter, tmp_path: Path) -> None:
        imgs = "".join(f'<img src="https://cdn.example.com/img{i}.png">' for i in range(60))
        html = f"<html><body>{imgs}</body></html>"

        transport = _mock_transport(
            {
                "cdn.example.com": httpx.Response(200, content=TINY_PNG),
            }
        )

        with (
            patch("app.templates.upload.image_importer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.__aenter__") as mock_client_enter,
        ):
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_image_download_size = 5 * 1024 * 1024
            settings.max_images_per_template = 50
            settings.image_download_timeout = 5.0
            settings.image_storage_path = str(tmp_path)

            client = httpx.AsyncClient(transport=transport)
            mock_client_enter.return_value = client

            _, images = await importer.import_images(html, upload_id=1)

        # All deduplicate to same hash, so only 1 unique image stored,
        # but 50 ImportedImage entries (one per processed img tag)
        assert len(images) == 50

    @pytest.mark.asyncio
    async def test_invalid_image_content_rejected(
        self, importer: ImageImporter, tmp_path: Path
    ) -> None:
        html = '<html><body><img src="https://cdn.example.com/fake.png"></body></html>'

        transport = _mock_transport(
            {
                "fake.png": httpx.Response(200, content=b"<html>not an image</html>"),
            }
        )

        with (
            patch("app.templates.upload.image_importer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.__aenter__") as mock_client_enter,
        ):
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_image_download_size = 5 * 1024 * 1024
            settings.max_images_per_template = 50
            settings.image_download_timeout = 5.0
            settings.image_storage_path = str(tmp_path)

            client = httpx.AsyncClient(transport=transport)
            mock_client_enter.return_value = client

            _, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 0

    @pytest.mark.asyncio
    async def test_dimensions_extracted(self, importer: ImageImporter, tmp_path: Path) -> None:
        html = '<html><body><img src="https://cdn.example.com/photo.png"></body></html>'

        transport = _mock_transport(
            {
                "photo.png": httpx.Response(200, content=TINY_PNG),
            }
        )

        with (
            patch("app.templates.upload.image_importer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.__aenter__") as mock_client_enter,
        ):
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_image_download_size = 5 * 1024 * 1024
            settings.max_images_per_template = 50
            settings.image_download_timeout = 5.0
            settings.image_storage_path = str(tmp_path)

            client = httpx.AsyncClient(transport=transport)
            mock_client_enter.return_value = client

            _, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 1
        assert images[0].intrinsic_width == 1
        assert images[0].intrinsic_height == 1

    @pytest.mark.asyncio
    async def test_display_dimensions_from_attrs(
        self, importer: ImageImporter, tmp_path: Path
    ) -> None:
        html = '<html><body><img src="https://cdn.example.com/hero.png" width="300" height="200"></body></html>'

        transport = _mock_transport(
            {
                "hero.png": httpx.Response(200, content=TINY_PNG),
            }
        )

        with (
            patch("app.templates.upload.image_importer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.__aenter__") as mock_client_enter,
        ):
            settings = mock_settings.return_value.templates
            settings.import_images = True
            settings.max_image_download_size = 5 * 1024 * 1024
            settings.max_images_per_template = 50
            settings.image_download_timeout = 5.0
            settings.image_storage_path = str(tmp_path)

            client = httpx.AsyncClient(transport=transport)
            mock_client_enter.return_value = client

            _, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 1
        assert images[0].display_width == 300
        assert images[0].display_height == 200

    @pytest.mark.asyncio
    async def test_disabled_by_config(self, importer: ImageImporter) -> None:
        html = '<html><body><img src="https://cdn.example.com/x.png"></body></html>'

        with patch("app.templates.upload.image_importer.get_settings") as mock_settings:
            mock_settings.return_value.templates.import_images = False

            result_html, images = await importer.import_images(html, upload_id=1)

        assert len(images) == 0
        assert result_html == html
