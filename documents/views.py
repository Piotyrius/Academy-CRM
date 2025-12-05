"""
Views for documents app.
"""
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, permissions
from django.http import Http404
from academy_crm.google_drive import get_drive_service_or_none
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
        Set owner to current user and, when Drive is enabled, upload the
        attached file to Google Drive and create a FileObject record.
        """
        request = self.request
        file = request.FILES.get("file")
        user = request.user

        drive = get_drive_service_or_none()
        if drive and file:
            # Build logical path: academy-crm/documents/user-<id>
            path_segments = ["academy-crm", "documents", f"user-{user.id}"]
            folder_id = drive.ensure_folder_path(path_segments)

            uploaded = drive.upload_file(
                name=file.name,
                mime_type=file.content_type or "application/octet-stream",
                content=file.file,
                folder_id=folder_id,
            )

            file_obj = FileObject.objects.create(
                organization=getattr(user, "organization", None),
                owner_type=FileOwnerType.DOCUMENT,
                owner_id=None,
                drive_file_id=uploaded.file_id,
                drive_folder_id=uploaded.folder_id,
                logical_path="/".join(path_segments),
                mime_type=uploaded.mime_type,
                size=uploaded.size,
                original_name=uploaded.name,
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
        else:
            serializer.save(owner=user)