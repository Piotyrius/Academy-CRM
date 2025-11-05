"""
Notifications models for Academy CRM (Phase 2 scaffold).
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """Notification model (minimal scaffold for Phase 2)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Placeholder for Phase 2
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')