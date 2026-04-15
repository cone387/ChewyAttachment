"""DRF serializers for ChewyAttachment"""

from django.conf import settings
from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import Attachment


def get_datetime_format():
    """Get datetime format from settings"""
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    return chewy_settings.get("DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S")


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Attachment model (read operations)"""

    preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "original_name",
            "mime_type",
            "size",
            "owner_id",
            "is_public",
            "storage_config_id",
            "created_at",
            "preview_url",
            "download_url",
            "file_url",
        ]
        read_only_fields = fields

    def get_preview_url(self, obj):
        """Generate preview URL path dynamically based on router configuration"""
        request = self.context.get('request')
        if request:
            return reverse('attachment-preview', kwargs={'pk': obj.id}, request=request)
        return None

    def get_download_url(self, obj):
        """Generate download URL path"""
        request = self.context.get('request')
        if request:
            return reverse('attachment-download', kwargs={'pk': obj.id}, request=request)
        return None

    def get_file_url(self, obj):
        """
        Get direct file URL for cloud storage or signed URL.
        For local storage, returns the download URL.
        """
        try:
            from .storage import get_storage_engine_for_attachment
            from ..core.storage import FileStorageEngine

            storage = get_storage_engine_for_attachment(obj.storage_config_id)

            # For local file storage, return the download URL (not the raw path)
            if isinstance(storage, FileStorageEngine):
                return self.get_download_url(obj)

            # For cloud storage, return the direct/signed URL
            return storage.get_file_url(obj.storage_path)
        except Exception:
            return self.get_download_url(obj)

    def get_created_at(self, obj):
        """Format created_at with configured format"""
        if obj.created_at:
            datetime_format = get_datetime_format()
            return obj.created_at.strftime(datetime_format)
        return None


class AttachmentUploadSerializer(serializers.Serializer):
    """Serializer for file upload"""

    file = serializers.FileField(required=True)
    is_public = serializers.BooleanField(default=False, required=False)
    storage_config_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="S3存储配置ID，不传则使用系统默认配置",
    )

    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided")

        chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})

        # Check file size limit
        max_size = chewy_settings.get("MAX_FILE_SIZE", 10 * 1024 * 1024)  # 10MB default
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )

        # Check allowed extensions
        allowed_extensions = chewy_settings.get("ALLOWED_EXTENSIONS")
        if allowed_extensions:
            import os
            file_ext = os.path.splitext(value.name)[1].lower()
            if file_ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File extension '{file_ext}' is not allowed. "
                    f"Allowed extensions: {', '.join(allowed_extensions)}"
                )

        # Validate MIME type matches file content (prevent extension spoofing)
        if chewy_settings.get("VALIDATE_MIME_CONTENT", False):
            self._validate_mime_content(value)

        return value

    @staticmethod
    def _validate_mime_content(value):
        """
        Validate that the file's actual MIME type is consistent with its extension.
        Reads the first 8KB to detect the real MIME type via python-magic.
        """
        from ..core.utils import detect_mime_type, get_file_extension

        # Read a sample for detection, then seek back
        sample = value.read(8192)
        value.seek(0)

        detected_mime = detect_mime_type(sample, value.name)
        file_ext = get_file_extension(value.name)

        # Build a mapping of dangerous mismatches
        # We only block clearly dangerous cases: executable content disguised as safe types
        dangerous_mimes = {
            "application/x-executable",
            "application/x-dosexec",
            "application/x-msdos-program",
            "application/x-msdownload",
            "application/x-sharedlib",
        }
        safe_extensions = {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".txt", ".rtf", ".csv", ".json", ".xml", ".html", ".css",
            ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
        }

        if detected_mime in dangerous_mimes and file_ext in safe_extensions:
            raise serializers.ValidationError(
                f"File content type '{detected_mime}' does not match "
                f"file extension '{file_ext}'. Upload rejected for security reasons."
            )
