"""
Views for catalog app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from subscriptions.mixins import (
    OrganizationFilterMixin, FeatureRequiredMixin, OrganizationAutoSetMixin
)
from .models import Program, Course, Cohort, Session, CohortStatus
from admissions.models import EnrollmentStatus
from .serializers import (
    ProgramSerializer,
    CourseSerializer,
    CohortSerializer,
    SessionSerializer
)
from .services.session_generator import SessionGenerator
from .permissions import IsAdminOrLecturerOwner


class ProgramViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Program model."""
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated]
    required_feature = 'catalog'  # Require catalog module
    filterset_fields = ['active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class CourseViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Course model."""
    queryset = Course.objects.select_related('program').all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    required_feature = 'catalog'  # Require catalog module
    filterset_fields = ['program']
    search_fields = ['title', 'code', 'description']
    ordering_fields = ['title', 'created_at']
    ordering = ['title']


class CohortViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Cohort model."""
    queryset = Cohort.objects.select_related('course', 'course__program', 'lecturer').all()
    serializer_class = CohortSerializer
    permission_classes = [IsAuthenticated]
    required_feature = 'catalog'  # Require catalog module
    filterset_fields = ['course', 'lecturer', 'status']
    search_fields = ['name', 'course__title']
    ordering_fields = ['start_date', 'name', 'created_at']
    ordering = ['-start_date']
    
    def get_permissions(self):
        """Restrict write operations to admin/lecturer only."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'generate_sessions']:
            # Use IsAdminOrLecturerOwner from catalog permissions
            from .permissions import IsAdminOrLecturerOwner
            return [IsAuthenticated(), IsAdminOrLecturerOwner()]
        # list and retrieve are accessible to all authenticated users (filtered by role)
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role and organization."""
        queryset = super().get_queryset()  # OrganizationFilterMixin handles organization filtering
        user = self.request.user
        
        # Lecturers only see their own cohorts
        if user.is_lecturer:
            queryset = queryset.filter(lecturer=user)
        
        # Annotate enrollment count to avoid N+1 queries
        # Use different name to avoid conflict with property
        queryset = queryset.annotate(
            _annotated_enrollment_count=Count(
                'enrollments',
                filter=Q(enrollments__status=EnrollmentStatus.ACTIVE)
            )
        )
        
        return queryset
    
    @extend_schema(
        tags=['Catalog'],
        summary="Generate recurring sessions",
        description=(
            "Generate recurring sessions for a cohort based on a pattern (e.g., 'TUE,THU'). "
            "Creates session instances for each occurrence matching the pattern within the cohort's date range."
        ),
        request={
            'type': 'object',
            'properties': {
                'pattern': {
                    'type': 'string',
                    'description': 'Day pattern (e.g., "TUE,THU" or "MON,WED,FRI")',
                    'example': 'TUE,THU'
                },
                'start_time': {
                    'type': 'string',
                    'format': 'time',
                    'description': 'Session start time (HH:MM format)',
                    'example': '19:00'
                },
                'end_time': {
                    'type': 'string',
                    'format': 'time',
                    'description': 'Session end time (HH:MM format)',
                    'example': '21:00'
                },
                'exclude_holidays': {
                    'type': 'boolean',
                    'description': 'Whether to exclude holidays from generation',
                    'default': True
                },
                'manual_exclusions': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'date'},
                    'description': 'List of specific dates to exclude (YYYY-MM-DD format)'
                }
            },
            'required': ['pattern']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'created': {'type': 'integer', 'description': 'Number of sessions created'},
                    'sessions': {
                        'type': 'array',
                        'items': {'type': 'object'},
                        'description': 'List of created sessions'
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            },
            404: OpenApiTypes.OBJECT,
        }
    )
    @action(detail=True, methods=['post'])
    def generate_sessions(self, request, pk=None):
        """Generate recurring sessions for a cohort."""
        cohort = self.get_object()
        pattern = request.data.get('pattern', '')  # e.g., 'TUE,THU'
        start_time = request.data.get('start_time', '19:00')
        end_time = request.data.get('end_time', '21:00')
        exclude_holidays = request.data.get('exclude_holidays', True)
        manual_exclusions = request.data.get('manual_exclusions', [])
        
        if not pattern:
            return Response(
                {'error': 'Pattern is required (e.g., "TUE,THU")'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        generator = SessionGenerator(cohort)
        sessions = generator.generate_sessions(
            pattern=pattern,
            start_time=start_time,
            end_time=end_time,
            exclude_holidays=exclude_holidays,
            manual_exclusions=manual_exclusions
        )
        
        serializer = SessionSerializer(sessions, many=True)
        return Response({
            'created': len(sessions),
            'sessions': serializer.data
        })


class SessionViewSet(
    FeatureRequiredMixin,
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Session model."""
    queryset = Session.objects.select_related('cohort').all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    required_feature = 'catalog'  # Require catalog module
    filterset_fields = ['cohort', 'is_cancelled']
    search_fields = ['cohort__name']
    ordering_fields = ['start_at']
    ordering = ['start_at']
    
    def get_queryset(self):
        """Filter queryset based on user role and organization."""
        queryset = super().get_queryset()  # OrganizationFilterMixin handles organization filtering
        user = self.request.user
        
        # Lecturers only see sessions for their cohorts
        if user.is_lecturer:
            queryset = queryset.filter(cohort__lecturer=user)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(start_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_at__date__lte=date_to)
        
        return queryset
    
    def perform_create(self, serializer):
        """Validate session time and cohort dates."""
        cohort = serializer.validated_data['cohort']
        start_at = serializer.validated_data['start_at']
        end_at = serializer.validated_data['end_at']
        
        # Validate that start_at < end_at
        if start_at >= end_at:
            raise ValidationError({
                'end_at': 'Session end time must be after start time.'
            })
        
        # Validate that session dates are within cohort date range
        if start_at.date() < cohort.start_date or end_at.date() > cohort.end_date:
            raise ValidationError({
                'start_at': f'Session dates must be within cohort date range ({cohort.start_date} to {cohort.end_date}).'
            })
        
        serializer.save()
    
    def perform_update(self, serializer):
        """Validate session time and cohort dates on update."""
        cohort = serializer.validated_data.get('cohort') or serializer.instance.cohort
        start_at = serializer.validated_data.get('start_at') or serializer.instance.start_at
        end_at = serializer.validated_data.get('end_at') or serializer.instance.end_at
        
        # Validate that start_at < end_at
        if start_at >= end_at:
            raise ValidationError({
                'end_at': 'Session end time must be after start time.'
            })
        
        # Validate that session dates are within cohort date range
        if start_at.date() < cohort.start_date or end_at.date() > cohort.end_date:
            raise ValidationError({
                'start_at': f'Session dates must be within cohort date range ({cohort.start_date} to {cohort.end_date}).'
            })
        
        serializer.save()


class LecturerViewSet(FeatureRequiredMixin, viewsets.ViewSet):
    """ViewSet for lecturer-specific endpoints."""
    permission_classes = [IsAuthenticated]
    required_feature = 'catalog'  # Require catalog module
    
    @extend_schema(
        tags=['Catalog'],
        summary="Get lecturer cohorts",
        description="Retrieve all cohorts assigned to the current authenticated lecturer.",
        responses={
            200: {
                'type': 'array',
                'items': {'type': 'object'}
            },
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                },
                'description': 'Only lecturers can access this endpoint'
            },
            401: OpenApiTypes.OBJECT,
        }
    )
    @action(detail=False, methods=['get'])
    def cohorts(self, request):
        """Get lecturer's own cohorts."""
        if not request.user.is_lecturer:
            return Response(
                {'error': 'Only lecturers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get organization for filtering
        organization = getattr(request, 'organization', None)
        if not organization and hasattr(request.user, 'organization'):
            organization = request.user.organization
        
        cohorts = Cohort.objects.filter(lecturer=request.user)
        if organization:
            cohorts = cohorts.filter(organization=organization)
        
        serializer = CohortSerializer(cohorts, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sessions(self, request):
        """Get lecturer's own sessions."""
        if not request.user.is_lecturer:
            return Response(
                {'error': 'Only lecturers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get organization for filtering
        organization = getattr(request, 'organization', None)
        if not organization and hasattr(request.user, 'organization'):
            organization = request.user.organization
        
        sessions = Session.objects.filter(cohort__lecturer=request.user)
        if organization:
            sessions = sessions.filter(organization=organization)
        
        # Filter by date range
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            sessions = sessions.filter(start_at__date__gte=date_from)
        if date_to:
            sessions = sessions.filter(start_at__date__lte=date_to)
        
        serializer = SessionSerializer(sessions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Catalog'],
        summary="List cohorts ready to start",
        description="Retrieve all cohorts that have reached minimum enrollment threshold (admin only).",
        responses={
            200: {
                'type': 'array',
                'items': {'$ref': '#/components/schemas/Cohort'}
            },
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    def ready_to_start(self, request):
        """Get cohorts ready to start (admin only)."""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can view cohorts ready to start'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        # Filter cohorts that are ready to start
        ready_cohorts = []
        for cohort in queryset:
            if cohort.is_ready_to_start and cohort.status == CohortStatus.PLANNED:
                ready_cohorts.append(cohort)
        
        serializer = self.get_serializer(ready_cohorts, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Catalog'],
        summary="Start a cohort",
        description="Manually start a cohort by changing its status to ENROLLING or ACTIVE (admin only).",
        request={
            'type': 'object',
            'properties': {
                'status': {
                    'type': 'string',
                    'enum': ['ENROLLING', 'ACTIVE'],
                    'description': 'New status for the cohort'
                }
            }
        },
        responses={
            200: {
                '$ref': '#/components/schemas/Cohort'
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            },
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    )
    @action(detail=True, methods=['post'])
    def start_cohort(self, request, pk=None):
        """Manually start a cohort (admin only)."""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can start cohorts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        cohort = self.get_object()
        new_status = request.data.get('status', CohortStatus.ENROLLING)
        
        if new_status not in [CohortStatus.ENROLLING, CohortStatus.ACTIVE]:
            return Response(
                {'error': 'Status must be ENROLLING or ACTIVE'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cohort.is_ready_to_start:
            return Response(
                {'error': 'Cohort has not reached minimum enrollment threshold'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cohort.status = new_status
        cohort.save()
        
        serializer = self.get_serializer(cohort)
        return Response(serializer.data)