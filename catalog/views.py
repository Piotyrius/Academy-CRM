"""
Views for catalog app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from subscriptions.mixins import (
    OrganizationFilterMixin, FeatureRequiredMixin, OrganizationAutoSetMixin
)
from .models import Program, Course, Cohort, Session
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
    queryset = Cohort.objects.select_related('course', 'lecturer').all()
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
        
        return queryset
    
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


class LecturerViewSet(FeatureRequiredMixin, viewsets.ViewSet):
    """ViewSet for lecturer-specific endpoints."""
    permission_classes = [IsAuthenticated]
    required_feature = 'catalog'  # Require catalog module
    
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