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
            # Ensure file pointer is at the beginning
            if hasattr(file, 'seek'):
                file.seek(0)
            elif hasattr(file, 'file') and hasattr(file.file, 'seek'):
                file.file.seek(0)

            # Build hierarchical folder structure: org/{org_id}/gallery/user-{user_id}
            # This provides better organization and multi-tenant isolation
            organization = getattr(user, "organization", None)
            if organization:
                folder = f"org-{organization.id}/gallery/user-{user.id}"
            else:
                folder = f"gallery/user-{user.id}"
            
            uploaded = cloudinary_service.upload_file(
                file_content=file.file if hasattr(file, 'file') else file,
                folder=folder,
                resource_type="auto",
            )

            file_obj = FileObject.objects.create(
                organization=organization,
                owner_type=FileOwnerType.GALLERY_WORK,
                owner_id=None,
                cloudinary_public_id=uploaded.public_id,
                cloudinary_folder=uploaded.folder,
                cloudinary_url=uploaded.secure_url,
                cloudinary_resource_type=uploaded.resource_type,
                logical_path=folder,
                mime_type=file_content_type,
                size=uploaded.bytes,
                original_name=file_name,
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
            logger.error(
                f"Cloudinary upload error during gallery work upload: "
                f"error={str(e)}, user={user.id}, file_name={file_name}"
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


