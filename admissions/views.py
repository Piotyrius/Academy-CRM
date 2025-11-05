"""
Views for admissions app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from accounts.models import Role
from .models import Application, Enrollment, ApplicationStatus, EnrollmentStatus
from .serializers import ApplicationSerializer, EnrollmentSerializer
from .permissions import IsAdminOrLecturerOwner


class ApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Application model."""
    queryset = Application.objects.select_related('program').all()
    serializer_class = ApplicationSerializer
    filterset_fields = ['status', 'program']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """Public can create, authenticated can view."""
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdminOrLecturerOwner()]
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept application and create enrollment."""
        application = self.get_object()
        
        if application.status != ApplicationStatus.ACCEPTED:
            return Response(
                {'error': 'Application must be accepted first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get cohort from request
        cohort_id = request.data.get('cohort_id')
        if not cohort_id:
            return Response(
                {'error': 'cohort_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from catalog.models import Cohort
            cohort = Cohort.objects.get(id=cohort_id)
        except Cohort.DoesNotExist:
            return Response(
                {'error': 'Cohort not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if student user exists or create
        try:
            from accounts.models import User
            student = User.objects.get(email=application.email)
            if student.role != Role.STUDENT:
                return Response(
                    {'error': 'User with this email is not a student'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            # Create student user
            student = User.objects.create_user(
                email=application.email,
                first_name=application.name.split()[0] if application.name.split() else '',
                last_name=' '.join(application.name.split()[1:]) if len(application.name.split()) > 1 else '',
                phone=application.phone,
                role=Role.STUDENT
            )
        
        # Create enrollment
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            cohort=cohort,
            defaults={'status': EnrollmentStatus.PENDING}
        )
        
        serializer = EnrollmentSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Enrollment model."""
    queryset = Enrollment.objects.select_related('student', 'cohort').all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'cohort', 'student']
    search_fields = ['student__email', 'student__first_name', 'student__last_name', 'cohort__name']
    ordering_fields = ['enrolled_at', 'status']
    ordering = ['-enrolled_at']
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students only see their own enrollments
        if user.is_student:
            queryset = queryset.filter(student=user)
        # Lecturers only see enrollments for their cohorts
        elif user.is_lecturer:
            queryset = queryset.filter(cohort__lecturer=user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate enrollment (check capacity)."""
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.PENDING:
            return Response(
                {'error': 'Enrollment is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check capacity
        cohort = enrollment.cohort
        if cohort.is_full:
            return Response(
                {'error': 'Cohort is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enrollment.status = EnrollmentStatus.ACTIVE
        enrollment.save()
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw enrollment."""
        enrollment = self.get_object()
        enrollment.status = EnrollmentStatus.WITHDRAWN
        enrollment.save()
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark enrollment as completed."""
        enrollment = self.get_object()
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
        enrollment.save()
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)