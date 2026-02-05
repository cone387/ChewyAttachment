"""Common data schemas for ChewyAttachment"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


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


@dataclass
class S3ConfigSchema:
    """
    S3 storage configuration schema.
    
    This schema defines the configuration needed to connect to an S3-compatible
    storage service. It can be used for AWS S3, MinIO, Aliyun OSS, etc.
    
    Attributes:
        config_id: Unique identifier for this configuration
        bucket_name: S3 bucket name
        region: AWS region or equivalent (default: us-east-1)
        endpoint_url: Custom S3 endpoint URL (for S3-compatible services like MinIO)
        access_key: AWS access key ID
        secret_key: AWS secret access key
        prefix: Key prefix for all files (default: attachments)
        public_read: Whether files should be publicly readable (default: False)
        extra_options: Additional options for the storage backend
    """
    
    config_id: str
    bucket_name: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None
    prefix: str = "attachments"
    public_read: bool = False
    extra_options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, include_secrets: bool = False) -> dict:
        """
        Convert to dictionary.
        
        Args:
            include_secrets: Whether to include sensitive fields (access_key, secret_key)
        
        Returns:
            Dictionary representation
        """
        result = {
            "config_id": self.config_id,
            "bucket_name": self.bucket_name,
            "region": self.region,
            "endpoint_url": self.endpoint_url,
            "prefix": self.prefix,
            "public_read": self.public_read,
        }
        if include_secrets:
            result["access_key"] = self.access_key
            result["secret_key"] = self.secret_key
        return result
