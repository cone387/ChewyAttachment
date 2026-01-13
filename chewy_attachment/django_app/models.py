"""Django models for ChewyAttachment"""

import uuid

from django.conf import settings
from django.db import models

from ..core.schemas import FileMetadata, UserContext


def get_storage_root():
    """Get storage root from Django settings"""
    from pathlib import Path

    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    if "STORAGE_ROOT" in chewy_settings:
        return chewy_settings["STORAGE_ROOT"]

    base_dir = getattr(settings, "BASE_DIR", Path.cwd())
    return Path(base_dir) / "media" / "attachments"


def get_attachment_table_name():
    """Get custom table name from Django settings"""
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    return chewy_settings.get("TABLE_NAME", "chewy_attachment_files")


class Attachment(models.Model):
    """Attachment model for storing file metadata"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100)
    size = models.BigIntegerField()
    owner_id = models.CharField(max_length=100, db_index=True)
    is_public = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        # Use db_table property to support dynamic table name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner_id", "created_at"]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set table name
        if not hasattr(self._meta, '_db_table_set'):
            self._meta.db_table = get_attachment_table_name()
            self._meta._db_table_set = True

    def __str__(self):
        return f"{self.original_name} ({self.id})"

    def to_file_metadata(self) -> FileMetadata:
        """Convert to FileMetadata for permission checking"""
        return FileMetadata(
            id=str(self.id),
            original_name=self.original_name,
            storage_path=self.storage_path,
            mime_type=self.mime_type,
            size=self.size,
            owner_id=self.owner_id,
            is_public=self.is_public,
            created_at=self.created_at,
        )

    @staticmethod
    def get_user_context(request) -> UserContext:
        """Extract UserContext from Django request"""
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)
            return UserContext.authenticated(user_id)
        return UserContext.anonymous()
