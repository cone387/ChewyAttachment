"""FastAPI router for ChewyAttachment"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..core.schemas import UserContext
from ..core.storage import FileStorageEngine
from . import crud
from .dependencies import (
    get_current_user_optional,
    get_current_user_required,
    get_session,
    get_storage_engine,
    require_delete_permission,
    require_view_permission,
)
from .models import Attachment, AttachmentCreate
from .schemas import AttachmentListResponse, AttachmentResponse, ErrorResponse

router = APIRouter(prefix="/files", tags=["attachments"])


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
    session: Session = Depends(get_session),
    storage: FileStorageEngine = Depends(get_storage_engine),
    user: UserContext = Depends(get_current_user_required),
):
    """
    Upload a new file.

    - **file**: File to upload
    - **is_public**: Whether the file should be publicly accessible
    """
    content = await file.read()
    original_name = file.filename or "unnamed"

    result = storage.save_file(content, original_name)

    attachment_data = AttachmentCreate(
        original_name=original_name,
        storage_path=result.storage_path,
        mime_type=result.mime_type,
        size=result.size,
        owner_id=user.user_id,
        is_public=is_public,
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
    storage: FileStorageEngine = Depends(get_storage_engine),
):
    """
    Download file content (attachment mode - triggers download).

    - **attachment_id**: UUID of the attachment
    """
    try:
        file_path = storage.get_file_path(attachment.storage_path)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage",
        )

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
        headers={"Content-Disposition": f'attachment; filename="{attachment.original_name}"'},
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
    storage: FileStorageEngine = Depends(get_storage_engine),
):
    """
    Preview file in browser (inline mode - displays in browser).

    - **attachment_id**: UUID of the attachment
    """
    try:
        file_path = storage.get_file_path(attachment.storage_path)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage",
        )

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
        headers={"Content-Disposition": f'inline; filename="{attachment.original_name}"'},
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
    storage: FileStorageEngine = Depends(get_storage_engine),
):
    """
    Delete a file.

    Only the file owner can delete the file.

    - **attachment_id**: UUID of the attachment
    """
    storage.delete_file(attachment.storage_path)
    crud.delete_attachment(session, attachment)
    return None
