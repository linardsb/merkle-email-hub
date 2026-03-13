# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
"""Unit tests for image_analyzer module."""

import base64

from app.qa_engine.image_analyzer import (
    ImageFormat,
    _calc_data_uri_bytes,
    _detect_format,
    _is_tracking_pixel,
    analyze_images,
    clear_image_cache,
    get_cached_result,
)

# ── Format Detection ──


class TestImageFormatDetection:
    def test_jpeg_from_url_extension(self):
        assert _detect_format("https://cdn.example.com/hero.jpg") == ImageFormat.JPEG
        assert _detect_format("https://cdn.example.com/hero.jpeg") == ImageFormat.JPEG

    def test_png_from_url_extension(self):
        assert _detect_format("https://cdn.example.com/logo.png") == ImageFormat.PNG

    def test_gif_from_url_extension(self):
        assert _detect_format("https://cdn.example.com/banner.gif") == ImageFormat.GIF

    def test_webp_from_url_extension(self):
        assert _detect_format("https://cdn.example.com/hero.webp") == ImageFormat.WEBP

    def test_bmp_from_url_detected(self):
        assert _detect_format("https://cdn.example.com/old.bmp") == ImageFormat.BMP

    def test_tiff_from_url_detected(self):
        assert _detect_format("https://cdn.example.com/photo.tiff") == ImageFormat.TIFF
        assert _detect_format("https://cdn.example.com/photo.tif") == ImageFormat.TIFF

    def test_format_from_data_uri_mime(self):
        assert _detect_format("data:image/png;base64,abc") == ImageFormat.PNG
        assert _detect_format("data:image/jpeg;base64,abc") == ImageFormat.JPEG
        assert _detect_format("data:image/gif;base64,abc") == ImageFormat.GIF

    def test_unknown_format_no_extension(self):
        assert _detect_format("https://cdn.example.com/image") == ImageFormat.UNKNOWN
        assert _detect_format("") == ImageFormat.UNKNOWN

    def test_extension_with_query_params(self):
        assert _detect_format("https://cdn.example.com/hero.png?v=2&w=600") == ImageFormat.PNG


# ── Tracking Pixel Detection ──


class TestTrackingPixelDetection:
    def test_1x1_is_tracking_pixel(self):
        assert _is_tracking_pixel("1", "1", "https://example.com/img.png") is True

    def test_0x0_is_tracking_pixel(self):
        assert _is_tracking_pixel("0", "0", "https://example.com/img.png") is True

    def test_normal_dimensions_not_tracking(self):
        assert _is_tracking_pixel("600", "300", "https://example.com/hero.png") is False

    def test_tracking_src_pattern_detected(self):
        assert _is_tracking_pixel("10", "10", "https://track.example.com/open") is True
        assert _is_tracking_pixel(None, None, "https://cdn.example.com/pixel.gif") is True
        assert _is_tracking_pixel(None, None, "https://cdn.example.com/beacon") is True

    def test_1x1_with_px_suffix(self):
        assert _is_tracking_pixel("1px", "1px", "https://example.com/img.png") is True

    def test_none_dimensions_no_tracking_src(self):
        assert _is_tracking_pixel(None, None, "https://cdn.example.com/hero.png") is False


# ── Data URI Byte Calculation ──


class TestDataUriBytes:
    def test_base64_data_uri(self):
        payload = base64.b64encode(b"hello world").decode()
        src = f"data:image/png;base64,{payload}"
        result = _calc_data_uri_bytes(src)
        assert result == 11  # len("hello world")

    def test_non_base64_data_uri(self):
        src = "data:image/svg+xml,<svg></svg>"
        result = _calc_data_uri_bytes(src)
        assert result == len(b"<svg></svg>")

    def test_not_data_uri(self):
        assert _calc_data_uri_bytes("https://example.com/img.png") == 0

    def test_no_comma(self):
        assert _calc_data_uri_bytes("data:image/png") == 0


# ── Image Parsing ──


class TestImageParsing:
    def test_basic_image_attributes(self):
        html = '<html><body><img src="https://example.com/hero.png" alt="Hero" width="600" height="300"></body></html>'
        result = analyze_images(html)
        assert result.total_count == 1
        img = result.images[0]
        assert img.src == "https://example.com/hero.png"
        assert img.alt == "Hero"
        assert img.width == "600"
        assert img.height == "300"
        assert img.format == ImageFormat.PNG

    def test_missing_alt_is_none(self):
        html = '<html><body><img src="https://example.com/img.png" width="100" height="100"></body></html>'
        result = analyze_images(html)
        assert result.images[0].alt is None

    def test_empty_alt_is_empty_string(self):
        html = '<html><body><img src="https://example.com/img.png" alt="" width="100" height="100"></body></html>'
        result = analyze_images(html)
        assert result.images[0].alt == ""

    def test_image_inside_link_detected(self):
        html = '<html><body><a href="https://example.com"><img src="https://example.com/cta.png" alt="CTA" width="200" height="50"></a></body></html>'
        result = analyze_images(html)
        assert result.images[0].is_inside_link is True

    def test_image_not_inside_link(self):
        html = '<html><body><img src="https://example.com/hero.png" alt="Hero" width="600" height="300"></body></html>'
        result = analyze_images(html)
        assert result.images[0].is_inside_link is False

    def test_border_zero_detected(self):
        html = '<html><body><img src="https://example.com/img.png" alt="test" width="100" height="100" border="0"></body></html>'
        result = analyze_images(html)
        assert result.images[0].has_border_zero is True

    def test_display_block_detected(self):
        html = '<html><body><img src="https://example.com/img.png" alt="test" width="100" height="100" style="display:block;"></body></html>'
        result = analyze_images(html)
        assert result.images[0].has_display_block is True

    def test_display_block_not_present(self):
        html = '<html><body><img src="https://example.com/img.png" alt="test" width="100" height="100"></body></html>'
        result = analyze_images(html)
        assert result.images[0].has_display_block is False

    def test_data_uri_size_calculated(self):
        payload = base64.b64encode(b"x" * 5000).decode()
        html = f'<html><body><img src="data:image/png;base64,{payload}" alt="test" width="100" height="100"></body></html>'
        result = analyze_images(html)
        img = result.images[0]
        assert img.is_data_uri is True
        assert img.data_uri_bytes == 5000

    def test_aria_hidden_detected(self):
        html = '<html><body><img src="https://example.com/pixel.gif" width="1" height="1" alt="" aria-hidden="true"></body></html>'
        result = analyze_images(html)
        assert result.images[0].has_aria_hidden is True


# ── Full Analysis ──


class TestImageAnalysis:
    def test_no_images_empty_result(self):
        html = "<html><body><p>No images</p></body></html>"
        result = analyze_images(html)
        assert result.total_count == 0
        assert result.images == ()

    def test_single_valid_image(self):
        html = '<html><body><img src="https://example.com/hero.png" alt="Hero" width="600" height="300"></body></html>'
        result = analyze_images(html)
        assert result.total_count == 1
        assert result.images_with_alt == 1
        assert result.images_missing_alt == 0
        assert result.images_missing_dimensions == 0

    def test_multiple_images_aggregation(self):
        html = """<html><body>
        <img src="https://example.com/a.png" alt="A" width="100" height="100">
        <img src="https://example.com/b.jpg" alt="B" width="200" height="200">
        <img src="https://example.com/c.gif" width="50" height="50">
        </body></html>"""
        result = analyze_images(html)
        assert result.total_count == 3
        assert result.images_with_alt == 2
        assert result.images_missing_alt == 1

    def test_format_distribution(self):
        html = """<html><body>
        <img src="https://example.com/a.png" alt="" width="100" height="100">
        <img src="https://example.com/b.png" alt="" width="100" height="100">
        <img src="https://example.com/c.jpg" alt="" width="100" height="100">
        </body></html>"""
        result = analyze_images(html)
        assert result.format_distribution == {"png": 2, "jpeg": 1}

    def test_tracking_pixel_count(self):
        html = """<html><body>
        <img src="https://example.com/hero.png" alt="Hero" width="600" height="300">
        <img src="https://track.example.com/open" width="1" height="1" alt="">
        </body></html>"""
        result = analyze_images(html)
        assert result.tracking_pixel_count == 1

    def test_missing_alt_count_excludes_tracking(self):
        html = """<html><body>
        <img src="https://example.com/hero.png" width="600" height="300">
        <img src="https://track.example.com/pixel" width="1" height="1">
        </body></html>"""
        result = analyze_images(html)
        # hero is missing alt (not tracking) → counted
        # pixel is tracking → NOT counted in missing_alt
        assert result.images_missing_alt == 1

    def test_missing_dimensions_count(self):
        html = """<html><body>
        <img src="https://example.com/a.png" alt="A">
        <img src="https://example.com/b.png" alt="B" width="100">
        <img src="https://example.com/c.png" alt="C" width="100" height="100">
        </body></html>"""
        result = analyze_images(html)
        assert result.images_missing_dimensions == 2


# ── Caching ──


class TestCaching:
    def test_same_html_returns_cached(self):
        clear_image_cache()
        html = '<html><body><img src="https://example.com/hero.png" alt="Hero" width="600" height="300"></body></html>'
        r1 = get_cached_result(html)
        r2 = get_cached_result(html)
        assert r1 is r2

    def test_clear_cache_invalidates(self):
        html = '<html><body><img src="https://example.com/hero.png" alt="Hero" width="600" height="300"></body></html>'
        r1 = get_cached_result(html)
        clear_image_cache()
        r2 = get_cached_result(html)
        assert r1 is not r2
        assert r1.total_count == r2.total_count
