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


class AttachmentBase(models.Model):
    """Abstract base model for storing file metadata"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    original_name = models.CharField(
        max_length=255,
        verbose_name="文件名",
    )
    storage_path = models.CharField(
        max_length=500,
        verbose_name="存储路径",
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name="文件类型",
    )
    size = models.BigIntegerField(
        verbose_name="文件大小",
        help_text="单位：字节",
    )
    owner_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="所有者ID",
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="公开访问",
        help_text="公开文件可被任何人访问",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="创建时间",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        verbose_name = "附件"
        verbose_name_plural = "附件"
        indexes = [
            models.Index(fields=["owner_id", "created_at"]),
        ]

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


class Attachment(AttachmentBase):
    """
    Default concrete implementation of AttachmentBase.
    
    This model can be swapped out by setting CHEWY_ATTACHMENT_MODEL
    in your Django settings, similar to AUTH_USER_MODEL.
    """

    class Meta(AttachmentBase.Meta):
        db_table = "chewy_attachments"
        abstract = False
        swappable = 'CHEWY_ATTACHMENT_MODEL'
