"""
Catalog models for Academy CRM.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from accounts.models import User, Role


class Program(models.Model):
    """Program model (e.g., Programming, Cybersecurity)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='programs',
        null=True,
        blank=True,
        help_text=_('Organization this program belongs to')
    )
    name = models.CharField(max_length=200, help_text=_('Program name'))
    code = models.CharField(max_length=50, help_text=_('Program code'))  # Removed unique=True, will be unique per org
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default='1.0', help_text=_('Program version'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'programs'
        verbose_name = _('program')
        verbose_name_plural = _('programs')
        ordering = ['name']
        unique_together = [['organization', 'code']]  # Code unique per organization
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['code']),
            models.Index(fields=['active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    """Course model (e.g., Frontend Development, Backend Development)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True,
        help_text=_('Organization this course belongs to')
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50, help_text=_('Course code'))
    hours = models.IntegerField(validators=[MinValueValidator(1)], help_text=_('Total course hours'))
    credits = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True, help_text=_('Course credits'))
    syllabus_version = models.CharField(max_length=20, default='1.0')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses'
        verbose_name = _('course')
        verbose_name_plural = _('courses')
        ordering = ['title']
        unique_together = [['program', 'code']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['program']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.code})"


class CohortStatus(models.TextChoices):
    """Cohort status choices."""
    PLANNED = 'PLANNED', _('Planned')
    ENROLLING = 'ENROLLING', _('Enrolling')
    ACTIVE = 'ACTIVE', _('Active')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class Cohort(models.Model):
    """Cohort model (a group of students taking a course together)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='cohorts',
        null=True,
        blank=True,
        help_text=_('Organization this cohort belongs to')
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='cohorts')
    name = models.CharField(max_length=200, help_text=_('Cohort name'))
    lecturer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cohorts',
        limit_choices_to={'role': Role.LECTURER}
    )
    capacity = models.IntegerField(validators=[MinValueValidator(1)], help_text=_('Maximum number of students'))
    start_date = models.DateField(help_text=_('Cohort start date'))
    end_date = models.DateField(help_text=_('Cohort end date'))
    status = models.CharField(
        max_length=20,
        choices=CohortStatus.choices,
        default=CohortStatus.PLANNED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cohorts'
        verbose_name = _('cohort')
        verbose_name_plural = _('cohorts')
        ordering = ['-start_date', 'name']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['course']),
            models.Index(fields=['lecturer']),
            models.Index(fields=['status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.course.title}"
    
    @property
    def current_enrollment_count(self):
        """Get current number of active enrollments."""
        return self.enrollments.filter(status='ACTIVE').count()
    
    @property
    def is_full(self):
        """Check if cohort is at capacity."""
        return self.current_enrollment_count >= self.capacity


class Session(models.Model):
    """Session model (individual class sessions)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True,
        help_text=_('Organization this session belongs to')
    )
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='sessions')
    start_at = models.DateTimeField(help_text=_('Session start time'))
    end_at = models.DateTimeField(help_text=_('Session end time'))
    location = models.CharField(max_length=200, blank=True, help_text=_('Physical location'))
    online_link = models.URLField(blank=True, help_text=_('Online meeting link'))
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sessions'
        verbose_name = _('session')
        verbose_name_plural = _('sessions')
        ordering = ['start_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['cohort']),
            models.Index(fields=['start_at']),
            models.Index(fields=['is_cancelled']),
            models.Index(fields=['cohort', 'start_at']),  # Composite index for common query pattern
        ]
    
    def __str__(self):
        return f"{self.cohort.name} - {self.start_at.strftime('%Y-%m-%d %H:%M')}"