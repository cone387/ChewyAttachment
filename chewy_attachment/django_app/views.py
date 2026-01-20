"""DRF views for ChewyAttachment"""

from django.conf import settings
from django.http import FileResponse, Http404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from ..core.permissions import PermissionChecker, load_permission_class
from ..core.storage import FileStorageEngine
from ..core.utils import generate_uuid
from django.apps import apps
from .models import Attachment, get_storage_root
from .permissions import IsAuthenticatedForUpload, IsOwnerOrPublicReadOnly
from .serializers import AttachmentSerializer, AttachmentUploadSerializer


def get_attachment_model():
    """获取当前活跃的 Attachment 模型（支持模型交换）"""
    from django.conf import settings
    
    # 检查是否设置了自定义模型
    model_name = getattr(settings, 'CHEWY_ATTACHMENT_MODEL', None)
    if model_name:
        app_label, model_class = model_name.split('.')
        return apps.get_model(app_label, model_class)
    
    # 默认使用内置模型
    return apps.get_model('chewy_attachment_django_app', 'Attachment')


def get_permission_classes():
    """
    Get permission classes from settings or use defaults.

    Settings:
        CHEWY_ATTACHMENT["PERMISSION_CLASSES"]: List of permission class paths

    Example:
        # settings.py
        CHEWY_ATTACHMENT = {
            "STORAGE_ROOT": BASE_DIR / "media" / "attachments",
            "PERMISSION_CLASSES": [
                "IsAuthenticatedForUpload",
                "myapp.permissions.CustomAttachmentPermission",
            ],
        }
    """
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    custom_classes = chewy_settings.get("PERMISSION_CLASSES")

    if custom_classes:
        loaded_classes = []
        for class_path in custom_classes:
            # If it's just a class name, try to load from default location
            if "." not in class_path:
                class_path = f"chewy_attachment.django_app.permissions.{class_path}"
            try:
                loaded_classes.append(load_permission_class(class_path))
            except ImportError as e:
                raise ImportError(
                    f"Failed to load permission class from CHEWY_ATTACHMENT['PERMISSION_CLASSES']: {e}"
                )
        return loaded_classes

    # Default permission classes
    return [IsAuthenticatedForUpload, IsOwnerOrPublicReadOnly]


class AttachmentPagination(PageNumberPagination):
    """Custom pagination for attachments"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for attachment operations.

    Endpoints:
    - POST /files/ - Upload file
    - GET /files/{id}/ - Get file info
    - DELETE /files/{id}/ - Delete file

    Custom Permissions:
        Configure via CHEWY_ATTACHMENT["PERMISSION_CLASSES"]
    """

    serializer_class = AttachmentSerializer
    pagination_class = AttachmentPagination
    http_method_names = ["get", "post", "delete", "head", "options"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically load permission classes
        self.permission_classes = get_permission_classes()

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        user = self.request.user
        Attachment = get_attachment_model()
        
        # Anonymous users: only public files
        if not user.is_authenticated:
            return Attachment.objects.filter(is_public=True)
        
        # Authenticated users: own files + public files
        from django.db.models import Q
        return Attachment.objects.filter(
            Q(owner_id=str(user.id)) | Q(is_public=True)
        )

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

        Attachment = get_attachment_model()
        attachment = Attachment.objects.create(
            id=generate_uuid(),
            original_name=original_name,
            storage_path=result.storage_path,
            mime_type=result.mime_type,
            size=result.size,
            owner_id=str(request.user.id),
            is_public=is_public,
        )

        output_serializer = AttachmentSerializer(attachment, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Get file metadata"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
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

        user_context = get_attachment_model().get_user_context(request)
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

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        """Preview file in browser (inline display)"""
        instance = self.get_object()

        user_context = get_attachment_model().get_user_context(request)
        file_metadata = instance.to_file_metadata()

        if not PermissionChecker.can_download(file_metadata, user_context):
            return Response(
                {"detail": "You do not have permission to preview this file"},
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
        response["Content-Disposition"] = f'inline; filename="{instance.original_name}"'
        response["Content-Length"] = instance.size
        return response


class AttachmentDownloadView(APIView):
    """
    Alternative download view using APIView.

    GET /files/{id}/content - Download file content

    Custom Permissions:
        Configure via CHEWY_ATTACHMENT["PERMISSION_CLASSES"]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically load permission classes
        self.permission_classes = get_permission_classes()

    def get_object(self, pk):
        """Get attachment by ID"""
        Attachment = get_attachment_model()
        try:
            return Attachment.objects.get(pk=pk)
        except Attachment.DoesNotExist:
            raise Http404("Attachment not found")

    def get(self, request, pk, format=None):
        """Download file"""
        attachment = self.get_object(pk)

        self.check_object_permissions(request, attachment)

        user_context = get_attachment_model().get_user_context(request)
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
