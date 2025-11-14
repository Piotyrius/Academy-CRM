"""
Assessment models for Academy CRM.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User, Role
from catalog.models import Cohort


class AssessmentKind(models.TextChoices):
    """Assessment kind choices."""
    EXAM = 'EXAM', _('Exam')
    QUIZ = 'QUIZ', _('Quiz')
    PROJECT = 'PROJECT', _('Project')


class Assessment(models.Model):
    """Assessment model."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='assessments',
        null=True,
        blank=True,
        help_text=_('Organization this assessment belongs to')
    )
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=20,
        choices=AssessmentKind.choices,
        default=AssessmentKind.QUIZ
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Weight percentage (0-100)')
    )
    due_at = models.DateTimeField(help_text=_('Due date and time'))
    published = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assessments'
        verbose_name = _('assessment')
        verbose_name_plural = _('assessments')
        ordering = ['-due_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['cohort']),
            models.Index(fields=['due_at']),
            models.Index(fields=['published']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.cohort.name}"


class Submission(models.Model):
    """Submission model."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='submissions',
        null=True,
        blank=True,
        help_text=_('Organization this submission belongs to')
    )
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submissions',
        limit_choices_to={'role': Role.STUDENT}
    )
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='submissions/', blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    late_flag = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'submissions'
        verbose_name = _('submission')
        verbose_name_plural = _('submissions')
        unique_together = [['assessment', 'student']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['assessment']),
            models.Index(fields=['student']),
            models.Index(fields=['submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assessment.title}"


class Grade(models.Model):
    """Grade model."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='grades',
        null=True,
        blank=True,
        help_text=_('Organization this grade belongs to')
    )
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='grades')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='grades',
        limit_choices_to={'role': Role.STUDENT}
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Student score')
    )
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=100,
        help_text=_('Maximum possible score')
    )
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='graded_assessments',
        limit_choices_to={'role__in': [Role.ADMIN, Role.LECTURER]}
    )
    graded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grades'
        verbose_name = _('grade')
        verbose_name_plural = _('grades')
        unique_together = [['assessment', 'student']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['assessment']),
            models.Index(fields=['student']),
            models.Index(fields=['graded_at']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assessment.title}: {self.score}/{self.max_score}"
    
    @property
    def percentage(self):
        """Calculate percentage score."""
        if self.max_score == 0:
            return 0
        return (self.score / self.max_score) * 100