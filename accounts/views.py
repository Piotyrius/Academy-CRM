"""
Views for accounts app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .mfa import generate_mfa_secret, verify_totp
from .serializers import (
    UserSerializer, UserCreateSerializer, CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from .permissions import IsAdminOrSelf, IsAdminUser
from .throttling import LoginAnonThrottle, LoginUserThrottle, PasswordResetAnonThrottle

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
        # Profile & MFA actions are available to any authenticated user (self only).
        if self.action in ['me', 'me_update', 'mfa_setup', 'mfa_verify', 'mfa_disable']:
            return [permissions.IsAuthenticated()]
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrSelf()]
        return [IsAdminUser()]
    
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

    @action(detail=False, methods=['post'])
    def mfa_setup(self, request):
        """
        Start MFA setup for the current user.

        Generates a new TOTP secret and returns it so the frontend can show a QR
        code. MFA is not enabled until `mfa_verify` succeeds.
        """
        user = request.user
        secret = generate_mfa_secret()
        # Store secret but keep mfa_enabled disabled until verification.
        user.mfa_secret = secret
        user.mfa_enabled = False
        user.save(update_fields=['mfa_secret', 'mfa_enabled'])
        return Response(
            {
                'mfa_secret': secret,
                'mfa_enabled': False,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'])
    def mfa_verify(self, request):
        """
        Verify an MFA code for the current user and enable MFA if valid.
        """
        user = request.user
        code = str(request.data.get('mfa_code', '')).strip()
        secret = getattr(user, 'mfa_secret', None)
        if not secret:
            return Response(
                {'detail': 'MFA is not in setup state for this account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not code or not verify_totp(secret, code):
            return Response(
                {'mfa_code': ['Invalid or expired MFA code.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mfa_enabled = True
        user.save(update_fields=['mfa_enabled'])
        return Response({'mfa_enabled': True}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def mfa_disable(self, request):
        """
        Disable MFA for the current user and clear the secret.
        """
        user = request.user
        user.mfa_secret = None
        user.mfa_enabled = False
        user.save(update_fields=['mfa_secret', 'mfa_enabled'])
        return Response({'mfa_enabled': False}, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view."""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]  # Explicitly allow unauthenticated access
    throttle_classes = [LoginAnonThrottle, LoginUserThrottle]


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@extend_schema(
    request=PasswordResetRequestSerializer,
    responses={200: OpenApiTypes.OBJECT},
    tags=['Authentication'],
    summary="Request password reset email",
    description=(
        "Accepts an email address and, if an account exists, sends a password "
        "reset link to that address. Always returns a generic success message "
        "to avoid leaking whether the email exists."
    ),
)
def password_reset_request(request):
    """Request password reset - sends email with reset link."""
    # Apply basic throttling to password reset requests
    for throttle in [PasswordResetAnonThrottle()]:
        if not throttle.allow_request(request, view=None):
            return Response(
                {'detail': 'Request was throttled. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if user exists - return success anyway
        return Response({
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)
    
    # Generate token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Create reset link - combine uid and token
    combined_token = f"{uid}.{token}"
    
    # Get frontend URL from settings or use request origin
    frontend_url = getattr(settings, 'FRONTEND_URL', None)
    if not frontend_url:
        # Try to get from request origin (for development)
        origin = request.META.get('HTTP_ORIGIN', '')
        if origin:
            frontend_url = origin
        else:
            # Fallback to request host
            frontend_url = request.build_absolute_uri('/').rstrip('/')
    
    reset_link = f"{frontend_url}/reset-password?token={combined_token}"
    
    # Send email
    try:
        send_mail(
            subject='Password Reset Request',
            message=f'Click the following link to reset your password:\n\n{reset_link}\n\nThis link will expire in 24 hours.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log error but don't reveal to user
        return Response({
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)
    
    return Response({
        'message': 'If an account exists with this email, a password reset link has been sent.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@extend_schema(
    request=PasswordResetConfirmSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    tags=['Authentication'],
    summary="Confirm password reset",
    description=(
        "Accepts a token (uid.token) and a new password. If the token is valid,"
        " the user's password is updated."
    ),
)
def password_reset_confirm(request):
    """Confirm password reset with token."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['password']
    
    try:
        # Decode user ID from token
        uid = force_str(urlsafe_base64_decode(token.split('.')[0]))
        user = User.objects.get(pk=uid)
        
        # Verify token
        token_part = token.split('.')[1] if '.' in token else token
        if not default_token_generator.check_token(user, token_part):
            return Response(
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password has been reset successfully.'
        }, status=status.HTTP_200_OK)
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {'error': 'Invalid or expired token.'},
            status=status.HTTP_400_BAD_REQUEST
        )


# Student portal views
class StudentPortalViewSet(viewsets.ViewSet):
    """
    ViewSet for student portal endpoints.
    Returns data filtered by the current user (student=request.user).
    Works for any authenticated user, but typically used by students.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def enrollments(self, request):
        """Get student's enrollments."""
        from admissions.models import Enrollment
        from admissions.serializers import EnrollmentSerializer
        enrollments = Enrollment.objects.filter(student=request.user).select_related(
            'cohort', 'cohort__course', 'cohort__course__program', 'cohort__lecturer'
        )
        serializer = EnrollmentSerializer(enrollments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def attendance(self, request):
        """Get student's attendance records."""
        from attendance.models import AttendanceRecord
        from attendance.serializers import AttendanceRecordSerializer
        attendance_records = AttendanceRecord.objects.filter(student=request.user).select_related(
            'session', 'session__cohort', 'marked_by'
        )
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
        assessments = Assessment.objects.filter(
            cohort_id__in=cohort_ids, 
            published=True
        ).select_related('cohort', 'cohort__course', 'cohort__lecturer')
        serializer = AssessmentSerializer(assessments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def payments(self, request):
        """Get student's invoices and payments."""
        from payments.models import Invoice, Payment
        from payments.serializers import InvoiceSerializer, PaymentSerializer
        
        invoices = Invoice.objects.filter(enrollment__student=request.user).select_related(
            'enrollment', 'enrollment__cohort', 'pricing', 'payment_plan'
        )
        payments = Payment.objects.filter(student=request.user).select_related(
            'invoice', 'recorded_by'
        )
        
        invoice_serializer = InvoiceSerializer(invoices, many=True, context={'request': request})
        payment_serializer = PaymentSerializer(payments, many=True, context={'request': request})
        
        return Response({
            'invoices': invoice_serializer.data,
            'payments': payment_serializer.data,
        })
    
    @action(detail=False, methods=['get'])
    def outstanding_balance(self, request):
        """Get total outstanding balance for student."""
        from payments.models import Invoice
        from payments.services.invoice_service import InvoiceService
        
        invoices = Invoice.objects.filter(
            enrollment__student=request.user
        ).exclude(status__in=['PAID', 'CANCELLED'])
        
        total_outstanding = sum(
            InvoiceService.calculate_outstanding_amount(invoice) 
            for invoice in invoices
        )
        
        return Response({
            'total_outstanding': total_outstanding,
            'invoice_count': invoices.count(),
        })
    
    @action(detail=False, methods=['get'])
    def grades(self, request):
        """Get student's grades."""
        from assessment.models import Grade
        from assessment.serializers import GradeSerializer
        grades = Grade.objects.filter(student=request.user).select_related(
            'assessment', 'assessment__cohort', 'graded_by'
        )
        serializer = GradeSerializer(grades, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def certificates(self, request):
        """Get student's certificates."""
        from certificates.models import Certificate
        from certificates.serializers import CertificateSerializer
        certificates = Certificate.objects.filter(student=request.user).select_related(
            'cohort', 'cohort__course', 'cohort__course__program'
        )
        serializer = CertificateSerializer(certificates, many=True, context={'request': request})
        return Response(serializer.data)