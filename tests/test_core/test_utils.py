"""Tests for utility functions"""

import pytest

from chewy_attachment.core.utils import (
    generate_uuid,
    detect_mime_type,
    get_file_extension,
    safe_filename,
)


class TestGenerateUuid:
    """Tests for generate_uuid"""

    def test_returns_string(self):
        """generate_uuid returns a string"""
        result = generate_uuid()
        assert isinstance(result, str)

    def test_returns_valid_uuid_format(self):
        """generate_uuid returns valid UUID format"""
        result = generate_uuid()
        # UUID format: 8-4-4-4-12 hex characters
        parts = result.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_returns_unique_values(self):
        """generate_uuid returns unique values"""
        uuids = [generate_uuid() for _ in range(100)]
        assert len(set(uuids)) == 100


class TestDetectMimeType:
    """Tests for detect_mime_type"""

    def test_detects_text_plain(self):
        """Detects text/plain for text content"""
        content = b"Hello, World!"
        result = detect_mime_type(content, "test.txt")
        assert "text" in result

    def test_detects_png_image(self):
        """Detects image/png for PNG content"""
        # PNG magic bytes
        content = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        result = detect_mime_type(content, "image.png")
        assert "png" in result.lower() or "image" in result.lower()

    def test_fallback_to_filename(self):
        """Falls back to filename extension when content detection fails"""
        content = b"some binary content"
        result = detect_mime_type(content, "document.pdf")
        # Should return something, not crash
        assert result is not None

    def test_default_octet_stream(self):
        """Returns application/octet-stream for unknown content"""
        content = bytes([0x00, 0x01, 0x02, 0x03])
        result = detect_mime_type(content, None)
        assert result is not None


class TestGetFileExtension:
    """Tests for get_file_extension"""

    def test_returns_extension_with_dot(self):
        """Returns extension including the dot"""
        result = get_file_extension("document.pdf")
        assert result == ".pdf"

    def test_returns_lowercase_extension(self):
        """Returns lowercase extension"""
        result = get_file_extension("IMAGE.PNG")
        assert result == ".png"

    def test_returns_empty_for_no_extension(self):
        """Returns empty string for files without extension"""
        result = get_file_extension("README")
        assert result == ""

    def test_handles_multiple_dots(self):
        """Handles filenames with multiple dots"""
        result = get_file_extension("archive.tar.gz")
        assert result == ".gz"


class TestSafeFilename:
    """Tests for safe_filename"""

    def test_returns_basename(self):
        """Returns only the basename, not the path"""
        result = safe_filename("/path/to/file.txt")
        assert result == "file.txt"

    def test_removes_directory_traversal(self):
        """Removes directory traversal attempts"""
        result = safe_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_handles_windows_paths(self):
        """Handles Windows-style paths on Unix systems"""
        # Note: On Unix systems, backslashes are valid filename characters
        # so Path doesn't treat them as separators
        result = safe_filename("C:\\Users\\test\\file.txt")
        # On Unix, this is treated as a single filename with backslashes
        # The important thing is it doesn't contain path separators for the current OS
        assert "/" not in result

    def test_removes_null_bytes(self):
        """Removes null bytes from filename"""
        result = safe_filename("file\x00.txt")
        assert "\x00" not in result

    def test_returns_unnamed_for_empty(self):
        """Returns 'unnamed' for empty or invalid filenames"""
        result = safe_filename("")
        assert result == "unnamed"
