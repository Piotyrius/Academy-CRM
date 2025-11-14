"""
Views for attendance app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from subscriptions.mixins import (
    OrganizationFilterMixin, FeatureRequiredMixin, OrganizationAutoSetMixin
)
from .models import AttendanceRecord, AttendanceStatus
from .serializers import AttendanceRecordSerializer, BulkAttendanceSerializer
from .permissions import IsAdminOrLecturerOwner
from catalog.models import Session


class AttendanceRecordViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for AttendanceRecord model."""
    queryset = AttendanceRecord.objects.select_related('session', 'student', 'marked_by').all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    required_feature = 'attendance'  # Require attendance module
    filterset_fields = ['session', 'student', 'status']
    search_fields = ['student__email', 'student__first_name', 'student__last_name']
    ordering_fields = ['marked_at', 'session__start_at']
    ordering = ['-marked_at']
    
    def get_queryset(self):
        """Filter queryset based on user role and organization."""
        queryset = super().get_queryset()  # OrganizationFilterMixin handles organization filtering
        user = self.request.user
        
        # Students only see their own attendance
        if user.is_student:
            queryset = queryset.filter(student=user)
        # Lecturers only see attendance for their cohorts
        elif user.is_lecturer:
            queryset = queryset.filter(session__cohort__lecturer=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set marked_by to current user."""
        serializer.save(marked_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Bulk mark attendance for multiple students."""
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        session_id = serializer.validated_data['session_id']
        records_data = serializer.validated_data['records']
        
        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not request.user.is_admin and session.cohort.lecturer != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        created_count = 0
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for record_data in records_data:
                try:
                    from accounts.models import User
                    from accounts.models import Role
                    student = User.objects.get(id=record_data['student_id'], role=Role.STUDENT)
                except User.DoesNotExist:
                    errors.append(f"Student {record_data['student_id']} not found")
                    continue
                
                status_value = record_data.get('status', AttendanceStatus.ABSENT)
                note = record_data.get('note', '')
                
                attendance_record, created = AttendanceRecord.objects.update_or_create(
                    session=session,
                    student=student,
                    defaults={
                        'status': status_value,
                        'note': note,
                        'marked_by': request.user,
                        'marked_at': timezone.now()
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        return Response({
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        })