"""
Django storage configuration utilities for ChewyAttachment.

This module provides utilities to configure storage engines for Django applications,
with special support for S3 via django-storages.
"""

from typing import Optional, Type, Union

from django.conf import settings
from django.core.files.storage import Storage, default_storage

from ..core.storage import (
    BaseStorageEngine,
    DjangoStorageEngine,
    FileStorageEngine,
    StorageManager,
    StorageConfigProvider,
)


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


def get_storage_manager() -> StorageManager:
    """
    Get the configured StorageManager for ChewyAttachment.
    
    This function reads the CHEWY_ATTACHMENT settings and returns a properly
    configured StorageManager instance.
    
    Settings:
        CHEWY_ATTACHMENT["STORAGE_CONFIG_PROVIDER"]: Path to custom provider class
        CHEWY_ATTACHMENT["STORAGE_ROOT"]: Local storage root for fallback
    
    Returns:
        StorageManager: Configured storage manager instance
    """
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    
    # Check if a custom provider is configured
    provider_path = chewy_settings.get("STORAGE_CONFIG_PROVIDER")
    provider = None
    
    if provider_path:
        # Import and instantiate custom provider
        module_path, class_name = provider_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        provider_class = getattr(module, class_name)
        provider = provider_class()
    
    # Get local storage root for fallback
    from .models import get_storage_root
    local_storage_root = chewy_settings.get("STORAGE_ROOT") or get_storage_root()
    
    # Get or create the singleton manager
    manager = StorageManager.get_instance()
    
    # Update provider if configured
    if provider is not None:
        manager.set_provider(provider)
    
    # Set local storage root if not already set
    if manager._local_storage_root is None:
        manager._local_storage_root = local_storage_root
    
    return manager


def get_storage_engine_for_attachment(storage_config_id: Optional[str] = None) -> BaseStorageEngine:
    """
    Get storage engine for a specific attachment based on its storage_config_id.
    
    This function is used when reading/downloading attachments to get the
    correct storage engine based on where the file was originally stored.
    
    Args:
        storage_config_id: The storage configuration ID from the attachment.
                          If None, returns the default storage engine.
    
    Returns:
        BaseStorageEngine: Storage engine for the attachment
    """
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    engine_type = chewy_settings.get("STORAGE_ENGINE", "file")
    
    # If using multi-S3 storage (has provider configured or storage_config_id is provided)
    if storage_config_id or chewy_settings.get("STORAGE_CONFIG_PROVIDER"):
        manager = get_storage_manager()
        if storage_config_id:
            return manager.get_engine(storage_config_id)
        else:
            return manager.get_default_engine()
    
    # Fallback to legacy single storage engine
    return get_storage_engine()


def get_storage_engine_for_upload(
    storage_config_id: Optional[str] = None,
) -> tuple[BaseStorageEngine, Optional[str]]:
    """
    Get storage engine for uploading a new attachment.
    
    This function returns both the storage engine and the config_id that
    should be stored with the attachment record.
    
    Args:
        storage_config_id: Optional storage configuration ID to use.
                          If None, uses the default configuration.
    
    Returns:
        Tuple of (storage_engine, config_id_to_store)
        - config_id_to_store may be None for local storage
    """
    chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
    
    # If using multi-S3 storage
    if storage_config_id or chewy_settings.get("STORAGE_CONFIG_PROVIDER"):
        manager = get_storage_manager()
        return manager.get_engine_for_attachment(storage_config_id)
    
    # Fallback to legacy single storage engine
    engine = get_storage_engine()
    return engine, None