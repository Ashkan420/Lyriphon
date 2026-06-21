import pytest
from utils.url_validation import is_valid_url, _is_valid_image_url, _safe_link


class TestIsValidUrl:
    def test_valid_http(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https(self):
        assert is_valid_url("https://example.com/path") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_ftp_scheme(self):
        assert is_valid_url("ftp://example.com") is False

    def test_invalid_empty_string(self):
        assert is_valid_url("") is False

    def test_invalid_just_scheme(self):
        assert is_valid_url("https://") is False

    def test_valid_with_port(self):
        assert is_valid_url("http://example.com:8080/api") is True

    def test_blocks_private_host(self):
        assert is_valid_url("http://localhost:8080/api") is False

    def test_blocks_private_ip_literals(self):
        assert is_valid_url("http://127.0.0.1/admin") is False
        assert is_valid_url("http://10.0.0.5") is False
        assert is_valid_url("http://192.168.1.1") is False
        assert is_valid_url("http://169.254.169.254/latest/meta-data") is False

    def test_allows_public_ip_literal(self):
        assert is_valid_url("http://8.8.8.8") is True

    def test_valid_with_query(self):
        assert is_valid_url("https://example.com/path?q=1&b=2") is True

    def test_invalid_none(self):
        assert is_valid_url(None) is False


class TestIsValidImageUrl:
    def test_valid_jpg(self):
        assert _is_valid_image_url("https://example.com/img.jpg") is True

    def test_valid_jpeg(self):
        assert _is_valid_image_url("https://example.com/img.jpeg") is True

    def test_valid_png(self):
        assert _is_valid_image_url("http://cdn.test.com/photo.png") is True

    def test_valid_webp(self):
        assert _is_valid_image_url("https://cdn.test.com/photo.webp") is True

    def test_case_insensitive(self):
        assert _is_valid_image_url("https://example.com/img.JPG") is True
        assert _is_valid_image_url("https://example.com/img.PNG") is True

    def test_invalid_gif(self):
        assert _is_valid_image_url("https://example.com/img.gif") is False

    def test_invalid_no_extension(self):
        assert _is_valid_image_url("https://example.com/img") is False

    def test_invalid_empty_string(self):
        assert _is_valid_image_url("") is False

    def test_invalid_none(self):
        assert _is_valid_image_url(None) is False

    def test_invalid_no_scheme(self):
        assert _is_valid_image_url("example.com/img.jpg") is False

    def test_valid_with_path_segments(self):
        assert _is_valid_image_url("https://cdn.deezer.com/images/cover/abc123/500x500.jpg") is True


class TestSafeLink:
    def test_with_url(self):
        result = _safe_link("Click me", "https://example.com")
        assert result == '<a href="https://example.com">Click me</a>'

    def test_without_url_empty_string(self):
        result = _safe_link("Just text", "")
        assert result == "Just text"

    def test_without_url_none(self):
        result = _safe_link("Just text", None)
        assert result == "Just text"

    def test_escapes_text(self):
        result = _safe_link("Hello & World", "https://x.com")
        assert "Hello &amp; World" in result
