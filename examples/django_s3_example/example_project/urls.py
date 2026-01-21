"""
URL configuration for Django S3 example project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/attachments/', include('chewy_attachment.django_app.urls')),
]