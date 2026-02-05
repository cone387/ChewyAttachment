"""Dependency injection for ChewyAttachment FastAPI app"""

from pathlib import Path
from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, SQLModel, create_engine

from ..core.permissions import PermissionChecker
from ..core.schemas import UserContext
from ..core.storage import (
    BaseStorageEngine,
    FileStorageEngine,
    StorageManager,
    StorageConfigProvider,
)
from .crud import get_attachment
from .models import Attachment

_engine = None
_storage_root: Optional[Path] = None
_storage_config_provider: Optional[StorageConfigProvider] = None

def configure(
    database_url: str,
    storage_root: str | Path,
    storage_config_provider: Optional[StorageConfigProvider] = None,
) -> None:
    """
    Configure database and storage for the FastAPI app.

    Must be called before using the app.

    Args:
        database_url: SQLAlchemy database URL
        storage_root: Root directory for file storage (fallback for local storage)
        storage_config_provider: Optional custom storage configuration provider
                                for multi-S3 storage support
    """
    global _engine, _storage_root, _storage_config_provider

    _engine = create_engine(database_url, echo=False)
    SQLModel.metadata.create_all(_engine)
    _storage_root = Path(storage_root)
    _storage_config_provider = storage_config_provider
    
    # Configure StorageManager singleton
    manager = StorageManager(
        provider=storage_config_provider,
        local_storage_root=_storage_root,
    )
    StorageManager.set_instance(manager)

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


def get_storage_engine() -> BaseStorageEngine:
    """
    Get default storage engine dependency.

    Returns:
        BaseStorageEngine instance (FileStorageEngine or S3StorageEngine)
    """
    if _storage_root is None:
        raise RuntimeError(
            "Storage not configured. Call configure() first."
        )
    
    manager = StorageManager.get_instance()
    return manager.get_default_engine()


def get_storage_engine_for_attachment(storage_config_id: Optional[str] = None) -> BaseStorageEngine:
    """
    Get storage engine for a specific attachment based on its storage_config_id.
    
    Args:
        storage_config_id: The storage configuration ID from the attachment.
                          If None, returns the default storage engine.
    
    Returns:
        BaseStorageEngine: Storage engine for the attachment
    """
    manager = StorageManager.get_instance()
    
    if storage_config_id:
        return manager.get_engine(storage_config_id)
    else:
        return manager.get_default_engine()


def get_storage_engine_for_upload(
    storage_config_id: Optional[str] = None,
) -> tuple[BaseStorageEngine, Optional[str]]:
    """
    Get storage engine for uploading a new attachment.
    
    Args:
        storage_config_id: Optional storage configuration ID to use.
                          If None, uses the default configuration.
    
    Returns:
        Tuple of (storage_engine, config_id_to_store)
        - config_id_to_store may be None for local storage
    """
    manager = StorageManager.get_instance()
    return manager.get_engine_for_attachment(storage_config_id)


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


def get_current_user_optional(
    user: UserContext = Depends(get_current_user),
) -> Optional[UserContext]:
    """
    Get current user, allowing anonymous access.

    Args:
        user: User context from get_current_user

    Returns:
        UserContext instance or None if anonymous
    """
    return user if user.is_authenticated else None


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
