"""DRF serializers for ChewyAttachment"""

from rest_framework import serializers

from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Attachment model (read operations)"""

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
        ]
        read_only_fields = fields


class AttachmentUploadSerializer(serializers.Serializer):
    """Serializer for file upload"""

    file = serializers.FileField(required=True)
    is_public = serializers.BooleanField(default=False, required=False)

    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided")
        return value
