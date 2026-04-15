"""
Django settings for S3 storage example.

This example shows how to configure ChewyAttachment with AWS S3 storage
using django-storages.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-example-key-change-in-production"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "storages",  # django-storages
    # ChewyAttachment
    "chewy_attachment.django_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "example_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Internationalization
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# ============================================================================
# AWS S3 Configuration
# ============================================================================

# AWS credentials (better to use environment variables or IAM roles)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "your-bucket-name")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

# S3 settings
AWS_S3_CUSTOM_DOMAIN = None  # Use CloudFront domain if you have one
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",  # 1 day cache
}

# File storage settings
AWS_DEFAULT_ACL = "private"  # Files are private by default
AWS_S3_FILE_OVERWRITE = False  # Don't overwrite files with same name
AWS_QUERYSTRING_AUTH = True  # Use signed URLs for private files
AWS_QUERYSTRING_EXPIRE = 3600  # Signed URLs expire in 1 hour

# Use S3 for media files
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Optional: Use S3 for static files too
# STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

# Media files URL (will be S3 URLs)
if AWS_S3_CUSTOM_DOMAIN:
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
else:
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"

# ============================================================================
# ChewyAttachment Configuration
# ============================================================================

CHEWY_ATTACHMENT = {
    # Use Django's default storage (which we configured to use S3)
    "STORAGE_ENGINE": "django",
    
    # File size limits
    "MAX_FILE_SIZE": 10 * 1024 * 1024,  # 10MB
    
    # Allowed file types
    "ALLOWED_EXTENSIONS": [
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        # Documents
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".rtf", ".odt", ".ods", ".odp",
        # Archives
        ".zip", ".rar", ".7z", ".tar", ".gz",
        # Others
        ".mp4", ".mp3", ".wav", ".avi", ".mov",
    ],
    
    # Permission settings
    "DEFAULT_PERMISSION": "private",  # Files are private by default
    "ALLOW_ANONYMOUS_UPLOAD": False,  # Only authenticated users can upload
    "ALLOW_ANONYMOUS_ACCESS": False,  # Only authenticated users can access
    
    # URL settings
    "URL_EXPIRES_IN": 3600,  # Signed URLs expire in 1 hour
}

# ============================================================================
# Alternative: Custom S3 Storage Class
# ============================================================================

# If you need more control, you can create a custom storage class:
"""
from storages.backends.s3boto3 import S3Boto3Storage

class MediaStorage(S3Boto3Storage):
    bucket_name = AWS_STORAGE_BUCKET_NAME
    location = 'media'  # Store media files in 'media' folder
    default_acl = 'private'
    file_overwrite = False
    custom_domain = AWS_S3_CUSTOM_DOMAIN

# Then use it in CHEWY_ATTACHMENT:
CHEWY_ATTACHMENT = {
    "STORAGE_ENGINE": "django",
    "DJANGO_STORAGE_CLASS": "path.to.MediaStorage",
    # ... other settings
}
"""