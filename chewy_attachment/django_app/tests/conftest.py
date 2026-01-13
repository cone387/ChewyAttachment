"""pytest configuration for Django tests"""

from pathlib import Path

import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings for tests"""
    if settings.configured:
        return

    test_dir = Path(__file__).parent.absolute()
    storage_root = test_dir / "test_storage"

    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "rest_framework",
            "chewy_attachment.django_app",
        ],
        ROOT_URLCONF="chewy_attachment.django_app.urls",
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": [],
            "DEFAULT_PERMISSION_CLASSES": [],
        },
        CHEWY_ATTACHMENT={
            "STORAGE_ROOT": storage_root,
        },
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
        SECRET_KEY="test-secret-key-for-testing-only",
        BASE_DIR=test_dir,
    )

    django.setup()


def pytest_sessionfinish(session, exitstatus):
    """Clean up test storage after tests"""
    import shutil

    test_dir = Path(__file__).parent.absolute()
    storage_root = test_dir / "test_storage"
    if storage_root.exists():
        shutil.rmtree(storage_root)
