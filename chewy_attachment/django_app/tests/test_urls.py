"""Test URL configuration"""

from django.urls import include, path

urlpatterns = [
    path("api/attachments/", include("chewy_attachment.django_app.urls")),
]