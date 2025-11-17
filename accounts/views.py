"""
Views for accounts app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserCreateSerializer, CustomTokenObtainPairSerializer
from .permissions import IsAdminOrSelf

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    Admins can manage all users, users can view/edit themselves.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_login', 'email']
    ordering = ['-date_joined']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrSelf()]
        return [permissions.IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch', 'put'])
    def me_update(self, request):
        """Update current user profile."""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view."""
    serializer_class = CustomTokenObtainPairSerializer


# Student portal views
class StudentPortalViewSet(viewsets.ViewSet):
    """ViewSet for student portal endpoints."""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def enrollments(self, request):
        """Get student's enrollments."""
        from admissions.models import Enrollment
        from admissions.serializers import EnrollmentSerializer
        enrollments = Enrollment.objects.filter(student=request.user)
        serializer = EnrollmentSerializer(enrollments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def attendance(self, request):
        """Get student's attendance records."""
        from attendance.models import AttendanceRecord
        from attendance.serializers import AttendanceRecordSerializer
        attendance_records = AttendanceRecord.objects.filter(student=request.user)
        serializer = AttendanceRecordSerializer(attendance_records, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assessments(self, request):
        """Get student's assessments."""
        from assessment.models import Assessment
        from assessment.serializers import AssessmentSerializer
        from admissions.models import Enrollment
        # Get cohorts student is enrolled in
        enrollments = Enrollment.objects.filter(student=request.user, status='ACTIVE')
        cohort_ids = enrollments.values_list('cohort_id', flat=True)
        assessments = Assessment.objects.filter(cohort_id__in=cohort_ids, published=True)
        serializer = AssessmentSerializer(assessments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def grades(self, request):
        """Get student's grades."""
        from assessment.models import Grade
        from assessment.serializers import GradeSerializer
        grades = Grade.objects.filter(student=request.user)
        serializer = GradeSerializer(grades, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def certificates(self, request):
        """Get student's certificates."""
        from certificates.models import Certificate
        from certificates.serializers import CertificateSerializer
        certificates = Certificate.objects.filter(student=request.user)
        serializer = CertificateSerializer(certificates, many=True, context={'request': request})
        return Response(serializer.data)