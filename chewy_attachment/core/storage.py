"""File storage engine for ChewyAttachment"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .exceptions import StorageException
from .schemas import FileUploadResult
from .utils import detect_mime_type, generate_uuid, get_file_extension, safe_filename


class FileStorageEngine:
    """
    File storage engine that handles physical file operations.

    Files are stored in a date-based directory structure:
    <storage_root>/YYYY/MM/DD/<uuid>.<ext>
    """

    def __init__(self, storage_root: str | Path):
        """
        Initialize storage engine.

        Args:
            storage_root: Root directory for file storage
        """
        self.storage_root = Path(storage_root)
        self._ensure_storage_root()

    def _ensure_storage_root(self) -> None:
        """Ensure storage root directory exists"""
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageException(f"Cannot create storage root: {e}")

    def _generate_storage_path(self, original_name: str) -> str:
        """
        Generate storage path for a file.

        Returns relative path from storage root: YYYY/MM/DD/<uuid>.<ext>
        """
        now = datetime.now()
        date_path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}"
        file_id = generate_uuid()
        ext = get_file_extension(safe_filename(original_name))
        filename = f"{file_id}{ext}" if ext else file_id
        return f"{date_path}/{filename}"

    def _get_full_path(self, storage_path: str) -> Path:
        """Get full filesystem path from relative storage path"""
        full_path = (self.storage_root / storage_path).resolve()
        if not str(full_path).startswith(str(self.storage_root.resolve())):
            raise StorageException("Invalid storage path: directory traversal detected")
        return full_path

    def save_file(
        self,
        content: bytes,
        original_name: str,
        storage_path: Optional[str] = None,
    ) -> FileUploadResult:
        """
        Save file content to storage.

        Args:
            content: File content as bytes
            original_name: Original filename
            storage_path: Optional custom storage path (relative)

        Returns:
            FileUploadResult with storage_path, size, and mime_type
        """
        if storage_path is None:
            storage_path = self._generate_storage_path(original_name)

        full_path = self._get_full_path(storage_path)

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)
        except Exception as e:
            raise StorageException(f"Failed to save file: {e}")

        mime_type = detect_mime_type(content, original_name)
        size = len(content)

        return FileUploadResult(
            storage_path=storage_path,
            size=size,
            mime_type=mime_type,
        )

    def get_file(self, storage_path: str) -> bytes:
        """
        Read file content from storage.

        Args:
            storage_path: Relative path to file

        Returns:
            File content as bytes
        """
        full_path = self._get_full_path(storage_path)

        if not full_path.exists():
            raise StorageException(f"File not found: {storage_path}")

        try:
            return full_path.read_bytes()
        except Exception as e:
            raise StorageException(f"Failed to read file: {e}")

    def get_file_path(self, storage_path: str) -> Path:
        """
        Get full filesystem path for a file.

        Args:
            storage_path: Relative path to file

        Returns:
            Full Path object
        """
        full_path = self._get_full_path(storage_path)

        if not full_path.exists():
            raise StorageException(f"File not found: {storage_path}")

        return full_path

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_path: Relative path to file

        Returns:
            True if deleted, False if file didn't exist
        """
        full_path = self._get_full_path(storage_path)

        if not full_path.exists():
            return False

        try:
            full_path.unlink()
            return True
        except Exception as e:
            raise StorageException(f"Failed to delete file: {e}")

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in storage"""
        try:
            full_path = self._get_full_path(storage_path)
            return full_path.exists()
        except StorageException:
            return False
