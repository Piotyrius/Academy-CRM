"""
Serializers for admissions app.
"""
from rest_framework import serializers
from .models import Application, Enrollment, ApplicationStatus, EnrollmentStatus
from accounts.models import User
from catalog.models import Program, Cohort


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['id', 'consent_ts', 'created_at', 'updated_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for Enrollment model."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    cohort_course = serializers.CharField(source='cohort.course.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ['id', 'enrolled_at', 'created_at', 'updated_at']
