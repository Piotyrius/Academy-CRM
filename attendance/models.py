"""
Attendance models for Academy CRM.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User, Role
from catalog.models import Session


class AttendanceStatus(models.TextChoices):
    """Attendance status choices."""
    PRESENT = 'PRESENT', _('Present')
    LATE = 'LATE', _('Late')
    ABSENT = 'ABSENT', _('Absent')


class AttendanceRecord(models.Model):
    """Attendance record model."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        limit_choices_to={'role': Role.STUDENT}
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.ABSENT
    )
    note = models.TextField(blank=True)
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marked_attendance',
        limit_choices_to={'role__in': [Role.ADMIN, Role.LECTURER]}
    )
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance_records'
        verbose_name = _('attendance record')
        verbose_name_plural = _('attendance records')
        unique_together = [['session', 'student']]
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['student']),
            models.Index(fields=['status']),
            models.Index(fields=['marked_at']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.session} ({self.get_status_display()})"