import logging
from django.utils import timezone
from django.db.models import Q
from django.http import Http404
from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.exceptions import ValidationError, APIException
from googleapiclient.errors import HttpError
from academy_crm.google_drive import get_drive_service_or_none
from storage.models import FileObject, FileOwnerType, FileActivity
from .models import Work, WorkStatus
from .serializers import WorkSerializer

logger = logging.getLogger(__name__)


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
        
        # Log what files are being sent from frontend
        logger.info(
            f"Gallery work upload request from user {user.id}: "
            f"FILES keys: {list(request.FILES.keys())}, "
            f"DATA keys: {list(request.data.keys())}"
        )
        
        file = request.FILES.get("media")

        # Validate that a file was provided
        if not file:
            # Check if frontend sent file with different field name
            available_files = list(request.FILES.keys())
            if available_files:
                logger.warning(
                    f"File uploaded with wrong field name. Expected 'media', got: {available_files}"
                )
                raise ValidationError({
                    'media': f'A file must be uploaded with field name "media". Received files with names: {", ".join(available_files)}'
                })
            raise ValidationError({
                'media': 'A file must be uploaded for gallery works.'
            })
        
        # Validate file object
        if not hasattr(file, 'name') or not hasattr(file, 'size'):
            logger.error(f"Invalid file object received: {type(file)}, attributes: {dir(file)}")
            raise ValidationError({
                'media': 'Invalid file object received. Please ensure you are uploading a valid file.'
            })
        
        # Log file details for debugging
        file_size = getattr(file, 'size', None)
        file_name = getattr(file, 'name', 'unknown')
        file_content_type = getattr(file, 'content_type', 'unknown')
        logger.info(
            f"Uploading file: name={file_name}, size={file_size}, "
            f"content_type={file_content_type}, user={user.id}"
        )
        
        # Validate file size (optional - you can set a max size)
        if file_size and file_size > 100 * 1024 * 1024:  # 100MB limit
            raise ValidationError({
                'media': f'File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size (100MB).'
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
            # Use "gallery" directly since root folder is already "academy-crm"
            path_segments = ["gallery", f"user-{user.id}"]
            folder_id = drive.ensure_folder_path(path_segments)

            # Ensure file pointer is at the beginning
            if hasattr(file, 'seek'):
                file.seek(0)
            elif hasattr(file, 'file') and hasattr(file.file, 'seek'):
                file.file.seek(0)

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
        except HttpError as e:
            # Handle Google Drive API errors specifically
            error_reason = None
            error_message = str(e)
            
            # Log the full error for debugging
            logger.error(
                f"Google Drive API error during gallery work upload: "
                f"status={e.resp.status}, error={error_message}, "
                f"error_details={getattr(e, 'error_details', None)}, "
                f"user={user.id}, file_name={file_name}"
            )
            
            # Try to extract error reason from error_details
            if hasattr(e, 'error_details') and e.error_details:
                for detail in e.error_details:
                    if isinstance(detail, dict):
                        if 'reason' in detail:
                            error_reason = detail.get('reason')
                            break
                        # Also check for nested error objects
                        if 'error' in detail and isinstance(detail['error'], dict):
                            if 'reason' in detail['error']:
                                error_reason = detail['error'].get('reason')
                                break
            
            # Also check error message for storage quota exceeded
            if 'storageQuotaExceeded' in error_message.lower():
                error_reason = 'storageQuotaExceeded'
            
            # Check for service account storage quota limitation
            if 'Service Accounts do not have storage quota' in error_message:
                logger.error(
                    f"Service account cannot upload to personal Drive folder. "
                    f"Service accounts can only upload to Shared Drives (Google Workspace) or use OAuth delegation."
                )
                exc = APIException(
                    detail=(
                        'Service accounts cannot upload files to personal Google Drive folders. '
                        'You must either: (1) Use a Shared Drive (Google Workspace), or '
                        '(2) Use OAuth delegation to impersonate a user account. '
                        'Please contact your administrator to set up a Shared Drive or configure OAuth delegation.'
                    )
                )
                exc.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                raise exc
            
            # Check for storage quota exceeded error
            if e.resp.status == 403 and error_reason == 'storageQuotaExceeded':
                # Try to get quota information for better error message
                quota_info = None
                try:
                    quota_info = drive.get_storage_quota()
                except Exception:
                    pass  # Ignore quota check errors
                
                logger.warning(
                    f"Storage quota exceeded for user {user.id} when uploading file {file_name} "
                    f"(size: {file_size} bytes). Quota info: {quota_info}"
                )
                
                # Build detailed error message
                if quota_info and quota_info.get('limit'):
                    limit_gb = quota_info['limit'] / (1024 ** 3)
                    usage_gb = quota_info['usage'] / (1024 ** 3)
                    detail = (
                        f'Google Drive storage quota exceeded. '
                        f'Service account storage: {usage_gb:.2f} GB / {limit_gb:.2f} GB used. '
                        f'Please free up space in the service account\'s Google Drive or contact your administrator. '
                        f'Note: The application uses a service account, not your personal Google Drive account.'
                    )
                else:
                    detail = (
                        'Google Drive storage quota exceeded for the service account. '
                        'Please free up space in the service account\'s Google Drive or contact your administrator. '
                        'Note: The application uses a Google Drive service account (configured via GOOGLE_DRIVE_CLIENT_EMAIL), '
                        'which has its own storage quota separate from your personal Google Drive account.'
                    )
                
                exc = APIException(detail=detail)
                exc.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                raise exc
            
            # Handle other HTTP errors
            exc = APIException(
                detail=f'Failed to upload file to Google Drive: {str(e)}'
            )
            if e.resp.status == 403:
                exc.status_code = status.HTTP_403_FORBIDDEN
            elif e.resp.status == 413:
                exc.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            else:
                exc.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise exc
        except Exception as e:
            # If upload fails with other errors, raise exception
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


