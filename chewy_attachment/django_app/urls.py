"""URL configuration for ChewyAttachment Django app"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import AttachmentViewSet, HealthCheckView, StorageStatsView

router = DefaultRouter()
router.register(r"files", AttachmentViewSet, basename="attachment")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("stats/", StorageStatsView.as_view(), name="storage-stats"),
]
