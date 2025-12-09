"""
Models for student/lecturer works gallery.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from storage.models import FileObject, FileOwnerType


class WorkStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    PUBLISHED = 'PUBLISHED', _('Published')


class Work(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'subscriptions.Organization',
        on_delete=models.CASCADE,
        related_name='works',
        null=True,
        blank=True,
        help_text=_('Organization this work belongs to')
    )
    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='works')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Legacy media field; new uploads will use FileObject when Cloudinary is enabled.
    media = models.FileField(upload_to='gallery/', blank=True)
    file_object = models.ForeignKey(
        FileObject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_works",
        help_text=_("Backed file object in Cloudinary or other storage"),
    )
    status = models.CharField(max_length=10, choices=WorkStatus.choices, default=WorkStatus.DRAFT)
    is_public = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gallery_works'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['owner']),
            models.Index(fields=['status', 'is_public']),
        ]

    def __str__(self):
        return self.title


