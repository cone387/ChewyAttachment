"""Permission checking logic for ChewyAttachment"""

import importlib
from typing import Optional, Type

from .schemas import FileMetadata, UserContext


class PermissionChecker:
    """
    Permission checker for file operations.

    Rules:
    - View/Download: is_public=True OR owner_id == current_user_id
    - Delete: owner_id == current_user_id
    """

    @staticmethod
    def can_view(file: FileMetadata, user: UserContext) -> bool:
        """
        Check if user can view file metadata.

        Args:
            file: File metadata
            user: User context

        Returns:
            True if user can view the file
        """
        if file.is_public:
            return True

        if user.is_authenticated and user.user_id == file.owner_id:
            return True

        return False

    @staticmethod
    def can_download(file: FileMetadata, user: UserContext) -> bool:
        """
        Check if user can download file content.

        Same rules as can_view.
        """
        return PermissionChecker.can_view(file, user)

    @staticmethod
    def can_delete(file: FileMetadata, user: UserContext) -> bool:
        """
        Check if user can delete file.

        Only owner can delete.

        Args:
            file: File metadata
            user: User context

        Returns:
            True if user can delete the file
        """
        if not user.is_authenticated:
            return False

        return user.user_id == file.owner_id

    @staticmethod
    def check_view_permission(
        file: FileMetadata,
        user: UserContext,
    ) -> Optional[str]:
        """
        Check view permission and return error message if denied.

        Returns:
            None if allowed, error message if denied
        """
        if PermissionChecker.can_view(file, user):
            return None
        return "You do not have permission to view this file"

    @staticmethod
    def check_download_permission(
        file: FileMetadata,
        user: UserContext,
    ) -> Optional[str]:
        """
        Check download permission and return error message if denied.

        Returns:
            None if allowed, error message if denied
        """
        if PermissionChecker.can_download(file, user):
            return None
        return "You do not have permission to download this file"

    @staticmethod
    def check_delete_permission(
        file: FileMetadata,
        user: UserContext,
    ) -> Optional[str]:
        """
        Check delete permission and return error message if denied.

        Returns:
            None if allowed, error message if denied
        """
        if PermissionChecker.can_delete(file, user):
            return None
        return "Only the file owner can delete this file"


def load_permission_class(import_path: str) -> Type:
    """
    Dynamically load a permission class from import path.

    Args:
        import_path: Full import path like "myapp.permissions.MyPermissionClass"

    Returns:
        The permission class

    Raises:
        ImportError: If module or class cannot be imported
        AttributeError: If class not found in module

    Example:
        >>> perm_class = load_permission_class("myapp.permissions.CustomPermission")
    """
    try:
        module_path, class_name = import_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        raise ImportError(
            f"Could not import permission class '{import_path}': {e}"
        ) from e
