"""Pydantic schemas for ChewyAttachment FastAPI app"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class AttachmentResponse(BaseModel):
    """Response schema for attachment"""

    id: str
    original_name: str
    mime_type: str
    size: int
    owner_id: str
    is_public: bool
    created_at: datetime
    preview_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AttachmentListResponse(BaseModel):
    """Paginated list response"""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    items: list[AttachmentResponse] = Field(..., description="List of attachments")


class AttachmentUploadForm(BaseModel):
    """Form data for file upload (excluding file itself)"""

    is_public: bool = False


class ErrorResponse(BaseModel):
    """Error response schema"""

    detail: str
