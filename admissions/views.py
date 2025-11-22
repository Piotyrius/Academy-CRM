"""
Views for admissions app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.db import transaction, models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string
from subscriptions.mixins import (
    OrganizationFilterMixin, FeatureRequiredMixin, OrganizationAutoSetMixin
)
from accounts.models import Role
from .models import Application, Enrollment, ApplicationStatus, EnrollmentStatus
from .serializers import ApplicationSerializer, EnrollmentSerializer
from .permissions import IsAdminOrLecturerOwner


class ApplicationViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Application model."""
    queryset = Application.objects.select_related('program').all()
    serializer_class = ApplicationSerializer
    required_feature = 'admissions'  # Require admissions module
    filterset_fields = ['status', 'program']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """Public can create, authenticated can view."""
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdminOrLecturerOwner()]
    
    def _parse_name(self, full_name):
        """Parse full name into first_name and last_name, handling edge cases."""
        if not full_name or not full_name.strip():
            return '', ''
        
        name_parts = full_name.strip().split()
        
        if len(name_parts) == 0:
            return '', ''
        elif len(name_parts) == 1:
            return name_parts[0], ''
        else:
            # First part is first name, rest is last name
            return name_parts[0], ' '.join(name_parts[1:])
    
    def _generate_temp_password(self):
        """Generate a secure temporary password."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        # Generate 12-character password
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
        return password
    
    def _send_password_setup_email(self, user, temp_password):
        """Send password setup email to new user."""
        try:
            # Get frontend URL from settings or use request origin
            frontend_url = getattr(settings, 'FRONTEND_URL', None)
            if not frontend_url:
                frontend_url = 'https://your-academy.com'  # Default fallback
            
            reset_link = f"{frontend_url}/reset-password?email={user.email}"
            
            send_mail(
                subject='Welcome to Academy - Set Your Password',
                message=f'''Welcome to {user.organization.name if user.organization else "the Academy"}!

Your account has been created. Please set your password using the link below:

{reset_link}

Or use this temporary password to login: {temp_password}

Please change your password after first login.

This link will expire in 7 days.''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail the enrollment creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send password setup email to {user.email}: {e}")
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept application and create enrollment."""
        application = self.get_object()
        
        # Check if already accepted
        if application.status == ApplicationStatus.ACCEPTED:
            return Response(
                {'error': 'Application is already accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already rejected
        if application.status == ApplicationStatus.REJECTED:
            return Response(
                {'error': 'Cannot accept a rejected application'},
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
            cohort = Cohort.objects.select_for_update().get(id=cohort_id)
        except Cohort.DoesNotExist:
            return Response(
                {'error': 'Cohort not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate that cohort's program matches application's program
        if cohort.course.program != application.program:
            return Response(
                {
                    'error': 'Program mismatch',
                    'detail': f'Application is for program "{application.program.name}" but cohort belongs to program "{cohort.course.program.name}"'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get organization from application or request context
        organization = application.organization
        if not organization:
            organization = getattr(request, 'organization', None)
            if not organization and hasattr(request.user, 'organization'):
                organization = request.user.organization
        
        with transaction.atomic():
            # Lock cohort for update to prevent race condition
            cohort = Cohort.objects.select_for_update().get(id=cohort_id)
            
            # Check if student user exists or create
            user_created = False
            temp_password = None
            try:
                from accounts.models import User
                student = User.objects.get(email=application.email)
                if student.role != Role.STUDENT:
                    return Response(
                        {'error': 'User with this email is not a student'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Update organization if not set
                if not student.organization and organization:
                    student.organization = organization
                    student.save()
            except User.DoesNotExist:
                # Parse name
                first_name, last_name = self._parse_name(application.name)
                
                # Generate temporary password
                temp_password = self._generate_temp_password()
                
                # Create student user
                student = User.objects.create_user(
                    email=application.email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=application.phone,
                    role=Role.STUDENT,
                    organization=organization
                )
                user_created = True
                
                # Set temporary password
                student.set_password(temp_password)
                student.save()
            
            # Check capacity before creating enrollment
            active_count = cohort.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()
            has_capacity = active_count < cohort.capacity
            
            # Determine enrollment status
            enrollment_status = EnrollmentStatus.ACTIVE if has_capacity else EnrollmentStatus.PENDING
            
            # Create enrollment with organization
            enrollment, created = Enrollment.objects.get_or_create(
                student=student,
                cohort=cohort,
                defaults={
                    'status': enrollment_status,
                    'organization': organization or cohort.organization
                }
            )
            
            # If enrollment already exists, update status if needed
            if not created and enrollment.status == EnrollmentStatus.PENDING and has_capacity:
                enrollment.status = EnrollmentStatus.ACTIVE
                enrollment.save()
            
            # Set application status to ACCEPTED
            application.status = ApplicationStatus.ACCEPTED
            application.save()
            
            # Send password setup email if user was just created
            if user_created and temp_password:
                self._send_password_setup_email(student, temp_password)
        
        serializer = EnrollmentSerializer(enrollment)
        response_data = serializer.data
        response_data['user_created'] = user_created
        if user_created:
            response_data['message'] = 'Student account created. Password setup email sent.'
        
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class EnrollmentViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Enrollment model."""
    queryset = Enrollment.objects.select_related('student', 'cohort').all()
    serializer_class = EnrollmentSerializer
    required_feature = 'admissions'  # Require admissions module
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
        """Activate enrollment (check capacity with race condition protection)."""
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.PENDING:
            return Response(
                {'error': 'Enrollment is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Lock cohort for update to prevent race condition
            cohort = Cohort.objects.select_for_update().get(id=enrollment.cohort.id)
            
            # Re-check capacity with locked cohort
            active_count = cohort.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()
            if active_count >= cohort.capacity:
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
    
    @action(detail=False, methods=['get'])
    def waitlist(self, request):
        """Get waitlisted enrollments (pending enrollments for full cohorts)."""
        # Only admins can see waitlist
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can view waitlist'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get pending enrollments for full cohorts
        from catalog.models import Cohort
        full_cohort_ids = Cohort.objects.annotate(
            enrollment_count=models.Count('enrollments', filter=models.Q(enrollments__status='ACTIVE'))
        ).filter(
            models.Q(enrollment_count__gte=models.F('capacity'))
        ).values_list('id', flat=True)
        
        waitlist_enrollments = self.queryset.filter(
            status=EnrollmentStatus.PENDING,
            cohort_id__in=full_cohort_ids
        )
        
        serializer = self.get_serializer(waitlist_enrollments, many=True)
        return Response({
            'count': waitlist_enrollments.count(),
            'enrollments': serializer.data
        })
    
    @extend_schema(
        summary="Bulk activate enrollments",
        description="Activate multiple pending enrollments at once (admin only). Only enrollments with status PENDING will be activated. Enrollments for full cohorts will be skipped with an error message.",
        request={
            'application/json': {
                'type': 'object',
                'required': ['enrollment_ids'],
                'properties': {
                    'enrollment_ids': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'format': 'uuid',
                            'example': 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
                        },
                        'description': 'Array of enrollment UUIDs to activate',
                        'minItems': 1
                    }
                },
                'examples': {
                    'single_enrollment': {
                        'summary': 'Activate single enrollment',
                        'value': {
                            'enrollment_ids': ['f47ac10b-58cc-4372-a567-0e02b2c3d479']
                        }
                    },
                    'multiple_enrollments': {
                        'summary': 'Activate multiple enrollments',
                        'value': {
                            'enrollment_ids': [
                                'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                                'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
                            ]
                        }
                    }
                }
            }
        },
        responses={
            200: {
                'description': 'Enrollments activated successfully',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'activated': {
                                    'type': 'integer',
                                    'description': 'Number of enrollments successfully activated'
                                },
                                'enrollments': {
                                    'type': 'array',
                                    'items': {'$ref': '#/components/schemas/Enrollment'}
                                },
                                'errors': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                    'description': 'Error messages for enrollments that could not be activated'
                                }
                            }
                        },
                        'examples': {
                            'success': {
                                'summary': 'All enrollments activated',
                                'value': {
                                    'activated': 2,
                                    'enrollments': [
                                        {
                                            'id': 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                                            'status': 'ACTIVE',
                                            'student_name': 'John Doe',
                                            'cohort_name': 'FSD Cohort 2025-01'
                                        }
                                    ],
                                    'errors': []
                                }
                            },
                            'partial_success': {
                                'summary': 'Some enrollments activated, some failed',
                                'value': {
                                    'activated': 1,
                                    'enrollments': [
                                        {
                                            'id': 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                                            'status': 'ACTIVE'
                                        }
                                    ],
                                    'errors': [
                                        'Enrollment a1b2c3d4-e5f6-7890-abcd-ef1234567890: Cohort is full'
                                    ]
                                }
                            }
                        }
                    }
                }
            },
            400: {
                'description': 'Bad request - enrollment_ids is required or empty',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'error': {'type': 'string'}
                            }
                        },
                        'example': {
                            'error': 'enrollment_ids is required'
                        }
                    }
                }
            },
            403: {
                'description': 'Forbidden - only admins can bulk activate',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'error': {'type': 'string'}
                            }
                        },
                        'example': {
                            'error': 'Only admins can bulk activate enrollments'
                        }
                    }
                }
            }
        },
        tags=['Enrollments']
    )
    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """Bulk activate enrollments (admin only)."""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can bulk activate enrollments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        enrollment_ids = request.data.get('enrollment_ids', [])
        if not enrollment_ids:
            return Response(
                {'error': 'enrollment_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enrollments = self.queryset.filter(
            id__in=enrollment_ids,
            status=EnrollmentStatus.PENDING
        ).select_related('cohort', 'student')
        
        activated = []
        errors = []
        enrollments_to_activate = []
        
        with transaction.atomic():
            # Group enrollments by cohort to minimize cohort locks
            from collections import defaultdict
            enrollments_by_cohort = defaultdict(list)
            for enrollment in enrollments:
                enrollments_by_cohort[enrollment.cohort_id].append(enrollment)
            
            # Process each cohort once
            for cohort_id, cohort_enrollments in enrollments_by_cohort.items():
                try:
                    # Lock cohort for update (once per cohort, not per enrollment)
                    cohort = Cohort.objects.select_for_update().get(id=cohort_id)
                    
                    # Get current active count once per cohort
                    active_count = cohort.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()
                    available_spots = cohort.capacity - active_count
                    
                    # Process enrollments for this cohort
                    for enrollment in cohort_enrollments:
                        if available_spots <= 0:
                            errors.append(f"Enrollment {enrollment.id}: Cohort is full")
                            continue
                        
                        enrollment.status = EnrollmentStatus.ACTIVE
                        enrollments_to_activate.append(enrollment)
                        available_spots -= 1
                        
                except Cohort.DoesNotExist:
                    for enrollment in cohort_enrollments:
                        errors.append(f"Enrollment {enrollment.id}: Cohort not found")
                except Exception as e:
                    for enrollment in cohort_enrollments:
                        errors.append(f"Enrollment {enrollment.id}: {str(e)}")
            
            # Bulk update all enrollments at once
            if enrollments_to_activate:
                Enrollment.objects.bulk_update(enrollments_to_activate, fields=['status'])
                
                # Serialize activated enrollments
                for enrollment in enrollments_to_activate:
                    serializer = self.get_serializer(enrollment)
                    activated.append(serializer.data)
        
        return Response({
            'activated': len(activated),
            'enrollments': activated,
            'errors': errors
        })