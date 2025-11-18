"""
Views for assessment app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.http import Http404
from subscriptions.mixins import (
    OrganizationFilterMixin, FeatureRequiredMixin, OrganizationAutoSetMixin
)
from .models import Assessment, Submission, Grade
from .serializers import AssessmentSerializer, SubmissionSerializer, GradeSerializer
from .permissions import IsAdminOrLecturerOwner


class AssessmentViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Assessment model."""
    queryset = Assessment.objects.select_related('cohort').all()
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    required_feature = 'assessment'  # Require assessment module
    filterset_fields = ['cohort', 'kind', 'published']
    search_fields = ['title', 'description']
    ordering_fields = ['due_at', 'created_at']
    ordering = ['-due_at']
    
    def get_permissions(self):
        """Restrict write operations to admin/lecturer only."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrLecturerOwner()]
        # list and retrieve are accessible to all authenticated users (filtered by role)
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role and organization."""
        queryset = super().get_queryset()  # OrganizationFilterMixin handles organization filtering
        user = self.request.user
        
        # Students only see published assessments
        if user.is_student:
            queryset = queryset.filter(published=True)
        # Lecturers only see assessments for their cohorts
        elif user.is_lecturer:
            queryset = queryset.filter(cohort__lecturer=user)
        
        return queryset


class SubmissionViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Submission model."""
    queryset = Submission.objects.select_related('assessment', 'student').all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    required_feature = 'assessment'  # Require assessment module
    filterset_fields = ['assessment', 'student']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']
    
    def get_queryset(self):
        """Filter queryset based on user role and organization."""
        queryset = super().get_queryset()  # OrganizationFilterMixin handles organization filtering
        user = self.request.user
        
        # Students only see their own submissions
        if user.is_student:
            queryset = queryset.filter(student=user)
        # Lecturers only see submissions for their cohorts
        elif user.is_lecturer:
            queryset = queryset.filter(assessment__cohort__lecturer=user)
        
        return queryset
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    def perform_create(self, serializer):
        """Set student and check if late."""
        student = self.request.user
        assessment = serializer.validated_data['assessment']
        
        # Check if late
        late_flag = timezone.now() > assessment.due_at
        
        serializer.save(student=student, late_flag=late_flag)


class GradeViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Grade model."""
    queryset = Grade.objects.select_related('assessment', 'student', 'graded_by').all()
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    required_feature = 'assessment'  # Require assessment module
    filterset_fields = ['assessment', 'student']
    ordering_fields = ['graded_at']
    ordering = ['-graded_at']
    
    def get_queryset(self):
        """Filter queryset based on user role and organization."""
        queryset = super().get_queryset()  # OrganizationFilterMixin handles organization filtering
        user = self.request.user
        
        # Students only see their own grades
        if user.is_student:
            queryset = queryset.filter(student=user)
        # Lecturers only see grades for their cohorts
        elif user.is_lecturer:
            queryset = queryset.filter(assessment__cohort__lecturer=user)
        
        return queryset
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    def perform_create(self, serializer):
        """Set graded_by to current user."""
        serializer.save(graded_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def moderate(self, request, pk=None):
        """Moderate grade (admin approval)."""
        grade = self.get_object()
        approved = request.data.get('approved', False)
        
        # This would typically update a moderation status field
        # For now, we'll just return the grade
        serializer = self.get_serializer(grade)
        return Response({
            'grade': serializer.data,
            'moderated': True,
            'approved': approved
        })