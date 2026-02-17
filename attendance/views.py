"""
Views for attendance app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.http import Http404
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
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    def perform_create(self, serializer):
        """Set marked_by to current user and validate enrollment."""
        session = serializer.validated_data['session']
        student = serializer.validated_data['student']
        
        # Validate that student is enrolled in the cohort
        from admissions.utils import is_student_enrolled
        if not is_student_enrolled(student, session.cohort, status='ACTIVE'):
            raise ValidationError({
                'student': 'Student must be actively enrolled in this cohort to mark attendance.'
            })
        
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
        is_authorized = request.user.is_admin or session.cohort.lecturer == request.user
        
        if not is_authorized:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        created_count = 0
        updated_count = 0
        errors = []
        
        # Batch fetch all students to avoid N+1 queries
        from accounts.models import User, Role
        student_ids = [record_data['student_id'] for record_data in records_data]
        students = {str(student.id): student for student in User.objects.filter(
            id__in=student_ids,
            role=Role.STUDENT
        )}
        
        # Batch check enrollments to avoid N+1 queries
        from admissions.models import Enrollment, EnrollmentStatus
        enrolled_student_ids = set(Enrollment.objects.filter(
            student_id__in=student_ids,
            cohort=session.cohort,
            status=EnrollmentStatus.ACTIVE
        ).values_list('student_id', flat=True))
        
        # Get existing attendance records to separate creates from updates
        existing_records = {
            str(record.student_id): record
            for record in AttendanceRecord.objects.filter(
                session=session,
                student_id__in=student_ids
            )
        }
        
        records_to_create = []
        records_to_update = []
        
        with transaction.atomic():
            for record_data in records_data:
                student_id = record_data['student_id']
                student = students.get(str(student_id))
                
                if not student:
                    errors.append(f"Student {student_id} not found or is not a student")
                    continue
                
                # Validate that student is enrolled in the cohort
                if str(student.id) not in enrolled_student_ids:
                    errors.append(f"Student {student.get_full_name()} is not actively enrolled in this cohort")
                    continue
                
                status_value = record_data.get('status', AttendanceStatus.ABSENT)
                note = record_data.get('note', '')
                marked_at = timezone.now()
                
                existing_record = existing_records.get(str(student_id))
                
                if existing_record:
                    # Update existing record
                    existing_record.status = status_value
                    existing_record.note = note
                    existing_record.marked_by = request.user
                    existing_record.marked_at = marked_at
                    records_to_update.append(existing_record)
                else:
                    # Create new record
                    records_to_create.append(AttendanceRecord(
                        session=session,
                        student=student,
                        status=status_value,
                        note=note,
                        marked_by=request.user,
                        marked_at=marked_at,
                        organization=session.organization or session.cohort.organization
                    ))
            
            # Bulk create new records
            if records_to_create:
                AttendanceRecord.objects.bulk_create(records_to_create)
                created_count = len(records_to_create)
            
            # Bulk update existing records
            if records_to_update:
                AttendanceRecord.objects.bulk_update(
                    records_to_update,
                    fields=['status', 'note', 'marked_by', 'marked_at']
                )
                updated_count = len(records_to_update)
        
        return Response({
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        })