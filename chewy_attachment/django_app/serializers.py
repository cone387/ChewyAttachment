"""DRF serializers for ChewyAttachment"""

from django.conf import settings
from rest_framework import serializers

from .models import Attachment


def get_datetime_format():
    """Get datetime format from settings"""
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    return chewy_settings.get("DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S")


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Attachment model (read operations)"""

    content_url = serializers.SerializerMethodField()
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
            "created_at",
            "content_url",
        ]
        read_only_fields = fields

    def get_content_url(self, obj):
        """Generate content download URL"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                f'/api/attachments/files/{obj.id}/content/'
            )
        return f'/api/attachments/files/{obj.id}/content/'

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

    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided")
        return value
