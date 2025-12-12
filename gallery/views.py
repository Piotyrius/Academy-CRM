import logging
from django.utils import timezone
from django.db.models import Q
from django.http import Http404
from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.exceptions import ValidationError, APIException
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from academy_crm.cloudinary_service import get_cloudinary_service_or_none
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
    
    @extend_schema(
        tags=['Gallery'],
        summary="Create gallery work with media upload",
        description=(
            "Create a new gallery work with media file upload. The file is uploaded to Cloudinary. "
            "Accepts multipart/form-data with 'media' field. Maximum file size: 100MB. "
            "Supports images, videos, and other media types."
        ),
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'media': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Media file to upload (image, video, etc.) - max 100MB'
                    },
                    'title': {
                        'type': 'string',
                        'description': 'Work title'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Work description'
                    },
                    'is_public': {
                        'type': 'boolean',
                        'description': 'Whether the work is publicly visible'
                    },
                    'status': {
                        'type': 'string',
                        'enum': ['DRAFT', 'PUBLISHED'],
                        'description': 'Work status'
                    }
                },
                'required': ['media']
            }
        },
        responses={
            201: WorkSerializer,
            400: {
                'type': 'object',
                'properties': {
                    'media': {'type': 'array', 'items': {'type': 'string'}}
                },
                'description': 'Validation error - missing file or invalid file'
            },
            401: OpenApiTypes.OBJECT,
            500: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                },
                'description': 'File upload failed'
            },
            503: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                },
                'description': 'Cloudinary is not configured'
            }
        }
    )
    def create(self, request, *args, **kwargs):
        # The serializer has media field as write_only=True, so it won't interfere
        # We handle the actual file upload in perform_create
        return super().create(request, *args, **kwargs)

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
        Create gallery work with file upload to Cloudinary.
        Cloudinary storage is required - no fallback to local storage.
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

        # Validate that Cloudinary is configured
        cloudinary_service = get_cloudinary_service_or_none()
        if not cloudinary_service:
            exc = APIException(
                detail='Cloudinary storage is required for file uploads. Please configure Cloudinary integration.'
            )
            exc.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            raise exc

        # Upload file to Cloudinary
        try:
            # Build hierarchical folder structure: org/{org_id}/gallery/user-{user_id}
            # This provides better organization and multi-tenant isolation
            organization = getattr(user, "organization", None)
            if organization:
                folder = f"org-{organization.id}/gallery/user-{user.id}"
            else:
                folder = f"gallery/user-{user.id}"
            
            # Handle file content for Cloudinary upload
            # Django's UploadedFile objects are file-like and can be passed directly
            # Ensure the file pointer is at the beginning before upload
            file_content = file
            if hasattr(file, 'file'):
                # For InMemoryUploadedFile or TemporaryUploadedFile, get the underlying file
                file_content = file.file
            elif not hasattr(file, 'read'):
                # If it doesn't have a read method, it's not a valid file-like object
                raise ValueError(f"Invalid file object type: {type(file)}")
            
            # Ensure file pointer is at the beginning
            if hasattr(file_content, 'seek'):
                file_content.seek(0)
            
            logger.info(
                f"Uploading to Cloudinary: folder={folder}, "
                f"file_type={type(file_content).__name__}, user={user.id}"
            )
            
            uploaded = cloudinary_service.upload_file(
                file_content=file_content,
                folder=folder,
                resource_type="auto",
            )

            # Determine visibility from request data or serializer validated data
            is_public = False
            if hasattr(serializer, 'validated_data') and serializer.validated_data:
                is_public = serializer.validated_data.get("is_public", False)
            else:
                # Fallback to request data if validated_data is not available
                is_public = request.data.get("is_public", "false").lower() in ("true", "1", "yes")
            
            # Create FileObject record
            try:
                file_obj = FileObject.objects.create(
                    organization=organization,
                    owner_type=FileOwnerType.GALLERY_WORK,
                    owner_id=None,
                    # Cloudinary fields
                    cloudinary_public_id=uploaded.public_id,
                    cloudinary_folder=uploaded.folder,
                    cloudinary_url=uploaded.secure_url,
                    cloudinary_resource_type=uploaded.resource_type,
                    # Legacy Drive fields (set to empty string to satisfy NOT NULL constraint if present)
                    drive_file_id="",  # Empty string for Cloudinary uploads
                    drive_folder_id="",  # Empty string for Cloudinary uploads
                    logical_path=folder,
                    mime_type=file_content_type,
                    size=uploaded.bytes,
                    original_name=file_name,
                    created_by=user,
                    visibility="PUBLIC" if is_public else "PRIVATE",
                )
            except Exception as e:
                logger.error(
                    f"Failed to create FileObject: error={str(e)}, "
                    f"user={user.id}, file_name={file_name}"
                )
                raise APIException(
                    detail=f'Failed to create file record: {str(e)}'
                ) from e
            
            # Save Work instance (without media field - we use file_object instead)
            try:
                # Exclude media from validated_data to prevent serializer from trying to save it
                save_data = serializer.validated_data.copy() if hasattr(serializer, 'validated_data') and serializer.validated_data else {}
                save_data.pop('media', None)  # Remove media field if present
                instance = serializer.save(owner=user, file_object=file_obj, **save_data)
            except Exception as e:
                # If Work creation fails, try to clean up the FileObject
                try:
                    file_obj.delete()
                except Exception:
                    pass
                logger.error(
                    f"Failed to create Work instance: error={str(e)}, "
                    f"user={user.id}, file_name={file_name}"
                )
                raise APIException(
                    detail=f'Failed to create gallery work: {str(e)}'
                ) from e
            
            # Update FileObject with the Work instance ID
            try:
                file_obj.owner_id = instance.id
                file_obj.save(update_fields=["owner_id"])
            except Exception as e:
                logger.warning(
                    f"Failed to update FileObject owner_id: error={str(e)}, "
                    f"file_obj={file_obj.id}, work={instance.id}"
                )
                # Non-critical error, continue

            # Create FileActivity record (non-critical, log but don't fail)
            try:
                FileActivity.objects.create(
                    file=file_obj,
                    user=user,
                    action="uploaded",
                    ip=request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or "unknown",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create FileActivity: error={str(e)}, "
                    f"file_obj={file_obj.id}, user={user.id}"
                )
                # Non-critical error, continue
        except Exception as e:
            # If upload fails, raise exception with detailed error information
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(
                f"Cloudinary upload error during gallery work upload: "
                f"error={str(e)}, error_type={type(e).__name__}, "
                f"user={user.id}, file_name={file_name}, file_size={file_size}, "
                f"traceback={error_traceback}"
            )
            exc = APIException(
                detail=f'Failed to upload file to Cloudinary: {str(e)}'
            )
            exc.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise exc

    @extend_schema(
        tags=['Gallery'],
        summary="Publish gallery work",
        description="Publish a gallery work (change status to PUBLISHED). Only the work owner or admin can publish.",
        responses={
            200: WorkSerializer,
            403: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                },
                'description': 'Forbidden - not owner or admin'
            },
            404: OpenApiTypes.OBJECT,
        }
    )
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


