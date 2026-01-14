"""Django app configuration for ChewyAttachment"""

from django.apps import AppConfig


class ChewyAttachmentConfig(AppConfig):
    """Django app configuration"""

    name = "chewy_attachment.django_app"
    verbose_name = "Chewy Attachment"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Called when the app is ready.
        Apply custom table name from settings if configured.
        """
        from django.conf import settings
        from .models import Attachment

        chewy_settings = getattr(settings, "CHEWY_ATTACHMENT", {})
        custom_table_name = chewy_settings.get("TABLE_NAME")

        if custom_table_name:
            # Dynamically set the table name
            Attachment._meta.db_table = custom_table_name
