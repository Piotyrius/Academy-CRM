"""
Documents models for Academy CRM.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from storage.models import FileObject, FileOwnerType


class DocumentKind(models.TextChoices):
    """Document kind choices."""
    CONSENT = 'CONSENT', _('Consent Form')
    ID = 'ID', _('ID Document')
    OTHER = 'OTHER', _('Other')


class Document(models.Model):
    """Document model for file uploads."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
        help_text=_('Organization this document belongs to')
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    kind = models.CharField(
        max_length=20,
        choices=DocumentKind.choices,
        default=DocumentKind.OTHER
    )
    # Legacy file field kept for backwards compatibility; new uploads will
    # primarily use Google Drive via ``storage.FileObject`` when enabled.
    file = models.FileField(upload_to='documents/', blank=True)
    file_object = models.ForeignKey(
        FileObject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        help_text=_("Backed file object in Google Drive or other storage"),
    )
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=[
            ('PRIVATE', _('Private')),
            ('ADMIN', _('Admin Only')),
            ('LECTURER', _('Lecturer Visible')),
        ],
        default='PRIVATE'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents'
        verbose_name = _('document')
        verbose_name_plural = _('documents')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['owner']),
            models.Index(fields=['kind']),
        ]
    
    def __str__(self):
        return f"{self.owner.get_full_name()} - {self.get_kind_display()}"