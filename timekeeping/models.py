"""
Models for lecturer timekeeping and payroll basics.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class Rate(models.Model):
    """Simple per-lecturer hourly rate.

    Amounts are stored in minor units (e.g., cents) for precision.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='rates',
        null=True,
        blank=True,
        help_text=_('Organization this rate belongs to')
    )
    lecturer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='rates')
    per_hour_minor = models.BigIntegerField(validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='USD')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tk_rates'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['lecturer', 'active'])
        ]
        constraints = [
            models.UniqueConstraint(fields=['lecturer'], condition=models.Q(active=True), name='tk_one_active_rate_per_lecturer'),
        ]

    def __str__(self):
        return f"{self.lecturer.email} @ {Decimal(self.per_hour_minor) / 100} {self.currency}/h"


class WorkLogSource(models.TextChoices):
    SESSION = 'SESSION', _('From session')
    MANUAL = 'MANUAL', _('Manual entry')


class WorkLog(models.Model):
    """Recorded lecturer working time.

    Phase 1: primarily generated from sessions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='worklogs',
        null=True,
        blank=True,
        help_text=_('Organization this worklog belongs to')
    )
    lecturer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='worklogs')
    session = models.ForeignKey('catalog.Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    minutes = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    source = models.CharField(max_length=10, choices=WorkLogSource.choices, default=WorkLogSource.SESSION)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tk_worklogs'
        ordering = ['-start_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['lecturer', 'start_at']),
            models.Index(fields=['session']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(end_at__gt=models.F('start_at')), name='tk_worklog_valid_range'),
        ]

    def __str__(self):
        return f"{self.lecturer.email} {self.start_at} - {self.end_at} ({self.minutes}m)"


class TimesheetStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    SUBMITTED = 'SUBMITTED', _('Submitted')
    APPROVED = 'APPROVED', _('Approved')
    PAID = 'PAID', _('Paid')


class Timesheet(models.Model):
    """Aggregate of approved worklogs for a period.

    Minimal fields for future phases; total minutes are recomputed on demand.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='timesheets',
        null=True,
        blank=True,
        help_text=_('Organization this timesheet belongs to')
    )
    lecturer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='timesheets')
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=12, choices=TimesheetStatus.choices, default=TimesheetStatus.OPEN)
    total_minutes = models.PositiveIntegerField(default=0)
    amount_minor = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tk_timesheets'
        unique_together = [['lecturer', 'period_start', 'period_end']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['lecturer', 'period_start', 'period_end'])
        ]


