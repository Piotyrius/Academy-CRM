"""
Notifications models for Academy CRM (Phase 2 scaffold).
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    """Notification type choices."""
    COHORT_READY = 'COHORT_READY', _('Cohort Ready to Start')
    INVOICE_CREATED = 'INVOICE_CREATED', _('Invoice Created')
    PAYMENT_RECEIVED = 'PAYMENT_RECEIVED', _('Payment Received')
    PAYMENT_OVERDUE = 'PAYMENT_OVERDUE', _('Payment Overdue')
    OTHER = 'OTHER', _('Other')


class Notification(models.Model):
    """Notification model for user notifications."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,  # Temporarily nullable for migration, will be made required after migration
        blank=True,
        help_text=_('User who receives this notification')
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.OTHER,
        help_text=_('Type of notification')
    )
    related_cohort = models.ForeignKey(
        'catalog.Cohort',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        help_text=_('Related cohort (if applicable)')
    )
    message = models.TextField(default='', help_text=_('Notification message'))
    is_read = models.BooleanField(default=False, help_text=_('Whether notification has been read'))
    read_at = models.DateTimeField(null=True, blank=True, help_text=_('When notification was read'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.email}"