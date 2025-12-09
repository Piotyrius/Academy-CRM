"""
Views for documents app.
"""
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import APIException
from django.http import Http404
from academy_crm.cloudinary_service import get_cloudinary_service_or_none
from storage.models import FileObject, FileOwnerType, FileActivity
from .models import Document
from .serializers import DocumentSerializer
from .permissions import IsOwnerOrAdmin


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document model."""
    queryset = Document.objects.select_related('owner').all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filterset_fields = ['kind', 'owner', 'visibility']
    search_fields = ['description']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
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
                    organization=getattr(user, "organization", None),
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