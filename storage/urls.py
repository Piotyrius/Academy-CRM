from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ArchiveViewSet, FileViewSet, download_file

router = DefaultRouter()
router.register(r"files", FileViewSet, basename="file")
router.register(r"archive/files", ArchiveViewSet, basename="archive-file")

urlpatterns = [
    path("", include(router.urls)),
    path("files/<uuid:pk>/download/", download_file, name="file-download"),
]








