"""Utility functions for ChewyAttachment"""

import mimetypes
import uuid
from pathlib import Path
from typing import Optional

try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


def generate_uuid() -> str:
    """Generate a UUID string for file ID"""
    return str(uuid.uuid4())


def detect_mime_type(content: bytes, filename: Optional[str] = None) -> str:
    """
    Detect MIME type of file content.

    Uses python-magic if available, falls back to mimetypes based on filename.
    """
    if HAS_MAGIC:
        try:
            mime = magic.Magic(mime=True)
            return mime.from_buffer(content)
        except Exception:
            pass

    if filename:
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            return guessed_type

    return "application/octet-stream"


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    path = Path(filename)
    return path.suffix.lower() if path.suffix else ""


def safe_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other issues.

    Returns only the basename without any directory components.
    """
    name = Path(filename).name
    name = name.replace("\x00", "")
    return name if name else "unnamed"
