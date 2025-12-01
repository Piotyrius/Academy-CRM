from django.http import Http404, HttpResponse
from django.utils import timezone
from django.conf import settings
from rest_framework import permissions, response, status, viewsets, decorators

from academy_crm.google_drive import get_drive_service_or_none
from .models import FileObject, FileActivity
from .serializers import FileObjectSerializer


class IsAdminOrHighest(permissions.BasePermission):
    """
    Simple permission that reuses existing user flags for highest-rank users.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (getattr(user, "is_admin", False) or getattr(user, "is_superuser", False))
        )


class FileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for files (used mostly for archived/admin browsing).
    """

    queryset = FileObject.objects.all().select_related("organization", "created_by")
    serializer_class = FileObjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["owner_type", "owner_id", "is_archived"]
    ordering = ["-created_at"]


class ArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only archive browser for FileObject records.
    """

    queryset = FileObject.objects.filter(is_archived=True).select_related(
        "organization", "created_by"
    )
    serializer_class = FileObjectSerializer
    permission_classes = [IsAdminOrHighest]
    filterset_fields = ["owner_type", "owner_id", "deleted_by"]
    ordering = ["-deleted_at"]

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise Http404("Archived file not found.")

    @decorators.action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        obj = self.get_object()
        drive = get_drive_service_or_none()
        if not drive:
            return response.Response(
                {"detail": "Google Drive is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        content, mime_type = drive.download_file(obj.drive_file_id)
        FileActivity.objects.create(
            file=obj,
            user=request.user if request.user.is_authenticated else None,
            action="downloaded",
            ip=request.META.get("REMOTE_ADDR"),
        )
        resp = HttpResponse(content, content_type=mime_type)
        resp["Content-Disposition"] = f'attachment; filename="{obj.original_name}"'
        return resp

    @decorators.action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        obj = self.get_object()
        drive = get_drive_service_or_none()
        if not drive:
            return response.Response(
                {"detail": "Google Drive is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # For now we only move back to the stored ``drive_folder_id``; in the
        # future ``logical_path`` can be used to restore exact nested folders.
        target_parent = obj.drive_folder_id or settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
        if target_parent:
            drive.move_file(obj.drive_file_id, target_parent)

        obj.is_archived = False
        obj.deleted_at = None
        obj.deleted_by = None
        obj.save(update_fields=["is_archived", "deleted_at", "deleted_by"])

        FileActivity.objects.create(
            file=obj,
            user=request.user if request.user.is_authenticated else None,
            action="restored",
            ip=request.META.get("REMOTE_ADDR"),
        )

        return response.Response(FileObjectSerializer(obj).data)


@decorators.api_view(["GET"])
@decorators.permission_classes([permissions.IsAuthenticated])
def download_file(request, pk):
    """
    Generic download endpoint for non-archived files.
    """
    try:
        obj = FileObject.objects.get(pk=pk, is_archived=False)
    except FileObject.DoesNotExist:
        raise Http404("File not found.")

    drive = get_drive_service_or_none()
    if not drive:
        return response.Response(
            {"detail": "Google Drive is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    content, mime_type = drive.download_file(obj.drive_file_id)
    FileActivity.objects.create(
        file=obj,
        user=request.user if request.user.is_authenticated else None,
        action="downloaded",
        ip=request.META.get("REMOTE_ADDR"),
    )
    resp = HttpResponse(content, content_type=mime_type)
    resp["Content-Disposition"] = f'attachment; filename="{obj.original_name}"'
    return resp


