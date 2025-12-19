"""
Views for payments app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from subscriptions.mixins import (
    OrganizationFilterMixin, OrganizationAutoSetMixin
)
from .models import (
    Pricing, PaymentPlan, Discount, Invoice, Payment,
    PaymentSchedule, PaymentMethod
)
from .serializers import (
    PricingSerializer, PaymentPlanSerializer, DiscountSerializer,
    InvoiceSerializer, PaymentSerializer, PaymentScheduleSerializer,
    PaymentMethodSerializer
)
from .permissions import IsAdminOrReadOnly, CanViewOwnInvoices
from .services.invoice_service import InvoiceService
from .services.payment_service import PaymentService
from .services.schedule_service import PaymentScheduleService
from .services.discount_service import DiscountService
from admissions.models import Enrollment


class PricingViewSet(
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Pricing model."""
    queryset = Pricing.objects.select_related('organization', 'content_type').all()
    serializer_class = PricingSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['is_active', 'content_type']
    search_fields = ['amount']
    ordering_fields = ['effective_from', 'amount']
    ordering = ['-effective_from']


class PaymentPlanViewSet(
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for PaymentPlan model."""
    queryset = PaymentPlan.objects.select_related('organization').all()
    serializer_class = PaymentPlanSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


class DiscountViewSet(
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Discount model."""
    queryset = Discount.objects.select_related('organization').all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['type', 'applicable_to', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


class InvoiceViewSet(
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Invoice model."""
    queryset = Invoice.objects.select_related(
        'organization', 'enrollment', 'enrollment__student',
        'enrollment__cohort', 'pricing', 'payment_plan'
    ).all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewOwnInvoices]
    filterset_fields = ['enrollment', 'status', 'payment_plan']
    search_fields = ['invoice_number']
    ordering_fields = ['created_at', 'due_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students only see their own invoices
        if user.is_student:
            queryset = queryset.filter(enrollment__student=user)
        
        return queryset
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    @action(detail=False, methods=['post'])
    def create_for_enrollment(self, request):
        """Create invoice for an enrollment."""
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied("Only admins can create invoices.")
        
        enrollment_id = request.data.get('enrollment')
        payment_plan_id = request.data.get('payment_plan')
        discount_ids = request.data.get('discounts', [])
        
        try:
            enrollment = Enrollment.objects.get(id=enrollment_id)
        except Enrollment.DoesNotExist:
            raise ValidationError({'enrollment': 'Enrollment not found.'})
        
        try:
            payment_plan = PaymentPlan.objects.get(id=payment_plan_id)
        except PaymentPlan.DoesNotExist:
            raise ValidationError({'payment_plan': 'Payment plan not found.'})
        
        discounts = []
        if discount_ids:
            discounts = Discount.objects.filter(id__in=discount_ids)
        
        try:
            invoice = InvoiceService.create_invoice_for_enrollment(
                enrollment, payment_plan, discounts
            )
            
            # Create payment schedule
            PaymentScheduleService.create_payment_schedule(invoice, payment_plan)
            
            serializer = self.get_serializer(invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            raise ValidationError({'error': str(e)})
    
    @action(detail=True, methods=['post'])
    def apply_discounts(self, request, pk=None):
        """Apply discounts to an invoice."""
        invoice = self.get_object()
        discount_ids = request.data.get('discounts', [])
        
        discounts = Discount.objects.filter(id__in=discount_ids)
        student = invoice.enrollment.student
        enrollment = invoice.enrollment
        
        applicable_discounts = DiscountService.get_applicable_discounts(
            invoice, student, enrollment
        )
        
        # Filter to only include requested discounts that are applicable
        discounts_to_apply = [d for d in discounts if d in applicable_discounts]
        
        DiscountService.apply_discounts_to_invoice(invoice, discounts_to_apply)
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def outstanding_balance(self, request, pk=None):
        """Get outstanding balance for an invoice."""
        invoice = self.get_object()
        outstanding = InvoiceService.calculate_outstanding_amount(invoice)
        
        return Response({
            'invoice_number': invoice.invoice_number,
            'total_amount': invoice.total_amount,
            'paid_amount': invoice.paid_amount,
            'outstanding_amount': outstanding,
            'status': invoice.status,
        })
    
    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """Issue an invoice."""
        invoice = self.get_object()
        InvoiceService.issue_invoice(invoice)
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Payments'],
        summary="Get payment status for cohort",
        description="Get payment status for all students in a cohort (admin only).",
        parameters=[
            OpenApiParameter(
                name='cohort_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Cohort UUID',
                required=True
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'cohort_name': {'type': 'string'},
                    'total_expected': {'type': 'number'},
                    'total_paid': {'type': 'number'},
                    'outstanding': {'type': 'number'},
                    'students': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'student_name': {'type': 'string'},
                                'student_email': {'type': 'string'},
                                'invoice_number': {'type': 'string'},
                                'total_amount': {'type': 'number'},
                                'paid_amount': {'type': 'number'},
                                'outstanding_amount': {'type': 'number'},
                                'status': {'type': 'string'}
                            }
                        }
                    }
                }
            },
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    @action(detail=False, methods=['get'])
    def cohort_payment_summary(self, request):
        """Get payment summary for a cohort (admin only)."""
        from catalog.models import Cohort
        from decimal import Decimal
        
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can view cohort payment summaries'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        cohort_id = request.query_params.get('cohort_id')
        if not cohort_id:
            return Response(
                {'error': 'cohort_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cohort = Cohort.objects.get(id=cohort_id)
        except Cohort.DoesNotExist:
            return Response(
                {'error': 'Cohort not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all enrollments for this cohort
        enrollments = cohort.enrollments.filter(status='ACTIVE').select_related('student')
        
        students_data = []
        total_expected = Decimal('0.00')
        total_paid = Decimal('0.00')
        
        for enrollment in enrollments:
            # Get invoice for enrollment
            invoice = enrollment.invoices.first()
            if invoice:
                total_expected += invoice.total_amount
                total_paid += invoice.paid_amount
                
                students_data.append({
                    'student_name': enrollment.student.get_full_name(),
                    'student_email': enrollment.student.email,
                    'invoice_number': invoice.invoice_number,
                    'total_amount': float(invoice.total_amount),
                    'paid_amount': float(invoice.paid_amount),
                    'outstanding_amount': float(invoice.outstanding_amount),
                    'status': invoice.status
                })
            else:
                # No invoice yet
                students_data.append({
                    'student_name': enrollment.student.get_full_name(),
                    'student_email': enrollment.student.email,
                    'invoice_number': None,
                    'total_amount': 0.0,
                    'paid_amount': 0.0,
                    'outstanding_amount': 0.0,
                    'status': 'NO_INVOICE'
                })
        
        return Response({
            'cohort_name': cohort.name,
            'cohort_id': str(cohort.id),
            'total_expected': float(total_expected),
            'total_paid': float(total_paid),
            'outstanding': float(total_expected - total_paid),
            'students': students_data
        })
    
    @extend_schema(
        tags=['Payments'],
        summary="Get student's own payments",
        description="Get all invoices and payments for the current student.",
        responses={
            200: {
                'type': 'array',
                'items': {'$ref': '#/components/schemas/Invoice'}
            },
            403: OpenApiTypes.OBJECT,
        }
    )
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """Get current student's invoices and payments."""
        if not request.user.is_student:
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all invoices for student's enrollments
        invoices = Invoice.objects.filter(
            enrollment__student=request.user
        ).select_related('enrollment', 'enrollment__cohort', 'payment_plan').order_by('-created_at')
        
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)


class PaymentViewSet(
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for Payment model."""
    queryset = Payment.objects.select_related(
        'organization', 'invoice', 'student', 'recorded_by'
    ).all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['invoice', 'student', 'status', 'payment_method']
    search_fields = ['payment_number', 'receipt_number']
    ordering_fields = ['payment_date', 'created_at']
    ordering = ['-payment_date']
    
    def get_permissions(self):
        """Restrict write operations to admin only."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'record_payment', 'process_refund']:
            return [permissions.IsAuthenticated(), IsAdminOrReadOnly()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students only see their own payments
        if user.is_student:
            queryset = queryset.filter(student=user)
        
        return queryset
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    @action(detail=False, methods=['post'])
    def record_payment(self, request):
        """Record a manual payment."""
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied("Only admins can record payments.")
        
        invoice_id = request.data.get('invoice')
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'MANUAL')
        
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise ValidationError({'invoice': 'Invoice not found.'})
        
        try:
            payment = PaymentService.record_payment(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                recorded_by=request.user,
                notes=request.data.get('notes', ''),
                payment_date=request.data.get('payment_date', timezone.now()),
            )
            
            serializer = self.get_serializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            raise ValidationError({'error': str(e)})
    
    @action(detail=True, methods=['post'])
    def process_refund(self, request, pk=None):
        """Process a refund for a payment."""
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied("Only admins can process refunds.")
        
        payment = self.get_object()
        amount = request.data.get('amount')
        reason = request.data.get('reason', '')
        
        try:
            payment = PaymentService.process_refund(
                payment=payment,
                amount=amount,
                reason=reason,
                recorded_by=request.user,
            )
            
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
        except ValueError as e:
            raise ValidationError({'error': str(e)})


class PaymentScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for PaymentSchedule model."""
    queryset = PaymentSchedule.objects.select_related('invoice').all()
    serializer_class = PaymentScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['invoice', 'status']
    ordering_fields = ['scheduled_date']
    ordering = ['scheduled_date']
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students only see their own payment schedules
        if user.is_student:
            queryset = queryset.filter(invoice__enrollment__student=user)
        
        return queryset
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")
    
    @action(detail=False, methods=['post'])
    def mark_overdue(self, request):
        """Check and mark overdue payment schedules."""
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied("Only admins can mark overdue payments.")
        
        count = PaymentScheduleService.check_overdue_payments()
        return Response({'overdue_count': count})


class PaymentMethodViewSet(
    OrganizationFilterMixin,
    OrganizationAutoSetMixin,
    viewsets.ModelViewSet
):
    """ViewSet for PaymentMethod model."""
    queryset = PaymentMethod.objects.select_related('organization').all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']

