"""DRF views for ChewyAttachment"""

from django.http import FileResponse, Http404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..core.permissions import PermissionChecker
from ..core.storage import FileStorageEngine
from ..core.utils import generate_uuid
from .models import Attachment, get_storage_root
from .permissions import IsAuthenticatedForUpload, IsOwnerOrPublicReadOnly
from .serializers import AttachmentSerializer, AttachmentUploadSerializer


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for attachment operations.

    Endpoints:
    - POST /files/ - Upload file
    - GET /files/{id}/ - Get file info
    - DELETE /files/{id}/ - Delete file
    """

    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticatedForUpload, IsOwnerOrPublicReadOnly]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_storage_engine(self) -> FileStorageEngine:
        """Get storage engine instance"""
        return FileStorageEngine(get_storage_root())

    def create(self, request, *args, **kwargs):
        """Handle file upload"""
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        is_public = serializer.validated_data.get("is_public", False)

        content = uploaded_file.read()
        original_name = uploaded_file.name

        storage = self.get_storage_engine()
        result = storage.save_file(content, original_name)

        attachment = Attachment.objects.create(
            id=generate_uuid(),
            original_name=original_name,
            storage_path=result.storage_path,
            mime_type=result.mime_type,
            size=result.size,
            owner_id=str(request.user.id),
            is_public=is_public,
        )

        output_serializer = AttachmentSerializer(attachment)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Get file metadata"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete file"""
        instance = self.get_object()

        storage = self.get_storage_engine()
        storage.delete_file(instance.storage_path)

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="content")
    def download(self, request, pk=None):
        """Download file content"""
        instance = self.get_object()

        user_context = Attachment.get_user_context(request)
        file_metadata = instance.to_file_metadata()

        if not PermissionChecker.can_download(file_metadata, user_context):
            return Response(
                {"detail": "You do not have permission to download this file"},
                status=status.HTTP_403_FORBIDDEN,
            )

        storage = self.get_storage_engine()

        try:
            file_path = storage.get_file_path(instance.storage_path)
        except Exception:
            raise Http404("File not found on storage")

        response = FileResponse(
            open(file_path, "rb"),
            content_type=instance.mime_type,
        )
        response["Content-Disposition"] = f'attachment; filename="{instance.original_name}"'
        response["Content-Length"] = instance.size
        return response


class AttachmentDownloadView(APIView):
    """
    Alternative download view using APIView.

    GET /files/{id}/content - Download file content
    """

    permission_classes = [IsOwnerOrPublicReadOnly]

    def get_object(self, pk):
        """Get attachment by ID"""
        try:
            return Attachment.objects.get(pk=pk)
        except Attachment.DoesNotExist:
            raise Http404("Attachment not found")

    def get(self, request, pk, format=None):
        """Download file"""
        attachment = self.get_object(pk)

        self.check_object_permissions(request, attachment)

        user_context = Attachment.get_user_context(request)
        file_metadata = attachment.to_file_metadata()

        if not PermissionChecker.can_download(file_metadata, user_context):
            return Response(
                {"detail": "You do not have permission to download this file"},
                status=status.HTTP_403_FORBIDDEN,
            )

        storage = FileStorageEngine(get_storage_root())

        try:
            file_path = storage.get_file_path(attachment.storage_path)
        except Exception:
            raise Http404("File not found on storage")

        response = FileResponse(
            open(file_path, "rb"),
            content_type=attachment.mime_type,
        )
        response["Content-Disposition"] = f'attachment; filename="{attachment.original_name}"'
        response["Content-Length"] = attachment.size
        return response
