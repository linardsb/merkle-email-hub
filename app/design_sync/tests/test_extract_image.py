"""Tests for Figma design screenshot capture in the diagnostic extract script."""

from __future__ import annotations

import io
import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.design_sync.diagnose.extract import (
    _build_parser,
    _capture_design_image,
    _read_png_dimensions,
)


def _make_png(width: int = 200, height: int = 400) -> bytes:
    """Create a minimal valid PNG with the given dimensions in the IHDR chunk."""
    from PIL import Image

    img = Image.new("RGB", (width, height), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── _read_png_dimensions ──


class TestReadPngDimensions:
    def test_valid_png(self) -> None:
        png = _make_png(600, 2518)
        w, h = _read_png_dimensions(png)
        assert w == 600
        assert h == 2518

    def test_small_png(self) -> None:
        png = _make_png(1, 1)
        w, h = _read_png_dimensions(png)
        assert w == 1
        assert h == 1

    def test_invalid_data(self) -> None:
        w, h = _read_png_dimensions(b"not a png at all")
        assert w is None
        assert h is None

    def test_too_short(self) -> None:
        w, h = _read_png_dimensions(b"\x89PNG\r\n\x1a\n")
        assert w is None
        assert h is None

    def test_raw_header(self) -> None:
        """Manually crafted PNG header with known dimensions."""
        header = b"\x89PNG\r\n\x1a\n"
        # IHDR chunk: length (13) + "IHDR" + width + height + ...
        ihdr_data = struct.pack(">II", 1200, 5036)
        # Need 8 bytes before the width/height at offset 16
        chunk = b"\x00\x00\x00\x0dIHDR" + ihdr_data + b"\x00\x00\x00\x00\x00"
        data = header + chunk
        w, h = _read_png_dimensions(data)
        assert w == 1200
        assert h == 5036


# ── _capture_design_image ──

_SERVICE_CLASS = "app.design_sync.figma.service.FigmaDesignSyncService"


def _mock_service(
    *,
    exported: list[MagicMock] | None = None,
    export_side_effect: Exception | None = None,
    image_bytes: bytes = b"",
    download_side_effect: Exception | None = None,
) -> MagicMock:
    """Build a mock FigmaDesignSyncService instance."""
    svc = MagicMock()
    if export_side_effect:
        svc.export_images = AsyncMock(side_effect=export_side_effect)
    else:
        svc.export_images = AsyncMock(return_value=exported or [])
    if download_side_effect:
        svc.download_image_bytes = AsyncMock(side_effect=download_side_effect)
    else:
        svc.download_image_bytes = AsyncMock(return_value=image_bytes)
    return svc


class TestCaptureDesignImage:
    @pytest.mark.asyncio
    async def test_happy_path(self, tmp_path: Path) -> None:
        png_bytes = _make_png(1200, 5036)
        mock_exported = MagicMock()
        svc = _mock_service(exported=[mock_exported], image_bytes=png_bytes)

        with (
            patch(_SERVICE_CLASS, return_value=svc),
            patch("app.design_sync.diagnose.extract._get_scale", return_value=2.0),
        ):
            path, w, h = await _capture_design_image(
                "VUlWjZGAEVZr3mK1EawsYR", "fake-token", "2833-1623", tmp_path
            )

        assert path is not None
        assert path == tmp_path / "design.png"
        assert path.exists()
        assert path.read_bytes() == png_bytes
        assert w == 1200
        assert h == 5036

    @pytest.mark.asyncio
    async def test_api_error_graceful(self, tmp_path: Path) -> None:
        svc = _mock_service(export_side_effect=RuntimeError("Figma API error"))

        with (
            patch(_SERVICE_CLASS, return_value=svc),
            patch("app.design_sync.diagnose.extract._get_scale", return_value=2.0),
        ):
            path, w, h = await _capture_design_image(
                "VUlWjZGAEVZr3mK1EawsYR", "fake-token", "2833-1623", tmp_path
            )

        assert path is None
        assert w is None
        assert h is None
        assert not (tmp_path / "design.png").exists()

    @pytest.mark.asyncio
    async def test_empty_response(self, tmp_path: Path) -> None:
        svc = _mock_service(exported=[])

        with (
            patch(_SERVICE_CLASS, return_value=svc),
            patch("app.design_sync.diagnose.extract._get_scale", return_value=2.0),
        ):
            path, w, h = await _capture_design_image(
                "VUlWjZGAEVZr3mK1EawsYR", "fake-token", "2833-1623", tmp_path
            )

        assert path is None
        assert w is None
        assert h is None

    @pytest.mark.asyncio
    async def test_download_error_graceful(self, tmp_path: Path) -> None:
        mock_exported = MagicMock()
        svc = _mock_service(
            exported=[mock_exported],
            download_side_effect=TimeoutError("CDN timeout"),
        )

        with (
            patch(_SERVICE_CLASS, return_value=svc),
            patch("app.design_sync.diagnose.extract._get_scale", return_value=2.0),
        ):
            path, w, h = await _capture_design_image(
                "VUlWjZGAEVZr3mK1EawsYR", "fake-token", "2833-1623", tmp_path
            )

        assert path is None
        assert w is None
        assert h is None

    @pytest.mark.asyncio
    async def test_node_id_converted_to_colon_format(self, tmp_path: Path) -> None:
        """Dash-format node ID (2833-1623) must be converted to colon (2833:1623)."""
        png_bytes = _make_png(100, 100)
        mock_exported = MagicMock()
        svc = _mock_service(exported=[mock_exported], image_bytes=png_bytes)

        with (
            patch(_SERVICE_CLASS, return_value=svc),
            patch("app.design_sync.diagnose.extract._get_scale", return_value=2.0),
        ):
            await _capture_design_image(
                "VUlWjZGAEVZr3mK1EawsYR", "fake-token", "2833-1623", tmp_path
            )

        # Verify the colon-format node ID was passed to export_images
        call_args = svc.export_images.call_args
        assert call_args is not None
        node_ids_arg = call_args[0][2]  # 3rd positional arg
        assert node_ids_arg == ["2833:1623"]


# ── CLI flag ──


class TestCliNoImageFlag:
    def test_no_image_flag_present(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--connection-id", "5", "--no-image"])
        assert args.no_image is True

    def test_no_image_flag_absent(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--connection-id", "5"])
        assert args.no_image is False

    def test_no_image_with_node_id(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "--connection-id",
                "5",
                "--node-id",
                "2833-1623",
                "--no-image",
            ]
        )
        assert args.no_image is True
        assert args.node_id == "2833-1623"
