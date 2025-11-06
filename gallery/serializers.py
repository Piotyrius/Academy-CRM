from rest_framework import serializers
from .models import Work, WorkStatus


class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['id', 'owner', 'title', 'description', 'media', 'status', 'is_public', 'published_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'published_at', 'created_at', 'updated_at']


