"""
Views for documents app.
"""
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from django.http import Http404, HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from academy_crm.cloudinary_service import get_cloudinary_service_or_none
from storage.models import FileObject, FileOwnerType, FileActivity
from .models import Document
from .serializers import DocumentSerializer
from .permissions import IsOwnerOrAdmin


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document model."""
    queryset = Document.objects.select_related('owner', 'file_object').all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filterset_fields = ['kind', 'owner', 'visibility']
    search_fields = ['description']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @extend_schema(
        tags=['Documents'],
        summary="Create document with file upload",
        description=(
            "Create a new document with file upload. The file is uploaded to Cloudinary. "
            "Accepts multipart/form-data with 'file' field. Maximum file size depends on Cloudinary limits."
        ),
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Document file to upload'
                    },
                    'kind': {
                        'type': 'string',
                        'description': 'Document type/category'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Document description'
                    },
                    'visibility': {
                        'type': 'string',
                        'enum': ['PRIVATE', 'LECTURER', 'ADMIN'],
                        'description': 'Document visibility level'
                    }
                },
                'required': ['file']
            }
        },
        responses={
            201: DocumentSerializer,
            400: OpenApiTypes.OBJECT,
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
        """Filter queryset based on user role and visibility."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students only see their own documents
        if user.is_student:
            queryset = queryset.filter(owner=user)
        # Lecturers can see documents with LECTURER visibility
        elif user.is_lecturer:
            queryset = queryset.filter(
                models.Q(owner=user) | models.Q(visibility__in=['LECTURER', 'ADMIN'])
            )
        
        return queryset
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    def perform_create(self, serializer):
        """
        Set owner to current user and upload the attached file to Cloudinary
        and create a FileObject record.
        """
        request = self.request
        file = request.FILES.get("file")
        user = request.user

        cloudinary_service = get_cloudinary_service_or_none()
        if cloudinary_service and file:
            # Build hierarchical folder structure: org/{org_id}/documents/user-{user_id}
            # This provides better organization and multi-tenant isolation
            organization = getattr(user, "organization", None)
            if organization:
                folder = f"org-{organization.id}/documents/user-{user.id}"
            else:
                folder = f"documents/user-{user.id}"
            
            try:
                # Ensure file pointer is at the beginning
                if hasattr(file, 'seek'):
                    file.seek(0)
                elif hasattr(file, 'file') and hasattr(file.file, 'seek'):
                    file.file.seek(0)

                uploaded = cloudinary_service.upload_file(
                    file_content=file.file if hasattr(file, 'file') else file,
                    folder=folder,
                    resource_type="auto",
                )

                file_obj = FileObject.objects.create(
                    organization=organization,
                    owner_type=FileOwnerType.DOCUMENT,
                    owner_id=None,
                    cloudinary_public_id=uploaded.public_id,
                    cloudinary_folder=uploaded.folder,
                    cloudinary_url=uploaded.secure_url,
                    cloudinary_resource_type=uploaded.resource_type,
                    logical_path=folder,
                    mime_type=file.content_type or "application/octet-stream",
                    size=uploaded.bytes,
                    original_name=file.name,
                    created_by=user,
                    visibility="PRIVATE",
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
                    detail=f'Failed to upload file to Cloudinary: {str(e)}'
                )
                exc.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                raise exc
        else:
            serializer.save(owner=user)
    
    @extend_schema(
        tags=['Documents'],
        summary="Download document file",
        description=(
            "Download a document file. Returns a redirect to the Cloudinary URL if available, "
            "or falls back to legacy file storage. Logs the download activity."
        ),
        responses={
            302: {
                'description': 'Redirect to file URL',
                'headers': {
                    'Location': {
                        'schema': {'type': 'string'},
                        'description': 'URL to the document file'
                    }
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'}
                },
                'description': 'Document or file not found'
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
    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Download a document file.
        
        Returns a redirect to the Cloudinary URL if the document has a file_object
        with a Cloudinary URL. Falls back to legacy file storage if available.
        Logs the download activity for audit purposes.
        """
        document = self.get_object()
        cloudinary_service = get_cloudinary_service_or_none()
        
        # Check if document has a file_object with Cloudinary URL
        if document.file_object and document.file_object.cloudinary_url:
            # Log download activity
            FileActivity.objects.create(
                file=document.file_object,
                user=request.user if request.user.is_authenticated else None,
                action="downloaded",
                ip=request.META.get("REMOTE_ADDR"),
            )
            # Redirect to Cloudinary URL for direct download
            return HttpResponseRedirect(document.file_object.cloudinary_url)
        
        # Fallback to legacy file storage
        if document.file:
            # Log download activity if we have a file_object
            if document.file_object:
                FileActivity.objects.create(
                    file=document.file_object,
                    user=request.user if request.user.is_authenticated else None,
                    action="downloaded",
                    ip=request.META.get("REMOTE_ADDR"),
                )
            # Return redirect to legacy file URL
            return HttpResponseRedirect(document.file.url)
        
        # No file available
        return Response(
            {"detail": "Document file not available. The document may not have been uploaded yet."},
            status=status.HTTP_404_NOT_FOUND
        )