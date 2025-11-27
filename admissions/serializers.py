"""
Serializers for admissions app.
"""
from rest_framework import serializers
from .models import (
    Application,
    Enrollment,
    ApplicationStatus,
    EnrollmentStatus,
    ApplicationPhone,
)
from accounts.models import User
from catalog.models import Program, Cohort


class ApplicationPhoneSerializer(serializers.ModelSerializer):
    """Serializer for additional application phone numbers."""

    class Meta:
        model = ApplicationPhone
        fields = ['id', 'name', 'phone', 'created_at']
        read_only_fields = ['id', 'created_at']


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""

    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    phones = ApplicationPhoneSerializer(many=True, required=False)

    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['id', 'consent_ts', 'created_at', 'updated_at']

    def create(self, validated_data):
        phones_data = validated_data.pop('phones', [])
        application = super().create(validated_data)

        # Create related phone records, if any
        for phone_data in phones_data:
            ApplicationPhone.objects.create(application=application, **phone_data)

        return application

    def update(self, instance, validated_data):
        phones_data = validated_data.pop('phones', None)
        application = super().update(instance, validated_data)

        if phones_data is not None:
            # Replace existing phone entries with the new list
            application.phones.all().delete()
            for phone_data in phones_data:
                ApplicationPhone.objects.create(application=application, **phone_data)

        return application


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
