"""Django app configuration for ChewyAttachment"""

from django.apps import AppConfig


class ChewyAttachmentConfig(AppConfig):
    """Django app configuration"""

    name = "chewy_attachment.django_app"
    verbose_name = "Chewy Attachment"
    default_auto_field = "django.db.models.BigAutoField"
