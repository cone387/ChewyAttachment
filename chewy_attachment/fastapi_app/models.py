"""SQLModel models for ChewyAttachment FastAPI app"""

import os
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from ..core.schemas import FileMetadata


def get_attachment_table_name() -> str:
    """Get custom table name from environment variable or use default"""
    return os.getenv("CHEWY_ATTACHMENT_TABLE_NAME", "chewy_attachment_files")


class Attachment(SQLModel, table=True):
    """Attachment model for storing file metadata"""

    # Note: __tablename__ should be set before class instantiation
    # For FastAPI, recommend using environment variable CHEWY_ATTACHMENT_TABLE_NAME
    # or override this in your application
    __tablename__: str = get_attachment_table_name()

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    original_name: str = Field(max_length=255)
    storage_path: str = Field(max_length=500)
    mime_type: str = Field(max_length=100)
    size: int
    owner_id: str = Field(max_length=100, index=True)
    is_public: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)

    def to_file_metadata(self) -> FileMetadata:
        """Convert to FileMetadata for permission checking"""
        return FileMetadata(
            id=self.id,
            original_name=self.original_name,
            storage_path=self.storage_path,
            mime_type=self.mime_type,
            size=self.size,
            owner_id=self.owner_id,
            is_public=self.is_public,
            created_at=self.created_at,
        )


class AttachmentCreate(SQLModel):
    """Schema for creating attachment (internal use)"""

    original_name: str
    storage_path: str
    mime_type: str
    size: int
    owner_id: str
    is_public: bool = False
