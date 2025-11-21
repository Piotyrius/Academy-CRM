"""
Simple Django TestCase tests for payments app.
Run with: python manage.py test payments.tests_simple
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient
from rest_framework import status
from payments.models import (
    Pricing, PaymentPlan, Discount, Invoice, Payment,
    PaymentSchedule, PaymentPlanType, DiscountType,
    DiscountApplicableTo, InvoiceStatus, PaymentStatus,
    PaymentMethodCode
)
from payments.services import (
    PricingService, InvoiceService, DiscountService,
    PaymentService, PaymentScheduleService
)
from catalog.models import Program, Course, Cohort
from admissions.models import Enrollment, EnrollmentStatus
from accounts.models import User, Role
from subscriptions.models import Organization


class PaymentsTestCase(TestCase):
    """Base test case with common setup."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Academy',
            domain='testacademy',
            status='ACTIVE'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role=Role.ADMIN,
            organization=self.organization
        )
        
        self.student_user = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='User',
            role=Role.STUDENT,
            organization=self.organization
        )
        
        self.program = Program.objects.create(
            organization=self.organization,
            name='Full Stack Development',
            code='FSD',
            active=True
        )
        
        self.course = Course.objects.create(
            organization=self.organization,
            program=self.program,
            title='Web Development',
            code='WD101',
            hours=120
        )
        
        start_date = date.today()
        end_date = start_date + timedelta(days=90)
        self.cohort = Cohort.objects.create(
            organization=self.organization,
            course=self.course,
            name='FSD Cohort 2025-01',
            capacity=25,
            start_date=start_date,
            end_date=end_date
        )
        
        self.enrollment = Enrollment.objects.create(
            organization=self.organization,
            student=self.student_user,
            cohort=self.cohort,
            status=EnrollmentStatus.ACTIVE
        )
        
        # Create pricing
        content_type = ContentType.objects.get_for_model(Cohort)
        self.pricing_cohort = Pricing.objects.create(
            organization=self.organization,
            content_type=content_type,
            object_id=self.cohort.id,
            amount=Decimal('1000.00'),
            currency='USD',
            effective_from=date.today(),
            is_active=True
        )
        
        # Create payment plans
        self.payment_plan_full = PaymentPlan.objects.create(
            organization=self.organization,
            name='Full Payment',
            type=PaymentPlanType.FULL,
            discount_percentage=Decimal('10.00')
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)


class TestPricingService(PaymentsTestCase):
    """Test PricingService."""
    
    def test_get_pricing_for_enrollment(self):
        """Test getting pricing for enrollment."""
        pricing = PricingService.get_pricing_for_enrollment(self.enrollment)
        self.assertIsNotNone(pricing)
        self.assertEqual(pricing.amount, Decimal('1000.00'))
    
    def test_get_pricing_amount(self):
        """Test getting pricing amount."""
        amount = PricingService.get_pricing_amount(self.enrollment)
        self.assertEqual(amount, Decimal('1000.00'))


class TestInvoiceService(PaymentsTestCase):
    """Test InvoiceService."""
    
    def test_create_invoice_for_enrollment(self):
        """Test creating invoice for enrollment."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            self.enrollment, self.payment_plan_full
        )
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.enrollment, self.enrollment)
        self.assertEqual(invoice.pricing, self.pricing_cohort)
    
    def test_calculate_outstanding_amount(self):
        """Test calculating outstanding amount."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            self.enrollment, self.payment_plan_full
        )
        
        # Create a payment
        Payment.objects.create(
            organization=self.organization,
            invoice=invoice,
            student=self.student_user,
            payment_number='PAY-TEST-001',
            amount=Decimal('300.00'),
            currency='USD',
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            recorded_by=self.admin_user
        )
        
        outstanding = InvoiceService.calculate_outstanding_amount(invoice)
        self.assertGreater(outstanding, Decimal('0.00'))


class TestPaymentService(PaymentsTestCase):
    """Test PaymentService."""
    
    def test_record_payment(self):
        """Test recording a payment."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            self.enrollment, self.payment_plan_full
        )
        
        payment = PaymentService.record_payment(
            invoice=invoice,
            amount=Decimal('500.00'),
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            recorded_by=self.admin_user
        )
        self.assertEqual(payment.amount, Decimal('500.00'))
        self.assertEqual(payment.status, PaymentStatus.COMPLETED)


class TestInvoiceAPI(PaymentsTestCase):
    """Test Invoice API endpoints."""
    
    def test_create_invoice_for_enrollment(self):
        """Test creating invoice via API."""
        response = self.client.post('/api/v1/payments/invoices/create_for_enrollment/', {
            'enrollment': str(self.enrollment.id),
            'payment_plan': str(self.payment_plan_full.id)
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('invoice_number', response.data)
    
    def test_list_invoices(self):
        """Test listing invoices."""
        InvoiceService.create_invoice_for_enrollment(
            self.enrollment, self.payment_plan_full
        )
        
        response = self.client.get('/api/v1/payments/invoices/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

