"""Django admin configuration for ChewyAttachment"""

from django.contrib import admin

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for Attachment model"""

    list_display = ["id", "original_name", "mime_type", "size", "owner_id", "is_public", "created_at"]
    list_filter = ["is_public", "mime_type", "created_at"]
    search_fields = ["original_name", "owner_id"]
    readonly_fields = ["id", "storage_path", "mime_type", "size", "created_at"]
    ordering = ["-created_at"]
