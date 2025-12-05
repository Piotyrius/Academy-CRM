from django.utils import timezone
from django.db.models import Q
from django.http import Http404
from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.exceptions import ValidationError, APIException
from academy_crm.google_drive import get_drive_service_or_none
from storage.models import FileObject, FileOwnerType, FileActivity
from .models import Work, WorkStatus
from .serializers import WorkSerializer


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'is_admin', False))


class WorkViewSet(viewsets.ModelViewSet):
    queryset = Work.objects.select_related('owner').all()
    serializer_class = WorkSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['owner', 'status', 'is_public']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return qs
        # Owners see own items; others see published + permitted
        return qs.filter(Q(owner=user) | Q(status=WorkStatus.PUBLISHED, is_public=True))
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")

    def perform_create(self, serializer):
        """
        Create gallery work with file upload to Google Drive.
        Google Drive storage is required - no fallback to local storage.
        """
        request = self.request
        user = request.user
        file = request.FILES.get("media")

        # Validate that a file was provided
        if not file:
            raise ValidationError({
                'media': 'A file must be uploaded for gallery works.'
            })

        # Validate that Google Drive is configured
        drive = get_drive_service_or_none()
        if not drive:
            exc = APIException(
                detail='Google Drive storage is required for file uploads. Please configure Google Drive integration.'
            )
            exc.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            raise exc

        # Upload file to Google Drive
        try:
            path_segments = ["academy-crm", "gallery", f"user-{user.id}"]
            folder_id = drive.ensure_folder_path(path_segments)

            uploaded = drive.upload_file(
                name=file.name,
                mime_type=file.content_type or "application/octet-stream",
                content=file.file,
                folder_id=folder_id,
            )

            file_obj = FileObject.objects.create(
                organization=getattr(user, "organization", None),
                owner_type=FileOwnerType.GALLERY_WORK,
                owner_id=None,
                drive_file_id=uploaded.file_id,
                drive_folder_id=uploaded.folder_id,
                logical_path="/".join(path_segments),
                mime_type=uploaded.mime_type,
                size=uploaded.size,
                original_name=uploaded.name,
                created_by=user,
                visibility="PUBLIC" if serializer.validated_data.get("is_public") else "PRIVATE",
            )
            instance = serializer.save(owner=user, file_object=file_obj)
            file_obj.owner_id = instance.id
            file_obj.save(update_fields=["owner_id"])

            FileActivity.objects.create(
                file=file_obj,
                user=user,
                action="uploaded",
                ip=request.META.get("REMOTE_ADDR"),
            )
        except Exception as e:
            # If upload fails, raise exception
            exc = APIException(
                detail=f'Failed to upload file to Google Drive: {str(e)}'
            )
            exc.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise exc

    @decorators.action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def publish(self, request, pk=None):
        work = self.get_object()
        user = request.user
        if not (getattr(user, 'is_admin', False) or work.owner_id == user.id):
            return response.Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        work.status = WorkStatus.PUBLISHED
        work.published_at = timezone.now()
        work.save(update_fields=['status', 'published_at'])
        return response.Response(WorkSerializer(work).data)


