"""DRF views for ChewyAttachment"""

import logging

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models import Sum, Count
from django.http import FileResponse, Http404, HttpResponseRedirect

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..core.permissions import PermissionChecker, load_permission_class
from ..core.storage import DjangoStorageEngine, S3StorageEngine
from ..core.utils import generate_uuid
from .. import __version__
from .permissions import IsAuthenticatedForUpload, IsOwnerOrPublicReadOnly
from .serializers import AttachmentSerializer, AttachmentUploadSerializer

logger = logging.getLogger("chewy_attachment")


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


def _is_cloud_storage(storage) -> bool:
    """Check if the storage engine is a cloud storage backend."""
    if isinstance(storage, S3StorageEngine):
        return True
    if isinstance(storage, DjangoStorageEngine) and not hasattr(storage.storage, 'path'):
        return True
    return False


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

    def get_storage_engine(self, storage_config_id=None):
        """Get storage engine instance for reading/downloading"""
        from .storage import get_storage_engine_for_attachment
        return get_storage_engine_for_attachment(storage_config_id)

    def get_storage_engine_for_upload(self, storage_config_id=None):
        """Get storage engine instance for uploading"""
        from .storage import get_storage_engine_for_upload
        return get_storage_engine_for_upload(storage_config_id)

    def create(self, request, *args, **kwargs):
        """Handle file upload"""
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        is_public = serializer.validated_data.get("is_public", False)
        storage_config_id = serializer.validated_data.get("storage_config_id")

        content = uploaded_file.read()
        original_name = uploaded_file.name

        storage, actual_config_id = self.get_storage_engine_for_upload(storage_config_id)
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
            storage_config_id=actual_config_id,
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

        storage = self.get_storage_engine(instance.storage_config_id)
        storage.delete_file(instance.storage_path)

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _serve_file(self, instance, disposition: str):
        """Serve a file — redirect to cloud URL or stream from local storage."""
        storage = self.get_storage_engine(instance.storage_config_id)
        try:
            if _is_cloud_storage(storage):
                file_url = storage.get_file_url(instance.storage_path)
                return HttpResponseRedirect(file_url)
            else:
                file_path = storage.get_file_path(instance.storage_path)
                response = FileResponse(
                    open(file_path, "rb"),
                    content_type=instance.mime_type,
                )
                response["Content-Disposition"] = (
                    f'{disposition}; filename="{instance.original_name}"'
                )
                response["Content-Length"] = instance.size
                return response
        except Exception:
            logger.exception("Failed to serve file %s", instance.storage_path)
            raise Http404("File not found on storage")

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

        return self._serve_file(instance, disposition="attachment")

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

        return self._serve_file(instance, disposition="inline")


class HealthCheckView(APIView):
    """
    Health check endpoint for ChewyAttachment.
    
    Returns the health status of the service including:
    - Database connectivity
    - Storage engine availability
    - Version information
    
    GET /health/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Perform health check"""
        health_status = {
            "status": "healthy",
            "version": __version__,
            "checks": {},
        }
        
        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": str(e),
            }
        
        # Check storage engine
        try:
            from .storage import get_storage_engine
            storage = get_storage_engine()
            storage_type = type(storage).__name__
            health_status["checks"]["storage"] = {
                "status": "healthy",
                "type": storage_type,
                "message": "Storage engine initialized",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["storage"] = {
                "status": "unhealthy",
                "message": str(e),
            }
        
        # Return appropriate status code
        status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=status_code)


class StorageStatsView(APIView):
    """
    Storage statistics endpoint for ChewyAttachment.
    
    Returns storage usage statistics:
    - For authenticated users: their own storage stats
    - For admin users: global stats (if requested)
    
    GET /stats/
    GET /stats/?global=true  (admin only)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get storage statistics"""
        user = request.user
        Attachment = get_attachment_model()
        
        # Check if global stats requested (admin only)
        show_global = request.query_params.get("global", "").lower() == "true"
        
        if show_global and user.is_staff:
            # Global statistics for admin
            stats = self._get_global_stats(Attachment)
        else:
            # User's own statistics
            stats = self._get_user_stats(Attachment, str(user.id))
        
        return Response(stats)
    
    def _get_user_stats(self, Attachment, user_id: str) -> dict:
        """Get statistics for a specific user"""
        queryset = Attachment.objects.filter(owner_id=user_id)
        
        aggregation = queryset.aggregate(
            total_files=Count("id"),
            total_size=Sum("size"),
        )
        
        # Get breakdown by MIME type
        mime_breakdown = (
            queryset.values("mime_type")
            .annotate(count=Count("id"), size=Sum("size"))
            .order_by("-size")[:10]
        )
        
        # Get breakdown by storage config
        storage_breakdown = (
            queryset.values("storage_config_id")
            .annotate(count=Count("id"), size=Sum("size"))
            .order_by("-size")
        )
        
        return {
            "scope": "user",
            "user_id": user_id,
            "total_files": aggregation["total_files"] or 0,
            "total_size": aggregation["total_size"] or 0,
            "total_size_human": self._format_size(aggregation["total_size"] or 0),
            "by_mime_type": [
                {
                    "mime_type": item["mime_type"],
                    "count": item["count"],
                    "size": item["size"] or 0,
                    "size_human": self._format_size(item["size"] or 0),
                }
                for item in mime_breakdown
            ],
            "by_storage": [
                {
                    "storage_config_id": item["storage_config_id"] or "local",
                    "count": item["count"],
                    "size": item["size"] or 0,
                    "size_human": self._format_size(item["size"] or 0),
                }
                for item in storage_breakdown
            ],
        }
    
    def _get_global_stats(self, Attachment) -> dict:
        """Get global statistics (admin only)"""
        queryset = Attachment.objects.all()
        
        aggregation = queryset.aggregate(
            total_files=Count("id"),
            total_size=Sum("size"),
            total_users=Count("owner_id", distinct=True),
        )
        
        # Get breakdown by MIME type
        mime_breakdown = (
            queryset.values("mime_type")
            .annotate(count=Count("id"), size=Sum("size"))
            .order_by("-size")[:10]
        )
        
        # Get breakdown by storage config
        storage_breakdown = (
            queryset.values("storage_config_id")
            .annotate(count=Count("id"), size=Sum("size"))
            .order_by("-size")
        )
        
        # Get top users by storage
        top_users = (
            queryset.values("owner_id")
            .annotate(count=Count("id"), size=Sum("size"))
            .order_by("-size")[:10]
        )
        
        return {
            "scope": "global",
            "total_files": aggregation["total_files"] or 0,
            "total_size": aggregation["total_size"] or 0,
            "total_size_human": self._format_size(aggregation["total_size"] or 0),
            "total_users": aggregation["total_users"] or 0,
            "by_mime_type": [
                {
                    "mime_type": item["mime_type"],
                    "count": item["count"],
                    "size": item["size"] or 0,
                    "size_human": self._format_size(item["size"] or 0),
                }
                for item in mime_breakdown
            ],
            "by_storage": [
                {
                    "storage_config_id": item["storage_config_id"] or "local",
                    "count": item["count"],
                    "size": item["size"] or 0,
                    "size_human": self._format_size(item["size"] or 0),
                }
                for item in storage_breakdown
            ],
            "top_users": [
                {
                    "owner_id": item["owner_id"],
                    "count": item["count"],
                    "size": item["size"] or 0,
                    "size_human": self._format_size(item["size"] or 0),
                }
                for item in top_users
            ],
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable string"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
