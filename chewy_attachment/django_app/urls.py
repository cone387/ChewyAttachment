"""URL configuration for ChewyAttachment Django app"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import AttachmentViewSet

router = DefaultRouter()
router.register(r"files", AttachmentViewSet, basename="attachment")

urlpatterns = [
    path("", include(router.urls)),
]
