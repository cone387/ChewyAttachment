"""Common data schemas for ChewyAttachment"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FileMetadata:
    """File metadata structure"""

    id: str
    original_name: str
    storage_path: str
    mime_type: str
    size: int
    owner_id: str
    is_public: bool
    created_at: datetime

    def to_dict(self, include_storage_path: bool = False) -> dict:
        """Convert to dictionary for API response"""
        result = {
            "id": self.id,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "size": self.size,
            "owner_id": self.owner_id,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat(),
        }
        if include_storage_path:
            result["storage_path"] = self.storage_path
        return result


@dataclass
class FileUploadResult:
    """Result of file upload operation"""

    storage_path: str
    size: int
    mime_type: str


@dataclass
class UserContext:
    """User context for permission checking"""

    user_id: Optional[str] = None
    is_authenticated: bool = False

    @classmethod
    def anonymous(cls) -> "UserContext":
        """Create anonymous user context"""
        return cls(user_id=None, is_authenticated=False)

    @classmethod
    def authenticated(cls, user_id: str) -> "UserContext":
        """Create authenticated user context"""
        return cls(user_id=user_id, is_authenticated=True)
