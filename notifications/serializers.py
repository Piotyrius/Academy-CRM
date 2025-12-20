"""
Serializers for notifications app.
"""
from rest_framework import serializers
from .models import Notification, NotificationType


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    related_cohort_name = serializers.CharField(source='related_cohort.name', read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'read_at']
    
    def update(self, instance, validated_data):
        """Update notification, specifically for marking as read."""
        from django.utils import timezone
        
        # If marking as read, set read_at timestamp
        if 'is_read' in validated_data and validated_data['is_read'] and not instance.is_read:
            validated_data['read_at'] = timezone.now()
        elif 'is_read' in validated_data and not validated_data['is_read']:
            validated_data['read_at'] = None
        
        return super().update(instance, validated_data)



