"""
Models for student/lecturer works gallery.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class WorkStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    PUBLISHED = 'PUBLISHED', _('Published')


class Work(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='works')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media = models.FileField(upload_to='gallery/')
    status = models.CharField(max_length=10, choices=WorkStatus.choices, default=WorkStatus.DRAFT)
    is_public = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gallery_works'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['status', 'is_public']),
        ]

    def __str__(self):
        return self.title


