"""DRF permission classes for ChewyAttachment"""

from rest_framework import permissions

from ..core.permissions import PermissionChecker
from .models import Attachment


class IsOwnerOrPublicReadOnly(permissions.BasePermission):
    """
    Permission class for attachment access.

    - View/Download: public files OR owner
    - Delete: owner only
    """

    def has_object_permission(self, request, view, obj: Attachment):
        user_context = Attachment.get_user_context(request)
        file_metadata = obj.to_file_metadata()

        if request.method in permissions.SAFE_METHODS:
            return PermissionChecker.can_view(file_metadata, user_context)

        if request.method == "DELETE":
            return PermissionChecker.can_delete(file_metadata, user_context)

        return False


class IsAuthenticatedForUpload(permissions.BasePermission):
    """Permission class requiring authentication for upload"""

    def has_permission(self, request, view):
        if view.action == "create":
            return request.user and request.user.is_authenticated
        return True
