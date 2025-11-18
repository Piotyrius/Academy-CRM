"""
Views for documents app.
"""
from django.db import models
from rest_framework import viewsets, permissions
from django.http import Http404
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
        """Set owner to current user."""
        serializer.save(owner=self.request.user)