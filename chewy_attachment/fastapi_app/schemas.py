"""Pydantic schemas for ChewyAttachment FastAPI app"""

from datetime import datetime

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    """Response schema for attachment"""

    id: str
    original_name: str
    mime_type: str
    size: int
    owner_id: str
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentUploadForm(BaseModel):
    """Form data for file upload (excluding file itself)"""

    is_public: bool = False


class ErrorResponse(BaseModel):
    """Error response schema"""

    detail: str
