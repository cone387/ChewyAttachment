"""File storage engines for ChewyAttachment"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional, Union, Dict

from .exceptions import StorageException
from .schemas import FileUploadResult, S3ConfigSchema, MigrationResult, MigrationSummary
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
        try:
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
        self._endpoint_url = endpoint_url
        self._region_name = region_name
        
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

        if self.public_read:
            # For public files, return the direct URL
            endpoint_url = getattr(self, '_endpoint_url', None)
            if endpoint_url:
                # Custom endpoint (MinIO, etc.) — use it directly
                base = endpoint_url.rstrip("/")
                return f"{base}/{self.bucket_name}/{s3_key}"
            else:
                # Standard AWS S3 URL
                region = self._region_name
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

    @classmethod
    def from_config(cls, config: S3ConfigSchema) -> "S3StorageEngine":
        """
        Create S3StorageEngine from S3ConfigSchema.
        
        Args:
            config: S3 configuration schema
            
        Returns:
            Configured S3StorageEngine instance
        """
        return cls(
            bucket_name=config.bucket_name,
            region_name=config.region,
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            prefix=config.prefix,
            public_read=config.public_read,
        )


class StorageConfigProvider(ABC):
    """
    Abstract base class for storage configuration providers.
    
    This interface allows applications to provide S3 configurations from
    any source (database, config files, environment variables, etc.)
    without ChewyAttachment needing to know the implementation details.
    
    The provider is responsible for:
    - Managing S3 configuration storage (including sensitive credentials)
    - Providing configurations by ID
    - Providing a default configuration for uploads without explicit config_id
    
    Example implementation:
    
        class MyStorageConfigProvider(StorageConfigProvider):
            def get_config(self, config_id: str) -> S3ConfigSchema:
                config = MyS3ConfigModel.objects.get(id=config_id)
                return S3ConfigSchema(
                    config_id=str(config.id),
                    bucket_name=config.bucket,
                    access_key=decrypt(config.access_key),
                    secret_key=decrypt(config.secret_key),
                    region=config.region,
                    endpoint_url=config.endpoint,
                )
            
            def get_default_config(self) -> Optional[S3ConfigSchema]:
                return self.get_config("default")
    """
    
    @abstractmethod
    def get_config(self, config_id: str) -> S3ConfigSchema:
        """
        Get S3 configuration by ID.
        
        Args:
            config_id: Unique identifier for the configuration
            
        Returns:
            S3ConfigSchema with complete configuration including credentials
            
        Raises:
            StorageException: If configuration not found or invalid
        """
        pass
    
    @abstractmethod
    def get_default_config(self) -> Optional[S3ConfigSchema]:
        """
        Get the default S3 configuration.
        
        This is used when no config_id is specified during upload.
        
        Returns:
            S3ConfigSchema for default configuration, or None if no default is set
        """
        pass
    
    def list_configs(self) -> list:
        """
        List available configuration IDs.
        
        Override this method to provide a list of available configurations.
        Default implementation returns an empty list.
        
        Returns:
            List of configuration IDs
        """
        return []


class EnvironmentStorageConfigProvider(StorageConfigProvider):
    """
    Storage configuration provider that reads from environment variables.
    
    This is the default provider for simple setups and testing.
    It supports a single S3 configuration from environment variables.
    
    Environment variables:
        - CHEWY_S3_BUCKET_NAME: S3 bucket name (required)
        - CHEWY_S3_ACCESS_KEY: AWS access key ID (required)
        - CHEWY_S3_SECRET_KEY: AWS secret access key (required)
        - CHEWY_S3_REGION: AWS region (default: us-east-1)
        - CHEWY_S3_ENDPOINT_URL: Custom S3 endpoint URL (optional, for MinIO etc.)
        - CHEWY_S3_PREFIX: Key prefix for files (default: attachments)
        - CHEWY_S3_PUBLIC_READ: Whether files are public (default: false)
    
    For testing with MinIO:
        export CHEWY_S3_ENDPOINT_URL=http://localhost:9000
        export CHEWY_S3_BUCKET_NAME=test-bucket
        export CHEWY_S3_ACCESS_KEY=minioadmin
        export CHEWY_S3_SECRET_KEY=minioadmin123
    """
    
    DEFAULT_CONFIG_ID = "default"
    
    def get_config(self, config_id: str) -> S3ConfigSchema:
        """Get configuration from environment variables."""
        if config_id != self.DEFAULT_CONFIG_ID:
            raise StorageException(
                f"Configuration '{config_id}' not found. "
                f"EnvironmentStorageConfigProvider only supports '{self.DEFAULT_CONFIG_ID}' config."
            )
        
        config = self.get_default_config()
        if config is None:
            raise StorageException(
                "S3 configuration not found in environment variables. "
                "Please set CHEWY_S3_BUCKET_NAME, CHEWY_S3_ACCESS_KEY, and CHEWY_S3_SECRET_KEY."
            )
        return config
    
    def get_default_config(self) -> Optional[S3ConfigSchema]:
        """Get default configuration from environment variables."""
        bucket_name = os.getenv("CHEWY_S3_BUCKET_NAME")
        access_key = os.getenv("CHEWY_S3_ACCESS_KEY")
        secret_key = os.getenv("CHEWY_S3_SECRET_KEY")
        
        if not all([bucket_name, access_key, secret_key]):
            return None
        
        return S3ConfigSchema(
            config_id=self.DEFAULT_CONFIG_ID,
            bucket_name=bucket_name,
            access_key=access_key,
            secret_key=secret_key,
            region=os.getenv("CHEWY_S3_REGION", "us-east-1"),
            endpoint_url=os.getenv("CHEWY_S3_ENDPOINT_URL"),
            prefix=os.getenv("CHEWY_S3_PREFIX", "attachments"),
            public_read=os.getenv("CHEWY_S3_PUBLIC_READ", "").lower() in ("true", "1", "yes"),
        )
    
    def list_configs(self) -> list:
        """List available configurations."""
        if self.get_default_config() is not None:
            return [self.DEFAULT_CONFIG_ID]
        return []


class StorageManager:
    """
    Manager for multiple storage configurations.
    
    This class manages multiple S3 storage engines, creating them on-demand
    based on configuration IDs. It uses a provider pattern to obtain
    configurations, allowing applications to store credentials securely.
    
    Features:
    - Lazy initialization of storage engines
    - Caching of created engines to avoid repeated initialization
    - Thread-safe engine creation
    - Support for local file storage as fallback
    
    Usage:
        # With default environment provider
        manager = StorageManager()
        
        # With custom provider
        manager = StorageManager(provider=MyStorageConfigProvider())
        
        # Get storage engine for a specific config
        engine = manager.get_engine("my-s3-config")
        
        # Get default storage engine
        engine = manager.get_default_engine()
    """
    
    _instance: Optional["StorageManager"] = None
    _lock = Lock()
    
    def __init__(
        self,
        provider: Optional[StorageConfigProvider] = None,
        local_storage_root: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize StorageManager.
        
        Args:
            provider: Storage configuration provider. If None, uses EnvironmentStorageConfigProvider.
            local_storage_root: Root directory for local file storage fallback.
        """
        self._provider = provider or EnvironmentStorageConfigProvider()
        self._local_storage_root = Path(local_storage_root) if local_storage_root else None
        self._engines: Dict[str, BaseStorageEngine] = {}
        self._engines_lock = Lock()
    
    @classmethod
    def get_instance(cls) -> "StorageManager":
        """
        Get the singleton instance of StorageManager.
        
        Returns:
            StorageManager singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def set_instance(cls, manager: "StorageManager") -> None:
        """
        Set the singleton instance of StorageManager.
        
        This is useful for configuring a custom provider at application startup.
        
        Args:
            manager: StorageManager instance to use as singleton
        """
        with cls._lock:
            cls._instance = manager
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        with cls._lock:
            cls._instance = None
    
    @property
    def provider(self) -> StorageConfigProvider:
        """Get the storage configuration provider."""
        return self._provider
    
    def set_provider(self, provider: StorageConfigProvider) -> None:
        """
        Set a new storage configuration provider.
        
        This will clear all cached engines.
        
        Args:
            provider: New storage configuration provider
        """
        with self._engines_lock:
            self._provider = provider
            self._engines.clear()
    
    def get_engine(self, config_id: str) -> BaseStorageEngine:
        """
        Get storage engine for a specific configuration.
        
        Engines are cached after first creation.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Storage engine for the configuration
            
        Raises:
            StorageException: If configuration not found or engine creation fails
        """
        if config_id in self._engines:
            return self._engines[config_id]
        
        with self._engines_lock:
            # Double-check after acquiring lock
            if config_id in self._engines:
                return self._engines[config_id]
            
            config = self._provider.get_config(config_id)
            engine = S3StorageEngine.from_config(config)
            self._engines[config_id] = engine
            return engine
    
    def get_default_engine(self) -> BaseStorageEngine:
        """
        Get the default storage engine.
        
        If no S3 configuration is available, falls back to local file storage
        if local_storage_root is configured.
        
        Returns:
            Default storage engine
            
        Raises:
            StorageException: If no default configuration and no local storage fallback
        """
        config = self._provider.get_default_config()
        
        if config is not None:
            return self.get_engine(config.config_id)
        
        # Fallback to local storage if configured
        if self._local_storage_root is not None:
            if "local" not in self._engines:
                with self._engines_lock:
                    if "local" not in self._engines:
                        self._engines["local"] = FileStorageEngine(self._local_storage_root)
            return self._engines["local"]
        
        raise StorageException(
            "No default S3 configuration found and no local storage fallback configured. "
            "Please configure a StorageConfigProvider or set local_storage_root."
        )
    
    def get_engine_for_attachment(
        self,
        storage_config_id: Optional[str] = None,
    ) -> tuple[BaseStorageEngine, Optional[str]]:
        """
        Get storage engine for an attachment operation.
        
        This method determines which storage engine to use based on the
        provided config_id, returning both the engine and the actual
        config_id that should be stored with the attachment.
        
        Args:
            storage_config_id: Optional configuration ID. If None, uses default.
            
        Returns:
            Tuple of (storage_engine, config_id_to_store)
            - config_id_to_store is None for local storage
        """
        if storage_config_id:
            engine = self.get_engine(storage_config_id)
            return engine, storage_config_id
        
        config = self._provider.get_default_config()
        if config is not None:
            engine = self.get_engine(config.config_id)
            return engine, config.config_id
        
        # Fallback to local storage
        if self._local_storage_root is not None:
            engine = self.get_default_engine()
            return engine, None
        
        raise StorageException(
            "No storage configuration available. "
            "Please provide a config_id or configure a default storage."
        )
    
    def clear_cache(self) -> None:
        """Clear all cached storage engines."""
        with self._engines_lock:
            self._engines.clear()
    
    def list_configs(self) -> list:
        """List available configuration IDs from the provider."""
        return self._provider.list_configs()


class StorageMigrator:
    """
    Migrator for transferring files between different storage configurations.
    
    This class handles the migration of files from one storage configuration
    to another, supporting both single file and batch migrations.
    
    Features:
    - Single file migration
    - Batch migration with progress callback
    - Optional source file deletion after successful migration
    - Detailed migration results and summary
    - Support for migrating between any storage types (local, S3, etc.)
    
    Usage:
        # Create migrator
        manager = StorageManager.get_instance()
        migrator = StorageMigrator(manager)
        
        # Migrate a single file
        result = migrator.migrate_file(
            attachment_id="123",
            original_name="document.pdf",
            source_config_id="old-s3",
            source_storage_path="2026/01/01/abc.pdf",
            target_config_id="new-s3",
            delete_source=True,
        )
        
        # Batch migration with callback
        def on_progress(current, total, result):
            print(f"Migrated {current}/{total}: {result.original_name}")
        
        summary = migrator.migrate_batch(
            attachments=[...],
            target_config_id="new-s3",
            delete_source=True,
            on_progress=on_progress,
        )
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Initialize StorageMigrator.
        
        Args:
            storage_manager: StorageManager instance for accessing storage engines
        """
        self._manager = storage_manager
    
    def migrate_file(
        self,
        attachment_id: str,
        original_name: str,
        source_config_id: Optional[str],
        source_storage_path: str,
        target_config_id: str,
        delete_source: bool = False,
        new_storage_path: Optional[str] = None,
    ) -> MigrationResult:
        """
        Migrate a single file from source storage to target storage.
        
        Args:
            attachment_id: ID of the attachment being migrated
            original_name: Original filename (used for generating new path if needed)
            source_config_id: Source storage configuration ID (None for local storage)
            source_storage_path: Current storage path of the file
            target_config_id: Target storage configuration ID
            delete_source: Whether to delete the source file after successful migration
            new_storage_path: Optional custom path in target storage. If None, generates new path.
        
        Returns:
            MigrationResult with migration details
        """
        result = MigrationResult(
            attachment_id=attachment_id,
            original_name=original_name,
            source_config_id=source_config_id,
            target_config_id=target_config_id,
            old_storage_path=source_storage_path,
        )
        
        try:
            # Get source storage engine
            if source_config_id:
                source_engine = self._manager.get_engine(source_config_id)
            else:
                source_engine = self._manager.get_default_engine()
            
            # Get target storage engine
            target_engine = self._manager.get_engine(target_config_id)
            
            # Check if source file exists
            if not source_engine.file_exists(source_storage_path):
                result.error = f"Source file not found: {source_storage_path}"
                return result
            
            # Read file content from source
            content = source_engine.get_file(source_storage_path)
            
            # Save to target storage
            upload_result = target_engine.save_file(
                content=content,
                original_name=original_name,
                storage_path=new_storage_path,
            )
            
            result.new_storage_path = upload_result.storage_path
            result.success = True
            
            # Delete source file if requested
            if delete_source:
                try:
                    source_engine.delete_file(source_storage_path)
                    result.source_deleted = True
                except Exception as e:
                    # Migration succeeded but source deletion failed
                    # This is not a critical error, just log it
                    result.error = f"Migration succeeded but failed to delete source: {e}"
            
            return result
            
        except StorageException as e:
            result.error = str(e)
            return result
        except Exception as e:
            result.error = f"Unexpected error: {e}"
            return result
    
    def migrate_batch(
        self,
        attachments: list,
        target_config_id: str,
        delete_source: bool = False,
        on_progress: Optional[callable] = None,
        on_error: Optional[callable] = None,
        stop_on_error: bool = False,
    ) -> MigrationSummary:
        """
        Migrate multiple files to a target storage configuration.
        
        Args:
            attachments: List of attachment objects or dicts with required fields:
                        - id: Attachment ID
                        - original_name: Original filename
                        - storage_config_id: Current storage configuration ID
                        - storage_path: Current storage path
            target_config_id: Target storage configuration ID
            delete_source: Whether to delete source files after successful migration
            on_progress: Optional callback function(current: int, total: int, result: MigrationResult)
            on_error: Optional callback function(result: MigrationResult)
            stop_on_error: Whether to stop migration on first error
        
        Returns:
            MigrationSummary with overall migration statistics and individual results
        """
        summary = MigrationSummary()
        total = len(attachments)
        
        for index, attachment in enumerate(attachments, 1):
            # Extract attachment info (support both objects and dicts)
            if isinstance(attachment, dict):
                attachment_id = attachment.get("id", "")
                original_name = attachment.get("original_name", "")
                source_config_id = attachment.get("storage_config_id")
                source_storage_path = attachment.get("storage_path", "")
            else:
                attachment_id = getattr(attachment, "id", "")
                original_name = getattr(attachment, "original_name", "")
                source_config_id = getattr(attachment, "storage_config_id", None)
                source_storage_path = getattr(attachment, "storage_path", "")
            
            # Skip if already in target storage
            if source_config_id == target_config_id:
                result = MigrationResult(
                    attachment_id=str(attachment_id),
                    original_name=original_name,
                    source_config_id=source_config_id,
                    target_config_id=target_config_id,
                    old_storage_path=source_storage_path,
                    new_storage_path=source_storage_path,
                    success=True,
                    error="Skipped: already in target storage",
                )
                summary.add_result(result)
                
                if on_progress:
                    on_progress(index, total, result)
                
                continue
            
            # Migrate the file
            result = self.migrate_file(
                attachment_id=str(attachment_id),
                original_name=original_name,
                source_config_id=source_config_id,
                source_storage_path=source_storage_path,
                target_config_id=target_config_id,
                delete_source=delete_source,
            )
            
            summary.add_result(result)
            
            # Call progress callback
            if on_progress:
                on_progress(index, total, result)
            
            # Handle errors
            if not result.success:
                if on_error:
                    on_error(result)
                
                if stop_on_error:
                    break
        
        return summary
    
    def sync_to_target(
        self,
        attachments: list,
        target_config_id: str,
        update_callback: Optional[callable] = None,
        delete_source: bool = False,
        on_progress: Optional[callable] = None,
    ) -> MigrationSummary:
        """
        Sync attachments to a target storage and update their records.
        
        This is a higher-level method that:
        1. Migrates files to the target storage
        2. Calls update_callback to update attachment records with new storage info
        
        Args:
            attachments: List of attachment objects or dicts
            target_config_id: Target storage configuration ID
            update_callback: Callback to update attachment record after migration.
                           Signature: update_callback(attachment_id, new_storage_path, new_config_id)
            delete_source: Whether to delete source files after successful migration
            on_progress: Optional progress callback
        
        Returns:
            MigrationSummary with migration results
        
        Example:
            def update_attachment(attachment_id, new_path, new_config_id):
                Attachment.objects.filter(id=attachment_id).update(
                    storage_path=new_path,
                    storage_config_id=new_config_id,
                )
            
            summary = migrator.sync_to_target(
                attachments=Attachment.objects.filter(owner_id=user_id),
                target_config_id="new-s3",
                update_callback=update_attachment,
                delete_source=True,
            )
        """
        summary = MigrationSummary()
        total = len(attachments)
        
        for index, attachment in enumerate(attachments, 1):
            # Extract attachment info
            if isinstance(attachment, dict):
                attachment_id = attachment.get("id", "")
                original_name = attachment.get("original_name", "")
                source_config_id = attachment.get("storage_config_id")
                source_storage_path = attachment.get("storage_path", "")
            else:
                attachment_id = getattr(attachment, "id", "")
                original_name = getattr(attachment, "original_name", "")
                source_config_id = getattr(attachment, "storage_config_id", None)
                source_storage_path = getattr(attachment, "storage_path", "")
            
            # Skip if already in target storage
            if source_config_id == target_config_id:
                result = MigrationResult(
                    attachment_id=str(attachment_id),
                    original_name=original_name,
                    source_config_id=source_config_id,
                    target_config_id=target_config_id,
                    old_storage_path=source_storage_path,
                    new_storage_path=source_storage_path,
                    success=True,
                    error="Skipped: already in target storage",
                )
                summary.add_result(result)
                
                if on_progress:
                    on_progress(index, total, result)
                
                continue
            
            # Migrate the file
            result = self.migrate_file(
                attachment_id=str(attachment_id),
                original_name=original_name,
                source_config_id=source_config_id,
                source_storage_path=source_storage_path,
                target_config_id=target_config_id,
                delete_source=delete_source,
            )
            
            # Update attachment record if migration succeeded
            if result.success and update_callback and result.new_storage_path:
                try:
                    update_callback(
                        str(attachment_id),
                        result.new_storage_path,
                        target_config_id,
                    )
                except Exception as e:
                    # Record update failed, but file was migrated
                    result.error = f"File migrated but record update failed: {e}"
            
            summary.add_result(result)
            
            if on_progress:
                on_progress(index, total, result)
        
        return summary