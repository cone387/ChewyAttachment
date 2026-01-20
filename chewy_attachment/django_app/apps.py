"""Django app configuration for ChewyAttachment"""

from django.apps import AppConfig


class ChewyAttachmentConfig(AppConfig):
    """Django app configuration"""

    name = "chewy_attachment.django_app"
    label = "chewy_attachment_django_app"  # 明确指定应用标签
    verbose_name = "Chewy Attachment"
    default_auto_field = "django.db.models.BigAutoField"
