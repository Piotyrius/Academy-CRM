"""
Views for notifications app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from subscriptions.mixins import OrganizationFilterMixin
from .models import Notification
from .serializers import NotificationSerializer
from .services.notification_service import NotificationService


class NotificationViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    """ViewSet for Notification model."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter notifications to current user only."""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @extend_schema(
        tags=['Notifications'],
        summary="List unread notifications",
        description="Get all unread notifications for the current user.",
        responses={
            200: {
                'type': 'array',
                'items': {'$ref': '#/components/schemas/Notification'}
            }
        }
    )
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications for current user."""
        notifications = NotificationService.get_unread_notifications(request.user)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Notifications'],
        summary="Mark notification as read",
        description="Mark a notification as read.",
        responses={
            200: NotificationSerializer,
            404: OpenApiTypes.OBJECT,
        }
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = NotificationService.mark_as_read(pk, request.user)
        if not notification:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Notifications'],
        summary="Mark all notifications as read",
        description="Mark all unread notifications for current user as read.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'marked': {'type': 'integer', 'description': 'Number of notifications marked as read'}
                }
            }
        }
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all unread notifications as read."""
        unread_notifications = NotificationService.get_unread_notifications(request.user)
        count = unread_notifications.update(is_read=True, read_at=timezone.now())
        return Response({'marked': count})
