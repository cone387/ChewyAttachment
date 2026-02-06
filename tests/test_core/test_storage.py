"""Tests for core storage engines"""

import pytest
from pathlib import Path

from chewy_attachment.core.storage import FileStorageEngine
from chewy_attachment.core.exceptions import StorageException


@pytest.fixture
def storage_engine(storage_root):
    """Create a FileStorageEngine instance"""
    return FileStorageEngine(storage_root)


class TestFileStorageEngine:
    """Tests for FileStorageEngine"""

    def test_save_file_creates_file(self, storage_engine, sample_file_content):
        """Test that save_file creates a file and returns correct metadata"""
        result = storage_engine.save_file(sample_file_content, "test.txt")

        assert result.storage_path is not None
        assert result.size == len(sample_file_content)
        assert result.mime_type == "text/plain"

    def test_save_file_with_custom_path(self, storage_engine, sample_file_content):
        """Test saving file with custom storage path"""
        custom_path = "custom/path/file.txt"
        result = storage_engine.save_file(
            sample_file_content, "test.txt", storage_path=custom_path
        )

        assert result.storage_path == custom_path

    def test_get_file_returns_content(self, storage_engine, sample_file_content):
        """Test that get_file returns the correct content"""
        result = storage_engine.save_file(sample_file_content, "test.txt")
        retrieved = storage_engine.get_file(result.storage_path)

        assert retrieved == sample_file_content

    def test_get_file_not_found_raises_exception(self, storage_engine):
        """Test that get_file raises exception for non-existent file"""
        with pytest.raises(StorageException):
            storage_engine.get_file("nonexistent/path.txt")

    def test_file_exists_returns_true_for_existing_file(
        self, storage_engine, sample_file_content
    ):
        """Test file_exists returns True for existing file"""
        result = storage_engine.save_file(sample_file_content, "test.txt")

        assert storage_engine.file_exists(result.storage_path) is True

    def test_file_exists_returns_false_for_nonexistent_file(self, storage_engine):
        """Test file_exists returns False for non-existent file"""
        assert storage_engine.file_exists("nonexistent/path.txt") is False

    def test_delete_file_removes_file(self, storage_engine, sample_file_content):
        """Test that delete_file removes the file"""
        result = storage_engine.save_file(sample_file_content, "test.txt")
        storage_engine.delete_file(result.storage_path)

        assert storage_engine.file_exists(result.storage_path) is False

    def test_delete_nonexistent_file_does_not_raise(self, storage_engine):
        """Test that deleting non-existent file does not raise exception (idempotent)"""
        # FileStorageEngine.delete_file is idempotent - it doesn't raise if file doesn't exist
        storage_engine.delete_file("nonexistent/path.txt")
        # Should complete without error

    def test_get_file_path_returns_absolute_path(
        self, storage_engine, sample_file_content
    ):
        """Test that get_file_path returns absolute path"""
        result = storage_engine.save_file(sample_file_content, "test.txt")
        file_path = storage_engine.get_file_path(result.storage_path)

        assert isinstance(file_path, Path)
        assert file_path.is_absolute()
        assert file_path.exists()

    def test_mime_type_detection(self, storage_engine, sample_image_content):
        """Test MIME type detection for different file types"""
        result = storage_engine.save_file(sample_image_content, "image.png")

        # Should detect as image/png based on content or extension
        assert "image" in result.mime_type or "png" in result.mime_type
