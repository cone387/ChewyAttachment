"""File storage engines for ChewyAttachment"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .exceptions import StorageException
from .schemas import FileUploadResult
from .utils import detect_mime_type, generate_uuid, get_file_extension, safe_filename


class BaseStorageEngine(ABC):
    """
    Abstract base class for storage engines.
    
    All storage engines must implement these methods to provide
    consistent file storage operations.
    """

    @abstractmethod
    def save_file(
        self,
        content: bytes,
        original_name: str,
        storage_path: Optional[str] = None,
    ) -> FileUploadResult:
        """Save file content to storage"""
        pass

    @abstractmethod
    def get_file(self, storage_path: str) -> bytes:
        """Read file content from storage"""
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in storage"""
        pass

    @abstractmethod
    def get_file_url(self, storage_path: str, expires_in: Optional[int] = None) -> str:
        """Get URL for accessing the file"""
        pass

    def _generate_storage_path(self, original_name: str) -> str:
        """
        Generate storage path for a file.

        Returns relative path: YYYY/MM/DD/<uuid>.<ext>
        """
        now = datetime.now()
        date_path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}"
        file_id = generate_uuid()
        ext = get_file_extension(safe_filename(original_name))
        filename = f"{file_id}{ext}" if ext else file_id
        return f"{date_path}/{filename}"


class FileStorageEngine(BaseStorageEngine):
    """
    Local file storage engine that handles physical file operations.

    Files are stored in a date-based directory structure:
    <storage_root>/YYYY/MM/DD/<uuid>.<ext>
    """

    def __init__(self, storage_root: Union[str, Path]):
        """
        Initialize storage engine.

        Args:
            storage_root: Root directory for file storage
        """
        self.storage_root = Path(storage_root)
        self._ensure_storage_root()

    def _ensure_storage_root(self) -> None:
        """Ensure storage root directory exists"""
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageException(f"Cannot create storage root: {e}")

    def _get_full_path(self, storage_path: str) -> Path:
        """Get full filesystem path from relative storage path"""
        full_path = (self.storage_root / storage_path).resolve()
        if not str(full_path).startswith(str(self.storage_root.resolve())):
            raise StorageException("Invalid storage path: directory traversal detected")
        return full_path

    def save_file(
        self,
        content: bytes,
        original_name: str,
        storage_path: Optional[str] = None,
    ) -> FileUploadResult:
        """
        Save file content to storage.

        Args:
            content: File content as bytes
            original_name: Original filename
            storage_path: Optional custom storage path (relative)

        Returns:
            FileUploadResult with storage_path, size, and mime_type
        """
        if storage_path is None:
            storage_path = self._generate_storage_path(original_name)

        full_path = self._get_full_path(storage_path)

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)
        except Exception as e:
            raise StorageException(f"Failed to save file: {e}")

        mime_type = detect_mime_type(content, original_name)
        size = len(content)

        return FileUploadResult(
            storage_path=storage_path,
            size=size,
            mime_type=mime_type,
        )

    def get_file(self, storage_path: str) -> bytes:
        """
        Read file content from storage.

        Args:
            storage_path: Relative path to file

        Returns:
            File content as bytes
        """
        full_path = self._get_full_path(storage_path)

        if not full_path.exists():
            raise StorageException(f"File not found: {storage_path}")

        try:
            return full_path.read_bytes()
        except Exception as e:
            raise StorageException(f"Failed to read file: {e}")

    def get_file_path(self, storage_path: str) -> Path:
        """
        Get full filesystem path for a file.

        Args:
            storage_path: Relative path to file

        Returns:
            Full Path object
        """
        full_path = self._get_full_path(storage_path)

        if not full_path.exists():
            raise StorageException(f"File not found: {storage_path}")

        return full_path

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_path: Relative path to file

        Returns:
            True if deleted, False if file didn't exist
        """
        full_path = self._get_full_path(storage_path)

        if not full_path.exists():
            return False

        try:
            full_path.unlink()
            return True
        except Exception as e:
            raise StorageException(f"Failed to delete file: {e}")

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in storage"""
        try:
            full_path = self._get_full_path(storage_path)
            return full_path.exists()
        except StorageException:
            return False

    def get_file_url(self, storage_path: str, expires_in: Optional[int] = None) -> str:
        """
        Get URL for accessing the file.
        
        For local storage, this returns the storage path.
        The actual URL construction should be handled by the web framework.
        """
        if not self.file_exists(storage_path):
            raise StorageException(f"File not found: {storage_path}")
        return storage_path


class DjangoStorageEngine(BaseStorageEngine):
    """
    Django storage engine that uses Django's storage backend system.
    
    This allows using django-storages for S3, Azure, GCS, etc.
    """

    def __init__(self, storage_backend=None):
        """
        Initialize Django storage engine.

        Args:
            storage_backend: Django storage backend instance.
                           If None, uses default file storage.
        """
        try:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
        except ImportError:
            raise StorageException("Django is required for DjangoStorageEngine")

        self.storage = storage_backend or default_storage
        self.ContentFile = ContentFile

    def save_file(
        self,
        content: bytes,
        original_name: str,
        storage_path: Optional[str] = None,
    ) -> FileUploadResult:
        """Save file using Django storage backend"""
        if storage_path is None:
            storage_path = self._generate_storage_path(original_name)

        try:
            content_file = self.ContentFile(content)
            # Django storage will handle the actual saving
            saved_path = self.storage.save(storage_path, content_file)
        except Exception as e:
            raise StorageException(f"Failed to save file: {e}")

        mime_type = detect_mime_type(content, original_name)
        size = len(content)

        return FileUploadResult(
            storage_path=saved_path,
            size=size,
            mime_type=mime_type,
        )

    def get_file(self, storage_path: str) -> bytes:
        """Read file content using Django storage backend"""
        try:
            with self.storage.open(storage_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            raise StorageException(f"File not found: {storage_path}")
        except Exception as e:
            raise StorageException(f"Failed to read file: {e}")

    def delete_file(self, storage_path: str) -> bool:
        """Delete file using Django storage backend"""
        try:
            if self.storage.exists(storage_path):
                self.storage.delete(storage_path)
                return True
            return False
        except Exception as e:
            raise StorageException(f"Failed to delete file: {e}")

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists using Django storage backend"""
        try:
            return self.storage.exists(storage_path)
        except Exception:
            return False

    def get_file_url(self, storage_path: str, expires_in: Optional[int] = None) -> str:
        """Get file URL using Django storage backend"""
        if not self.file_exists(storage_path):
            raise StorageException(f"File not found: {storage_path}")

        try:
            # For django-storages S3, this will generate signed URLs if configured
            return self.storage.url(storage_path)
        except Exception as e:
            raise StorageException(f"Failed to generate file URL: {e}")

    def get_file_path(self, storage_path: str) -> Path:
        """
        Get file path for local storage backends.
        
        Note: This only works for local file storage backends.
        For cloud storage, use get_file_url() instead.
        """
        if not hasattr(self.storage, 'path'):
            raise StorageException(
                "get_file_path() is only supported for local storage backends. "
                "Use get_file_url() for cloud storage."
            )
        
        if not self.file_exists(storage_path):
            raise StorageException(f"File not found: {storage_path}")
            
        try:
            return Path(self.storage.path(storage_path))
        except Exception as e:
            raise StorageException(f"Failed to get file path: {e}")


# For FastAPI, we keep the S3 implementation for direct use
class S3StorageEngine(BaseStorageEngine):
    """
    S3-compatible storage engine for cloud storage.
    
    Supports AWS S3 and S3-compatible services like MinIO, DigitalOcean Spaces, etc.
    Primarily for FastAPI applications.
    """

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        prefix: str = "attachments",
        public_read: bool = False,
    ):
        """
        Initialize S3 storage engine.

        Args:
            bucket_name: S3 bucket name
            region_name: AWS region name (default: us-east-1)
            endpoint_url: Custom S3 endpoint URL (for S3-compatible services)
            aws_access_key_id: AWS access key ID (if not using environment/IAM)
            aws_secret_access_key: AWS secret access key (if not using environment/IAM)
            prefix: Key prefix for all files (default: attachments)
            public_read: Whether to make files publicly readable (default: False)
        """
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
        except ImportError:
            raise StorageException(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            )

        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.public_read = public_read
        
        # Initialize S3 client
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        
        self.s3_client = session.client(
            "s3",
            endpoint_url=endpoint_url,
        )
        
        # Test connection and bucket access
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise StorageException(f"S3 bucket '{bucket_name}' not found")
            elif error_code == "403":
                raise StorageException(f"Access denied to S3 bucket '{bucket_name}'")
            else:
                raise StorageException(f"S3 connection error: {e}")
        except NoCredentialsError:
            raise StorageException("AWS credentials not found")

    def _get_s3_key(self, storage_path: str) -> str:
        """Convert storage path to S3 key"""
        if self.prefix:
            return f"{self.prefix}/{storage_path}"
        return storage_path

    def save_file(
        self,
        content: bytes,
        original_name: str,
        storage_path: Optional[str] = None,
    ) -> FileUploadResult:
        """Save file content to S3"""
        if storage_path is None:
            storage_path = self._generate_storage_path(original_name)

        s3_key = self._get_s3_key(storage_path)
        mime_type = detect_mime_type(content, original_name)
        size = len(content)

        try:
            extra_args = {
                "ContentType": mime_type,
            }
            
            if self.public_read:
                extra_args["ACL"] = "public-read"

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                **extra_args,
            )
        except Exception as e:
            raise StorageException(f"Failed to save file to S3: {e}")

        return FileUploadResult(
            storage_path=storage_path,
            size=size,
            mime_type=mime_type,
        )

    def get_file(self, storage_path: str) -> bytes:
        """Read file content from S3"""
        s3_key = self._get_s3_key(storage_path)

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response["Body"].read()
        except self.s3_client.exceptions.NoSuchKey:
            raise StorageException(f"File not found: {storage_path}")
        except Exception as e:
            raise StorageException(f"Failed to read file from S3: {e}")

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from S3"""
        s3_key = self._get_s3_key(storage_path)

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            raise StorageException(f"Failed to delete file from S3: {e}")

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in S3"""
        s3_key = self._get_s3_key(storage_path)

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            # For other errors, assume file doesn't exist
            return False

    def get_file_url(self, storage_path: str, expires_in: Optional[int] = None) -> str:
        """
        Get URL for accessing the file.
        
        Args:
            storage_path: Relative path to file
            expires_in: URL expiration time in seconds (default: 3600 for private, None for public)
            
        Returns:
            Pre-signed URL for private files or public URL for public files
        """
        s3_key = self._get_s3_key(storage_path)

        if not self.file_exists(storage_path):
            raise StorageException(f"File not found: {storage_path}")

        if self.public_read:
            # For public files, return the direct URL
            if hasattr(self.s3_client, '_endpoint') and self.s3_client._endpoint.host:
                endpoint = self.s3_client._endpoint.host
                return f"https://{endpoint}/{self.bucket_name}/{s3_key}"
            else:
                # Standard AWS S3 URL
                region = self.s3_client._client_config.region_name
                if region == "us-east-1":
                    return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
                else:
                    return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        else:
            # For private files, generate pre-signed URL
            if expires_in is None:
                expires_in = 3600  # 1 hour default

            try:
                return self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expires_in,
                )
            except Exception as e:
                raise StorageException(f"Failed to generate pre-signed URL: {e}")