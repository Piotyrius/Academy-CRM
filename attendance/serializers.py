"""
Serializers for attendance app.
"""
from rest_framework import serializers
from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceRecord model."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    session_cohort = serializers.CharField(source='session.cohort.name', read_only=True)
    session_start = serializers.DateTimeField(source='session.start_at', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.get_full_name', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = '__all__'
        read_only_fields = ['id', 'marked_at', 'updated_at']


class BulkAttendanceSerializer(serializers.Serializer):
    """Serializer for bulk attendance marking."""
    session_id = serializers.UUIDField()
    records = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
    
    def validate_records(self, value):
        """Validate records structure."""
        for record in value:
            if 'student_id' not in record or 'status' not in record:
                raise serializers.ValidationError("Each record must have 'student_id' and 'status'")
        return value
