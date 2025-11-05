"""
Certificates models for Academy CRM.
"""
import uuid
import secrets
from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User, Role
from catalog.models import Cohort


class CertificateStatus(models.TextChoices):
    """Certificate status choices."""
    ISSUED = 'ISSUED', _('Issued')
    REVOKED = 'REVOKED', _('Revoked')


class Certificate(models.Model):
    """Certificate model."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certificates',
        limit_choices_to={'role': Role.STUDENT}
    )
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='certificates')
    serial = models.CharField(max_length=100, unique=True, db_index=True, help_text=_('Certificate serial number'))
    qr_token = models.CharField(max_length=64, unique=True, db_index=True, help_text=_('QR code verification token'))
    pdf_file = models.FileField(upload_to='certificates/', blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=CertificateStatus.choices,
        default=CertificateStatus.ISSUED
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'certificates'
        verbose_name = _('certificate')
        verbose_name_plural = _('certificates')
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['cohort']),
            models.Index(fields=['serial']),
            models.Index(fields=['qr_token']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.cohort.name} ({self.serial})"
    
    def save(self, *args, **kwargs):
        """Generate serial and QR token if not set."""
        if not self.serial:
            self.serial = self._generate_serial()
        if not self.qr_token:
            self.qr_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    
    def _generate_serial(self):
        """Generate certificate serial number."""
        from django.utils import timezone
        year = timezone.now().year
        # Format: ACAD-YYYY-{increment}
        from django.db.models import Count
        count = Certificate.objects.filter(
            serial__startswith=f"ACAD-{year}-"
        ).count() + 1
        return f"ACAD-{year}-{count:05d}"