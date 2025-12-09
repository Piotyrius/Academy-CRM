from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.conf import settings
from rest_framework import permissions, response, status, viewsets, decorators

from academy_crm.cloudinary_service import get_cloudinary_service_or_none
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

    @decorators.action(detail=True, methods=["post"], url_path="archive", permission_classes=[IsAdminOrHighest])
    def archive(self, request, pk=None):
        """
        Archive a file by moving it to archive folder and marking as archived.
        """
        obj = self.get_object()
        cloudinary_service = get_cloudinary_service_or_none()
        if not cloudinary_service:
            return response.Response(
                {"detail": "Cloudinary is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Move file to archive folder
        if obj.cloudinary_public_id and not obj.is_archived:
            # Extract public_id without folder prefix
            public_id_parts = obj.cloudinary_public_id.split('/')
            file_name = public_id_parts[-1]
            
            # Get current folder
            current_folder = obj.cloudinary_folder or obj.logical_path
            
            # Move to archive folder
            cloudinary_service.move_file(
                public_id=file_name,
                from_folder=current_folder,
                to_folder="archive"
            )
            
            # Update FileObject
            obj.is_archived = True
            obj.deleted_at = timezone.now()
            obj.deleted_by = request.user if request.user.is_authenticated else None
            obj.cloudinary_folder = "archive"
            obj.cloudinary_public_id = f"archive/{file_name}"
            obj.cloudinary_url = cloudinary_service.get_file_url(
                obj.cloudinary_public_id,
                resource_type=obj.cloudinary_resource_type or "image"
            )
            obj.save(update_fields=["is_archived", "deleted_at", "deleted_by", "cloudinary_folder", "cloudinary_public_id", "cloudinary_url"])

            FileActivity.objects.create(
                file=obj,
                user=request.user if request.user.is_authenticated else None,
                action="archived",
                ip=request.META.get("REMOTE_ADDR"),
            )

        return response.Response(FileObjectSerializer(obj).data)


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
        cloudinary_service = get_cloudinary_service_or_none()
        if not cloudinary_service:
            return response.Response(
                {"detail": "Cloudinary is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        
        # Use Cloudinary URL for download
        if obj.cloudinary_url:
            FileActivity.objects.create(
                file=obj,
                user=request.user if request.user.is_authenticated else None,
                action="downloaded",
                ip=request.META.get("REMOTE_ADDR"),
            )
            # Redirect to Cloudinary URL for direct download
            return HttpResponseRedirect(obj.cloudinary_url)
        else:
            return response.Response(
                {"detail": "File URL not available."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @decorators.action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        obj = self.get_object()
        cloudinary_service = get_cloudinary_service_or_none()
        if not cloudinary_service:
            return response.Response(
                {"detail": "Cloudinary is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Move file back from archive folder to original folder
        if obj.cloudinary_public_id and obj.cloudinary_folder:
            # Extract public_id without folder prefix
            public_id_parts = obj.cloudinary_public_id.split('/')
            file_name = public_id_parts[-1]
            
            # Get original folder from logical_path or cloudinary_folder
            original_folder = obj.logical_path or obj.cloudinary_folder
            # Remove 'archive/' prefix if present
            if original_folder.startswith('archive/'):
                original_folder = original_folder.replace('archive/', '', 1)
            
            # Move from archive to original folder
            cloudinary_service.move_file(
                public_id=file_name,
                from_folder="archive",
                to_folder=original_folder
            )
            
            # Update FileObject with new folder and URL
            obj.cloudinary_folder = original_folder
            obj.cloudinary_public_id = f"{original_folder}/{file_name}"
            obj.cloudinary_url = cloudinary_service.get_file_url(
                obj.cloudinary_public_id,
                resource_type=obj.cloudinary_resource_type or "image"
            )

        obj.is_archived = False
        obj.deleted_at = None
        obj.deleted_by = None
        obj.save(update_fields=["is_archived", "deleted_at", "deleted_by", "cloudinary_folder", "cloudinary_public_id", "cloudinary_url"])

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

    cloudinary_service = get_cloudinary_service_or_none()
    if not cloudinary_service:
        return response.Response(
            {"detail": "Cloudinary is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Use Cloudinary URL for download
    if obj.cloudinary_url:
        FileActivity.objects.create(
            file=obj,
            user=request.user if request.user.is_authenticated else None,
            action="downloaded",
            ip=request.META.get("REMOTE_ADDR"),
        )
        # Redirect to Cloudinary URL for direct download
        return HttpResponseRedirect(obj.cloudinary_url)
    else:
        return response.Response(
            {"detail": "File URL not available."},
            status=status.HTTP_404_NOT_FOUND,
        )


