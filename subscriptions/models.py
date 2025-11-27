"""
Subscription models for multi-tenant Academy CRM.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone


class OrganizationStatus(models.TextChoices):
    """Organization status choices."""
    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    TRIAL = 'TRIAL', _('Trial')
    INACTIVE = 'INACTIVE', _('Inactive')


class Organization(models.Model):
    """
    Organization model representing a tenant/academy.
    Each organization is isolated and can have its own subscription plan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text=_('Organization/Academy name'))
    domain = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Subdomain for this organization (e.g., "academy1" for academy1.yourdomain.com)')
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.TRIAL,
        help_text=_('Organization status')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Trial expiration date')
    )
    
    class Meta:
        db_table = 'organizations'
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')
        ordering = ['name']
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_trial_active(self):
        """Check if organization is in active trial period."""
        if self.status != OrganizationStatus.TRIAL:
            return False
        if self.trial_ends_at is None:
            return True
        return timezone.now() < self.trial_ends_at
    
    # --- Subscription limit helpers -------------------------------------------------
    def _get_subscription(self):
        """
        Safely return this organization's subscription, or None.
        
        Uses the reverse one-to-one relation but avoids raising if missing.
        """
        try:
            return self.subscription  # type: ignore[attr-defined]
        except Subscription.DoesNotExist:  # pragma: no cover - defensive
            return None
        except AttributeError:  # pragma: no cover - defensive
            return None
    
    def _get_plan_limits(self):
        """
        Return (max_users, max_students) tuple for this organization's plan.
        None means unlimited.
        """
        subscription = self._get_subscription()
        if not subscription or not subscription.plan or not subscription.is_active:
            return None, None
        plan = subscription.plan
        return plan.max_users, plan.max_students
    
    def can_add_user(self):
        """
        Check if another user can be added under the current subscription plan.
        
        Returns (allowed: bool, message: str | None)
        """
        max_users, _ = self._get_plan_limits()
        # Unlimited users for this plan
        if max_users is None:
            return True, None
        
        # Count active users in this organization
        current_users = self.users.filter(is_active=True).count()
        if current_users >= max_users:
            return False, _(
                f'User limit reached for the current subscription plan (max {max_users} users).'
            )
        return True, None
    
    def can_enroll_student(self):
        """
        Check if another student enrollment can be created under the plan.
        
        Returns (allowed: bool, message: str | None)
        """
        _, max_students = self._get_plan_limits()
        # Unlimited students for this plan
        if max_students is None:
            return True, None
        
        # Count active + pending enrollments in this organization
        active_statuses = ['ACTIVE', 'PENDING']
        current_enrollments = self.enrollments.filter(status__in=active_statuses).count()
        if current_enrollments >= max_students:
            return False, _(
                f'Student limit reached for the current subscription plan (max {max_students} students).'
            )
        return True, None


class BillingCycle(models.TextChoices):
    """Billing cycle choices."""
    MONTHLY = 'MONTHLY', _('Monthly')
    QUARTERLY = 'QUARTERLY', _('Quarterly')
    YEARLY = 'YEARLY', _('Yearly')


class SubscriptionPlan(models.Model):
    """
    Subscription plan model defining available plans and their features.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text=_('Plan name (e.g., Basic, Pro, Enterprise)'))
    description = models.TextField(blank=True, help_text=_('Plan description'))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Monthly price')
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        help_text=_('Billing cycle')
    )
    is_active = models.BooleanField(default=True, help_text=_('Is this plan currently available?'))
    max_users = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('Maximum number of users (null = unlimited)')
    )
    max_students = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('Maximum number of students (null = unlimited)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        verbose_name = _('subscription plan')
        verbose_name_plural = _('subscription plans')
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} (${self.price}/{self.billing_cycle.lower()})"


class PlanFeature(models.Model):
    """
    PlanFeature model maps subscription plans to enabled modules/features.
    Each feature represents a module that can be enabled/disabled.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name='features',
        help_text=_('Subscription plan')
    )
    module_name = models.CharField(
        max_length=50,
        help_text=_('Module name (e.g., attendance, assessment, timekeeping)')
    )
    enabled = models.BooleanField(default=True, help_text=_('Is this feature enabled for this plan?'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'plan_features'
        verbose_name = _('plan feature')
        verbose_name_plural = _('plan features')
        unique_together = [['plan', 'module_name']]
        indexes = [
            models.Index(fields=['plan', 'module_name']),
        ]
    
    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"{self.plan.name} - {self.module_name} ({status})"


class SubscriptionStatus(models.TextChoices):
    """Subscription status choices."""
    ACTIVE = 'ACTIVE', _('Active')
    TRIAL = 'TRIAL', _('Trial')
    EXPIRED = 'EXPIRED', _('Expired')
    CANCELLED = 'CANCELLED', _('Cancelled')
    SUSPENDED = 'SUSPENDED', _('Suspended')


class Subscription(models.Model):
    """
    Subscription model linking organizations to subscription plans.
    Tracks subscription status, dates, and billing information.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='subscription',
        help_text=_('Organization this subscription belongs to')
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        help_text=_('Subscription plan')
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
        help_text=_('Subscription status')
    )
    start_date = models.DateTimeField(auto_now_add=True, help_text=_('Subscription start date'))
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Subscription end date (null = ongoing)')
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Trial expiration date')
    )
    auto_renew = models.BooleanField(default=True, help_text=_('Auto-renew subscription?'))
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Cancellation date')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        verbose_name = _('subscription')
        verbose_name_plural = _('subscriptions')
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is currently active."""
        if self.status == SubscriptionStatus.CANCELLED:
            return False
        if self.status == SubscriptionStatus.SUSPENDED:
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True
    
    @property
    def is_trial(self):
        """Check if subscription is in trial period."""
        if self.status != SubscriptionStatus.TRIAL:
            return False
        if self.trial_ends_at is None:
            return True
        return timezone.now() < self.trial_ends_at


class Billing(models.Model):
    """
    Billing model for tracking payments and invoices.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='billings',
        help_text=_('Organization this billing belongs to')
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='billings',
        help_text=_('Subscription this billing is for')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Billing amount')
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', _('Pending')),
            ('PAID', _('Paid')),
            ('FAILED', _('Failed')),
            ('REFUNDED', _('Refunded')),
        ],
        default='PENDING',
        help_text=_('Payment status')
    )
    payment_date = models.DateTimeField(null=True, blank=True, help_text=_('Payment date'))
    due_date = models.DateTimeField(help_text=_('Payment due date'))
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Invoice number')
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Payment method (e.g., credit_card, paypal, bank_transfer)')
    )
    notes = models.TextField(blank=True, help_text=_('Additional notes'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billings'
        verbose_name = _('billing')
        verbose_name_plural = _('billings')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - ${self.amount} ({self.status})"

