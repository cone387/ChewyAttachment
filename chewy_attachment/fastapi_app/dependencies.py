"""Dependency injection for ChewyAttachment FastAPI app"""

from pathlib import Path
from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, SQLModel, create_engine

from ..core.permissions import PermissionChecker
from ..core.schemas import UserContext
from ..core.storage import FileStorageEngine
from .crud import get_attachment
from .models import Attachment

_engine = None
_storage_root: Optional[Path] = None


def configure(database_url: str, storage_root: str | Path) -> None:
    """
    Configure database and storage for the FastAPI app.

    Must be called before using the app.

    Args:
        database_url: SQLAlchemy database URL
        storage_root: Root directory for file storage
    """
    global _engine, _storage_root

    _engine = create_engine(database_url, echo=False)
    SQLModel.metadata.create_all(_engine)
    _storage_root = Path(storage_root)


def get_engine():
    """Get database engine"""
    if _engine is None:
        raise RuntimeError(
            "Database not configured. Call configure() first."
        )
    return _engine


def get_session() -> Generator[Session, None, None]:
    """
    Get database session dependency.

    Yields:
        Database session
    """
    engine = get_engine()
    with Session(engine) as session:
        yield session


def get_storage_engine() -> FileStorageEngine:
    """
    Get storage engine dependency.

    Returns:
        FileStorageEngine instance
    """
    if _storage_root is None:
        raise RuntimeError(
            "Storage not configured. Call configure() first."
        )
    return FileStorageEngine(_storage_root)


def get_current_user(request: Request) -> UserContext:
    """
    Get current user from request.

    This dependency should be overridden by the host application
    to provide actual user authentication.

    By default, it checks for user_id in request.state.

    Args:
        request: FastAPI request

    Returns:
        UserContext instance
    """
    if hasattr(request.state, "user_id") and request.state.user_id:
        return UserContext.authenticated(str(request.state.user_id))

    return UserContext.anonymous()


def get_current_user_required(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """
    Get current user, requiring authentication.

    Args:
        user: User context from get_current_user

    Returns:
        UserContext instance

    Raises:
        HTTPException: If user is not authenticated
    """
    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def get_attachment_or_404(
    attachment_id: str,
    session: Session = Depends(get_session),
) -> Attachment:
    """
    Get attachment by ID or raise 404.

    Args:
        attachment_id: Attachment ID
        session: Database session

    Returns:
        Attachment instance

    Raises:
        HTTPException: If attachment not found
    """
    attachment = get_attachment(session, attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    return attachment


def require_view_permission(
    attachment: Attachment = Depends(get_attachment_or_404),
    user: UserContext = Depends(get_current_user),
) -> Attachment:
    """
    Require view permission for attachment.

    Args:
        attachment: Attachment instance
        user: User context

    Returns:
        Attachment instance if permitted

    Raises:
        HTTPException: If permission denied
    """
    file_metadata = attachment.to_file_metadata()
    if not PermissionChecker.can_view(file_metadata, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this file",
        )
    return attachment


def require_delete_permission(
    attachment: Attachment = Depends(get_attachment_or_404),
    user: UserContext = Depends(get_current_user),
) -> Attachment:
    """
    Require delete permission for attachment.

    Args:
        attachment: Attachment instance
        user: User context

    Returns:
        Attachment instance if permitted

    Raises:
        HTTPException: If permission denied
    """
    file_metadata = attachment.to_file_metadata()
    if not PermissionChecker.can_delete(file_metadata, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the file owner can delete this file",
        )
    return attachment
