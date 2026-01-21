"""
Django storage configuration utilities for ChewyAttachment.

This module provides utilities to configure storage engines for Django applications,
with special support for S3 via django-storages.
"""

from typing import Optional, Type, Union

from django.conf import settings
from django.core.files.storage import Storage, default_storage

from ..core.storage import BaseStorageEngine, DjangoStorageEngine, FileStorageEngine


def get_storage_engine() -> BaseStorageEngine:
    """
    Get the configured storage engine for ChewyAttachment.
    
    This function reads the CHEWY_ATTACHMENT settings and returns the appropriate
    storage engine instance.
    
    Returns:
        BaseStorageEngine: Configured storage engine instance
    """
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    engine_type = chewy_settings.get("STORAGE_ENGINE", "file")
    
    if engine_type == "django":
        # Use Django's storage system (supports django-storages)
        storage_class = chewy_settings.get("DJANGO_STORAGE_CLASS")
        
        if storage_class:
            # Use custom storage class
            if isinstance(storage_class, str):
                # Import storage class from string
                module_path, class_name = storage_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                storage_class = getattr(module, class_name)
            
            storage_backend = storage_class()
        else:
            # Use default storage (configured in Django settings)
            storage_backend = default_storage
        
        return DjangoStorageEngine(storage_backend)
    
    elif engine_type == "file":
        # Use local file storage
        from .models import get_storage_root
        storage_root = chewy_settings.get("STORAGE_ROOT") or get_storage_root()
        return FileStorageEngine(storage_root)
    
    else:
        raise ValueError(f"Unknown storage engine type: {engine_type}")


def get_s3_storage_class():
    """
    Get a pre-configured S3 storage class for ChewyAttachment.
    
    This creates a custom S3Boto3Storage class with ChewyAttachment-specific
    settings applied.
    
    Returns:
        Type[S3Boto3Storage]: Configured S3 storage class
    """
    try:
        from storages.backends.s3boto3 import S3Boto3Storage
    except ImportError:
        raise ImportError(
            "django-storages is required for S3 storage. "
            "Install with: pip install 'chewy-attachment[django-s3]'"
        )
    
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    
    class ChewyS3Storage(S3Boto3Storage):
        """Custom S3 storage for ChewyAttachment"""
        
        # Use settings from CHEWY_ATTACHMENT or fall back to AWS_* settings
        bucket_name = chewy_settings.get("S3_BUCKET_NAME") or getattr(
            settings, "AWS_STORAGE_BUCKET_NAME", None
        )
        region_name = chewy_settings.get("S3_REGION_NAME") or getattr(
            settings, "AWS_S3_REGION_NAME", "us-east-1"
        )
        
        # File organization
        location = chewy_settings.get("S3_LOCATION", "attachments")
        
        # Security settings
        default_acl = chewy_settings.get("S3_DEFAULT_ACL") or getattr(
            settings, "AWS_DEFAULT_ACL", "private"
        )
        
        # File handling
        file_overwrite = chewy_settings.get("S3_FILE_OVERWRITE", False)
        
        # URL settings
        querystring_auth = chewy_settings.get("S3_QUERYSTRING_AUTH") or getattr(
            settings, "AWS_QUERYSTRING_AUTH", True
        )
        querystring_expire = chewy_settings.get("S3_QUERYSTRING_EXPIRE") or getattr(
            settings, "AWS_QUERYSTRING_EXPIRE", 3600
        )
        
        # Custom domain (CloudFront)
        custom_domain = chewy_settings.get("S3_CUSTOM_DOMAIN") or getattr(
            settings, "AWS_S3_CUSTOM_DOMAIN", None
        )
        
        # Object parameters
        object_parameters = chewy_settings.get("S3_OBJECT_PARAMETERS") or getattr(
            settings, "AWS_S3_OBJECT_PARAMETERS", {"CacheControl": "max-age=86400"}
        )
    
    return ChewyS3Storage


def configure_s3_storage() -> DjangoStorageEngine:
    """
    Configure and return a DjangoStorageEngine with S3 storage.
    
    This is a convenience function that creates a properly configured
    S3 storage engine for ChewyAttachment.
    
    Returns:
        DjangoStorageEngine: Storage engine configured for S3
    """
    storage_class = get_s3_storage_class()
    storage_backend = storage_class()
    return DjangoStorageEngine(storage_backend)


def validate_s3_configuration() -> bool:
    """
    Validate S3 configuration settings.
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    try:
        import boto3
        from storages.backends.s3boto3 import S3Boto3Storage
    except ImportError:
        return False
    
    # Check required settings
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not bucket_name:
        chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
        bucket_name = chewy_settings.get("S3_BUCKET_NAME")
    
    if not bucket_name:
        return False
    
    # Try to create storage instance
    try:
        storage_class = get_s3_storage_class()
        storage = storage_class()
        # Test connection by checking if bucket exists
        storage.connection.meta.client.head_bucket(Bucket=bucket_name)
        return True
    except Exception:
        return False


# Convenience function for backward compatibility
def get_django_storage_engine(storage_backend: Optional[Storage] = None) -> DjangoStorageEngine:
    """
    Create a DjangoStorageEngine with optional custom storage backend.
    
    Args:
        storage_backend: Optional Django storage backend. If None, uses default_storage.
    
    Returns:
        DjangoStorageEngine: Configured storage engine
    """
    return DjangoStorageEngine(storage_backend or default_storage)