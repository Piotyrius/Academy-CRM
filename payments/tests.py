"""
Comprehensive tests for payments app.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from payments.models import (
    Pricing, PaymentPlan, Discount, Invoice, Payment,
    PaymentSchedule, PaymentMethod, PaymentPlanType,
    DiscountType, DiscountApplicableTo, InvoiceStatus,
    PaymentStatus, PaymentMethodCode, PaymentGateway
)
from payments.services import (
    PricingService, InvoiceService, DiscountService,
    PaymentService, PaymentScheduleService
)
from catalog.models import Program, Course, Cohort
from admissions.models import Enrollment, EnrollmentStatus
from accounts.models import Role
from subscriptions.models import Organization


@pytest.fixture
def organization(db):
    """Create an organization."""
    return Organization.objects.create(
        name='Test Academy',
        domain='testacademy',
        status='ACTIVE'
    )


@pytest.fixture
def program(db, organization):
    """Create a program."""
    return Program.objects.create(
        organization=organization,
        name='Full Stack Development',
        code='FSD',
        active=True
    )


@pytest.fixture
def course(db, program):
    """Create a course."""
    return Course.objects.create(
        organization=program.organization,
        program=program,
        title='Web Development',
        code='WD101',
        hours=120
    )


@pytest.fixture
def cohort(db, course):
    """Create a cohort."""
    start_date = date.today()
    end_date = start_date + timedelta(days=90)
    return Cohort.objects.create(
        organization=course.organization,
        course=course,
        name='FSD Cohort 2025-01',
        capacity=25,
        start_date=start_date,
        end_date=end_date
    )


@pytest.fixture
def enrollment(db, student_user, cohort):
    """Create an enrollment."""
    return Enrollment.objects.create(
        organization=cohort.organization,
        student=student_user,
        cohort=cohort,
        status=EnrollmentStatus.ACTIVE
    )


@pytest.fixture
def pricing_cohort(db, organization, cohort):
    """Create pricing for a cohort."""
    content_type = ContentType.objects.get_for_model(Cohort)
    return Pricing.objects.create(
        organization=organization,
        content_type=content_type,
        object_id=cohort.id,
        amount=Decimal('1000.00'),
        currency='USD',
        effective_from=date.today(),
        is_active=True
    )


@pytest.fixture
def payment_plan_monthly(db, organization):
    """Create a monthly payment plan."""
    return PaymentPlan.objects.create(
        organization=organization,
        name='Monthly Installments',
        type=PaymentPlanType.MONTHLY,
        installment_count=3,
        discount_percentage=Decimal('0.00')
    )


@pytest.fixture
def payment_plan_full(db, organization):
    """Create a full payment plan."""
    return PaymentPlan.objects.create(
        organization=organization,
        name='Full Payment',
        type=PaymentPlanType.FULL,
        discount_percentage=Decimal('10.00')
    )


@pytest.fixture
def discount_full_payment(db, organization):
    """Create a full payment discount."""
    return Discount.objects.create(
        organization=organization,
        name='Early Bird Discount',
        type=DiscountType.PERCENTAGE,
        value=Decimal('15.00'),
        applicable_to=DiscountApplicableTo.FULL_PAYMENT,
        is_active=True,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timedelta(days=30)
    )


@pytest.fixture
def discount_sibling(db, organization):
    """Create a sibling discount."""
    return Discount.objects.create(
        organization=organization,
        name='Sibling Discount',
        type=DiscountType.PERCENTAGE,
        value=Decimal('10.00'),
        applicable_to=DiscountApplicableTo.SIBLING,
        is_active=True,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timedelta(days=365)
    )


@pytest.fixture
def invoice(db, enrollment, pricing_cohort, payment_plan_full):
    """Create an invoice."""
    return InvoiceService.create_invoice_for_enrollment(
        enrollment, payment_plan_full
    )


@pytest.fixture
def payment(db, invoice, student_user, admin_user):
    """Create a payment."""
    return Payment.objects.create(
        organization=invoice.organization,
        invoice=invoice,
        student=student_user,
        payment_number='PAY-TEST-001',
        amount=Decimal('500.00'),
        currency='USD',
        payment_method=PaymentMethodCode.BANK_TRANSFER,
        status=PaymentStatus.COMPLETED,
        payment_date=timezone.now(),
        recorded_by=admin_user
    )


# ==================== MODEL TESTS ====================

@pytest.mark.django_db
class TestPricingModel:
    """Test Pricing model."""
    
    def test_create_pricing(self, organization, cohort):
        """Test creating a pricing."""
        content_type = ContentType.objects.get_for_model(Cohort)
        pricing = Pricing.objects.create(
            organization=organization,
            content_type=content_type,
            object_id=cohort.id,
            amount=Decimal('1000.00'),
            currency='USD',
            effective_from=date.today()
        )
        assert pricing.amount == Decimal('1000.00')
        assert pricing.currency == 'USD'
        assert pricing.is_active is True
    
    def test_pricing_validation(self, organization, cohort):
        """Test pricing date validation."""
        content_type = ContentType.objects.get_for_model(Cohort)
        from django.core.exceptions import ValidationError
        
        pricing = Pricing(
            organization=organization,
            content_type=content_type,
            object_id=cohort.id,
            amount=Decimal('1000.00'),
            effective_from=date.today(),
            effective_to=date.today() - timedelta(days=1)  # Invalid: to < from
        )
        
        with pytest.raises(ValidationError):
            pricing.clean()


@pytest.mark.django_db
class TestPaymentPlanModel:
    """Test PaymentPlan model."""
    
    def test_create_monthly_plan(self, organization):
        """Test creating monthly payment plan."""
        plan = PaymentPlan.objects.create(
            organization=organization,
            name='Monthly Plan',
            type=PaymentPlanType.MONTHLY,
            installment_count=3
        )
        assert plan.type == PaymentPlanType.MONTHLY
        assert plan.installment_count == 3
    
    def test_create_full_payment_plan(self, organization):
        """Test creating full payment plan."""
        plan = PaymentPlan.objects.create(
            organization=organization,
            name='Full Payment',
            type=PaymentPlanType.FULL
        )
        assert plan.type == PaymentPlanType.FULL
        assert plan.installment_count is None
    
    def test_payment_plan_validation(self, organization):
        """Test payment plan validation."""
        from django.core.exceptions import ValidationError
        
        # Full payment plan should not have installment_count
        plan = PaymentPlan(
            organization=organization,
            name='Invalid Plan',
            type=PaymentPlanType.FULL,
            installment_count=3
        )
        
        with pytest.raises(ValidationError):
            plan.clean()
        
        # Monthly plan must have installment_count
        plan2 = PaymentPlan(
            organization=organization,
            name='Invalid Monthly',
            type=PaymentPlanType.MONTHLY
        )
        
        with pytest.raises(ValidationError):
            plan2.clean()


@pytest.mark.django_db
class TestDiscountModel:
    """Test Discount model."""
    
    def test_create_percentage_discount(self, organization):
        """Test creating percentage discount."""
        discount = Discount.objects.create(
            organization=organization,
            name='Test Discount',
            type=DiscountType.PERCENTAGE,
            value=Decimal('15.00'),
            applicable_to=DiscountApplicableTo.CUSTOM,
            is_active=True,
            valid_from=timezone.now()
        )
        assert discount.type == DiscountType.PERCENTAGE
        assert discount.value == Decimal('15.00')
    
    def test_create_fixed_amount_discount(self, organization):
        """Test creating fixed amount discount."""
        discount = Discount.objects.create(
            organization=organization,
            name='Fixed Discount',
            type=DiscountType.FIXED_AMOUNT,
            value=Decimal('100.00'),
            applicable_to=DiscountApplicableTo.CUSTOM,
            is_active=True,
            valid_from=timezone.now()
        )
        assert discount.type == DiscountType.FIXED_AMOUNT
        assert discount.value == Decimal('100.00')


@pytest.mark.django_db
class TestInvoiceModel:
    """Test Invoice model."""
    
    def test_create_invoice(self, enrollment, pricing_cohort, payment_plan_full):
        """Test creating an invoice."""
        invoice = Invoice.objects.create(
            organization=enrollment.organization,
            enrollment=enrollment,
            invoice_number='INV-TEST-20250101-ABCD1234',
            pricing=pricing_cohort,
            payment_plan=payment_plan_full,
            subtotal=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            total_amount=Decimal('900.00'),
            due_date=date.today() + timedelta(days=30)
        )
        assert invoice.total_amount == Decimal('900.00')
        assert invoice.outstanding_amount == Decimal('900.00')
        assert invoice.status == InvoiceStatus.DRAFT
    
    def test_invoice_outstanding_amount(self, enrollment, pricing_cohort, payment_plan_full):
        """Test invoice outstanding amount calculation."""
        invoice = Invoice.objects.create(
            organization=enrollment.organization,
            enrollment=enrollment,
            invoice_number='INV-TEST-20250101-ABCD1234',
            pricing=pricing_cohort,
            payment_plan=payment_plan_full,
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('300.00'),
            due_date=date.today() + timedelta(days=30)
        )
        assert invoice.outstanding_amount == Decimal('700.00')
    
    def test_invoice_validation(self, enrollment, pricing_cohort, payment_plan_full):
        """Test invoice validation."""
        from django.core.exceptions import ValidationError
        
        # Paid amount cannot exceed total amount
        invoice = Invoice(
            organization=enrollment.organization,
            enrollment=enrollment,
            invoice_number='INV-TEST-20250101-ABCD1234',
            pricing=pricing_cohort,
            payment_plan=payment_plan_full,
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1500.00'),  # Invalid
            due_date=date.today() + timedelta(days=30)
        )
        
        with pytest.raises(ValidationError):
            invoice.clean()


@pytest.mark.django_db
class TestPaymentModel:
    """Test Payment model."""
    
    def test_create_payment(self, invoice, student_user, admin_user):
        """Test creating a payment."""
        payment = Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            student=student_user,
            payment_number='PAY-TEST-20250101-ABCD1234',
            amount=Decimal('500.00'),
            currency='USD',
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            recorded_by=admin_user
        )
        assert payment.amount == Decimal('500.00')
        assert payment.status == PaymentStatus.COMPLETED


@pytest.mark.django_db
class TestPaymentScheduleModel:
    """Test PaymentSchedule model."""
    
    def test_create_payment_schedule(self, invoice):
        """Test creating payment schedule."""
        schedule = PaymentSchedule.objects.create(
            invoice=invoice,
            scheduled_date=date.today() + timedelta(days=30),
            amount=Decimal('333.33'),
            status='PENDING'
        )
        assert schedule.amount == Decimal('333.33')
        assert schedule.status == 'PENDING'


# ==================== SERVICE TESTS ====================

@pytest.mark.django_db
class TestPricingService:
    """Test PricingService."""
    
    def test_get_pricing_for_enrollment_cohort_level(self, enrollment, pricing_cohort):
        """Test getting pricing at cohort level."""
        pricing = PricingService.get_pricing_for_enrollment(enrollment)
        assert pricing is not None
        assert pricing.amount == Decimal('1000.00')
        assert pricing.pricing_object == enrollment.cohort
    
    def test_get_pricing_for_enrollment_course_level(self, enrollment, organization, course):
        """Test getting pricing at course level (when cohort pricing doesn't exist)."""
        # Create course-level pricing
        content_type = ContentType.objects.get_for_model(Course)
        Pricing.objects.create(
            organization=organization,
            content_type=content_type,
            object_id=course.id,
            amount=Decimal('900.00'),
            currency='USD',
            effective_from=date.today(),
            is_active=True
        )
        
        pricing = PricingService.get_pricing_for_enrollment(enrollment)
        assert pricing is not None
        assert pricing.amount == Decimal('900.00')
        assert pricing.pricing_object == course
    
    def test_get_pricing_for_enrollment_program_level(self, enrollment, organization, program):
        """Test getting pricing at program level."""
        # Create program-level pricing
        content_type = ContentType.objects.get_for_model(Program)
        Pricing.objects.create(
            organization=organization,
            content_type=content_type,
            object_id=program.id,
            amount=Decimal('800.00'),
            currency='USD',
            effective_from=date.today(),
            is_active=True
        )
        
        pricing = PricingService.get_pricing_for_enrollment(enrollment)
        assert pricing is not None
        assert pricing.amount == Decimal('800.00')
        assert pricing.pricing_object == program
    
    def test_get_pricing_amount(self, enrollment, pricing_cohort):
        """Test getting pricing amount."""
        amount = PricingService.get_pricing_amount(enrollment)
        assert amount == Decimal('1000.00')


@pytest.mark.django_db
class TestInvoiceService:
    """Test InvoiceService."""
    
    def test_generate_invoice_number(self, organization):
        """Test invoice number generation."""
        invoice_number = InvoiceService.generate_invoice_number(organization)
        assert invoice_number.startswith('INV-')
        assert organization.domain[:4].upper() in invoice_number or organization.name[:4].upper().replace(' ', '') in invoice_number
    
    def test_create_invoice_for_enrollment(self, enrollment, pricing_cohort, payment_plan_full):
        """Test creating invoice for enrollment."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_full
        )
        assert invoice is not None
        assert invoice.enrollment == enrollment
        assert invoice.pricing == pricing_cohort
        assert invoice.payment_plan == payment_plan_full
        assert invoice.subtotal == Decimal('900.00')  # 1000 - 10% discount
        assert invoice.total_amount == Decimal('900.00')
        assert invoice.status == InvoiceStatus.DRAFT
    
    def test_create_invoice_with_discounts(self, enrollment, pricing_cohort, payment_plan_full, discount_full_payment):
        """Test creating invoice with discounts."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_full, [discount_full_payment]
        )
        assert invoice.discount_amount > Decimal('0.00')
        assert invoice.total_amount < invoice.subtotal
    
    def test_calculate_outstanding_amount(self, enrollment, pricing_cohort, payment_plan_full, student_user, admin_user):
        """Test calculating outstanding amount."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_full
        )
        
        # Create a payment
        Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            student=student_user,
            payment_number='PAY-TEST-001',
            amount=Decimal('300.00'),
            currency='USD',
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            recorded_by=admin_user
        )
        
        outstanding = InvoiceService.calculate_outstanding_amount(invoice)
        assert outstanding == Decimal('600.00')  # 900 - 300
    
    def test_update_invoice_status(self, enrollment, pricing_cohort, payment_plan_full, student_user, admin_user):
        """Test updating invoice status."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_full
        )
        
        # Partially pay
        Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            student=student_user,
            payment_number='PAY-TEST-001',
            amount=Decimal('300.00'),
            currency='USD',
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            recorded_by=admin_user
        )
        
        InvoiceService.update_invoice_status(invoice)
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.PARTIAL
        
        # Pay in full
        Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            student=student_user,
            payment_number='PAY-TEST-002',
            amount=Decimal('600.00'),
            currency='USD',
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            recorded_by=admin_user
        )
        
        InvoiceService.update_invoice_status(invoice)
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.PAID
    
    def test_issue_invoice(self, enrollment, pricing_cohort, payment_plan_full):
        """Test issuing an invoice."""
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_full
        )
        assert invoice.status == InvoiceStatus.DRAFT
        
        InvoiceService.issue_invoice(invoice)
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.issued_at is not None


@pytest.mark.django_db
class TestDiscountService:
    """Test DiscountService."""
    
    def test_get_applicable_discounts_full_payment(self, invoice, student_user, enrollment, discount_full_payment, payment_plan_full):
        """Test getting applicable discounts for full payment."""
        invoice.payment_plan = payment_plan_full
        invoice.save()
        
        discounts = DiscountService.get_applicable_discounts(
            invoice, student_user, enrollment
        )
        assert len(discounts) >= 1
        assert discount_full_payment in discounts
    
    def test_calculate_discount_amount_percentage(self, invoice, discount_full_payment):
        """Test calculating percentage discount."""
        invoice.subtotal = Decimal('1000.00')
        discount_amount = DiscountService.calculate_discount_amount(
            discount_full_payment, invoice
        )
        assert discount_amount == Decimal('150.00')  # 15% of 1000
    
    def test_calculate_discount_amount_fixed(self, invoice, organization):
        """Test calculating fixed amount discount."""
        discount = Discount.objects.create(
            organization=organization,
            name='Fixed Discount',
            type=DiscountType.FIXED_AMOUNT,
            value=Decimal('100.00'),
            applicable_to=DiscountApplicableTo.CUSTOM,
            is_active=True,
            valid_from=timezone.now()
        )
        invoice.subtotal = Decimal('1000.00')
        discount_amount = DiscountService.calculate_discount_amount(discount, invoice)
        assert discount_amount == Decimal('100.00')
    
    def test_apply_discounts_to_invoice(self, invoice, discount_full_payment):
        """Test applying discounts to invoice."""
        invoice.subtotal = Decimal('1000.00')
        DiscountService.apply_discounts_to_invoice(invoice, [discount_full_payment])
        assert invoice.discount_amount == Decimal('150.00')
        assert invoice.total_amount == Decimal('850.00')


@pytest.mark.django_db
class TestPaymentService:
    """Test PaymentService."""
    
    def test_generate_payment_number(self, organization):
        """Test payment number generation."""
        payment_number = PaymentService.generate_payment_number(organization)
        assert payment_number.startswith('PAY-')
    
    def test_generate_receipt_number(self, organization):
        """Test receipt number generation."""
        receipt_number = PaymentService.generate_receipt_number(organization)
        assert receipt_number.startswith('RCP-')
    
    def test_record_payment(self, invoice, admin_user):
        """Test recording a payment."""
        payment = PaymentService.record_payment(
            invoice=invoice,
            amount=Decimal('500.00'),
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            recorded_by=admin_user
        )
        assert payment.amount == Decimal('500.00')
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.recorded_by == admin_user
        
        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('500.00')
    
    def test_record_payment_exceeds_outstanding(self, invoice, admin_user):
        """Test that payment cannot exceed outstanding amount."""
        invoice.total_amount = Decimal('1000.00')
        invoice.save()
        
        with pytest.raises(ValueError, match='exceeds outstanding'):
            PaymentService.record_payment(
                invoice=invoice,
                amount=Decimal('1500.00'),
                payment_method=PaymentMethodCode.BANK_TRANSFER,
                recorded_by=admin_user
            )
    
    def test_process_refund(self, invoice, student_user, admin_user):
        """Test processing a refund."""
        # Create a payment first
        payment = Payment.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            student=student_user,
            payment_number='PAY-TEST-001',
            amount=Decimal('500.00'),
            currency='USD',
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            recorded_by=admin_user
        )
        
        # Process refund
        refunded_payment = PaymentService.process_refund(
            payment=payment,
            amount=Decimal('200.00'),
            reason='Partial refund requested',
            recorded_by=admin_user
        )
        
        assert refunded_payment.refund_amount == Decimal('200.00')
        assert refunded_payment.status == PaymentStatus.REFUNDED
        
        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('300.00')  # 500 - 200


@pytest.mark.django_db
class TestPaymentScheduleService:
    """Test PaymentScheduleService."""
    
    def test_create_payment_schedule_full_payment(self, invoice, payment_plan_full):
        """Test creating schedule for full payment."""
        schedules = PaymentScheduleService.create_payment_schedule(
            invoice, payment_plan_full
        )
        assert len(schedules) == 1
        assert schedules[0].amount == invoice.total_amount
        assert schedules[0].status == 'PENDING'
    
    def test_create_payment_schedule_monthly(self, invoice, payment_plan_monthly):
        """Test creating schedule for monthly installments."""
        invoice.total_amount = Decimal('900.00')
        invoice.save()
        
        schedules = PaymentScheduleService.create_payment_schedule(
            invoice, payment_plan_monthly
        )
        assert len(schedules) == 3  # 3 installments
        assert sum(s.amount for s in schedules) == invoice.total_amount
    
    def test_check_overdue_payments(self, invoice, payment_plan_full):
        """Test checking overdue payments."""
        # Create schedule with past date
        schedule = PaymentSchedule.objects.create(
            invoice=invoice,
            scheduled_date=date.today() - timedelta(days=10),
            amount=Decimal('300.00'),
            status='PENDING'
        )
        
        count = PaymentScheduleService.check_overdue_payments()
        assert count >= 1
        
        schedule.refresh_from_db()
        assert schedule.status == 'OVERDUE'
    
    def test_apply_late_fees(self, invoice, payment_plan_full):
        """Test applying late fees."""
        schedule = PaymentSchedule.objects.create(
            invoice=invoice,
            scheduled_date=date.today() - timedelta(days=10),
            amount=Decimal('300.00'),
            status='OVERDUE'
        )
        
        late_fee = PaymentScheduleService.apply_late_fees(
            schedule, late_fee_percentage=Decimal('5.00')
        )
        assert late_fee > Decimal('0.00')
        
        schedule.refresh_from_db()
        assert schedule.late_fee > Decimal('0.00')
        
        invoice.refresh_from_db()
        assert invoice.total_amount > Decimal('900.00')  # Original + late fee


# ==================== API ENDPOINT TESTS ====================

@pytest.mark.django_db
class TestPricingAPI:
    """Test Pricing API endpoints."""
    
    def test_list_pricings(self, authenticated_admin_client, organization, pricing_cohort):
        """Test listing pricings."""
        response = authenticated_admin_client.get('/api/v1/payments/pricings/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_pricing(self, authenticated_admin_client, organization, cohort):
        """Test creating a pricing."""
        content_type = ContentType.objects.get_for_model(Cohort)
        response = authenticated_admin_client.post('/api/v1/payments/pricings/', {
            'organization': str(organization.id),
            'content_type': content_type.id,
            'object_id': str(cohort.id),
            'amount': '1500.00',
            'currency': 'USD',
            'effective_from': date.today().isoformat(),
            'is_active': True
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Pricing.objects.filter(amount=Decimal('1500.00')).exists()


@pytest.mark.django_db
class TestPaymentPlanAPI:
    """Test PaymentPlan API endpoints."""
    
    def test_list_payment_plans(self, authenticated_admin_client, payment_plan_monthly):
        """Test listing payment plans."""
        response = authenticated_admin_client.get('/api/v1/payments/payment-plans/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_payment_plan(self, authenticated_admin_client, organization):
        """Test creating a payment plan."""
        response = authenticated_admin_client.post('/api/v1/payments/payment-plans/', {
            'organization': str(organization.id),
            'name': 'Quarterly Plan',
            'type': 'MONTHLY',
            'installment_count': 4,
            'discount_percentage': '5.00',
            'is_active': True
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert PaymentPlan.objects.filter(name='Quarterly Plan').exists()


@pytest.mark.django_db
class TestDiscountAPI:
    """Test Discount API endpoints."""
    
    def test_list_discounts(self, authenticated_admin_client, discount_full_payment):
        """Test listing discounts."""
        response = authenticated_admin_client.get('/api/v1/payments/discounts/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_discount(self, authenticated_admin_client, organization):
        """Test creating a discount."""
        response = authenticated_admin_client.post('/api/v1/payments/discounts/', {
            'organization': str(organization.id),
            'name': 'Summer Discount',
            'type': 'PERCENTAGE',
            'value': '20.00',
            'applicable_to': 'CUSTOM',
            'is_active': True,
            'valid_from': timezone.now().isoformat()
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Discount.objects.filter(name='Summer Discount').exists()


@pytest.mark.django_db
class TestInvoiceAPI:
    """Test Invoice API endpoints."""
    
    def test_list_invoices(self, authenticated_admin_client, invoice):
        """Test listing invoices."""
        response = authenticated_admin_client.get('/api/v1/payments/invoices/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_create_invoice_for_enrollment(self, authenticated_admin_client, enrollment, payment_plan_full):
        """Test creating invoice for enrollment."""
        response = authenticated_admin_client.post('/api/v1/payments/invoices/create_for_enrollment/', {
            'enrollment': str(enrollment.id),
            'payment_plan': str(payment_plan_full.id)
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'invoice_number' in response.data
        assert Invoice.objects.filter(enrollment=enrollment).exists()
    
    def test_get_outstanding_balance(self, authenticated_admin_client, invoice):
        """Test getting outstanding balance."""
        response = authenticated_admin_client.get(f'/api/v1/payments/invoices/{invoice.id}/outstanding_balance/')
        assert response.status_code == status.HTTP_200_OK
        assert 'outstanding_amount' in response.data
        assert 'total_amount' in response.data
    
    def test_issue_invoice(self, authenticated_admin_client, invoice):
        """Test issuing an invoice."""
        response = authenticated_admin_client.post(f'/api/v1/payments/invoices/{invoice.id}/issue/')
        assert response.status_code == status.HTTP_200_OK
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.ISSUED


@pytest.mark.django_db
class TestPaymentAPI:
    """Test Payment API endpoints."""
    
    def test_list_payments(self, authenticated_admin_client, payment):
        """Test listing payments."""
        response = authenticated_admin_client.get('/api/v1/payments/payments/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_record_payment(self, authenticated_admin_client, invoice, admin_user):
        """Test recording a payment."""
        response = authenticated_admin_client.post('/api/v1/payments/payments/record_payment/', {
            'invoice': str(invoice.id),
            'amount': '500.00',
            'payment_method': 'BANK_TRANSFER',
            'notes': 'Payment received'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Payment.objects.filter(invoice=invoice).exists()
    
    def test_process_refund(self, authenticated_admin_client, payment):
        """Test processing a refund."""
        response = authenticated_admin_client.post(f'/api/v1/payments/payments/{payment.id}/process_refund/', {
            'amount': '100.00',
            'reason': 'Customer requested refund'
        })
        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.refund_amount == Decimal('100.00')


@pytest.mark.django_db
class TestPaymentScheduleAPI:
    """Test PaymentSchedule API endpoints."""
    
    def test_list_payment_schedules(self, authenticated_admin_client, invoice):
        """Test listing payment schedules."""
        PaymentSchedule.objects.create(
            invoice=invoice,
            scheduled_date=date.today() + timedelta(days=30),
            amount=Decimal('300.00')
        )
        
        response = authenticated_admin_client.get('/api/v1/payments/payment-schedules/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_mark_overdue(self, authenticated_admin_client, invoice):
        """Test marking overdue payments."""
        PaymentSchedule.objects.create(
            invoice=invoice,
            scheduled_date=date.today() - timedelta(days=10),
            amount=Decimal('300.00'),
            status='PENDING'
        )
        
        response = authenticated_admin_client.post('/api/v1/payments/payment-schedules/mark_overdue/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['overdue_count'] >= 1


# ==================== INTEGRATION TESTS ====================

@pytest.mark.django_db
class TestPaymentFlow:
    """Test complete payment flow."""
    
    def test_complete_payment_flow(self, authenticated_admin_client, enrollment, pricing_cohort, payment_plan_full, student_user, admin_user):
        """Test complete flow from invoice creation to payment."""
        # 1. Create invoice
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_full
        )
        assert invoice.status == InvoiceStatus.DRAFT
        
        # 2. Create payment schedule
        schedules = PaymentScheduleService.create_payment_schedule(
            invoice, payment_plan_full
        )
        assert len(schedules) == 1
        
        # 3. Record payment
        payment = PaymentService.record_payment(
            invoice=invoice,
            amount=invoice.total_amount,
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            recorded_by=admin_user
        )
        assert payment.status == PaymentStatus.COMPLETED
        
        # 4. Update invoice status
        InvoiceService.update_invoice_status(invoice)
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.PAID
        
        # 5. Link payment to schedule
        PaymentService.apply_payment_to_schedule(payment, schedules[0])
        schedules[0].refresh_from_db()
        assert schedules[0].status == 'PAID'
    
    def test_monthly_installment_flow(self, authenticated_admin_client, enrollment, pricing_cohort, payment_plan_monthly, student_user, admin_user):
        """Test monthly installment payment flow."""
        # Create invoice
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment, payment_plan_monthly
        )
        invoice.total_amount = Decimal('900.00')
        invoice.save()
        
        # Create schedule
        schedules = PaymentScheduleService.create_payment_schedule(
            invoice, payment_plan_monthly
        )
        assert len(schedules) == 3
        
        # Pay first installment
        payment1 = PaymentService.record_payment(
            invoice=invoice,
            amount=schedules[0].amount,
            payment_method=PaymentMethodCode.BANK_TRANSFER,
            recorded_by=admin_user
        )
        PaymentService.apply_payment_to_schedule(payment1, schedules[0])
        
        schedules[0].refresh_from_db()
        assert schedules[0].status == 'PAID'
        
        # Check invoice status
        InvoiceService.update_invoice_status(invoice)
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.PARTIAL


# ==================== EDGE CASES & IMPROVEMENTS ====================

@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_pricing_found(self, enrollment):
        """Test when no pricing is found for enrollment."""
        pricing = PricingService.get_pricing_for_enrollment(enrollment)
        assert pricing is None
        
        amount = PricingService.get_pricing_amount(enrollment)
        assert amount is None
    
    def test_multiple_discounts(self, invoice, organization):
        """Test applying multiple discounts."""
        discount1 = Discount.objects.create(
            organization=organization,
            name='Discount 1',
            type=DiscountType.PERCENTAGE,
            value=Decimal('10.00'),
            applicable_to=DiscountApplicableTo.CUSTOM,
            is_active=True,
            valid_from=timezone.now()
        )
        discount2 = Discount.objects.create(
            organization=organization,
            name='Discount 2',
            type=DiscountType.FIXED_AMOUNT,
            value=Decimal('50.00'),
            applicable_to=DiscountApplicableTo.CUSTOM,
            is_active=True,
            valid_from=timezone.now()
        )
        
        invoice.subtotal = Decimal('1000.00')
        DiscountService.apply_discounts_to_invoice(invoice, [discount1, discount2])
        
        # Should apply both discounts
        assert invoice.discount_amount > Decimal('0.00')
        assert invoice.total_amount < invoice.subtotal
    
    def test_discount_max_cap(self, invoice, organization):
        """Test discount maximum cap."""
        discount = Discount.objects.create(
            organization=organization,
            name='Capped Discount',
            type=DiscountType.PERCENTAGE,
            value=Decimal('50.00'),  # 50% discount
            max_discount=Decimal('100.00'),  # But capped at $100
            applicable_to=DiscountApplicableTo.CUSTOM,
            is_active=True,
            valid_from=timezone.now()
        )
        
        invoice.subtotal = Decimal('1000.00')
        discount_amount = DiscountService.calculate_discount_amount(discount, invoice)
        assert discount_amount == Decimal('100.00')  # Capped, not $500
    
    def test_refund_exceeds_payment(self, payment):
        """Test that refund cannot exceed payment amount."""
        with pytest.raises(ValueError, match='exceeds'):
            PaymentService.process_refund(
                payment=payment,
                amount=payment.amount + Decimal('100.00'),
                reason='Test',
                recorded_by=payment.recorded_by
            )
