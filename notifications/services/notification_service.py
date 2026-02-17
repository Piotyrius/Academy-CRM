"""
Notification service for managing notifications.
"""
from accounts.models import Role
from ..models import Notification, NotificationType


class NotificationService:
    """Service for notification operations."""
    
    @staticmethod
    def notify_cohort_ready(cohort):
        """
        Create notifications for all admins when a cohort is ready to start.
        
        Args:
            cohort: Cohort instance
        """
        from accounts.models import User
        
        # Get all admin users for the organization
        admins = User.objects.filter(
            role=Role.ADMIN,
            organization=cohort.organization,
            is_active=True
        )
        
        message = (
            f"Cohort '{cohort.name}' has reached the minimum enrollment threshold "
            f"({cohort.current_enrollment_count} students). It is ready to start."
        )
        
        # Create notification for each admin
        notifications = []
        for admin in admins:
            notification = Notification.objects.create(
                user=admin,
                notification_type=NotificationType.COHORT_READY,
                related_cohort=cohort,
                message=message
            )
            notifications.append(notification)
        
        return notifications
    
    @staticmethod
    def get_unread_notifications(user):
        """
        Get unread notifications for a user.
        
        Args:
            user: User instance
            
        Returns:
            QuerySet of Notification instances
        """
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).order_by('-created_at')
    
    @staticmethod
    def mark_as_read(notification_id, user):
        """
        Mark a notification as read.
        
        Args:
            notification_id: UUID of notification
            user: User instance
            
        Returns:
            Notification instance
        """
        from django.utils import timezone
        
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            return notification
        except Notification.DoesNotExist:
            return None






