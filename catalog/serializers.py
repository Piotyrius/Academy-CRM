"""
Serializers for catalog app.
"""
from rest_framework import serializers
from .models import Program, Course, Cohort, Session, CohortStatus


class ProgramSerializer(serializers.ModelSerializer):
    """Serializer for Program model."""
    
    class Meta:
        model = Program
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CohortSerializer(serializers.ModelSerializer):
    """Serializer for Cohort model."""
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    lecturer_name = serializers.CharField(source='lecturer.get_full_name', read_only=True)
    lecturer_email = serializers.EmailField(source='lecturer.email', read_only=True)
    current_enrollment_count = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    def get_current_enrollment_count(self, obj):
        """Get enrollment count from annotation or property."""
        # Prefer annotated value if available
        if hasattr(obj, '_annotated_enrollment_count'):
            return obj._annotated_enrollment_count
        # Fallback to property
        return obj.current_enrollment_count
    
    def get_is_full(self, obj):
        """Check if cohort is full using annotated count or property."""
        count = self.get_current_enrollment_count(obj)
        return count >= obj.capacity
    
    class Meta:
        model = Cohort
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_enrollment_count', 'is_full']


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model."""
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    
    class Meta:
        model = Session
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
