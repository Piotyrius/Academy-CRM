"""
Admissions models for Academy CRM.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User, Role
from catalog.models import Program, Cohort, Course


class ApplicationStatus(models.TextChoices):
    """Application status choices."""
    NEW = 'NEW', _('New')
    IN_REVIEW = 'IN_REVIEW', _('In Review')
    ACCEPTED = 'ACCEPTED', _('Accepted')
    REJECTED = 'REJECTED', _('Rejected')


class Application(models.Model):
    """Application model for student applications."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='applications',
        null=True,
        blank=True,
        help_text=_('Organization this application belongs to')
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='applications')
    schedule_pref = models.CharField(max_length=100, blank=True, help_text=_('Schedule preference'))
    experience_level = models.CharField(max_length=50, blank=True, help_text=_('Experience level'))
    referral_source = models.CharField(max_length=100, blank=True, help_text=_('How did you hear about us?'))
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.NEW
    )
    notes = models.TextField(blank=True)
    consent_ts = models.DateTimeField(auto_now_add=True, help_text=_('Consent timestamp'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'applications'
        verbose_name = _('application')
        verbose_name_plural = _('applications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['program']),
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.program.name} ({self.get_status_display()})"


class ApplicationPhone(models.Model):
    """
    Additional phone numbers for an application.

    This allows storing multiple named phone numbers (e.g. parent contacts)
    without breaking the existing single `phone` field on Application.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        related_name='phones',
        on_delete=models.CASCADE,
        help_text=_('Application this phone number belongs to'),
    )
    name = models.CharField(
        max_length=255,
        help_text=_('Contact name or relation, e.g. "Mother", "Father", "Guardian"'),
    )
    phone = models.CharField(
        max_length=20,
        help_text=_('Phone number for this contact'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'application_phones'
        verbose_name = _('application phone')
        verbose_name_plural = _('application phones')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['application']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone}) - {self.application_id}"


class EnrollmentStatus(models.TextChoices):
    """Enrollment status choices."""
    PENDING = 'PENDING', _('Pending')
    ACTIVE = 'ACTIVE', _('Active')
    WITHDRAWN = 'WITHDRAWN', _('Withdrawn')
    COMPLETED = 'COMPLETED', _('Completed')


class Enrollment(models.Model):
    """Enrollment model linking students to cohorts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='enrollments',
        null=True,
        blank=True,
        help_text=_('Organization this enrollment belongs to')
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': Role.STUDENT}
    )
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='enrollments')
    preferred_course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_enrollments',
        help_text=_('Preferred course (can be changed by admin before cohort starts)')
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enrollments'
        verbose_name = _('enrollment')
        verbose_name_plural = _('enrollments')
        ordering = ['-enrolled_at']
        unique_together = [['student', 'cohort']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['student']),
            models.Index(fields=['cohort']),
            models.Index(fields=['status']),
            models.Index(fields=['enrolled_at']),
            models.Index(fields=['student', 'status']),  # Composite index for common query pattern
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.cohort.name} ({self.get_status_display()})"