"""FastAPI router for ChewyAttachment"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlmodel import Session, select, func

from ..core.schemas import UserContext
from ..core.storage import BaseStorageEngine
from .. import __version__
from . import crud
from .dependencies import (
    get_current_user_optional,
    get_current_user_required,
    get_session,
    get_storage_engine,
    get_storage_engine_for_attachment,
    get_storage_engine_for_upload,
    require_delete_permission,
    require_view_permission,
)
from .models import Attachment, AttachmentCreate
from .schemas import AttachmentListResponse, AttachmentResponse, ErrorResponse

router = APIRouter(prefix="/files", tags=["attachments"])
health_router = APIRouter(tags=["health"])


def _add_preview_url(attachment: Attachment, request: Request) -> AttachmentResponse:
    """Add preview_url to attachment response dynamically based on router configuration"""
    response = AttachmentResponse.model_validate(attachment)
    # Use url_for to generate URL based on actual route config, then extract path
    full_url = request.url_for("preview_file", attachment_id=attachment.id)
    response.preview_url = full_url.path
    return response


@router.get(
    "",
    response_model=AttachmentListResponse,
    responses={
        200: {"description": "List of attachments"},
    },
)
async def list_files(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
    user: Optional[UserContext] = Depends(get_current_user_optional),
):
    """
    List files with pagination.

    - Anonymous users: only public files
    - Authenticated users: own files + public files
    """
    user_id = user.user_id if user else None
    attachments, total = crud.get_attachments_for_user(session, user_id, page, page_size)

    # Add preview_url to each attachment
    items = [_add_preview_url(att, request) for att in attachments]

    return AttachmentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.post(
    "",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    is_public: bool = Form(default=False),
    storage_config_id: Optional[str] = Form(default=None, description="S3存储配置ID"),
    session: Session = Depends(get_session),
    user: UserContext = Depends(get_current_user_required),
):
    """
    Upload a new file.

    - **file**: File to upload
    - **is_public**: Whether the file should be publicly accessible
    - **storage_config_id**: Optional S3 storage configuration ID
    """
    content = await file.read()
    original_name = file.filename or "unnamed"

    storage, actual_config_id = get_storage_engine_for_upload(storage_config_id)
    result = storage.save_file(content, original_name)

    attachment_data = AttachmentCreate(
        original_name=original_name,
        storage_path=result.storage_path,
        mime_type=result.mime_type,
        size=result.size,
        owner_id=user.user_id,
        is_public=is_public,
        storage_config_id=actual_config_id,
    )

    attachment = crud.create_attachment(session, attachment_data)
    return _add_preview_url(attachment, request)


@router.get(
    "/{attachment_id}",
    response_model=AttachmentResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Attachment not found"},
    },
)
async def get_file_info(
    request: Request,
    attachment: Attachment = Depends(require_view_permission),
):
    """
    Get file metadata.

    - **attachment_id**: UUID of the attachment
    """
    return _add_preview_url(attachment, request)


@router.get(
    "/{attachment_id}/content",
    responses={
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Attachment not found"},
    },
)
async def download_file(
    attachment: Attachment = Depends(require_view_permission),
):
    """
    Download file content (attachment mode - triggers download).

    - **attachment_id**: UUID of the attachment
    """
    storage = get_storage_engine_for_attachment(attachment.storage_config_id)
    
    try:
        # For S3 storage, redirect to pre-signed URL
        if hasattr(storage, 's3_client'):
            file_url = storage.get_file_url(attachment.storage_path)
            return RedirectResponse(url=file_url, status_code=status.HTTP_302_FOUND)
        else:
            # For local storage, serve file directly
            file_path = storage.get_file_path(attachment.storage_path)
            return FileResponse(
                path=file_path,
                media_type=attachment.mime_type,
                filename=attachment.original_name,
                headers={"Content-Disposition": f'attachment; filename="{attachment.original_name}"'},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage",
        )


@router.get(
    "/{attachment_id}/preview",
    responses={
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Attachment not found"},
    },
)
async def preview_file(
    attachment: Attachment = Depends(require_view_permission),
):
    """
    Preview file in browser (inline mode - displays in browser).

    - **attachment_id**: UUID of the attachment
    """
    storage = get_storage_engine_for_attachment(attachment.storage_config_id)
    
    try:
        # For S3 storage, redirect to pre-signed URL
        if hasattr(storage, 's3_client'):
            file_url = storage.get_file_url(attachment.storage_path)
            return RedirectResponse(url=file_url, status_code=status.HTTP_302_FOUND)
        else:
            # For local storage, serve file directly
            file_path = storage.get_file_path(attachment.storage_path)
            return FileResponse(
                path=file_path,
                media_type=attachment.mime_type,
                filename=attachment.original_name,
                headers={"Content-Disposition": f'inline; filename="{attachment.original_name}"'},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage",
        )


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Attachment not found"},
    },
)
async def delete_file(
    attachment: Attachment = Depends(require_delete_permission),
    session: Session = Depends(get_session),
):
    """
    Delete a file.

    Only the file owner can delete the file.

    - **attachment_id**: UUID of the attachment
    """
    storage = get_storage_engine_for_attachment(attachment.storage_config_id)
    storage.delete_file(attachment.storage_path)
    crud.delete_attachment(session, attachment)
    return None


# Health check and stats endpoints
@health_router.get("/health", tags=["health"])
async def health_check(session: Session = Depends(get_session)):
    """
    Health check endpoint.
    
    Returns the health status of the service including:
    - Database connectivity
    - Storage engine availability
    - Version information
    """
    health_status = {
        "status": "healthy",
        "version": __version__,
        "checks": {},
    }
    
    # Check database connectivity
    try:
        session.exec(select(func.count()).select_from(Attachment)).first()
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
    
    if health_status["status"] != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )
    
    return health_status


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


@health_router.get("/stats", tags=["stats"])
async def storage_stats(
    session: Session = Depends(get_session),
    user: UserContext = Depends(get_current_user_required),
    show_global: bool = Query(False, alias="global", description="Show global stats (admin only)"),
):
    """
    Storage statistics endpoint.
    
    Returns storage usage statistics:
    - For authenticated users: their own storage stats
    - For admin users: global stats (if requested with ?global=true)
    """
    user_id = user.user_id
    
    if show_global:
        # Global statistics
        return _get_global_stats(session)
    else:
        # User's own statistics
        return _get_user_stats(session, user_id)


def _get_user_stats(session: Session, user_id: str) -> dict:
    """Get statistics for a specific user"""
    # Total files and size
    total_query = select(
        func.count(Attachment.id).label("total_files"),
        func.coalesce(func.sum(Attachment.size), 0).label("total_size"),
    ).where(Attachment.owner_id == user_id)
    
    result = session.exec(total_query).first()
    total_files = result[0] if result else 0
    total_size = result[1] if result else 0
    
    # Breakdown by MIME type
    mime_query = (
        select(
            Attachment.mime_type,
            func.count(Attachment.id).label("count"),
            func.coalesce(func.sum(Attachment.size), 0).label("size"),
        )
        .where(Attachment.owner_id == user_id)
        .group_by(Attachment.mime_type)
        .order_by(func.sum(Attachment.size).desc())
        .limit(10)
    )
    mime_results = session.exec(mime_query).all()
    
    # Breakdown by storage config
    storage_query = (
        select(
            Attachment.storage_config_id,
            func.count(Attachment.id).label("count"),
            func.coalesce(func.sum(Attachment.size), 0).label("size"),
        )
        .where(Attachment.owner_id == user_id)
        .group_by(Attachment.storage_config_id)
        .order_by(func.sum(Attachment.size).desc())
    )
    storage_results = session.exec(storage_query).all()
    
    return {
        "scope": "user",
        "user_id": user_id,
        "total_files": total_files,
        "total_size": total_size,
        "total_size_human": _format_size(total_size),
        "by_mime_type": [
            {
                "mime_type": row[0],
                "count": row[1],
                "size": row[2],
                "size_human": _format_size(row[2]),
            }
            for row in mime_results
        ],
        "by_storage": [
            {
                "storage_config_id": row[0] or "local",
                "count": row[1],
                "size": row[2],
                "size_human": _format_size(row[2]),
            }
            for row in storage_results
        ],
    }


def _get_global_stats(session: Session) -> dict:
    """Get global statistics"""
    # Total files, size, and users
    total_query = select(
        func.count(Attachment.id).label("total_files"),
        func.coalesce(func.sum(Attachment.size), 0).label("total_size"),
        func.count(func.distinct(Attachment.owner_id)).label("total_users"),
    )
    
    result = session.exec(total_query).first()
    total_files = result[0] if result else 0
    total_size = result[1] if result else 0
    total_users = result[2] if result else 0
    
    # Breakdown by MIME type
    mime_query = (
        select(
            Attachment.mime_type,
            func.count(Attachment.id).label("count"),
            func.coalesce(func.sum(Attachment.size), 0).label("size"),
        )
        .group_by(Attachment.mime_type)
        .order_by(func.sum(Attachment.size).desc())
        .limit(10)
    )
    mime_results = session.exec(mime_query).all()
    
    # Breakdown by storage config
    storage_query = (
        select(
            Attachment.storage_config_id,
            func.count(Attachment.id).label("count"),
            func.coalesce(func.sum(Attachment.size), 0).label("size"),
        )
        .group_by(Attachment.storage_config_id)
        .order_by(func.sum(Attachment.size).desc())
    )
    storage_results = session.exec(storage_query).all()
    
    # Top users by storage
    top_users_query = (
        select(
            Attachment.owner_id,
            func.count(Attachment.id).label("count"),
            func.coalesce(func.sum(Attachment.size), 0).label("size"),
        )
        .group_by(Attachment.owner_id)
        .order_by(func.sum(Attachment.size).desc())
        .limit(10)
    )
    top_users_results = session.exec(top_users_query).all()
    
    return {
        "scope": "global",
        "total_files": total_files,
        "total_size": total_size,
        "total_size_human": _format_size(total_size),
        "total_users": total_users,
        "by_mime_type": [
            {
                "mime_type": row[0],
                "count": row[1],
                "size": row[2],
                "size_human": _format_size(row[2]),
            }
            for row in mime_results
        ],
        "by_storage": [
            {
                "storage_config_id": row[0] or "local",
                "count": row[1],
                "size": row[2],
                "size_human": _format_size(row[2]),
            }
            for row in storage_results
        ],
        "top_users": [
            {
                "owner_id": row[0],
                "count": row[1],
                "size": row[2],
                "size_human": _format_size(row[2]),
            }
            for row in top_users_results
        ],
    }
