"""
Payment models for Academy CRM.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from accounts.models import User
from catalog.models import Program, Course, Cohort
from admissions.models import Enrollment


class Pricing(models.Model):
    """Flexible pricing model that can be set at Program, Course, or Cohort level."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='pricings',
        null=True,
        blank=True,
        help_text=_('Organization this pricing belongs to')
    )
    # Generic ForeignKey for flexible pricing levels.
    # Currently supports Program, Course, and Cohort; other models are rejected
    # in clean() to keep the domain explicit and pave the way for future
    # migration to concrete foreign keys.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    pricing_object = GenericForeignKey('content_type', 'object_id')
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Pricing amount')
    )
    currency = models.CharField(max_length=3, default='USD', help_text=_('Currency code'))
    effective_from = models.DateField(help_text=_('Price effective from date'))
    effective_to = models.DateField(null=True, blank=True, help_text=_('Price effective to date (null = ongoing)'))
    is_active = models.BooleanField(default=True, help_text=_('Is this pricing active?'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pricings'
        verbose_name = _('pricing')
        verbose_name_plural = _('pricings')
        ordering = ['-effective_from']
        unique_together = [['content_type', 'object_id', 'effective_from']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['effective_from', 'effective_to']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        obj_name = str(self.pricing_object) if self.pricing_object else 'Unknown'
        return f"{obj_name} - {self.amount} {self.currency} (from {self.effective_from})"
    
    def clean(self):
        """Validate pricing dates and target object type."""
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError(_('Effective to date must be after effective from date.'))
        
        # Restrict pricing targets to Program, Course, or Cohort to avoid
        # arbitrary generic relations and make future schema migration easier.
        allowed_models = {Program, Course, Cohort}
        if self.pricing_object is not None and type(self.pricing_object) not in allowed_models:
            raise ValidationError(
                _('Pricing can only be attached to Program, Course, or Cohort objects.')
            )
    
    # Convenience helpers to make querying and future migrations easier
    @property
    def is_program_pricing(self) -> bool:
        return isinstance(self.pricing_object, Program)

    @property
    def is_course_pricing(self) -> bool:
        return isinstance(self.pricing_object, Course)

    @property
    def is_cohort_pricing(self) -> bool:
        return isinstance(self.pricing_object, Cohort)


class PaymentPlanType(models.TextChoices):
    """Payment plan type choices."""
    MONTHLY = 'MONTHLY', _('Monthly Installments')
    FULL = 'FULL', _('Full Payment')
    CUSTOM = 'CUSTOM', _('Custom Plan')


class PaymentPlan(models.Model):
    """Defines payment structure (monthly installments, full payment, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='payment_plans',
        null=True,
        blank=True,
        help_text=_('Organization this payment plan belongs to')
    )
    name = models.CharField(max_length=100, help_text=_('Payment plan name'))
    type = models.CharField(
        max_length=20,
        choices=PaymentPlanType.choices,
        default=PaymentPlanType.MONTHLY,
        help_text=_('Payment plan type')
    )
    installment_count = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=_('Number of installments (null for full payment)')
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text=_('Discount percentage for this plan')
    )
    is_active = models.BooleanField(default=True, help_text=_('Is this plan active?'))
    description = models.TextField(blank=True, help_text=_('Plan description'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_plans'
        verbose_name = _('payment plan')
        verbose_name_plural = _('payment plans')
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def clean(self):
        """Validate payment plan."""
        if self.type == PaymentPlanType.FULL and self.installment_count:
            raise ValidationError(_('Full payment plans cannot have installment count.'))
        if self.type == PaymentPlanType.MONTHLY and not self.installment_count:
            raise ValidationError(_('Monthly plans must have installment count.'))


class DiscountType(models.TextChoices):
    """Discount type choices."""
    PERCENTAGE = 'PERCENTAGE', _('Percentage')
    FIXED_AMOUNT = 'FIXED_AMOUNT', _('Fixed Amount')


class DiscountApplicableTo(models.TextChoices):
    """Discount applicable to choices."""
    FULL_PAYMENT = 'FULL_PAYMENT', _('Full Payment')
    SIBLING = 'SIBLING', _('Sibling Discount')
    CUSTOM = 'CUSTOM', _('Custom')


class Discount(models.Model):
    """Flexible discount system."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='discounts',
        null=True,
        blank=True,
        help_text=_('Organization this discount belongs to')
    )
    name = models.CharField(max_length=100, help_text=_('Discount name'))
    type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
        help_text=_('Discount type')
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Discount value (percentage or fixed amount)')
    )
    applicable_to = models.CharField(
        max_length=20,
        choices=DiscountApplicableTo.choices,
        default=DiscountApplicableTo.CUSTOM,
        help_text=_('Discount applicable to')
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Discount code (for future promo codes)')
    )
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_('Minimum purchase amount for discount')
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_('Maximum discount amount (cap)')
    )
    is_active = models.BooleanField(default=True, help_text=_('Is this discount active?'))
    valid_from = models.DateTimeField(help_text=_('Discount valid from'))
    valid_to = models.DateTimeField(null=True, blank=True, help_text=_('Discount valid to (null = ongoing)'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'discounts'
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class InvoiceStatus(models.TextChoices):
    """Invoice status choices."""
    DRAFT = 'DRAFT', _('Draft')
    ISSUED = 'ISSUED', _('Issued')
    PARTIAL = 'PARTIAL', _('Partially Paid')
    PAID = 'PAID', _('Paid')
    OVERDUE = 'OVERDUE', _('Overdue')
    CANCELLED = 'CANCELLED', _('Cancelled')


class Invoice(models.Model):
    """Invoice model tracking what student owes for an enrollment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='invoices',
        null=True,
        blank=True,
        help_text=_('Organization this invoice belongs to')
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text=_('Enrollment this invoice is for')
    )
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Unique invoice number')
    )
    pricing = models.ForeignKey(
        Pricing,
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text=_('Pricing used for this invoice')
    )
    payment_plan = models.ForeignKey(
        PaymentPlan,
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text=_('Payment plan for this invoice')
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Subtotal before discounts')
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text=_('Total discount amount')
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Total amount due')
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text=_('Total amount paid')
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        help_text=_('Invoice status')
    )
    due_date = models.DateField(help_text=_('Payment due date'))
    issued_at = models.DateTimeField(null=True, blank=True, help_text=_('Invoice issued date'))
    email_sent = models.BooleanField(default=False, help_text=_('Whether invoice email has been sent'))
    email_sent_at = models.DateTimeField(null=True, blank=True, help_text=_('When invoice email was sent'))
    notes = models.TextField(blank=True, help_text=_('Additional notes'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        verbose_name = _('invoice')
        verbose_name_plural = _('invoices')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['enrollment']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.enrollment.student.get_full_name()}"
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount."""
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)
    
    def clean(self):
        """Validate invoice amounts."""
        if self.paid_amount > self.total_amount:
            raise ValidationError(_('Paid amount cannot exceed total amount.'))
        if self.discount_amount > self.subtotal:
            raise ValidationError(_('Discount amount cannot exceed subtotal.'))


class PaymentStatus(models.TextChoices):
    """Payment status choices."""
    PENDING = 'PENDING', _('Pending')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')
    REFUNDED = 'REFUNDED', _('Refunded')


class PaymentMethodCode(models.TextChoices):
    """Payment method code choices."""
    MANUAL = 'MANUAL', _('Manual Entry')
    CASH = 'CASH', _('Cash')
    BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
    CREDIT_CARD = 'CREDIT_CARD', _('Credit Card')
    DEBIT_CARD = 'DEBIT_CARD', _('Debit Card')
    CHECK = 'CHECK', _('Check')
    OTHER = 'OTHER', _('Other')


class PaymentGateway(models.TextChoices):
    """Payment gateway choices (for future e-commerce)."""
    MANUAL = 'MANUAL', _('Manual')
    STRIPE = 'STRIPE', _('Stripe')
    PAYPAL = 'PAYPAL', _('PayPal')
    SQUARE = 'SQUARE', _('Square')
    OTHER = 'OTHER', _('Other')


class Payment(models.Model):
    """Payment model recording actual payments made."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True,
        help_text=_('Organization this payment belongs to')
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text=_('Invoice this payment is for')
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_payments',
        limit_choices_to={'role': 'STUDENT'},
        help_text=_('Student who made the payment')
    )
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Unique payment number')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Payment amount')
    )
    currency = models.CharField(max_length=3, default='USD', help_text=_('Currency code'))
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethodCode.choices,
        default=PaymentMethodCode.MANUAL,
        help_text=_('Payment method')
    )
    payment_gateway = models.CharField(
        max_length=20,
        choices=PaymentGateway.choices,
        default=PaymentGateway.MANUAL,
        null=True,
        blank=True,
        help_text=_('Payment gateway (for e-commerce)')
    )
    gateway_transaction_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_('Gateway transaction ID (for e-commerce)')
    )
    gateway_response = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Gateway response data (for e-commerce)')
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text=_('Payment status')
    )
    payment_date = models.DateTimeField(help_text=_('Payment date'))
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_payments',
        help_text=_('Admin who recorded this payment')
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Receipt number')
    )
    notes = models.TextField(blank=True, help_text=_('Additional notes'))
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text=_('Refund amount')
    )
    refund_reason = models.TextField(blank=True, help_text=_('Refund reason'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['invoice']),
            models.Index(fields=['student']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['gateway_transaction_id']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_number} - {self.amount} {self.currency}"

    def clean(self):
        """
        Basic validation for gateway-related fields.

        For manual payments, gateway fields are optional. For real gateways
        (Stripe, PayPal, etc.), a transaction ID should be present once the
        payment is marked as completed to ensure traceability.
        """
        # Avoid circular import at module import time
        from .models import PaymentGateway, PaymentStatus  # type: ignore

        if (
            self.payment_gateway
            and self.payment_gateway != PaymentGateway.MANUAL
            and self.status == PaymentStatus.COMPLETED
            and not self.gateway_transaction_id
        ):
            raise ValidationError(
                _('gateway_transaction_id is required for completed gateway payments.')
            )


class PaymentScheduleStatus(models.TextChoices):
    """Payment schedule status choices."""
    PENDING = 'PENDING', _('Pending')
    PAID = 'PAID', _('Paid')
    OVERDUE = 'OVERDUE', _('Overdue')
    SKIPPED = 'SKIPPED', _('Skipped')


class PaymentSchedule(models.Model):
    """Payment schedule model tracking scheduled installment payments."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payment_schedules',
        help_text=_('Invoice this schedule item belongs to')
    )
    scheduled_date = models.DateField(help_text=_('Scheduled payment date'))
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Scheduled payment amount')
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentScheduleStatus.choices,
        default=PaymentScheduleStatus.PENDING,
        help_text=_('Schedule status')
    )
    paid_payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_schedules',
        help_text=_('Payment that fulfilled this schedule item')
    )
    late_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text=_('Late fee applied')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_schedules'
        verbose_name = _('payment schedule')
        verbose_name_plural = _('payment schedules')
        ordering = ['scheduled_date']
        indexes = [
            models.Index(fields=['invoice']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Schedule {self.scheduled_date} - {self.amount} ({self.get_status_display()})"


class PaymentMethod(models.Model):
    """Payment method configuration for admin."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='payment_methods',
        null=True,
        blank=True,
        help_text=_('Organization this payment method belongs to')
    )
    name = models.CharField(max_length=100, help_text=_('Payment method name'))
    code = models.CharField(
        max_length=50,
        help_text=_('Payment method code')
    )
    is_active = models.BooleanField(default=True, help_text=_('Is this payment method active?'))
    requires_receipt = models.BooleanField(
        default=False,
        help_text=_('Does this payment method require a receipt?')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = _('payment method')
        verbose_name_plural = _('payment methods')
        ordering = ['name']
        unique_together = [['organization', 'code']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"

