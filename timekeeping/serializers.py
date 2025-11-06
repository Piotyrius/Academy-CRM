from rest_framework import serializers
from .models import WorkLog, Rate, Timesheet


class RateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rate
        fields = ['id', 'lecturer', 'per_hour_minor', 'currency', 'active', 'created_at']
        read_only_fields = ['id', 'created_at']


class WorkLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLog
        fields = ['id', 'lecturer', 'session', 'start_at', 'end_at', 'minutes', 'source', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'source']


class TimesheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timesheet
        fields = ['id', 'lecturer', 'period_start', 'period_end', 'status', 'total_minutes', 'amount_minor', 'currency', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


